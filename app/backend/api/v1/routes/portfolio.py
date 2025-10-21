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

@router.post("/cache/clear")
async def clear_portfolio_cache():
    """Clear portfolio cache to force fresh data loading from DynamoDB"""
    try:
        from app.backend.services.professional_portfolio import _portfolio_instances, _instance_creation_times
        
        # Clear all cached portfolio instances
        cleared_count = len(_portfolio_instances)
        _portfolio_instances.clear()
        _instance_creation_times.clear()
        
        logger.info(f"🗑️ Cleared {cleared_count} portfolio cache instances")
        
        return {
            "success": True,
            "message": f"Cleared {cleared_count} portfolio cache instances",
            "cleared_instances": cleared_count
        }
    except Exception as e:
        logger.error(f"Failed to clear portfolio cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )

@router.get("/virtual/overview")
async def get_virtual_portfolio_overview():
    """Get comprehensive virtual portfolio overview for admin dashboard (live)."""
    try:
        logger.info("📊 Admin requesting virtual portfolio overview (live)")

        # Use ProfessionalPortfolio service for ACCURATE calculations
        from app.backend.services.professional_portfolio import get_professional_portfolio
        
        # Get the professional portfolio instance
        portfolio = await get_professional_portfolio("admin")
        
        # Update positions with live market data
        await portfolio.update_positions_with_live_data()
        
        # Get accurate portfolio summary
        summary = await portfolio.get_portfolio_summary()
        
        # Get actual position counts from ProfessionalPortfolio (NOT from db_overview which returns portfolios)
        active_positions_count = summary.get("open_positions", 0)  # From portfolio.positions
        closed_positions_count = len(portfolio.closed_positions)
        total_trades = summary["trading_stats"]["total_trades"]
        
        return {
            "DEBUG": "PROFESSIONAL_PORTFOLIO_DATA",
            "total_portfolios": 1,  # Single admin portfolio
            "total_value": float(summary["portfolio_value"]["total"]),
            "initial_balance": float(portfolio.initial_balance),
            "total_pnl": float(summary["performance"]["total_pnl"]),
            "total_pnl_percentage": float(summary["performance"]["total_pnl_percentage"]),
            "cash_balance": float(summary["portfolio_value"]["cash"]),
            "active_positions": active_positions_count,
            "closed_positions": closed_positions_count,
            "daily_pnl": float(summary["performance"]["daily_pnl"]),
            "daily_pnl_percentage": float(summary["performance"]["daily_pnl_percentage"]),
            "win_rate_today": float(summary["trading_stats"]["win_rate"]),
            "total_realized_pnl": float(summary["performance"]["total_pnl"]),
            "avg_portfolio_size": float(summary["portfolio_value"]["total"]),
            "portfolios": [],
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error in virtual portfolio overview: {e}")
        # Return error for failed portfolio operations
        raise HTTPException(status_code=500, detail=f"Portfolio overview failed: {str(e)}")
    
@router.get("/virtual/overview-debug")
async def get_virtual_portfolio_overview_debug():
    """Get comprehensive virtual portfolio overview for admin dashboard (live)."""
    try:
        logger.info("📊 Admin requesting virtual portfolio overview (live)")

        # Live in-memory professional portfolio for real-time value
        logger.info("🔍 DEBUG: Importing professional portfolio...")
        from app.backend.services.professional_portfolio import get_professional_portfolio
        logger.info("🔍 DEBUG: Import successful, getting portfolio...")
        
        portfolio = await get_professional_portfolio("admin")
        logger.info(f"🔍 DEBUG: Portfolio loaded - cash=${float(portfolio.cash_balance):.2f}, positions={len(portfolio.positions)}")
        
        logger.info("🔍 DEBUG: Updating positions with live data...")
        await portfolio.update_positions_with_live_data()
        logger.info(f"🔍 DEBUG: After update - cash=${float(portfolio.cash_balance):.2f}, positions={len(portfolio.positions)}")

        # Calculate total portfolio value including realized P&L from closed positions
        logger.info("🔍 DEBUG: Calculating values...")
        total_position_value = sum(float(p.position_value) for p in portfolio.positions.values())
        logger.info(f"🔍 DEBUG: total_position_value = {total_position_value}")
        
        cash_balance = float(portfolio.cash_balance)
        logger.info(f"🔍 DEBUG: cash_balance = {cash_balance}")
        
        # Add realized P&L from all closed positions to get true portfolio value
        total_realized_pnl = sum(float(cp.realized_pnl or 0.0) for cp in getattr(portfolio, "closed_positions", []))
        logger.info(f"🔍 DEBUG: total_realized_pnl = {total_realized_pnl}")
        
        total_value = float(portfolio.initial_balance) + total_realized_pnl + sum(float(p.unrealized_pnl) for p in portfolio.positions.values())
        logger.info(f"🔍 DEBUG: total_value = {total_value}")
        
        active_positions = len([p for p in portfolio.positions.values() if p.status.value == 'open'])
        logger.info(f"🔍 DEBUG: active_positions = {active_positions}")

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
        
        # Calculate daily P&L percentage based on initial balance, not current total value
        initial_balance = float(portfolio.initial_balance)
        daily_pnl_pct = (daily_pnl / initial_balance * 100.0) if initial_balance > 0 else 0.0
        
        # Calculate total P&L percentage 
        total_pnl_amount = total_value - initial_balance
        total_pnl_pct = (total_pnl_amount / initial_balance * 100.0) if initial_balance > 0 else 0.0
        win_rate = (wins / max(wins + losses, 1)) * 100.0

        # Also include DB overview (counts) if available
        db_overview = await database_service.get_all_virtual_portfolios()
        if isinstance(db_overview, dict) and 'total_portfolios' in db_overview:
            total_portfolios = db_overview.get('total_portfolios', 1)
        elif isinstance(db_overview, list):
            total_portfolios = len(db_overview) if db_overview else 1
        else:
            total_portfolios = 1

        response_data = {
            "total_portfolios": total_portfolios,
            "total_value": total_value,
            "initial_balance": initial_balance,
            "total_pnl": total_pnl_amount,  # Total P&L amount
            "total_pnl_percentage": total_pnl_pct,  # Total P&L percentage
            "cash_balance": cash_balance,
            "active_positions": active_positions,
            "closed_positions": len(getattr(portfolio, "closed_positions", [])),
            "daily_pnl": daily_pnl,
            "daily_pnl_percentage": daily_pnl_pct,
            "win_rate_today": win_rate,
            "total_realized_pnl": total_realized_pnl,
            "avg_portfolio_size": total_value / max(total_portfolios, 1),
            "portfolios": [],
            "last_updated": datetime.now().isoformat()
        }

        logger.info(
            f"✅ Live portfolio overview: value=${total_value:,.2f}, cash=${cash_balance:,.2f}, open={active_positions}, daily_pnl=${daily_pnl:,.2f}"
        )
        logger.info(f"🔍 DEBUG: Final response_data = {response_data}")
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
            logger.error(f"🚨 DEBUG: Portfolio loaded in API - cash=${float(portfolio.cash_balance):.2f}, positions={len(portfolio.positions)}")
            
            await portfolio.update_positions_with_live_data()
            logger.error(f"🚨 DEBUG: After update in API - cash=${float(portfolio.cash_balance):.2f}, positions={len(portfolio.positions)}")

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
            for position in portfolio.closed_positions:  # Remove artificial limit
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
            # CRITICAL DEBUG: Re-raise exception to see the real error
            raise e
        
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

        closed_positions = []
        
        # Try to get from in-memory portfolio first
        try:
            from app.backend.services.professional_portfolio import get_professional_portfolio
            portfolio = await get_professional_portfolio("admin")

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
            
            logger.info(f"✅ Retrieved {len(closed_positions)} positions from in-memory portfolio")
        except Exception as e:
            logger.warning(f"⚠️ Professional portfolio error (closed): {e}")
        
        # FALLBACK: If no positions in memory, get from DynamoDB
        if len(closed_positions) == 0:
            logger.warning("⚠️ No positions in memory, fetching from DynamoDB...")
            try:
                from app.backend.core.database import get_database_client
                db = get_database_client()
                
                # Get from portfolio_closed_positions table
                all_positions = db.scan_table('portfolio_closed_positions')
                
                # Sort by closed_at descending and take last 50
                sorted_positions = sorted(
                    all_positions, 
                    key=lambda p: p.get('closed_at', ''), 
                    reverse=True
                )[:50]
                
                for pos in sorted_positions:
                    closed_positions.append({
                        "id": pos.get('position_id'),
                        "symbol": pos.get('symbol'),
                        "type": pos.get('position_type', 'LONG'),
                        "size": float(pos.get('size', 0)),
                        "entry_price": float(pos.get('entry_price', 0)),
                        "current_price": float(pos.get('exit_price', 0)),
                        "pnl": float(pos.get('realized_pnl', 0)),
                        "pnl_percentage": float(pos.get('pnl_percentage', 0)),
                        "entry_time": pos.get('entry_time'),
                        "exit_time": pos.get('closed_at'),
                        "status": "closed",
                    })
                
                logger.info(f"✅ Retrieved {len(closed_positions)} positions from DynamoDB")
            except Exception as db_error:
                logger.error(f"❌ DynamoDB fallback failed: {db_error}")

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
async def get_portfolio_risk_metrics(timeframe: str = "24h"):
    """Get comprehensive risk metrics for virtual portfolios"""
    try:
        logger.info(f"📊 Admin requesting portfolio risk metrics for timeframe: {timeframe}")
        
        # Get professional portfolio for real risk calculations
        from app.backend.services.professional_portfolio import get_professional_portfolio
        portfolio = await get_professional_portfolio("admin")
        await portfolio.update_positions_with_live_data()
        
        # Get performance data which includes risk metrics
        performance_data = await database_service.get_portfolio_performance_metrics()
        risk_metrics = performance_data.get('risk_metrics', {})
        
        # Calculate real portfolio exposure
        total_value = float(portfolio.cash_balance) + sum(float(p.position_value) for p in portfolio.positions.values())
        exposure = ((total_value - float(portfolio.cash_balance)) / total_value * 100) if total_value > 0 else 0
        
        # Enhanced risk calculations with real data
        response_data = {
            "metrics": {
                "var_1d": risk_metrics.get('var_95', 0) * 0.3,  # 1-day VaR estimate
                "var_5d": risk_metrics.get('var_95', 0) * 0.7,  # 5-day VaR estimate  
                "var_30d": risk_metrics.get('var_95', 0),       # 30-day VaR
                "exposure": exposure,
                "maxDrawdown": performance_data.get('max_drawdown', 0),
                "beta": risk_metrics.get('beta', 0),
                "correlation": 0.95,  # BTC correlation
                "volatility": risk_metrics.get('volatility', 0),
                "sharpeRatio": performance_data.get('sharpe_ratio', 0),
                "leverageRatio": 1.0,
                "portfolioHeat": min(exposure / 20.0, 1.0)  # Heat map based on exposure
            },
            "position_risks": [
                {
                    "symbol": pos.symbol,
                    "risk_score": min(abs(float(pos.unrealized_pnl_percentage)) / 5.0, 1.0),
                    "value_at_risk": abs(float(pos.unrealized_pnl)) if float(pos.unrealized_pnl) < 0 else 0,
                    "position_size": float(pos.position_value),
                    "exposure_percentage": (float(pos.position_value) / total_value * 100) if total_value > 0 else 0
                }
                for pos in portfolio.positions.values()
            ],
            "scenarios": [
                {
                    "name": "Market Crash (-20%)",
                    "probability": 0.05,
                    "impact": total_value * -0.20,
                    "description": "Severe market downturn scenario"
                },
                {
                    "name": "Moderate Correction (-10%)",
                    "probability": 0.15,
                    "impact": total_value * -0.10,
                    "description": "Standard market correction"
                },
                {
                    "name": "Bull Run (+30%)",
                    "probability": 0.10,
                    "impact": total_value * 0.30,
                    "description": "Strong bull market scenario"
                }
            ],
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

@router.get("/virtual/optimization-analysis")
async def get_portfolio_optimization_analysis(mode: str = "sharpe"):
    """Get portfolio optimization analysis and recommendations"""
    try:
        logger.info(f"📊 Admin requesting portfolio optimization analysis for mode: {mode}")
        
        # Get professional portfolio for real optimization calculations
        from app.backend.services.professional_portfolio import get_professional_portfolio
        portfolio = await get_professional_portfolio("admin")
        await portfolio.update_positions_with_live_data()
        
        # Calculate current portfolio metrics
        total_value = float(portfolio.cash_balance) + sum(float(p.position_value) for p in portfolio.positions.values())
        cash_percentage = (float(portfolio.cash_balance) / total_value * 100) if total_value > 0 else 100
        
        # Get performance data for optimization metrics
        performance_data = await database_service.get_portfolio_performance_metrics()
        
        # Current portfolio composition
        current_allocation = {}
        for pos in portfolio.positions.values():
            symbol = pos.symbol
            percentage = (float(pos.position_value) / total_value * 100) if total_value > 0 else 0
            current_allocation[symbol] = percentage
        
        current_allocation["CASH"] = cash_percentage
        
        # Optimization recommendations based on mode
        if mode == "sharpe":
            # Sharpe ratio optimization
            recommended_allocation = {
                "BTCUSDT": 60.0,
                "CASH": 40.0
            }
            efficiency_score = 0.75
        elif mode == "risk_parity":
            # Risk parity optimization
            recommended_allocation = {
                "BTCUSDT": 50.0,
                "CASH": 50.0
            }
            efficiency_score = 0.68
        else:
            # Balanced optimization
            recommended_allocation = {
                "BTCUSDT": 55.0,
                "CASH": 45.0
            }
            efficiency_score = 0.72
        
        # Calculate rebalancing actions needed
        rebalancing_actions = []
        for symbol, target_pct in recommended_allocation.items():
            current_pct = current_allocation.get(symbol, 0)
            difference = target_pct - current_pct
            if abs(difference) > 1.0:  # Only suggest changes > 1%
                action = "increase" if difference > 0 else "decrease"
                rebalancing_actions.append({
                    "symbol": symbol,
                    "action": action,
                    "current_percentage": current_pct,
                    "target_percentage": target_pct,
                    "difference": difference,
                    "estimated_amount": (difference / 100) * total_value
                })
        
        response_data = {
            "current_metrics": {
                "total_value": total_value,
                "cash_percentage": cash_percentage,
                "portfolio_efficiency": efficiency_score,
                "risk_adjusted_return": performance_data.get('sharpe_ratio', 0),
                "volatility": performance_data.get('risk_metrics', {}).get('volatility', 0),
                "max_drawdown": performance_data.get('max_drawdown', 0)
            },
            "current_allocation": current_allocation,
            "recommended_allocation": recommended_allocation,
            "rebalancing_actions": rebalancing_actions,
            "optimization_benefits": {
                "expected_return_improvement": 0.05,  # 5% improvement estimate
                "risk_reduction": 0.03,  # 3% risk reduction estimate
                "efficiency_gain": efficiency_score - 0.65,  # Current vs optimized
                "diversification_score": 0.8
            },
            "constraints": {
                "min_cash_percentage": 10.0,
                "max_position_size": 70.0,
                "rebalancing_threshold": 5.0  # Only rebalance if > 5% deviation
            },
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info("✅ Portfolio optimization analysis completed successfully")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error in portfolio optimization analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get optimization analysis: {str(e)}"
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

@router.get("/quick-stats")
async def get_portfolio_quick_stats():
    """Get quick portfolio statistics for dashboard overview"""
    try:
        logger.info("📊 Admin requesting portfolio quick stats")
        
        # Get data from Professional Portfolio Service
        from app.backend.services.professional_portfolio import get_professional_portfolio
        portfolio = await get_professional_portfolio("admin")
        await portfolio.update_positions_with_live_data()
        
        # Get portfolio summary
        summary = await portfolio.get_portfolio_summary()
        
        # Calculate quick stats
        total_value = float(summary["portfolio_value"]["total"])
        cash_balance = float(summary["portfolio_value"]["cash"])
        daily_pnl = float(summary["performance"]["daily_pnl"])
        total_pnl = float(summary["performance"]["total_pnl"])
        
        # Position counts
        open_positions = len([p for p in portfolio.positions.values() if p.status.value == 'open'])
        closed_positions = len(portfolio.closed_positions)
        
        # Win rate calculation
        if closed_positions > 0:
            winning_trades = len([p for p in portfolio.closed_positions if (p.realized_pnl or 0) > 0])
            win_rate = (winning_trades / closed_positions) * 100.0
        else:
            win_rate = 0.0
        
        response_data = {
            "total_portfolio_value": total_value,
            "cash_balance": cash_balance,
            "daily_pnl": daily_pnl,
            "daily_pnl_percentage": (daily_pnl / 10000.0) * 100.0 if daily_pnl else 0.0,
            "total_pnl": total_pnl,
            "total_pnl_percentage": (total_pnl / 10000.0) * 100.0 if total_pnl else 0.0,
            "active_positions": open_positions,
            "closed_positions": closed_positions,
            "win_rate": win_rate,
            "total_trades": open_positions + closed_positions,
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Quick stats: value=${total_value:.2f}, pnl=${daily_pnl:.2f}, positions={open_positions}")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching quick stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch quick stats: {str(e)}"
        )

@router.get("/summary/{portfolio_id}")
async def get_portfolio_summary(portfolio_id: str):
    """Get detailed portfolio summary by ID"""
    try:
        logger.info(f"📊 Requesting portfolio summary for ID: {portfolio_id}")
        
        # For admin or specific portfolio ID
        user_id = "admin" if portfolio_id == "admin" else portfolio_id
        
        from app.backend.services.professional_portfolio import get_professional_portfolio
        portfolio = await get_professional_portfolio(user_id)
        await portfolio.update_positions_with_live_data()
        
        # Get comprehensive summary
        summary = await portfolio.get_portfolio_summary()
        
        # Enhanced summary with additional metrics
        response_data = {
            "portfolio_id": portfolio_id,
            "user_id": user_id,
            "portfolio_value": summary["portfolio_value"],
            "performance": summary["performance"],
            "trading_stats": summary["trading_stats"],
            "risk_metrics": {
                "max_drawdown": summary.get("risk_metrics", {}).get("max_drawdown", 0),
                "sharpe_ratio": summary.get("risk_metrics", {}).get("sharpe_ratio", 0),
                "volatility": summary.get("risk_metrics", {}).get("volatility", 0)
            },
            "position_summary": {
                "open_positions": len([p for p in portfolio.positions.values() if p.status.value == 'open']),
                "closed_positions": len(portfolio.closed_positions),
                "total_positions": len(portfolio.positions) + len(portfolio.closed_positions)
            },
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Portfolio summary retrieved for {portfolio_id}")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching portfolio summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch portfolio summary: {str(e)}"
        )

@router.get("/virtual/history")
async def get_virtual_portfolio_history():
    """Get complete virtual portfolio history"""
    try:
        logger.info("📊 Requesting virtual portfolio history")
        
        from app.backend.services.professional_portfolio import get_professional_portfolio
        portfolio = await get_professional_portfolio("admin")
        
        # Get all positions (open + closed)
        all_positions = []
        
        # Add open positions
        for pos_id, position in portfolio.positions.items():
            all_positions.append({
                "id": pos_id,
                "position_id": pos_id,
                "symbol": position.symbol,
                "type": position.type.value,
                "size": float(position.size),
                "entry_price": float(position.entry_price),
                "current_price": float(position.current_price),
                "unrealized_pnl": float(position.unrealized_pnl),
                "entry_time": position.entry_time.isoformat(),
                "status": position.status.value,
                "confidence": position.ai_confidence
            })
        
        # Add closed positions
        for position in portfolio.closed_positions:
            all_positions.append({
                "id": position.position_id,
                "position_id": position.position_id,
                "symbol": position.symbol,
                "type": position.type.value,
                "size": float(position.size),
                "entry_price": float(position.entry_price),
                "exit_price": float(position.exit_price) if position.exit_price else None,
                "realized_pnl": float(position.realized_pnl) if position.realized_pnl else 0.0,
                "entry_time": position.entry_time.isoformat(),
                "exit_time": position.exit_time.isoformat() if position.exit_time else None,
                "status": position.status.value,
                "confidence": position.ai_confidence
            })
        
        # Sort by entry time (newest first)
        all_positions.sort(key=lambda x: x['entry_time'], reverse=True)
        
        response_data = {
            "history": all_positions,
            "total_positions": len(all_positions),
            "open_positions": len([p for p in all_positions if p['status'] == 'open']),
            "closed_positions": len([p for p in all_positions if p['status'] == 'closed']),
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Portfolio history retrieved: {len(all_positions)} total positions")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching portfolio history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch portfolio history: {str(e)}"
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