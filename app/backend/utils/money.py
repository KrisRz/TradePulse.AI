"""
Money Math Utilities - TradePulse.AI
===================================

Professional money math utilities with strict Decimal handling
to prevent float/Decimal mixing issues in financial calculations.

Features:
- Strict Decimal-based arithmetic for all monetary values
- Professional rounding and quantization
- Type-safe conversions
- Binance compliance for lot sizes and price steps

Author: TradePulse.AI Development Team
Version: 1.0.0
"""

from decimal import Decimal, getcontext, ROUND_HALF_UP, ROUND_DOWN
from typing import Union, Optional
import logging

logger = logging.getLogger(__name__)

# Set high precision for financial calculations
getcontext().prec = 28

# Binance LOT_SIZE and PRICE_STEP constants for common symbols
BINANCE_LOT_SIZE = {
    "BTCUSDT": {
        "min_qty": Decimal("0.00001"),
        "max_qty": Decimal("9000.00000000"),
        "step_size": Decimal("0.00001")
    },
    "ETHUSDT": {
        "min_qty": Decimal("0.0001"),
        "max_qty": Decimal("9000.00000000"),
        "step_size": Decimal("0.0001")
    }
}

PRICE_STEP = {
    "BTCUSDT": Decimal("0.01"),
    "ETHUSDT": Decimal("0.01")
}

class MoneyError(Exception):
    """Custom exception for money math errors"""
    pass

def D(value: Union[str, int, float, Decimal]) -> Decimal:
    """
    Convert any numeric value to Decimal with strict type checking.

    Args:
        value: Numeric value to convert

    Returns:
        Decimal representation

    Raises:
        MoneyError: If conversion fails
    """
    if isinstance(value, Decimal):
        return value
    elif isinstance(value, (int, str)):
        return Decimal(str(value))
    elif isinstance(value, float):
        # Log warning for float conversion
        logger.warning(f"Converting float to Decimal: {value} -> {str(value)}")
        return Decimal(str(value))
    else:
        raise MoneyError(f"Cannot convert {type(value)} to Decimal: {value}")

def quantize_qty(quantity: Decimal, symbol: str = "BTCUSDT") -> Decimal:
    """
    Quantize quantity according to Binance LOT_SIZE rules.

    Args:
        quantity: Quantity to quantize
        symbol: Trading symbol for LOT_SIZE lookup

    Returns:
        Quantized quantity
    """
    lot_size = BINANCE_LOT_SIZE.get(symbol, BINANCE_LOT_SIZE["BTCUSDT"])
    return quantity.quantize(lot_size["step_size"], rounding=ROUND_DOWN)

def quantize_price(price: Decimal, symbol: str = "BTCUSDT") -> Decimal:
    """
    Quantize price according to symbol's price step.

    Args:
        price: Price to quantize
        symbol: Trading symbol for price step lookup

    Returns:
        Quantized price
    """
    step = PRICE_STEP.get(symbol, Decimal("0.01"))
    return price.quantize(step, rounding=ROUND_HALF_UP)

def calculate_position_value(price: Decimal, size: Decimal) -> Decimal:
    """
    Calculate position value with proper Decimal arithmetic.

    Args:
        price: Current price
        size: Position size

    Returns:
        Position value
    """
    return price * size

def calculate_pnl(entry_price: Decimal, exit_price: Decimal, size: Decimal, position_type: str = "LONG") -> Decimal:
    """
    Calculate P&L with commission consideration.

    Args:
        entry_price: Position entry price
        exit_price: Position exit price
        size: Position size
        position_type: "LONG" or "SHORT"

    Returns:
        Gross P&L
    """
    if position_type.upper() == "LONG":
        return (exit_price - entry_price) * size
    else:  # SHORT
        return (entry_price - exit_price) * size

def calculate_pnl_percentage(entry_price: Decimal, exit_price: Decimal, position_type: str = "LONG") -> Decimal:
    """
    Calculate P&L percentage.

    Args:
        entry_price: Position entry price
        exit_price: Position exit price
        position_type: "LONG" or "SHORT"

    Returns:
        P&L percentage
    """
    if entry_price == 0:
        return Decimal("0")

    if position_type.upper() == "LONG":
        return ((exit_price - entry_price) / entry_price) * Decimal("100")
    else:  # SHORT
        return ((entry_price - exit_price) / entry_price) * Decimal("100")

def calculate_risk_amount(entry_price: Decimal, stop_loss: Decimal, size: Decimal, position_type: str = "LONG") -> Decimal:
    """
    Calculate risk amount for position.

    Args:
        entry_price: Position entry price
        stop_loss: Stop loss price
        size: Position size
        position_type: "LONG" or "SHORT"

    Returns:
        Risk amount
    """
    if position_type.upper() == "LONG":
        return (entry_price - stop_loss) * size
    else:  # SHORT
        return (stop_loss - entry_price) * size

def calculate_position_size_risk_based(
    portfolio_value: Decimal,
    entry_price: Decimal,
    stop_loss: Decimal,
    max_risk_pct: Decimal = Decimal("0.02"),  # 2%
    symbol: str = "BTCUSDT"
) -> Decimal:
    """
    Calculate position size based on risk management.

    Args:
        portfolio_value: Total portfolio value
        entry_price: Expected entry price
        stop_loss: Stop loss price
        max_risk_pct: Maximum risk percentage
        symbol: Trading symbol

    Returns:
        Calculated position size
    """
    risk_amount = portfolio_value * max_risk_pct
    risk_per_unit = abs(entry_price - stop_loss)
    size = risk_amount / risk_per_unit
    return quantize_qty(size, symbol)

def calculate_tp_sl_from_rr(
    entry_price: Decimal,
    stop_loss: Decimal,
    risk_reward_ratio: Decimal = Decimal("2.0"),
    position_type: str = "LONG"
) -> tuple[Decimal, Decimal]:
    """
    Calculate take profit and stop loss from entry and risk-reward ratio.

    Args:
        entry_price: Entry price
        stop_loss: Stop loss price
        risk_reward_ratio: Risk-reward ratio
        position_type: "LONG" or "SHORT"

    Returns:
        Tuple of (take_profit, stop_loss)
    """
    risk_distance = abs(entry_price - stop_loss)
    reward_distance = risk_distance * risk_reward_ratio

    if position_type.upper() == "LONG":
        take_profit = entry_price + reward_distance
        return take_profit, stop_loss
    else:  # SHORT
        take_profit = entry_price - reward_distance
        return take_profit, stop_loss

def validate_monetary_operation(left: Union[Decimal, float], right: Union[Decimal, float], operation: str) -> tuple[Decimal, Decimal]:
    """
    Validate and convert operands for monetary operations.

    Args:
        left: Left operand
        right: Right operand
        operation: Operation description for error messages

    Returns:
        Tuple of (left_decimal, right_decimal)

    Raises:
        MoneyError: If operands are incompatible
    """
    left_dec = D(left)
    right_dec = D(right)

    if left_dec is None or right_dec is None:
        raise MoneyError(f"Invalid operands for {operation}: {left} {right}")

    return left_dec, right_dec

def safe_monetary_add(left: Union[Decimal, float], right: Union[Decimal, float]) -> Decimal:
    """Safe addition for monetary values"""
    left_dec, right_dec = validate_monetary_operation(left, right, "addition")
    return left_dec + right_dec

def safe_monetary_subtract(left: Union[Decimal, float], right: Union[Decimal, float]) -> Decimal:
    """Safe subtraction for monetary values"""
    left_dec, right_dec = validate_monetary_operation(left, right, "subtraction")
    return left_dec - right_dec

def safe_monetary_multiply(left: Union[Decimal, float], right: Union[Decimal, float]) -> Decimal:
    """Safe multiplication for monetary values"""
    left_dec, right_dec = validate_monetary_operation(left, right, "multiplication")
    return left_dec * right_dec

def safe_monetary_divide(left: Union[Decimal, float], right: Union[Decimal, float]) -> Decimal:
    """Safe division for monetary values"""
    left_dec, right_dec = validate_monetary_operation(left, right, "division")
    if right_dec == 0:
        raise MoneyError("Division by zero in monetary calculation")
    return left_dec / right_dec
