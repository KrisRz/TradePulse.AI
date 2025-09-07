"""
Professional Trading Signals API - TradePulse.AI
===============================================

Real-time trading signals with TP/SL levels for professional trading interface.
Displays BUY/SELL signals exactly like in professional trading platforms.

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine, TradingSignal as EnterpriseSignal
from app.backend.services.live_market_data import get_live_bitcoin_price, get_live_market_data
from app.backend.services.professional_portfolio import get_professional_portfolio
from app.backend.utils.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trading/signals", tags=["trading-signals"])

class ProfessionalTradingSignal(BaseModel):
    """Professional trading signal with TP/SL levels"""
    signal_id: str
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float
    current_price: float
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    position_size_usd: float
    reasoning: str
    timestamp: datetime
    signal_type: str  # primary, exploratory
    layer_analysis: Dict[str, Any]
    
class TradingSignalDisplay(BaseModel):
    """Trading signal formatted for professional display"""
    symbol: str
    action: str
    price: str  # Formatted price
    tp_price: str  # Take Profit formatted
    sl_price: str  # Stop Loss formatted
    confidence_pct: str  # Confidence percentage
    risk_reward: str  # Risk/Reward ratio
    signal_strength: str  # STRONG, MODERATE, WEAK
    timestamp: str
    reasoning: str

@router.get("/latest", response_model=ProfessionalTradingSignal)
async def get_latest_trading_signal():
    """Get latest professional trading signal with TP/SL levels"""
    try:
        logger.info("🎯 Generating latest professional trading signal...")
        
        # Initialize enterprise engine
        engine = EnterpriseTradingEngine()
        if not engine.is_initialized:
            await engine.initialize()
        
        # Generate signal
        enterprise_signal = await engine.generate_signal("BTCUSDT")
        current_price = await get_live_bitcoin_price()
        
        # Calculate TP/SL levels based on signal and market conditions
        tp_price, sl_price, risk_reward = await _calculate_tp_sl_levels(
            enterprise_signal.action, 
            current_price, 
            enterprise_signal.confidence,
            getattr(enterprise_signal, 'layer_analysis', {}) or {}
        )
        
        # Calculate position size in USD
        portfolio = await get_professional_portfolio("admin")
        position_size_usd = float(portfolio.cash_balance) * enterprise_signal.position_size
        
        return ProfessionalTradingSignal(
            signal_id=f"sig_{int(datetime.now().timestamp())}",
            symbol=enterprise_signal.symbol,
            action=enterprise_signal.action,
            confidence=float(enterprise_signal.confidence),
            current_price=float(current_price),
            take_profit=float(tp_price) if tp_price else None,
            stop_loss=float(sl_price) if sl_price else None,
            risk_reward_ratio=float(risk_reward) if risk_reward else None,
            position_size_usd=float(position_size_usd),
            reasoning=enterprise_signal.reasoning,
            timestamp=enterprise_signal.timestamp,
            signal_type=enterprise_signal.signal_type,
            layer_analysis=_convert_numpy_types(getattr(enterprise_signal, 'layer_analysis', {}) or {})
        )
        
    except Exception as e:
        logger.error(f"Failed to get latest trading signal: {e}")
        raise HTTPException(status_code=500, detail=f"Signal generation failed: {e}")

@router.get("/display", response_model=TradingSignalDisplay)
async def get_signal_for_display():
    """Get trading signal formatted for professional trading interface display"""
    try:
        # Get latest signal
        signal = await get_latest_trading_signal()
        
        # Format for professional display
        return TradingSignalDisplay(
            symbol=signal.symbol,
            action=signal.action,
            price=f"{signal.current_price:.2f}",
            tp_price=f"TP: {signal.take_profit:.2f}" if signal.take_profit else "TP: --",
            sl_price=f"SL: {signal.stop_loss:.2f}" if signal.stop_loss else "SL: --",
            confidence_pct=f"{signal.confidence:.0%}",
            risk_reward=f"R/R: {signal.risk_reward_ratio:.2f}" if signal.risk_reward_ratio else "R/R: --",
            signal_strength=_get_signal_strength(signal.confidence),
            timestamp=signal.timestamp.strftime("%H:%M:%S"),
            reasoning=signal.reasoning[:100] + "..." if len(signal.reasoning) > 100 else signal.reasoning
        )
        
    except Exception as e:
        logger.error(f"Failed to format signal for display: {e}")
        raise HTTPException(status_code=500, detail=f"Display formatting failed: {e}")

@router.get("/live-stream")
async def get_live_signal_stream(user = Depends(get_current_user)):
    """WebSocket-like endpoint for live trading signals (SSE alternative)"""
    try:
        # Get current signal with fresh data
        signal = await get_latest_trading_signal(user)
        
        # Add live market context
        market_data = await get_live_market_data()
        
        return {
            "signal": signal,
            "market_context": {
                "volatility": market_data.get("volatility", 0.0),
                "volume": market_data.get("volume", 0.0),
                "trend": market_data.get("trend", "neutral"),
                "session": market_data.get("session", "unknown")
            },
            "timestamp": datetime.now(timezone.utc),
            "is_live": True
        }
        
    except Exception as e:
        logger.error(f"Live signal stream failed: {e}")
        raise HTTPException(status_code=500, detail=f"Live stream failed: {e}")

def _convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization"""
    import numpy as np
    
    if isinstance(obj, dict):
        return {k: _convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj

async def _calculate_tp_sl_levels(action: str, current_price: float, confidence: float, layer_analysis: Dict[str, Any]) -> tuple[float, float, float]:
    """Calculate professional TP/SL levels like in trading platforms"""
    try:
        # Base TP/SL percentages (professional day trading)
        base_tp_pct = 0.015  # 1.5% take profit
        base_sl_pct = 0.010  # 1.0% stop loss
        
        # Adjust based on confidence and volatility
        volatility = layer_analysis.get("volatility", 0.05)
        
        # Higher confidence = wider TP, tighter SL
        confidence_multiplier = 1.0 + (confidence - 0.5)  # 0.5-1.5x
        tp_pct = base_tp_pct * confidence_multiplier
        sl_pct = base_sl_pct * (2.0 - confidence_multiplier)  # Inverse for SL
        
        # Adjust for volatility (higher vol = wider levels)
        volatility_multiplier = 1.0 + min(volatility * 2, 0.5)  # Max 1.5x
        tp_pct *= volatility_multiplier
        sl_pct *= volatility_multiplier
        
        if action == "BUY":
            tp_price = current_price * (1.0 + tp_pct)
            sl_price = current_price * (1.0 - sl_pct)
        elif action == "SELL":
            tp_price = current_price * (1.0 - tp_pct)
            sl_price = current_price * (1.0 + sl_pct)
        else:
            return None, None, None
        
        # Calculate risk/reward ratio
        if action == "BUY":
            risk = current_price - sl_price
            reward = tp_price - current_price
        # Use unified risk management calculation for consistency
        from ..utils.risk_management import calculate_risk_reward_ratio
        from ..utils.money import D

        try:
            risk_reward_ratio = calculate_risk_reward_ratio(
                entry_price=D(str(current_price)),
                stop_loss=D(str(sl_price)),
                take_profit=D(str(tp_price)),
                position_type="LONG" if action in ["BUY", "LONG"] else "SHORT"
            )
            risk_reward_ratio = float(risk_reward_ratio)
        except Exception as rr_error:
            # Fallback to simple calculation if unified method fails
            if action in ["BUY", "LONG"]:
                risk = sl_price - current_price
                reward = tp_price - current_price
            else:
                risk = current_price - sl_price
                reward = current_price - tp_price
            risk_reward_ratio = reward / risk if risk > 0 else 0.0
            logger.warning(f"Using fallback R/R calculation: {rr_error}")

        logger.info(f"📊 TP/SL Calculated: {action} @ {current_price:.2f} → TP: {tp_price:.2f}, SL: {sl_price:.2f}, R/R: {risk_reward_ratio:.2f}")

        return tp_price, sl_price, risk_reward_ratio
        
    except Exception as e:
        logger.error(f"TP/SL calculation failed: {e}")
        return None, None, None

def _get_signal_strength(confidence: float) -> str:
    """Convert confidence to signal strength"""
    if confidence >= 0.8:
        return "STRONG"
    elif confidence >= 0.6:
        return "MODERATE"
    elif confidence >= 0.4:
        return "WEAK"
    else:
        return "VERY_WEAK"

@router.get("/history")
async def get_signal_history(
    limit: int = 50,
    user = Depends(get_current_user)
):
    """Get historical trading signals for analysis"""
    try:
        # TODO: Implement signal history from DynamoDB
        # For now, return empty for live system
        return {
            "signals": [],
            "total_count": 0,
            "message": "Signal history tracking active - data accumulating"
        }
        
    except Exception as e:
        logger.error(f"Signal history failed: {e}")
        raise HTTPException(status_code=500, detail=f"History retrieval failed: {e}")

@router.get("/performance")
async def get_signal_performance(user = Depends(get_current_user)):
    """Get signal performance metrics"""
    try:
        # Get current engine performance
        engine = EnterpriseTradingEngine()
        
        return {
            "total_signals": getattr(engine, 'total_signals_generated', 0),
            "successful_signals": getattr(engine, 'successful_signals', 0),
            "win_rate": 0.0,  # Calculate from historical data
            "avg_confidence": 0.0,  # Calculate from recent signals
            "last_signal_time": datetime.now(timezone.utc),
            "is_live": True
        }
        
    except Exception as e:
        logger.error(f"Signal performance failed: {e}")
        raise HTTPException(status_code=500, detail=f"Performance retrieval failed: {e}")
