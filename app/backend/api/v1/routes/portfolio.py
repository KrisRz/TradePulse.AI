"""
Portfolio Management API Routes for TradePulse.AI Admin Dashboard
Real DynamoDB integration for virtual portfolio data
"""

from fastapi import APIRouter, Depends, HTTPException, status
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, List
from datetime import datetime
import logging

# from api.v1.routes.auth import verify_production_jwt_token
from app.backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)
router = APIRouter()
# security = HTTPBearer()

# Initialize database service
database_service = DatabaseService()

# Authentication disabled for testing

@router.get("/virtual/overview")
async def get_virtual_portfolio_overview():
    """Get comprehensive virtual portfolio overview for admin dashboard (live)."""
    try:
        logger.info("📊 Admin requesting virtual portfolio overview (live)")

        # Live in-memory professional portfolio for real-time value
        from app.backend.services.professional_portfolio import get_professional_portfolio
        portfolio = await get_professional_portfolio("admin")
        await portfolio.update_positions_with_live_data()

        total_position_value = sum(float(p.position_value) for p in portfolio.positions.values())
        cash_balance = float(getattr(portfolio, "available_cash", 0.0))
        total_value = cash_balance + total_position_value
        active_positions = len([p for p in portfolio.positions.values() if p.status.value == 'open'])

        # Daily P&L: realized today + current unrealized on open positions (approx intraday)
        from datetime import datetime as _dt
        today = _dt.utcnow().date()
        realized_today = 0.0
        wins = 0
        losses = 0
        total_closed = 0
        for cp in getattr(portfolio, "closed_positions", [])[-200:]:
            total_closed += 1
            if cp.exit_time and cp.exit_time.date() == today:
                realized_today += float(cp.realized_pnl or 0.0)
            if (cp.realized_pnl or 0.0) > 0:
                wins += 1
            elif (cp.realized_pnl or 0.0) < 0:
                losses += 1

        unrealized_open = sum(float(p.unrealized_pnl) for p in portfolio.positions.values())
        daily_pnl = realized_today + unrealized_open
        daily_pnl_pct = (daily_pnl / total_value * 100.0) if total_value > 0 else 0.0
        win_rate = (wins / max(wins + losses, 1)) * 100.0

        # Also include DB overview (counts) if available
        db_overview = await database_service.get_all_virtual_portfolios()
        if isinstance(db_overview, dict):
            total_portfolios = db_overview.get('total_portfolios', 1)
        else:
            total_portfolios = 1

        response_data = {
            "total_portfolios": total_portfolios,
            "total_value": total_value,
            "total_pnl": daily_pnl,  # for backwards compatibility
            "cash_balance": cash_balance,
            "active_positions": active_positions,
            "daily_pnl": daily_pnl,
            "daily_pnl_percentage": daily_pnl_pct,
            "win_rate_today": win_rate,
            "avg_portfolio_size": total_value / max(total_portfolios, 1),
            "portfolios": [],
            "last_updated": datetime.now().isoformat()
        }

        logger.info(
            f"✅ Live portfolio overview: value=${total_value:,.2f}, cash=${cash_balance:,.2f}, open={active_positions}, daily_pnl=${daily_pnl:,.2f}"
        )
        return response_data

    except Exception as e:
        logger.error(f"❌ Error fetching portfolio overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch portfolio overview: {str(e)}"
        )

@router.get("/virtual/positions")
async def get_virtual_positions():
    """Get all virtual trading positions across all users"""
    try:
        logger.info(f"📊 Requesting virtual positions")
        
        # Read from the in-memory professional portfolio used by trading engine
        try:
            from app.backend.services.professional_portfolio import get_professional_portfolio
            portfolio = await get_professional_portfolio("admin")
            await portfolio.update_positions_with_live_data()

            open_positions = []
            for pos_id, position in portfolio.positions.items():
                if position.status.value == 'open':
                    open_positions.append({
                        "id": pos_id,
                        "position_id": pos_id,
                        "symbol": position.symbol,
                        "type": position.type.value,
                        "size": float(position.size),
                        "entry_price": float(position.entry_price),
                        "current_price": float(position.current_price),
                        "unrealized_pnl": float(position.unrealized_pnl),
                        "unrealized_pnl_percentage": float(position.unrealized_pnl_percentage),
                        "entry_time": position.entry_time.isoformat(),
                        "status": position.status.value,
                        "confidence": position.ai_confidence,
                        "current_value": float(position.position_value)
                    })

            closed_positions = []
            for position in portfolio.closed_positions[-20:]:
                closed_positions.append({
                    "id": position.position_id,
                    "position_id": position.position_id,
                    "symbol": position.symbol,
                    "type": position.type.value,
                    "size": float(position.size),
                    "entry_price": float(position.entry_price),
                    "current_price": float(position.exit_price) if position.exit_price else float(position.current_price),
                    "pnl": float(position.realized_pnl),
                    "pnl_percentage": float(position.realized_pnl / (position.entry_price * position.size) * 100) if position.entry_price * position.size != 0 else 0.0,
                    "entry_time": position.entry_time.isoformat(),
                    "exit_time": position.exit_time.isoformat() if position.exit_time else None,
                    "status": position.status.value,
                })

        except Exception as e:
            logger.error(f"Professional portfolio error: {e}")
            open_positions = []
            closed_positions = []
        
        response_data = {
            "positions": open_positions,  # Frontend expects "positions" key
            "closed_positions": closed_positions,  # Provide closed positions stream
            "summary": {
                "total_open": len(open_positions),
                "total_closed": len(closed_positions),
                "total_value": sum(p.get('current_value', 0) for p in open_positions),
                "total_pnl": sum(p.get('unrealized_pnl', 0) for p in open_positions)
            },
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Positions retrieved: {len(open_positions)} open, {len(closed_positions)} closed")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch positions: {str(e)}"
        )


@router.get("/virtual/closed")
async def get_virtual_closed_positions():
    """Get recent closed positions for the admin dashboard."""
    try:
        logger.info("📊 Requesting virtual closed positions")

        try:
            from app.backend.services.professional_portfolio import get_professional_portfolio
            portfolio = await get_professional_portfolio("admin")

            closed_positions = []
            for position in portfolio.closed_positions[-50:]:
                closed_positions.append({
                    "id": position.position_id,
                    "symbol": position.symbol,
                    "type": position.type.value,
                    "size": float(position.size),
                    "entry_price": float(position.entry_price),
                    "current_price": float(position.exit_price) if position.exit_price else float(position.current_price),
                    "pnl": float(position.realized_pnl),
                    "pnl_percentage": float(position.realized_pnl_percentage) if hasattr(position, 'realized_pnl_percentage') and position.realized_pnl_percentage is not None else 0.0,
                    "entry_time": position.entry_time.isoformat(),
                    "exit_time": position.exit_time.isoformat() if position.exit_time else None,
                    "status": position.status.value,
                })
        except Exception as e:
            logger.error(f"Professional portfolio error (closed): {e}")
            closed_positions = []

        return {
            "closed_positions": closed_positions,
            "count": len(closed_positions),
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Error fetching closed positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch closed positions: {str(e)}"
        )

@router.get("/virtual/performance")
async def get_portfolio_performance():
    """Get real portfolio performance analytics (derived from live/closed positions)."""
    try:
        logger.info("📊 Admin requesting portfolio performance (live)")

        from app.backend.services.professional_portfolio import get_professional_portfolio
        import math
        portfolio = await get_professional_portfolio("admin")
        await portfolio.update_positions_with_live_data()

        # Build returns series from recent closed trades (as % of entry value)
        returns = []
        equity_curve = []
        equity = 10000.0
        for cp in getattr(portfolio, "closed_positions", [])[-200:]:
            entry_val = float(cp.entry_price * cp.size)
            r = (float(cp.realized_pnl or 0.0) / entry_val) if entry_val > 0 else 0.0
            returns.append(r)
            equity *= (1.0 + r)
            equity_curve.append({"date": (cp.exit_time or cp.entry_time).isoformat(), "value": equity})

        # Sharpe using trade returns as proxy (not daily); scale by sqrt(N)
        if returns:
            mean_r = sum(returns) / len(returns)
            std_r = (sum((x - mean_r) ** 2 for x in returns) / max(len(returns) - 1, 1)) ** 0.5
            sharpe = (mean_r / std_r) * (len(returns) ** 0.5) if std_r > 0 else 0.0
            win_rate = (len([x for x in returns if x > 0]) / len(returns)) * 100.0
        else:
            sharpe = 0.0
            win_rate = 0.0

        response_data = {
            "overall_performance": {
                "total_return": (equity / 10000.0 - 1.0) * 100.0 if equity_curve else 0.0,
                "sharpe_ratio": sharpe,
                "max_drawdown": _compute_max_drawdown(equity_curve),
                "win_rate": win_rate,
                "profit_factor": _compute_profit_factor(getattr(portfolio, "closed_positions", [])[-200:])
            },
            "monthly_returns": [],
            "equity_curve": equity_curve,
            "risk_metrics": {},
            "last_updated": datetime.now().isoformat()
        }

        logger.info("✅ Performance (live) computed")
        return response_data

    except Exception as e:
        logger.error(f"❌ Error fetching performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch performance: {str(e)}"
        )


def _compute_max_drawdown(equity_curve: List[Dict[str, Any]]) -> float:
    try:
        if not equity_curve:
            return 0.0
        values = [pt["value"] for pt in equity_curve]
        peak = values[0]
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            dd = (v - peak) / peak if peak > 0 else 0.0
            if dd < max_dd:
                max_dd = dd
        return round(max_dd * 100.0, 2)
    except Exception:
        return 0.0


def _compute_profit_factor(closed_positions: List[Any]) -> float:
    try:
        gross_profit = 0.0
        gross_loss = 0.0
        for cp in closed_positions:
            pnl = float(getattr(cp, 'realized_pnl', 0.0))
            if pnl > 0:
                gross_profit += pnl
            elif pnl < 0:
                gross_loss += -pnl
        if gross_loss == 0:
            return round(gross_profit, 2) if gross_profit > 0 else 0.0
        return round(gross_profit / gross_loss, 2)
    except Exception:
        return 0.0

@router.get("/virtual/risk-metrics")
async def get_portfolio_risk_metrics():
    """Get comprehensive risk metrics for virtual portfolios"""
    try:
        logger.info(f"📊 Admin requesting portfolio risk metrics")
        
        # Get performance data which includes risk metrics
        performance_data = await database_service.get_portfolio_performance_metrics()
        risk_metrics = performance_data.get('risk_metrics', {})
        
        # Enhance with additional risk calculations
        response_data = {
            "portfolio_risk": {
                "volatility": risk_metrics.get('volatility', 0),
                "beta": risk_metrics.get('beta', 0),
                "var_95": risk_metrics.get('var_95', 0),
                "sortino_ratio": risk_metrics.get('sortino_ratio', 0),
                "max_drawdown": performance_data.get('max_drawdown', 0),
                "sharpe_ratio": performance_data.get('sharpe_ratio', 0)
            },
            "position_risk": {
                "concentration_risk": 15.5,  # % in largest position
                "sector_exposure": {"crypto": 100, "stocks": 0, "forex": 0},
                "leverage_ratio": 1.0,
                "correlation_btc": 0.95
            },
            "risk_limits": {
                "max_position_size": 20.0,  # % of portfolio
                "max_daily_loss": 5.0,  # % of portfolio
                "max_drawdown_limit": 15.0,  # %
                "risk_per_trade": 2.0  # %
            },
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info("✅ Risk metrics retrieved successfully")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching risk metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch risk metrics: {str(e)}"
        )

@router.post("/virtual/rebalance")
async def rebalance_portfolio(rebalance_data: Dict[str, Any]):
    """Trigger portfolio rebalancing (admin only)"""
    try:
        logger.info(f"📊 Admin triggering portfolio rebalance")
        
        # Validate rebalance request
        user_id = rebalance_data.get('user_id')
        strategy = rebalance_data.get('strategy', 'conservative')
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID is required for rebalancing"
            )
        
        # Log admin action
        await database_service.log_admin_action(
            'admin',
            'portfolio_rebalance',
            {'target_user': user_id, 'strategy': strategy}
        )
        
        # In production, this would trigger actual rebalancing
        response_data = {
            "message": "Portfolio rebalancing initiated",
            "user_id": user_id,
            "strategy": strategy,
            "estimated_completion": (datetime.now()).isoformat(),
            "rebalance_id": f"rebal_{int(datetime.now().timestamp())}",
            "status": "pending"
        }
        
        logger.info(f"✅ Portfolio rebalance initiated for user {user_id}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error initiating rebalance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate rebalance: {str(e)}"
        )

@router.get("/virtual/analytics")
async def get_portfolio_analytics():
    """Get detailed portfolio analytics and insights"""
    try:
        logger.info(f"📊 Admin requesting portfolio analytics")
        
        # Get all portfolios and positions for analytics
        portfolio_data = await database_service.get_all_virtual_portfolios()
        positions = await database_service.get_all_virtual_positions()
        performance_data = await database_service.get_portfolio_performance_metrics()
        
        # Extract portfolios list from the returned data structure
        portfolios = portfolio_data.get('portfolios', []) if isinstance(portfolio_data, dict) else []
        
        # Calculate advanced analytics
        total_users = len(portfolios)
        active_positions = [p for p in positions if p.get('status') == 'open']
        closed_positions = [p for p in positions if p.get('status') == 'closed']
        
        response_data = {
            "user_distribution": {
                "total_users": total_users,
                "active_traders": len([p for p in portfolios if p.get('status') == 'active']),
                "inactive_users": total_users - len([p for p in portfolios if p.get('status') == 'active']),
                "profitable_users": len([p for p in portfolios if p.get('total_pnl', 0) > 0]),
                "loss_making_users": len([p for p in portfolios if p.get('total_pnl', 0) < 0])
            },
            "position_analytics": {
                "total_positions": len(positions),
                "open_positions": len(active_positions),
                "closed_positions": len(closed_positions),
                "avg_position_duration": 4.5,  # hours
                "position_win_rate": len([p for p in closed_positions if p.get('pnl', 0) > 0]) / len(closed_positions) * 100 if closed_positions else 0
            },
            "performance_metrics": {
                "best_performer": max(portfolios, key=lambda x: x.get('total_pnl', 0)) if portfolios else None,
                "worst_performer": min(portfolios, key=lambda x: x.get('total_pnl', 0)) if portfolios else None,
                "avg_portfolio_return": sum(p.get('total_pnl', 0) for p in portfolios) / len(portfolios) if portfolios else 0,
                "total_volume": sum(p.get('balance', 0) for p in portfolios)
            },
            "risk_analysis": performance_data.get('risk_metrics', {}),
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info("✅ Portfolio analytics retrieved successfully")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching portfolio analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch portfolio analytics: {str(e)}"
        )

@router.get("/health")
async def portfolio_health():
    """Portfolio service health check"""
    return {
        "service": "portfolio_management",
        "status": "operational",
        "database": "dynamodb_local",
        "timestamp": datetime.now().isoformat()
    }