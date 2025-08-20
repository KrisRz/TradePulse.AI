"""
Custom exception classes for TradePulse.AI backend
Provides structured error handling with proper HTTP status codes
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class TradePulseException(Exception):
    """Base exception for TradePulse.AI application"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(TradePulseException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = {"field": field} if field else {}
        super().__init__(message, "VALIDATION_ERROR", details)


class AuthenticationError(TradePulseException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, "AUTH_ERROR")


class AuthorizationError(TradePulseException):
    """Raised when authorization fails"""
    
    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(message, "AUTHORIZATION_ERROR")


class DatabaseError(TradePulseException):
    """Raised when database operations fail"""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        details = {"operation": operation} if operation else {}
        super().__init__(message, "DATABASE_ERROR", details)


class MarketDataError(TradePulseException):
    """Raised when market data operations fail"""
    
    def __init__(self, message: str, symbol: Optional[str] = None, **kwargs):
        details = {"symbol": symbol} if symbol else {}
        super().__init__(message, "MARKET_DATA_ERROR", details)


class TradingError(TradePulseException):
    """Raised when trading operations fail"""
    
    def __init__(self, message: str, position_id: Optional[str] = None, **kwargs):
        details = {"position_id": position_id} if position_id else {}
        super().__init__(message, "TRADING_ERROR", details)


class ModelError(TradePulseException):
    """Raised when ML model operations fail"""
    
    def __init__(self, message: str, model_name: Optional[str] = None, **kwargs):
        details = {"model_name": model_name} if model_name else {}
        super().__init__(message, "MODEL_ERROR", details)


class ConfigurationError(TradePulseException):
    """Raised when configuration is invalid"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        details = {"config_key": config_key} if config_key else {}
        super().__init__(message, "CONFIG_ERROR", details)


class ExternalServiceError(TradePulseException):
    """Raised when external service calls fail"""
    
    def __init__(self, message: str, service: Optional[str] = None, **kwargs):
        details = {"service": service} if service else {}
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)


# HTTP Exception Converters

def tradepulse_to_http_exception(exc: TradePulseException) -> HTTPException:
    """Convert TradePulse exception to HTTP exception"""
    
    status_code_map = {
        "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "AUTH_ERROR": status.HTTP_401_UNAUTHORIZED,
        "AUTHORIZATION_ERROR": status.HTTP_403_FORBIDDEN,
        "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "MARKET_DATA_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
        "TRADING_ERROR": status.HTTP_400_BAD_REQUEST,
        "MODEL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "CONFIG_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "EXTERNAL_SERVICE_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
        "UNKNOWN_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    
    status_code = status_code_map.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    detail = {
        "error_code": exc.error_code,
        "message": exc.message,
        "details": exc.details
    }
    
    return HTTPException(status_code=status_code, detail=detail)


# Common exception instances for quick use
class CommonExceptions:
    """Common exception instances for frequent use cases"""
    
    @staticmethod
    def unauthorized(message: str = "Authentication required") -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "AUTH_REQUIRED", "message": message}
        )
    
    @staticmethod
    def forbidden(message: str = "Access denied") -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "ACCESS_DENIED", "message": message}
        )
    
    @staticmethod
    def not_found(resource: str, identifier: str = "") -> HTTPException:
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "NOT_FOUND", "message": message, "resource": resource}
        )
    
    @staticmethod
    def bad_request(message: str, field: Optional[str] = None) -> HTTPException:
        detail = {"error_code": "BAD_REQUEST", "message": message}
        if field:
            detail["field"] = field
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
    
    @staticmethod
    def internal_error(message: str = "Internal server error") -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "message": message}
        )
    
    @staticmethod
    def service_unavailable(service: str = "External service") -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "SERVICE_UNAVAILABLE",
                "message": f"{service} is temporarily unavailable",
                "service": service
            }
        )


# Export all exceptions and utilities
__all__ = [
    "TradePulseException",
    "ValidationError",
    "AuthenticationError", 
    "AuthorizationError",
    "DatabaseError",
    "MarketDataError",
    "TradingError",
    "ModelError",
    "ConfigurationError",
    "ExternalServiceError",
    "tradepulse_to_http_exception",
    "CommonExceptions"
]