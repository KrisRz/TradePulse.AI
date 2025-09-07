"""
Professional Metrics Endpoint for TradePulse.AI
Provides system metrics and monitoring data
"""

import time
import psutil
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status

router = APIRouter()

# Track startup time
_startup_time = time.time()


@router.get("/metrics")
async def get_system_metrics() -> Dict[str, Any]:
    """Get comprehensive system metrics"""
    try:
        # System metrics
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Network connections
        connections = len(psutil.net_connections())
        
        # Uptime
        uptime_seconds = time.time() - _startup_time
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": uptime_seconds,
            "system": {
                "cpu": {
                    "percent": cpu_percent,
                    "cores": psutil.cpu_count()
                },
                "memory": {
                    "percent": memory.percent,
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2)
                },
                "disk": {
                    "percent": round((disk.used / disk.total) * 100, 1),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2)
                },
                "network": {
                    "connections": connections
                }
            },
            "health_status": "healthy" if cpu_percent < 80 and memory.percent < 80 else "degraded"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.get("/metrics/health")
async def health_summary() -> Dict[str, Any]:
    """Simple health summary"""
    try:
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Determine health status
        if cpu_percent > 90 or memory.percent > 90:
            status_level = "unhealthy"
        elif cpu_percent > 80 or memory.percent > 80:
            status_level = "degraded"
        else:
            status_level = "healthy"
        
        return {
            "status": status_level,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": time.time() - _startup_time,
            "checks": {
                "cpu": {
                    "status": "healthy" if cpu_percent < 80 else "degraded",
                    "value": cpu_percent
                },
                "memory": {
                    "status": "healthy" if memory.percent < 80 else "degraded", 
                    "value": memory.percent
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )

