"""
Professional Connection Manager for TradePulse.AI

Enterprise-grade connection pooling and management with:
- HTTP connection pooling
- Database connection management
- Circuit breaker pattern
- Retry logic with exponential backoff
- Health monitoring
- Resource cleanup
"""

import asyncio
import aiohttp
import boto3
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_settings
from .exceptions import ServiceUnavailableException, DatabaseException

logger = structlog.get_logger(__name__)


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.state == "OPEN":
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = "HALF_OPEN"
                return False
            return True
        return False
    
    def record_success(self):
        """Record successful operation"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class HTTPConnectionManager:
    """Professional HTTP connection manager with pooling"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.connector: Optional[aiohttp.TCPConnector] = None
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.settings = get_settings()
        
    async def initialize(self):
        """Initialize connection pool with professional settings"""
        if self.session:
            return  # Already initialized
            
        self.connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Per-host limit
            keepalive_timeout=60,  # Keep connections alive for 60s
            enable_cleanup_closed=True,  # Clean up closed connections
            use_dns_cache=True,  # Enable DNS caching
            ttl_dns_cache=300,  # DNS cache TTL
            ssl=False if self.settings.ENVIRONMENT == 'development' else True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=30,  # Total timeout
            connect=10,  # Connection timeout
            sock_read=20  # Socket read timeout
        )
        
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=timeout,
            raise_for_status=False  # Handle status codes manually
        )
        
        logger.info("HTTP connection pool initialized", 
                   pool_size=100, 
                   per_host_limit=30)
        
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[aiohttp.ClientSession, None]:
        """Get HTTP session with connection pooling"""
        if not self.session:
            await self.initialize()
        yield self.session
        
    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker()
        return self.circuit_breakers[service_name]
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def request_with_retry(
        self, 
        method: str, 
        url: str, 
        service_name: str = "default",
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Make HTTP request with retry logic and circuit breaker"""
        circuit_breaker = self.get_circuit_breaker(service_name)
        
        if circuit_breaker.is_open():
            raise ServiceUnavailableException(service_name)
        
        try:
            async with self.get_session() as session:
                response = await session.request(method, url, **kwargs)
                
                if response.status >= 500:
                    circuit_breaker.record_failure()
                    raise ServiceUnavailableException(service_name)
                else:
                    circuit_breaker.record_success()
                    
                return response
                
        except aiohttp.ClientError as e:
            circuit_breaker.record_failure()
            logger.error(f"HTTP request failed for {service_name}", 
                        url=url, error=str(e))
            raise ServiceUnavailableException(service_name) from e
    
    async def close(self):
        """Clean shutdown of connection pool"""
        if self.session:
            await self.session.close()
            logger.info("HTTP session closed")
            
        if self.connector:
            await self.connector.close()
            logger.info("HTTP connector closed")


class DynamoDBConnectionManager:
    """Professional DynamoDB connection manager with performance monitoring"""
    
    def __init__(self):
        self.client: Optional[Any] = None
        self.resource: Optional[Any] = None
        self.settings = get_settings()
        self.circuit_breaker = CircuitBreaker()
        
        # Performance monitoring
        self.connection_count = 0
        self.active_connections = 0
        self.total_operations = 0
        self.failed_operations = 0
        self.avg_response_time = 0.0
        self.last_health_check = None
        
    async def initialize(self):
        """Initialize DynamoDB connections"""
        if self.client:
            return  # Already initialized
            
        try:
            # Optimized configuration for DynamoDB Local high-performance trading
            config = boto3.session.Config(
                region_name=self.settings.AWS_REGION,
                retries={'max_attempts': 5, 'mode': 'adaptive'},
                max_pool_connections=100,  # Increased for high-frequency trading
                read_timeout=30,           # Reduced for faster timeouts
                connect_timeout=5,         # Faster connection establishment
                parameter_validation=False, # Skip validation for performance
                tcp_keepalive=True         # Keep connections alive
            )
            
            if self.settings.ENVIRONMENT == 'development':
                # Local DynamoDB
                self.client = boto3.client(
                    'dynamodb',
                    endpoint_url=self.settings.DYNAMODB_ENDPOINT,
                    aws_access_key_id='dummy',
                    aws_secret_access_key='dummy',
                    config=config
                )
                self.resource = boto3.resource(
                    'dynamodb',
                    endpoint_url=self.settings.DYNAMODB_ENDPOINT,
                    aws_access_key_id='dummy',
                    aws_secret_access_key='dummy',
                    config=config
                )
            else:
                # AWS DynamoDB
                self.client = boto3.client('dynamodb', config=config)
                self.resource = boto3.resource('dynamodb', config=config)
            
            # Test connection
            await self.health_check()
            
            logger.info("DynamoDB connection initialized", 
                       endpoint=self.settings.DYNAMODB_ENDPOINT,
                       environment=self.settings.ENVIRONMENT)
                       
        except Exception as e:
            logger.error("Failed to initialize DynamoDB connection", error=str(e))
            raise ServiceUnavailableException("DynamoDB") from e
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def execute_with_retry(self, operation_name: str, operation_func, *args, **kwargs):
        """Execute DynamoDB operation with retry logic"""
        if self.circuit_breaker.is_open():
            raise ServiceUnavailableException("DynamoDB")
        
        try:
            # Run in thread pool since boto3 is synchronous
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, operation_func, *args, **kwargs)
            
            self.circuit_breaker.record_success()
            return result
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"DynamoDB operation failed: {operation_name}", error=str(e))
            raise DatabaseException(operation_name) from e
    
    async def health_check(self) -> bool:
        """Check DynamoDB connectivity"""
        import time
        from datetime import datetime
        
        start_time = time.time()
        try:
            if not self.client:
                await self.initialize()
                
            # Simple health check - list tables
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.client.list_tables)
            
            # Record successful health check
            response_time = time.time() - start_time
            self.record_operation(response_time, success=True)
            self.last_health_check = datetime.utcnow()
            return True
            
        except Exception as e:
            # Record failed health check
            response_time = time.time() - start_time
            self.record_operation(response_time, success=False)
            logger.error("DynamoDB health check failed", error=str(e))
            return False
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get DynamoDB connection performance statistics"""
        success_rate = 0.0
        if self.total_operations > 0:
            success_rate = ((self.total_operations - self.failed_operations) / self.total_operations) * 100
        
        return {
            "connection_pool_size": 100,
            "active_connections": self.active_connections,
            "total_operations": self.total_operations,
            "failed_operations": self.failed_operations,
            "success_rate_percent": round(success_rate, 2),
            "avg_response_time_ms": round(self.avg_response_time * 1000, 2),
            "circuit_breaker_state": "closed" if not self.circuit_breaker.is_open() else "open",
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "endpoint": self.settings.DYNAMODB_ENDPOINT
        }
    
    def record_operation(self, response_time: float, success: bool = True):
        """Record operation metrics for monitoring"""
        self.total_operations += 1
        if not success:
            self.failed_operations += 1
        
        # Update rolling average response time
        if self.total_operations == 1:
            self.avg_response_time = response_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.avg_response_time = alpha * response_time + (1 - alpha) * self.avg_response_time
    
    def get_table(self, table_name: str):
        """Get DynamoDB table resource"""
        if not self.resource:
            raise ServiceUnavailableException("DynamoDB")
        return self.resource.Table(table_name)


class ConnectionManager:
    """Centralized connection manager for all services"""
    
    def __init__(self):
        self.http = HTTPConnectionManager()
        self.dynamodb = DynamoDBConnectionManager()
        self._initialized = False
    
    async def initialize(self):
        """Initialize all connection managers"""
        if self._initialized:
            return
            
        await asyncio.gather(
            self.http.initialize(),
            self.dynamodb.initialize()
        )
        
        self._initialized = True
        logger.info("All connection managers initialized")
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all connections"""
        return {
            "dynamodb": await self.dynamodb.health_check(),
            "http_pool": self.http.session is not None
        }
    
    async def close(self):
        """Clean shutdown of all connections"""
        await self.http.close()
        logger.info("All connections closed")


# Global connection manager instance
_connection_manager: Optional[ConnectionManager] = None

async def get_connection_manager() -> ConnectionManager:
    """Get or create global connection manager"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
        await _connection_manager.initialize()
    return _connection_manager

async def close_connections():
    """Close all connections - call on shutdown"""
    global _connection_manager
    if _connection_manager:
        await _connection_manager.close()
        _connection_manager = None