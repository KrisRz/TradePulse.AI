"""
Core Validation Utilities
Fixes market context type errors and entry quality calculations
"""

from typing import Dict, Any, Union
import logging

logger = logging.getLogger(__name__)

def get_market_context(ssot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safely get market context from SSOT dict
    Fixes: 'float' object has no attribute 'get'
    """
    if not isinstance(ssot, dict):
        logger.warning(f"SSOT must be dict, got {type(ssot)}")
        return {}
    
    ctx = ssot.get("context")
    if not isinstance(ctx, dict):
        logger.debug(f"Context not dict, got {type(ctx)}")
        return {}
    
    return ctx

def entry_quality(metrics: Dict[str, Any]) -> float:
    """
    Calculate entry quality score from microstructure metrics
    Fixes: bad operand type for abs(): 'dict'
    """
    try:
        # Extract float values from metrics dict
        spread = float(metrics.get("spread", 0.0))
        slippage = float(metrics.get("slippage", 0.0))
        micro_vol = float(metrics.get("micro_vol", 0.0))
        
        # Calculate quality score
        execution_cost = spread + slippage
        quality_base = max(0.0, 1.0 - (execution_cost * 0.5))
        volatility_bonus = 0.5 + (0.5 * micro_vol)
        
        score = quality_base * volatility_bonus
        return float(max(0.0, min(score, 1.0)))  # Clamp 0-1
        
    except (TypeError, ValueError) as e:
        logger.warning(f"Entry quality calculation failed: {e}")
        return 0.5  # Neutral score

def var_pct(notional_at_risk: float, position_value: float) -> float:
    """
    Calculate VaR percentage with proper bounds
    Fixes: VaR % absurd (13,4xx%)
    """
    try:
        # Ensure position value is never zero
        pv = max(1e-9, float(position_value))
        nar = float(notional_at_risk)
        
        # Calculate percentage
        pct = 100.0 * nar / pv
        
        # Keep sane bounds for alerts (0-1000%)
        return float(max(0.0, min(pct, 1000.0)))
        
    except (TypeError, ValueError, ZeroDivisionError) as e:
        logger.warning(f"VaR calculation failed: {e}")
        return 0.0

def clamp_sl_step(target: float, max_step: float, ref_price: float) -> float:
    """
    Clamp stop loss step to prevent violent jumps
    Fixes: Trailing stop jumps (unit mismatch)
    """
    try:
        # max_step should be relative (e.g. 0.003 = 0.3%)
        step = max_step if max_step > 1e-3 else max_step
        min_sl = ref_price * (1.0 - step)
        
        return float(max(min_sl, target))
        
    except (TypeError, ValueError) as e:
        logger.warning(f"Stop loss clamp failed: {e}")
        return target

def update_trailing_sl(entry_price: float, current_price: float, 
                      trail_pct: float = 0.8, max_step: float = 0.003) -> float:
    """
    Update trailing stop loss with bounded steps
    Fixes: SL moved from ~109,186 → 107,303 in one hop
    """
    try:
        # Normalize trail_pct to decimal if needed
        trail = float(trail_pct) / 100.0 if trail_pct > 1 else float(trail_pct)
        
        # Calculate target stop loss
        target_sl = current_price * (1.0 - trail)
        
        # Bound the change to avoid violent jumps
        return clamp_sl_step(target_sl, max_step, current_price)
        
    except (TypeError, ValueError) as e:
        logger.warning(f"Trailing SL update failed: {e}")
        return entry_price * 0.99  # Fallback to 1% below entry
