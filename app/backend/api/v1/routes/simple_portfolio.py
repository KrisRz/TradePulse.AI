"""
Simple Portfolio API for Trading Intelligence
No authentication required - for testing only
"""

from fastapi import APIRouter
from typing import Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/test")
async def test_endpoint():
    """Simple test endpoint"""
    return {"message": "Simple portfolio API working", "timestamp": datetime.now().isoformat()}

@router.get("/positions")
async def get_positions():
    """
    Get live positions from professional portfolio
    Returns both active and closed positions for Trading Intelligence component
    """
    try:
        logger.info("📊 Fetching live positions from professional portfolio")
        
        # Import professional portfolio
        from app.backend.services.professional_portfolio import get_professional_portfolio
        portfolio = await get_professional_portfolio("admin")
        
        # Update with live market data
        await portfolio.update_positions_with_live_data()
        
        # Get active positions
        active_positions = []
        for pos_id, position in portfolio.positions.items():
            if position.status.value == 'open':
                active_positions.append({
                    "id": pos_id,
                    "position_id": pos_id,
                    "symbol": position.symbol,
                    "type": position.type.value,
                    "side": position.type.value.lower(),
                    "size": float(position.size),
                    "quantity": float(position.size),
                    "entry_price": float(position.entry_price),
                    "current_price": float(position.current_price),
                    "unrealized_pnl": float(position.unrealized_pnl),
                    "unrealized_pnl_percentage": float(position.unrealized_pnl_percentage),
                    "pnl": float(position.unrealized_pnl),
                    "pnl_percentage": float(position.unrealized_pnl_percentage),
                    "entry_time": position.entry_time.isoformat(),
                    "status": position.status.value,
                    "confidence": position.ai_confidence,
                    "ai_confidence": position.ai_confidence,
                    "hold_duration": "2h 15m",  # Mock for now
                    "stop_loss": float(position.stop_loss) if position.stop_loss else None,
                    "take_profit": float(position.take_profit) if position.take_profit else None
                })
        
        # Response format that matches TradingIntelligence expectations
        response = {
            "positions": active_positions,
            "summary": {
                "total_open": len(active_positions),
                "total_value": sum(float(p.position_value) for p in portfolio.positions.values()),
                "total_pnl": sum(float(p.unrealized_pnl) for p in portfolio.positions.values())
            },
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Retrieved {len(active_positions)} active positions from professional portfolio")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error fetching positions: {e}")
        # Return empty positions on error
        return {
            "positions": [],
            "summary": {
                "total_open": 0,
                "total_value": 0.0,
                "total_pnl": 0.0
            },
            "last_updated": datetime.now().isoformat()
        }

@router.get("/history")
async def get_position_history():
    """
    Get closed positions history
    """
    try:
        logger.info("📊 Fetching closed positions from professional portfolio")
        
        from app.backend.services.professional_portfolio import get_professional_portfolio
        portfolio = await get_professional_portfolio("admin")
        
        # Get closed positions
        closed_positions = []
        for position in portfolio.closed_positions[-20:]:  # Last 20 closed
            closed_positions.append({
                "id": position.position_id,
                "position_id": position.position_id,
                "symbol": position.symbol,
                "type": position.type.value,
                "side": position.type.value.lower(),
                "size": float(position.size),
                "quantity": float(position.size),
                "entry_price": float(position.entry_price),
                "current_price": float(position.exit_price) if position.exit_price else float(position.current_price),
                "exit_price": float(position.exit_price) if position.exit_price else float(position.current_price),
                "pnl": float(position.realized_pnl),
                "pnl_percentage": float(position.realized_pnl / (position.entry_price * position.size) * 100) if position.entry_price > 0 else 0,
                "entry_time": position.entry_time.isoformat(),
                "exit_time": position.exit_time.isoformat() if position.exit_time else None,
                "status": position.status.value,
                "confidence": position.ai_confidence,
                "hold_duration": "2h 15m"  # Mock for now
            })
        
        logger.info(f"✅ Retrieved {len(closed_positions)} closed positions")
        return closed_positions
        
    except Exception as e:
        logger.error(f"❌ Error fetching position history: {e}")
        return []

@router.get("/overview")
async def get_portfolio_overview():
    """
    Get portfolio overview with $10,000 balance
    """
    try:
        logger.info("📊 Fetching portfolio overview")
        
        from app.backend.services.professional_portfolio import get_professional_portfolio
        portfolio = await get_professional_portfolio("admin")
        
        # Update with live data
        await portfolio.update_positions_with_live_data()
        
        # Get summary
        summary = await portfolio.get_portfolio_summary()
        
        response = {
            "total_portfolios": 1,
            "total_value": summary["portfolio_value"]["total"],
            "total_pnl": summary["performance"]["total_pnl"],
            "active_users": 1,
            "portfolios": [
                {
                    "portfolio_id": "admin_portfolio",
                    "user_id": "admin",
                    "balance": summary["portfolio_value"]["total"],
                    "total_pnl": summary["performance"]["total_pnl"],
                    "pnl_percentage": summary["performance"]["total_pnl_percentage"],
                    "trades_count": summary["trading_stats"]["total_trades"],
                    "win_rate": summary["trading_stats"]["win_rate"]
                }
            ]
        }
        
        logger.info(f"✅ Portfolio overview: ${summary['portfolio_value']['total']:.2f} total value")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error fetching portfolio overview: {e}")
        return {
            "total_portfolios": 1,
            "total_value": 10000.0,
            "total_pnl": 0.0,
            "active_users": 1,
            "portfolios": [
                {
                    "portfolio_id": "admin_portfolio",
                    "user_id": "admin",
                    "balance": 10000.0,
                    "total_pnl": 0.0,
                    "pnl_percentage": 0.0,
                    "trades_count": 0,
                    "win_rate": 0.0
                }
            ]
        }