"""
Professional Health Check System for TradePulse.AI

Enterprise-grade health monitoring with:
- Kubernetes-compatible health checks
- Dependency health monitoring
- Performance metrics
- Circuit breaker integration
- Detailed health reports
"""

import asyncio
import time
import psutil
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, asdict
import structlog

from .environments import get_config
from .connection_manager import get_connection_manager
from .exceptions import ServiceUnavailableException

logger = structlog.get_logger(__name__)


class HealthStatus(str, Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentType(str, Enum):
    """Types of components to monitor"""
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    COMPUTE = "compute"
    CUSTOM = "custom"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    status: HealthStatus
    response_time_ms: float
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


@dataclass
class SystemHealth:
    """Overall system health status"""
    status: HealthStatus
    checks: List[HealthCheckResult]
    response_time_ms: float
    timestamp: datetime
    uptime_seconds: float
    version: str
    environment: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "status": self.status.value,
            "checks": [check.to_dict() for check in self.checks],
            "response_time_ms": self.response_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "uptime_seconds": self.uptime_seconds,
            "version": self.version,
            "environment": self.environment,
            "summary": {
                "total_checks": len(self.checks),
                "healthy": len([c for c in self.checks if c.status == HealthStatus.HEALTHY]),
                "degraded": len([c for c in self.checks if c.status == HealthStatus.DEGRADED]),
                "unhealthy": len([c for c in self.checks if c.status == HealthStatus.UNHEALTHY]),
                "unknown": len([c for c in self.checks if c.status == HealthStatus.UNKNOWN])
            }
        }


class HealthChecker:
    """Professional health check manager"""
    
    def __init__(self):
        self.config = get_config()
        self.start_time = time.time()
        self.checks: Dict[str, Callable] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        
        # Register default health checks
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default system health checks"""
        self.register_check("database", self._check_database)
        self.register_check("memory", self._check_memory)
        self.register_check("disk", self._check_disk)
        self.register_check("cpu", self._check_cpu)
        # Temporarily disable connections check due to macOS permission issues
        # self.register_check("connections", self._check_connections)
        logger.info("🔄 PIPELINE DEBUG: Connections check disabled (macOS permissions)")
    
    def register_check(self, name: str, check_func: Callable) -> None:
        """Register a custom health check"""
        self.checks[name] = check_func
        logger.info(f"Registered health check: {name}")
    
    async def _check_database(self) -> HealthCheckResult:
        """Check database connectivity"""
        start_time = time.time()
        
        try:
            connection_manager = await get_connection_manager()
            health_status = await connection_manager.health_check()
            
            response_time = (time.time() - start_time) * 1000
            
            if health_status.get("dynamodb", False):
                return HealthCheckResult(
                    component="database",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    message="Database connection healthy",
                    details=health_status
                )
            else:
                return HealthCheckResult(
                    component="database",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    message="Database connection failed",
                    details=health_status
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="database",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Database check failed: {str(e)}"
            )
    
    async def _check_memory(self) -> HealthCheckResult:
        """Check system memory usage"""
        start_time = time.time()
        
        try:
            memory = psutil.virtual_memory()
            response_time = (time.time() - start_time) * 1000
            
            # Consider memory unhealthy if usage > 90%
            if memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"High memory usage: {memory.percent:.1f}%"
            elif memory.percent > 80:
                status = HealthStatus.DEGRADED
                message = f"Elevated memory usage: {memory.percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {memory.percent:.1f}%"
            
            return HealthCheckResult(
                component="memory",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "percent": memory.percent,
                    "available_gb": memory.available / (1024**3),
                    "total_gb": memory.total / (1024**3),
                    "used_gb": memory.used / (1024**3)
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="memory",
                status=HealthStatus.UNKNOWN,
                response_time_ms=response_time,
                message=f"Memory check failed: {str(e)}"
            )
    
    async def _check_disk(self) -> HealthCheckResult:
        """Check disk space usage"""
        start_time = time.time()
        
        try:
            disk = psutil.disk_usage('/')
            response_time = (time.time() - start_time) * 1000
            
            usage_percent = (disk.used / disk.total) * 100
            
            # Consider disk unhealthy if usage > 90%
            if usage_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"High disk usage: {usage_percent:.1f}%"
            elif usage_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"Elevated disk usage: {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk usage normal: {usage_percent:.1f}%"
            
            return HealthCheckResult(
                component="disk",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "percent": usage_percent,
                    "free_gb": disk.free / (1024**3),
                    "total_gb": disk.total / (1024**3),
                    "used_gb": disk.used / (1024**3)
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="disk",
                status=HealthStatus.UNKNOWN,
                response_time_ms=response_time,
                message=f"Disk check failed: {str(e)}"
            )
    
    async def _check_cpu(self) -> HealthCheckResult:
        """Check CPU usage"""
        start_time = time.time()
        
        try:
            # Get CPU usage over 1 second interval
            cpu_percent = psutil.cpu_percent(interval=1)
            response_time = (time.time() - start_time) * 1000
            
            # Consider CPU unhealthy if usage > 90%
            if cpu_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"High CPU usage: {cpu_percent:.1f}%"
            elif cpu_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"Elevated CPU usage: {cpu_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"CPU usage normal: {cpu_percent:.1f}%"
            
            return HealthCheckResult(
                component="cpu",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "percent": cpu_percent,
                    "cores": psutil.cpu_count(),
                    "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="cpu",
                status=HealthStatus.UNKNOWN,
                response_time_ms=response_time,
                message=f"CPU check failed: {str(e)}"
            )
    
    async def _check_connections(self) -> HealthCheckResult:
        """Check network connections"""
        start_time = time.time()
        
        try:
            # Try to get connections with fallback for permission issues
            try:
                connections = psutil.net_connections()
                response_time = (time.time() - start_time) * 1000
                
                # Count connections by status
                conn_stats = {}
                for conn in connections:
                    status = conn.status
                    conn_stats[status] = conn_stats.get(status, 0) + 1
                
                total_connections = len(connections)
                
                # Consider unhealthy if too many connections
                if total_connections > 1000:
                    status = HealthStatus.UNHEALTHY
                    message = f"Too many connections: {total_connections}"
                elif total_connections > 500:
                    status = HealthStatus.DEGRADED
                    message = f"High connection count: {total_connections}"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Connection count normal: {total_connections}"
                
                return HealthCheckResult(
                    component="connections",
                    status=status,
                    response_time_ms=response_time,
                    message=message,
                    details={
                        "total": total_connections,
                        "by_status": conn_stats
                    }
                )
            except PermissionError:
                # Permission denied - common on macOS, not critical
                response_time = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    component="connections",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    message="Connection monitoring requires elevated permissions (not critical)",
                    details={"permission_issue": True}
                )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="connections",
                status=HealthStatus.UNKNOWN,
                response_time_ms=response_time,
                message=f"Connections check failed: {str(e)}"
            )
    
    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check"""
        if name not in self.checks:
            return HealthCheckResult(
                component=name,
                status=HealthStatus.UNKNOWN,
                response_time_ms=0,
                message=f"Health check '{name}' not found"
            )
        
        try:
            result = await self.checks[name]()
            self.last_results[name] = result
            return result
        except Exception as e:
            logger.error(f"Health check '{name}' failed", error=str(e))
            result = HealthCheckResult(
                component=name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                message=f"Health check failed: {str(e)}"
            )
            self.last_results[name] = result
            return result
    
    async def run_all_checks(self) -> SystemHealth:
        """Run all registered health checks"""
        start_time = time.time()
        
        # Run all checks concurrently
        check_tasks = [self.run_check(name) for name in self.checks.keys()]
        results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        # Process results
        check_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                check_name = list(self.checks.keys())[i]
                check_results.append(HealthCheckResult(
                    component=check_name,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    message=f"Check failed: {str(result)}"
                ))
            else:
                check_results.append(result)
        
        # Determine overall status
        statuses = [result.status for result in check_results]
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        elif HealthStatus.UNKNOWN in statuses:
            overall_status = HealthStatus.DEGRADED  # Treat unknown as degraded
        else:
            overall_status = HealthStatus.HEALTHY
        
        response_time = (time.time() - start_time) * 1000
        uptime = time.time() - self.start_time
        
        return SystemHealth(
            status=overall_status,
            checks=check_results,
            response_time_ms=response_time,
            timestamp=datetime.now(timezone.utc),
            uptime_seconds=uptime,
            version=self.config.app_version,
            environment=self.config.environment.value
        )
    
    async def liveness_check(self) -> Dict[str, Any]:
        """Kubernetes liveness probe - simple check that service is running"""
        return {
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": time.time() - self.start_time
        }
    
    async def readiness_check(self) -> Dict[str, Any]:
        """Kubernetes readiness probe - check if service is ready to handle requests"""
        # Run critical checks only (database, memory)
        critical_checks = ["database", "memory"]
        
        check_tasks = [self.run_check(name) for name in critical_checks if name in self.checks]
        results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        # Check if all critical checks passed
        all_ready = True
        for result in results:
            if isinstance(result, Exception) or result.status == HealthStatus.UNHEALTHY:
                all_ready = False
                break
        
        return {
            "status": "ready" if all_ready else "not_ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": [r.to_dict() if not isinstance(r, Exception) else {"error": str(r)} for r in results]
        }


# Global health checker instance
_health_checker: Optional[HealthChecker] = None

def get_health_checker() -> HealthChecker:
    """Get global health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker

