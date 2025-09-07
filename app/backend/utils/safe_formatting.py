"""
Safe formatting utilities for TradePulse.AI
Prevents NoneType.__format__ errors and provides robust data formatting
"""

from typing import Any, Optional, Union
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def safe_format_price(value: Any, decimals: int = 2, default: str = "N/A") -> str:
    """
    Safely format price values, handling None and invalid types
    
    Args:
        value: Price value to format
        decimals: Number of decimal places
        default: Default string if value is None/invalid
        
    Returns:
        str: Formatted price string
    """
    if value is None:
        return default
        
    try:
        if isinstance(value, (int, float, Decimal)):
            if value == 0:
                return f"${0:.{decimals}f}"
            return f"${float(value):,.{decimals}f}"
        elif isinstance(value, str):
            try:
                numeric_value = float(value)
                return f"${numeric_value:,.{decimals}f}"
            except (ValueError, TypeError):
                return default
        else:
            return default
    except Exception as e:
        logger.warning(f"Error formatting price {value}: {e}")
        return default


def safe_format_percentage(value: Any, decimals: int = 2, default: str = "N/A") -> str:
    """
    Safely format percentage values
    
    Args:
        value: Percentage value to format (0.05 = 5%)
        decimals: Number of decimal places
        default: Default string if value is None/invalid
        
    Returns:
        str: Formatted percentage string
    """
    if value is None:
        return default
        
    try:
        if isinstance(value, (int, float, Decimal)):
            return f"{float(value) * 100:.{decimals}f}%"
        elif isinstance(value, str):
            try:
                numeric_value = float(value)
                return f"{numeric_value * 100:.{decimals}f}%"
            except (ValueError, TypeError):
                return default
        else:
            return default
    except Exception as e:
        logger.warning(f"Error formatting percentage {value}: {e}")
        return default


def safe_format_number(value: Any, decimals: int = 2, default: str = "N/A") -> str:
    """
    Safely format numeric values
    
    Args:
        value: Numeric value to format
        decimals: Number of decimal places
        default: Default string if value is None/invalid
        
    Returns:
        str: Formatted number string
    """
    if value is None:
        return default
        
    try:
        if isinstance(value, (int, float, Decimal)):
            return f"{float(value):.{decimals}f}"
        elif isinstance(value, str):
            try:
                numeric_value = float(value)
                return f"{numeric_value:.{decimals}f}"
            except (ValueError, TypeError):
                return default
        else:
            return default
    except Exception as e:
        logger.warning(f"Error formatting number {value}: {e}")
        return default


def safe_format_confidence(value: Any, as_percentage: bool = False, decimals: int = 2, default: str = "N/A") -> str:
    """
    Safely format confidence values
    
    Args:
        value: Confidence value (0.0-1.0 or 0-100)
        as_percentage: Whether to format as percentage
        decimals: Number of decimal places
        default: Default string if value is None/invalid
        
    Returns:
        str: Formatted confidence string
    """
    if value is None:
        return default
        
    try:
        if isinstance(value, (int, float, Decimal)):
            numeric_value = float(value)
            
            # Handle both 0-1 and 0-100 ranges
            if numeric_value > 1.0 and as_percentage:
                # Already in percentage form
                return f"{numeric_value:.{decimals}f}%"
            elif as_percentage:
                # Convert to percentage
                return f"{numeric_value * 100:.{decimals}f}%"
            else:
                # Return as decimal
                return f"{numeric_value:.{decimals}f}"
        elif isinstance(value, str):
            try:
                numeric_value = float(value)
                if as_percentage:
                    if numeric_value > 1.0:
                        return f"{numeric_value:.{decimals}f}%"
                    else:
                        return f"{numeric_value * 100:.{decimals}f}%"
                else:
                    return f"{numeric_value:.{decimals}f}"
            except (ValueError, TypeError):
                return default
        else:
            return default
    except Exception as e:
        logger.warning(f"Error formatting confidence {value}: {e}")
        return default


def safe_get_attr(obj: Any, attr_name: str, default: Any = None) -> Any:
    """
    Safely get attribute from object, returning default if None or missing
    
    Args:
        obj: Object to get attribute from
        attr_name: Name of attribute
        default: Default value if attribute is None/missing
        
    Returns:
        Any: Attribute value or default
    """
    if obj is None:
        return default
        
    try:
        value = getattr(obj, attr_name, default)
        return value if value is not None else default
    except Exception as e:
        logger.warning(f"Error getting attribute {attr_name} from {type(obj)}: {e}")
        return default


def validate_numeric_not_none(value: Any, field_name: str, allow_zero: bool = True) -> Union[float, None]:
    """
    Validate that a numeric value is not None and convert to float
    
    Args:
        value: Value to validate
        field_name: Name of field for error messages
        allow_zero: Whether to allow zero values
        
    Returns:
        float: Validated numeric value
        
    Raises:
        ValueError: If value is None or invalid
    """
    if value is None:
        raise ValueError(f"{field_name} cannot be None")
        
    try:
        numeric_value = float(value)
        
        if not allow_zero and numeric_value == 0:
            raise ValueError(f"{field_name} cannot be zero")
            
        return numeric_value
    except (ValueError, TypeError) as e:
        raise ValueError(f"{field_name} must be a valid number, got {type(value).__name__}: {value}")


def safe_divide(numerator: Any, denominator: Any, default: float = 0.0) -> float:
    """
    Safely divide two numbers, handling None and zero division
    
    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Default value if division fails
        
    Returns:
        float: Division result or default
    """
    try:
        if numerator is None or denominator is None:
            return default
            
        num = float(numerator)
        den = float(denominator)
        
        if den == 0:
            return default
            
        return num / den
    except (ValueError, TypeError, ZeroDivisionError):
        return default


# Convenience functions for common use cases
def fmt_price(value: Any) -> str:
    """Quick price formatting"""
    return safe_format_price(value)


def fmt_pct(value: Any) -> str:
    """Quick percentage formatting"""
    return safe_format_percentage(value)


def fmt_conf(value: Any) -> str:
    """Quick confidence formatting as percentage"""
    return safe_format_confidence(value, as_percentage=True)


def fmt_num(value: Any, decimals: int = 2) -> str:
    """Quick number formatting"""
    return safe_format_number(value, decimals)


# Validation helpers
def ensure_price_not_none(price: Any, context: str = "") -> float:
    """Ensure price is not None, raise descriptive error if it is"""
    return validate_numeric_not_none(price, f"price{' in ' + context if context else ''}", allow_zero=False)


def ensure_confidence_not_none(confidence: Any, context: str = "") -> float:
    """Ensure confidence is not None, raise descriptive error if it is"""
    return validate_numeric_not_none(confidence, f"confidence{' in ' + context if context else ''}", allow_zero=True)
