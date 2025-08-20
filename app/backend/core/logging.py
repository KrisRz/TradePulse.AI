"""
Logging configuration for TradePulse.AI backend
Uses structured logging with Structlog for production-ready logging
"""

import sys
import logging
import traceback
from typing import Dict, Any, Optional
import structlog
from structlog.processors import TimeStamper, JSONRenderer
from datetime import datetime


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    environment: str = "dev"
) -> None:
    """Configure structured logging for the application"""
    
    # Determine if we should use JSON format (production) or console (development)
    use_json = log_format.lower() == "json" or environment.lower() == "production"
    
    # Configure processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Add appropriate renderer
    if use_json:
        processors.append(JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
    
    # Silence noisy loggers in production
    if environment.lower() == "production":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("boto3").setLevel(logging.WARNING)
        logging.getLogger("botocore").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance"""
    return structlog.get_logger(name)


class StructuredLogger:
    """Enhanced structured logger with predefined log types"""
    
    def __init__(self, name: Optional[str] = None):
        self.logger = get_logger(name)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with context"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """Log error message with context and optional exception"""
        if error:
            kwargs.update({
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc() if hasattr(error, '__traceback__') else None
            })
        self.logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context"""
        self.logger.debug(message, **kwargs)
    
    def api_request(self, method: str, path: str, user_id: Optional[str] = None, **kwargs) -> None:
        """Log API request with structured data"""
        self.logger.info(
            "API request started",
            event_type="api_request",
            method=method,
            path=path,
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def api_response(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log API response with structured data"""
        self.logger.info(
            "API request completed",
            event_type="api_response",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def database_operation(
        self,
        operation: str,
        table: str,
        success: bool = True,
        duration_ms: Optional[float] = None,
        **kwargs
    ) -> None:
        """Log database operation with structured data"""
        self.logger.info(
            "Database operation",
            event_type="database_operation",
            operation=operation,
            table=table,
            success=success,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def trading_event(
        self,
        event_type: str,
        symbol: str,
        position_id: Optional[str] = None,
        amount: Optional[float] = None,
        price: Optional[float] = None,
        **kwargs
    ) -> None:
        """Log trading event with structured data"""
        self.logger.info(
            "Trading event",
            event_type=f"trading_{event_type}",
            symbol=symbol,
            position_id=position_id,
            amount=amount,
            price=price,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def security_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        **kwargs
    ) -> None:
        """Log security event with structured data"""
        log_method = self.logger.warning if not success else self.logger.info
        log_method(
            "Security event",
            event_type=f"security_{event_type}",
            user_id=user_id,
            ip_address=ip_address,
            success=success,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )


class LoggingMixin:
    """Mixin class to add logging capabilities to any class"""
    
    @property
    def logger(self) -> StructuredLogger:
        """Get logger for this class"""
        return StructuredLogger(self.__class__.__name__)
    
    def log_method_call(self, method_name: str, **kwargs) -> None:
        """Log method call with parameters"""
        self.logger.debug(
            f"Method called: {method_name}",
            method=method_name,
            class_name=self.__class__.__name__,
            **kwargs
        )
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Log error with context"""
        self.logger.error(
            f"Error in {self.__class__.__name__}",
            error=error,
            class_name=self.__class__.__name__,
            **(context or {})
        )


# Default logger instance
logger = StructuredLogger("tradepulse")

# Backwards compatibility functions
def log_api_request(method: str, path: str, **kwargs) -> None:
    """Log API request with structured data"""
    logger.api_request(method, path, **kwargs)


def log_api_response(method: str, path: str, status_code: int, duration: float, **kwargs) -> None:
    """Log API response with structured data"""
    logger.api_response(method, path, status_code, duration * 1000, **kwargs)  # Convert to ms


def log_database_operation(operation: str, table: str, **kwargs) -> None:
    """Log database operation with structured data"""
    logger.database_operation(operation, table, **kwargs)


def log_trading_event(event_type: str, symbol: str, **kwargs) -> None:
    """Log trading event with structured data"""
    logger.trading_event(event_type, symbol, **kwargs)


def log_error(error: Exception, context: Dict[str, Any] = None) -> None:
    """Log error with structured context"""
    context = context or {}
    logger.error("Application error", error=error, **context) 