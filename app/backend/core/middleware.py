"""
Professional Middleware Components for TradePulse.AI
Industry standard middleware with proper error handling and monitoring
"""

import time
from collections import defaultdict
from typing import Dict, List, Callable, Any

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from app.backend.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitStorage:
    """
    In-memory rate limit storage
    For production, consider Redis or distributed cache
    """
    
    def __init__(self):
        self._requests: Dict[str, List[float]] = defaultdict(list)
    
    def add_request(self, client_id: str, timestamp: float) -> None:
        """Add a request timestamp for client"""
        self._requests[client_id].append(timestamp)
    
    def get_request_count(self, client_id: str, window_start: float) -> int:
        """Get request count for client within time window"""
        if client_id not in self._requests:
            return 0
        
        # Clean old requests outside window
        self._requests[client_id] = [
            req_time for req_time in self._requests[client_id]
            if req_time >= window_start
        ]
        
        return len(self._requests[client_id])
    
    def cleanup_old_requests(self, cutoff_time: float) -> None:
        """Clean up old request records"""
        for client_id in list(self._requests.keys()):
            self._requests[client_id] = [
                req_time for req_time in self._requests[client_id]
                if req_time >= cutoff_time
            ]
            
            # Remove empty entries
            if not self._requests[client_id]:
                del self._requests[client_id]


def create_rate_limit_middleware(
    requests_per_minute: int = 100,
    window_seconds: int = 60
) -> Callable:
    """
    Create rate limiting middleware
    
    Args:
        requests_per_minute: Maximum requests per client per minute
        window_seconds: Time window in seconds
    
    Returns:
        Configured middleware function
    """
    storage = RateLimitStorage()
    
    async def rate_limit_middleware(request: Request, call_next):
        """Rate limiting middleware implementation"""
        
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Check current request count
        request_count = storage.get_request_count(client_ip, window_start)
        
        if request_count >= requests_per_minute:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                request_count=request_count,
                limit=requests_per_minute,
                path=request.url.path
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": window_seconds,
                        "limit": requests_per_minute,
                        "window_seconds": window_seconds
                    }
                }
            )
        
        # Add current request
        storage.add_request(client_ip, current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(requests_per_minute - request_count - 1)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + window_seconds))
        
        return response
    
    return rate_limit_middleware


def create_request_logging_middleware() -> Callable:
    """
    Create request/response logging middleware
    Logs all API requests with timing and status
    """
    
    async def request_logging_middleware(request: Request, call_next):
        """Request logging middleware implementation"""
        start_time = time.time()
        
        # Log request start
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown")
        )
        
        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Log successful response
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                client_ip=request.client.host if request.client else "unknown"
            )
            
            # Add timing header
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error response
            logger.error(
                "Request failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                error=str(e),
                error_type=type(e).__name__,
                client_ip=request.client.host if request.client else "unknown"
            )
            
            raise
    
    return request_logging_middleware


def create_security_headers_middleware() -> Callable:
    """
    Create security headers middleware
    Adds security headers to all responses
    """
    
    async def security_headers_middleware(request: Request, call_next):
        """Security headers middleware implementation"""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response
    
    return security_headers_middleware


def create_cors_middleware_config() -> Dict[str, Any]:
    """
    Create CORS middleware configuration
    Returns configuration dict for CORSMiddleware
    """
    return {
        "allow_origins": ["*"],  # Configure for production
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["*"],
        "expose_headers": ["X-Response-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
    }
