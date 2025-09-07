"""
Professional Exception Handling System for TradePulse.AI
"""

from typing import Optional, Dict, Any
from enum import Enum
import structlog
from fastapi import HTTPException, status

logger = structlog.get_logger(__name__)


class ErrorCategory(str, Enum):
    """Error categories for better error handling"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    AI_MODEL = "ai_model"
    TRADING = "trading"
    MARKET_DATA = "market_data"


class TradePulseException(Exception):
    """Base exception for TradePulse.AI with structured error handling"""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.message = message
        self.error_code = error_code
        self.category = category
        self.details = details or {}
        self.user_message = user_message or message
        self.http_status = http_status
        
        super().__init__(self.message)
        
        # Log the error with structured data
        logger.error(
            "TradePulse exception occurred",
            error_code=self.error_code,
            category=self.category.value,
            message=self.message,
            details=self.details
        )

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException"""
        return HTTPException(
            status_code=self.http_status,
            detail={
                "error": {
                    "code": self.error_code,
                    "message": self.user_message,
                    "category": self.category.value,
                    "details": self.details
                }
            }
        )


class ServiceUnavailableException(TradePulseException):
    """Raised when a required service is unavailable"""
    def __init__(self, service_name: str, **kwargs):
        super().__init__(
            message=f"Service '{service_name}' is currently unavailable",
            error_code="SVC_001",
            category=ErrorCategory.EXTERNAL_SERVICE,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service_name},
            user_message="A required service is temporarily unavailable.",
            **kwargs
        )


class ConfigurationException(TradePulseException):
    """Raised when configuration is invalid or missing"""
    def __init__(self, config_key: str, **kwargs):
        super().__init__(
            message=f"Invalid or missing configuration: {config_key}",
            error_code="CFG_001",
            category=ErrorCategory.CONFIGURATION,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"config_key": config_key},
            user_message="System configuration error.",
            **kwargs
        )


class DatabaseException(TradePulseException):
    """Raised when database operations fail"""
    def __init__(self, operation: str, table: Optional[str] = None, **kwargs):
        operation_details = {"operation": operation}
        if table:
            operation_details["table"] = table
        
        # Merge with any additional details from kwargs
        if "details" in kwargs:
            operation_details.update(kwargs.pop("details"))
            
        super().__init__(
            message=f"Database operation '{operation}' failed",
            error_code="DB_001",
            category=ErrorCategory.DATABASE,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=operation_details,
            user_message="A database error occurred.",
            **kwargs
        )


class ModelNotLoadedException(TradePulseException):
    """Raised when a required model is not loaded"""
    def __init__(self, model_name: str, **kwargs):
        super().__init__(
            message=f"Model '{model_name}' is not loaded",
            error_code="MDL_002",
            category=ErrorCategory.SYSTEM,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"model": model_name},
            user_message="AI analysis is temporarily unavailable.",
            **kwargs
        )


# Professional AI Model Exceptions
class AIModelException(TradePulseException):
    """Base exception for AI model related errors"""
    def __init__(self, message: str, model_name: str, layer: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="AI_MODEL_ERROR",
            category=ErrorCategory.AI_MODEL,
            details={"model": model_name, "layer": layer},
            user_message="AI analysis system error - professional deployment requires model fix",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            **kwargs
        )


class ModelNotLoadedException(AIModelException):
    """Raised when a required AI model is not loaded"""
    def __init__(self, model_name: str, layer: str = None, **kwargs):
        super().__init__(
            message=f"AI Model '{model_name}' not loaded - professional deployment requires all models",
            model_name=model_name,
            layer=layer,
            error_code="AI_MODEL_NOT_LOADED",
            **kwargs
        )


class ModelPredictionException(AIModelException):
    """Raised when AI model prediction fails"""
    def __init__(self, model_name: str, layer: str = None, prediction_value=None, **kwargs):
        super().__init__(
            message=f"AI Model '{model_name}' prediction failed - invalid output: {prediction_value}",
            model_name=model_name,
            layer=layer,
            error_code="AI_MODEL_PREDICTION_FAILED",
            details={"prediction_value": prediction_value},
            **kwargs
        )


class TradingEngineException(TradePulseException):
    """Base exception for trading engine errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="TRADING_ENGINE_ERROR",
            category=ErrorCategory.TRADING,
            user_message="Trading engine error - professional system requires immediate attention",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            **kwargs
        )


class MarketDataException(TradePulseException):
    """Base exception for market data errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="MARKET_DATA_ERROR",
            category=ErrorCategory.MARKET_DATA,
            user_message="Market data unavailable - professional system requires live data",
            **kwargs
        )


class ProfessionalDeploymentException(TradePulseException):
    """Raised when professional deployment standards are violated"""
    def __init__(self, violation: str, component: str = None, **kwargs):
        violation_details = {"violation": violation}
        if component:
            violation_details["component"] = component
        
        super().__init__(
            message=f"Professional deployment violation: {violation}",
            error_code="PROF_001",
            category=ErrorCategory.BUSINESS_LOGIC,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=violation_details,
            user_message="System operating in professional mode - no fallbacks allowed.",
            **kwargs
        )


class NoFallbackException(TradePulseException):
    """Raised when fallback logic is attempted in professional mode"""
    def __init__(self, operation: str, reason: str = None, **kwargs):
        operation_details = {"operation": operation}
        if reason:
            operation_details["reason"] = reason
        
        super().__init__(
            message=f"Fallback attempted for {operation} - not allowed in professional mode",
            error_code="NOFB_001", 
            category=ErrorCategory.BUSINESS_LOGIC,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=operation_details,
            user_message="Professional trading system requires real data - no fallbacks.",
            **kwargs
        )


class RealDataRequiredException(TradePulseException):
    """Raised when real data is required but not available"""
    def __init__(self, data_type: str, source: str = None, **kwargs):
        data_details = {"data_type": data_type}
        if source:
            data_details["source"] = source
        
        super().__init__(
            message=f"Real {data_type} data required - no mocks or demos allowed",
            error_code="REAL_001",
            category=ErrorCategory.DATA,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=data_details,
            user_message="Professional system requires live market data.",
            **kwargs
        )