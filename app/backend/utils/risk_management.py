"""
Risk Management Utilities - TradePulse.AI
=======================================

Professional risk management utilities for consistent TP/SL calculations
and risk-reward ratio computations.

Features:
- Standardized TP/SL calculation methods
- Consistent risk-reward ratio computation
- Professional position sizing based on risk
- Risk metrics calculation and validation

Author: TradePulse.AI Development Team
Version: 1.0.0
"""

import logging
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from ..utils.money import D, quantize_price, calculate_risk_amount

logger = logging.getLogger(__name__)

class RiskManagementError(Exception):
    """Custom exception for risk management errors"""
    pass

def calculate_tp_sl_from_entry(
    entry_price: Decimal,
    stop_loss: Optional[Decimal],
    take_profit: Optional[Decimal],
    risk_reward_ratio: Optional[Decimal] = None,
    position_type: str = "LONG",
    symbol: str = "BTCUSDT"
) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """
    Calculate take profit and stop loss from entry price and risk-reward ratio.

    Args:
        entry_price: Position entry price
        stop_loss: Stop loss price (if None, calculated from risk)
        take_profit: Take profit price (if None, calculated from R/R)
        risk_reward_ratio: Risk-reward ratio (default 2.0)
        position_type: "LONG" or "SHORT"
        symbol: Trading symbol for price quantization

    Returns:
        Tuple of (take_profit, stop_loss)
    """
    if risk_reward_ratio is None:
        risk_reward_ratio = D("2.0")

    if position_type.upper() == "LONG":
        if take_profit is None and stop_loss is not None:
            # Calculate TP from SL and R/R
            risk_distance = entry_price - stop_loss
            reward_distance = risk_distance * risk_reward_ratio
            take_profit = entry_price + reward_distance
        elif stop_loss is None and take_profit is not None:
            # Calculate SL from TP and R/R
            reward_distance = take_profit - entry_price
            risk_distance = reward_distance / risk_reward_ratio
            stop_loss = entry_price - risk_distance
    else:  # SHORT
        if take_profit is None and stop_loss is not None:
            # Calculate TP from SL and R/R
            risk_distance = stop_loss - entry_price
            reward_distance = risk_distance * risk_reward_ratio
            take_profit = entry_price - reward_distance
        elif stop_loss is None and take_profit is not None:
            # Calculate SL from TP and R/R
            reward_distance = entry_price - take_profit
            risk_distance = reward_distance / risk_reward_ratio
            stop_loss = entry_price + risk_distance

    # Quantize prices for exchange compliance
    if take_profit:
        take_profit = quantize_price(take_profit, symbol)
    if stop_loss:
        stop_loss = quantize_price(stop_loss, symbol)

    return take_profit, stop_loss

def calculate_risk_reward_ratio(
    entry_price: Decimal,
    stop_loss: Decimal,
    take_profit: Decimal,
    position_type: str = "LONG"
) -> Decimal:
    """
    Calculate risk-reward ratio from entry, SL, and TP.

    Args:
        entry_price: Position entry price
        stop_loss: Stop loss price
        take_profit: Take profit price
        position_type: "LONG" or "SHORT"

    Returns:
        Risk-reward ratio
    """
    if position_type.upper() == "LONG":
        if entry_price <= stop_loss or take_profit <= entry_price:
            raise RiskManagementError("Invalid LONG position: entry <= SL or TP <= entry")
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
    else:  # SHORT
        if entry_price >= stop_loss or take_profit >= entry_price:
            raise RiskManagementError("Invalid SHORT position: entry >= SL or TP >= entry")
        risk = stop_loss - entry_price
        reward = entry_price - take_profit

    if risk <= 0:
        raise RiskManagementError("Risk must be positive")

    return reward / risk

def calculate_position_size_risk_based(
    portfolio_value: Decimal,
    entry_price: Decimal,
    stop_loss: Decimal,
    max_risk_pct: Decimal = D("0.02"),  # 2%
    symbol: str = "BTCUSDT",
    position_type: str = "LONG"
) -> Decimal:
    """
    Calculate position size based on risk management.

    Args:
        portfolio_value: Total portfolio value
        entry_price: Expected entry price
        stop_loss: Stop loss price
        max_risk_pct: Maximum risk percentage per trade
        symbol: Trading symbol
        position_type: "LONG" or "SHORT"

    Returns:
        Position size in base currency
    """
    # Calculate maximum risk amount
    max_risk_amount = portfolio_value * max_risk_pct

    # Calculate risk per unit
    if position_type.upper() == "LONG":
        risk_per_unit = entry_price - stop_loss
    else:
        risk_per_unit = stop_loss - entry_price

    if risk_per_unit <= 0:
        raise RiskManagementError("Risk per unit must be positive")

    # Calculate position size
    position_size = max_risk_amount / risk_per_unit

    # Apply LOT_SIZE constraints
    from ..utils.money import quantize_qty
    return quantize_qty(position_size, symbol)

def validate_tp_sl_levels(
    entry_price: Decimal,
    stop_loss: Optional[Decimal],
    take_profit: Optional[Decimal],
    position_type: str = "LONG",
    min_rr_ratio: Decimal = D("0.5"),
    max_rr_ratio: Decimal = D("10.0")
) -> bool:
    """
    Validate TP/SL levels for reasonableness.

    Args:
        entry_price: Position entry price
        stop_loss: Stop loss price
        take_profit: Take profit price
        position_type: "LONG" or "SHORT"
        min_rr_ratio: Minimum acceptable risk-reward ratio
        max_rr_ratio: Maximum acceptable risk-reward ratio

    Returns:
        True if levels are valid, False otherwise
    """
    try:
        if not stop_loss or not take_profit:
            return True  # Skip validation if levels not set

        rr_ratio = calculate_risk_reward_ratio(entry_price, stop_loss, take_profit, position_type)

        if rr_ratio < min_rr_ratio:
            logger.warning(f"Risk-reward ratio too low: {rr_ratio:.2f} < {min_rr_ratio}")
            return False

        if rr_ratio > max_rr_ratio:
            logger.warning(f"Risk-reward ratio too high: {rr_ratio:.2f} > {max_rr_ratio}")
            return False

        return True

    except RiskManagementError as e:
        logger.error(f"TP/SL validation error: {e}")
        return False

def log_risk_metrics(
    entry_price: Decimal,
    stop_loss: Optional[Decimal],
    take_profit: Optional[Decimal],
    position_size: Decimal,
    portfolio_value: Decimal,
    position_type: str = "LONG",
    symbol: str = "BTCUSDT"
) -> None:
    """
    Log comprehensive risk metrics for position.

    Args:
        entry_price: Position entry price
        stop_loss: Stop loss price
        take_profit: Take profit price
        position_size: Position size
        portfolio_value: Total portfolio value
        position_type: "LONG" or "SHORT"
        symbol: Trading symbol
    """
    try:
        position_value = entry_price * position_size
        position_pct = (position_value / portfolio_value) * D("100")

        log_data = {
            "symbol": symbol,
            "position_type": position_type,
            "entry_price": float(entry_price),
            "position_size": float(position_size),
            "position_value": float(position_value),
            "position_pct": float(position_pct)
        }

        if stop_loss and take_profit:
            rr_ratio = calculate_risk_reward_ratio(entry_price, stop_loss, take_profit, position_type)
            risk_amount = calculate_risk_amount(entry_price, stop_loss, position_size, position_type)
            risk_pct = (risk_amount / portfolio_value) * D("100")

            log_data.update({
                "stop_loss": float(stop_loss),
                "take_profit": float(take_profit),
                "risk_reward_ratio": float(rr_ratio),
                "risk_amount": float(risk_amount),
                "risk_pct": float(risk_pct)
            })

        logger.info("Position risk metrics calculated", extra=log_data)

    except Exception as e:
        logger.error(f"Failed to calculate risk metrics: {e}")

def get_standard_tp_sl_pct(
    position_type: str = "LONG",
    risk_pct: Decimal = D("0.02"),  # 2% risk
    rr_ratio: Decimal = D("2.0")    # 2:1 reward
) -> Tuple[Decimal, Decimal]:
    """
    Get standard TP/SL percentages for position.

    Args:
        position_type: "LONG" or "SHORT"
        risk_pct: Risk percentage (stop loss distance)
        rr_ratio: Risk-reward ratio

    Returns:
        Tuple of (stop_loss_pct, take_profit_pct)
    """
    stop_loss_pct = risk_pct
    take_profit_pct = risk_pct * rr_ratio

    return stop_loss_pct, take_profit_pct
