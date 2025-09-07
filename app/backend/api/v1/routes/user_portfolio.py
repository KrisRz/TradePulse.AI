"""
User Portfolio API Routes - TradePulse.AI
User-facing portfolio management endpoints for live trading data
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from app.backend.core.config import get_settings
from app.backend.core.logging import get_logger
from app.backend.utils.dependencies import get_current_user, User
# from app.backend.services.professional_portfolio import get_professional_portfolio

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


class PortfolioOverview(BaseModel):
    """User portfolio overview response"""
    user_id: str
    total_balance: float
    available_balance: float
    total_pnl: float
    total_pnl_percentage: float
    open_positions_count: int
    closed_positions_count: int
    win_rate: float
    daily_pnl: float
    last_updated: str


@router.get("/overview")
async def get_user_portfolio_overview() -> Dict[str, Any]:
    """
    Get user's portfolio overview with live data
    
    Returns:
        Portfolio overview with live metrics
    """
    try:
        logger.info("📊 User requesting portfolio overview")
        
        # Simple test response for now
        return {
            "user_id": "admin",
            "total_balance": 10000.0,
            "available_balance": 10000.0,
            "total_pnl": 0.0,
            "total_pnl_percentage": 0.0,
            "open_positions_count": 0,
            "closed_positions_count": 0,
            "win_rate": 0.0,
            "daily_pnl": 0.0,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "positions": {
                "open": [],
                "recent_closed": []
            },
            "status": "test_mode"
        }
        
    except Exception as e:
        logger.error(f"Failed to get portfolio overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get portfolio overview: {str(e)}"
        )


@router.get("/dashboard/overview")
async def get_user_dashboard_overview(current_user: User = Depends(get_current_user)):
    """Get comprehensive user dashboard overview with live data"""
    try:
        logger.info(f"📊 User {current_user.email} requesting dashboard overview")
        
        # Get data from Professional Portfolio Service for real-time accuracy
        from app.backend.services.professional_portfolio import get_professional_portfolio
        # For development, map enterprise_admin to admin portfolio where all data is
        user_id = "admin" if current_user.id in ["admin", "enterprise_admin"] or current_user.email == "admin@tradepulse.ai" else current_user.id
        portfolio = await get_professional_portfolio(user_id)
        await portfolio.update_positions_with_live_data()
        
        # Get portfolio summary
        summary = await portfolio.get_portfolio_summary()
        
        # Get market data for context - use same method as other endpoints
        from app.backend.services.binance_hybrid_client import get_live_price_hybrid
        price_data = await get_live_price_hybrid("BTCUSDT")
        btc_price = price_data.get("price", 0)
        
        # Calculate comprehensive dashboard metrics
        total_value = float(summary["portfolio_value"]["total"])
        cash_balance = float(summary["portfolio_value"]["cash"])
        daily_pnl = float(summary["performance"]["daily_pnl"])
        total_pnl = float(summary["performance"]["total_pnl"])
        
        # Position analysis
        open_positions = len([p for p in portfolio.positions.values() if p.status.value == 'open'])
        closed_positions = len(portfolio.closed_positions)
        
        # Performance metrics
        win_rate = float(summary["trading_stats"]["win_rate"])
        
        # Recent activity (last 24h)
        from datetime import timedelta
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        recent_trades = [
            p for p in portfolio.closed_positions 
            if p.exit_time and p.exit_time > yesterday
        ]
        
        response_data = {
            "user_profile": {
                "user_id": current_user.id,
                "email": current_user.email,
                "account_type": "professional",
                "member_since": current_user.created_at if hasattr(current_user, 'created_at') else datetime.now().isoformat()
            },
            "portfolio_snapshot": {
                "total_value": total_value,
                "cash_balance": cash_balance,
                "invested_amount": total_value - cash_balance,
                "daily_pnl": daily_pnl,
                "daily_pnl_percentage": (daily_pnl / 10000.0) * 100.0,
                "total_pnl": total_pnl,
                "total_pnl_percentage": (total_pnl / 10000.0) * 100.0
            },
            "trading_activity": {
                "active_positions": open_positions,
                "closed_positions": closed_positions,
                "total_trades": open_positions + closed_positions,
                "win_rate": win_rate,
                "trades_today": len(recent_trades),
                "pnl_today": sum(float(p.realized_pnl or 0) for p in recent_trades)
            },
            "market_context": {
                "btc_price": btc_price,
                "market_status": "open",
                "last_signal": "analyzing"
            },
            "quick_actions": {
                "can_trade": True,
                "brain_enabled": True,
                "notifications_enabled": True
            },
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Dashboard overview for {current_user.email}: ${total_value:.2f} portfolio")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching dashboard overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard overview: {str(e)}"
        )


@router.get("/positions")
async def get_user_positions(
    status_filter: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's trading positions
    
    Args:
        status_filter: Filter by position status (open, closed)
        limit: Maximum number of positions to return
        current_user: Authenticated user
        
    Returns:
        List of user positions
    """
    try:
        logger.info(f"📈 User {current_user.email} requesting positions (filter: {status_filter})")
        
        # Get professional portfolio for the user
        portfolio = await get_professional_portfolio(current_user.email)
        
        # Update with live market data
        await portfolio.update_positions_with_live_data()
        
        # Filter positions
        positions = portfolio.positions
        if status_filter:
            positions = [pos for pos in positions if pos.status == status_filter]
        
        # Limit results
        positions = positions[:limit]
        
        # Format positions for response
        formatted_positions = []
        for pos in positions:
            formatted_positions.append({
                "id": pos.position_id,
                "symbol": pos.symbol,
                "side": pos.side,
                "size": pos.size,
                "entry_price": pos.entry_price,
                "current_price": pos.current_price,
                "exit_price": pos.exit_price,
                "unrealized_pnl": pos.unrealized_pnl,
                "realized_pnl": pos.realized_pnl,
                "status": pos.status,
                "created_at": pos.created_at.isoformat() if pos.created_at else None,
                "closed_at": pos.closed_at.isoformat() if pos.closed_at else None
            })
        
        return {
            "positions": formatted_positions,
            "total_count": len(formatted_positions),
            "filter_applied": status_filter,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get positions for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get positions: {str(e)}"
        )


@router.get("/performance")
async def get_user_performance_metrics(
    period_days: int = 30,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's performance metrics
    
    Args:
        period_days: Number of days to analyze
        current_user: Authenticated user
        
    Returns:
        Performance metrics and analytics
    """
    try:
        logger.info(f"📊 User {current_user.email} requesting performance metrics ({period_days} days)")
        
        # Get professional portfolio for the user
        portfolio = await get_professional_portfolio(current_user.email)
        
        # Calculate performance metrics
        closed_positions = [pos for pos in portfolio.positions if pos.status == "closed"]
        
        if not closed_positions:
            return {
                "message": "No trading history available",
                "metrics": {
                    "total_trades": 0,
                    "win_rate": 0.0,
                    "avg_profit": 0.0,
                    "avg_loss": 0.0,
                    "profit_factor": 0.0,
                    "sharpe_ratio": 0.0
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Calculate metrics
        profitable_trades = [pos for pos in closed_positions if pos.realized_pnl > 0]
        losing_trades = [pos for pos in closed_positions if pos.realized_pnl < 0]
        
        total_trades = len(closed_positions)
        win_rate = len(profitable_trades) / total_trades * 100
        
        avg_profit = sum(pos.realized_pnl for pos in profitable_trades) / len(profitable_trades) if profitable_trades else 0.0
        avg_loss = abs(sum(pos.realized_pnl for pos in losing_trades) / len(losing_trades)) if losing_trades else 0.0
        
        total_profit = sum(pos.realized_pnl for pos in profitable_trades)
        total_loss = abs(sum(pos.realized_pnl for pos in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Simplified Sharpe ratio calculation
        returns = [pos.realized_pnl / portfolio.initial_balance for pos in closed_positions]
        avg_return = sum(returns) / len(returns)
        return_std = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        sharpe_ratio = avg_return / return_std if return_std > 0 else 0.0
        
        performance_metrics = {
            "total_trades": total_trades,
            "profitable_trades": len(profitable_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe_ratio,
            "total_pnl": sum(pos.realized_pnl for pos in closed_positions),
            "period_days": period_days
        }
        
        return {
            "metrics": performance_metrics,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )
