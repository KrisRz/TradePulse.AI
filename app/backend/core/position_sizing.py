"""
Position Sizing Utilities
Fixes unit mismatch between requested USD notional and BTC quantity
"""

import logging
from typing import Union

logger = logging.getLogger(__name__)

def size_in_base(notional_usd: float, last_price: float, step: float = 0.00001) -> float:
    """
    Convert USD notional to BTC quantity with proper exchange step rounding
    
    Args:
        notional_usd: Desired USD position size
        last_price: Current BTC price in USD  
        step: Exchange step size (default 0.00001 for Binance BTC)
        
    Returns:
        BTC quantity rounded to exchange step
    """
    if last_price <= 0:
        raise ValueError("Price must be positive")
    
    # Convert USD to BTC
    qty_btc = float(notional_usd) / max(1e-9, float(last_price))
    
    # Round to exchange step size
    rounded_qty = float(round(qty_btc / step) * step)
    
    logger.debug(f"Position sizing: ${notional_usd:.2f} USD @ ${last_price:.2f} = {rounded_qty:.8f} BTC")
    
    return rounded_qty

def validate_position_size(size: float, min_size: float = 0.00001, max_size: float = 1000.0) -> bool:
    """
    Validate position size is within exchange limits
    
    Args:
        size: Position size in BTC
        min_size: Minimum position size 
        max_size: Maximum position size
        
    Returns:
        True if valid, False otherwise
    """
    return min_size <= size <= max_size

def calculate_usd_value(btc_quantity: float, price: float) -> float:
    """Calculate USD value of BTC position"""
    return float(btc_quantity) * float(price)
