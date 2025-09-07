"""
Phase 2.2: Performance Monitoring API for TradePulse.AI
Real-time performance metrics and optimization insights
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import time
from datetime import datetime, timezone

from app.backend.services.model_performance_optimizer import get_model_optimizer
from app.backend.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/performance", tags=["Performance"])


@router.get("/metrics")
async def get_performance_metrics() -> Dict[str, Any]:
    """Get comprehensive performance metrics"""
    try:
        optimizer = get_model_optimizer()
        summary = optimizer.get_performance_summary()
        
        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": summary,
            "optimization_status": {
                "target_met": summary.get("performance_target_met", False),
                "avg_latency_ms": summary.get("avg_total_time_ms", 0),
                "target_latency_ms": summary.get("target_latency_ms", 1000),
                "cache_efficiency": summary.get("cache_hit_rate", 0),
                "throughput_per_second": summary.get("avg_throughput_per_second", 0)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimization-status")
async def get_optimization_status() -> Dict[str, Any]:
    """Get current optimization status"""
    try:
        optimizer = get_model_optimizer()
        summary = optimizer.get_performance_summary()
        
        # Calculate optimization grades
        avg_latency = summary.get("avg_total_time_ms", 1000)
        cache_hit_rate = summary.get("cache_hit_rate", 0)
        target_latency = summary.get("target_latency_ms", 1000)
        
        # Performance grades
        latency_grade = "A" if avg_latency < target_latency * 0.5 else \
                       "B" if avg_latency < target_latency * 0.75 else \
                       "C" if avg_latency < target_latency else "D"
        
        cache_grade = "A" if cache_hit_rate > 80 else \
                     "B" if cache_hit_rate > 60 else \
                     "C" if cache_hit_rate > 40 else "D"
        
        overall_grade = "A" if latency_grade == "A" and cache_grade in ["A", "B"] else \
                       "B" if latency_grade in ["A", "B"] and cache_grade in ["B", "C"] else \
                       "C" if latency_grade in ["B", "C"] else "D"
        
        return {
            "status": "success",
            "optimization_active": True,
            "performance_grades": {
                "overall": overall_grade,
                "latency": latency_grade,
                "cache_efficiency": cache_grade
            },
            "metrics": {
                "avg_latency_ms": avg_latency,
                "target_latency_ms": target_latency,
                "cache_hit_rate": cache_hit_rate,
                "total_inferences": summary.get("total_inferences", 0),
                "uptime_hours": summary.get("optimization_uptime_hours", 0)
            },
            "recommendations": _generate_optimization_recommendations(summary)
        }
    except Exception as e:
        logger.error(f"Failed to get optimization status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-cache")
async def clear_performance_cache() -> Dict[str, Any]:
    """Clear performance caches"""
    try:
        optimizer = get_model_optimizer()
        optimizer.clear_caches()
        
        return {
            "status": "success",
            "message": "Performance caches cleared successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/layer-performance")
async def get_layer_performance() -> Dict[str, Any]:
    """Get per-layer performance breakdown"""
    try:
        optimizer = get_model_optimizer()
        
        # Get recent metrics by layer
        recent_metrics = optimizer.metrics_history[-50:] if optimizer.metrics_history else []
        
        layer_stats = {}
        for metric in recent_metrics:
            layer_name = metric.model_name
            if layer_name not in layer_stats:
                layer_stats[layer_name] = {
                    "total_calls": 0,
                    "total_time_ms": 0,
                    "avg_time_ms": 0,
                    "min_time_ms": float('inf'),
                    "max_time_ms": 0,
                    "avg_throughput": 0
                }
            
            stats = layer_stats[layer_name]
            stats["total_calls"] += 1
            stats["total_time_ms"] += metric.total_time_ms
            stats["min_time_ms"] = min(stats["min_time_ms"], metric.total_time_ms)
            stats["max_time_ms"] = max(stats["max_time_ms"], metric.total_time_ms)
        
        # Calculate averages
        for layer_name, stats in layer_stats.items():
            if stats["total_calls"] > 0:
                stats["avg_time_ms"] = stats["total_time_ms"] / stats["total_calls"]
                stats["avg_throughput"] = 1000.0 / max(stats["avg_time_ms"], 1.0)
        
        return {
            "status": "success",
            "layer_performance": layer_stats,
            "total_layers": len(layer_stats),
            "analysis_period": "last_50_inferences"
        }
    except Exception as e:
        logger.error(f"Failed to get layer performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-health")
async def get_system_health() -> Dict[str, Any]:
    """Get system health related to performance"""
    try:
        import psutil
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1.0)
        memory = psutil.virtual_memory()
        
        # Process metrics
        process = psutil.Process()
        process_memory = process.memory_info()
        process_cpu = process.cpu_percent()
        
        # Performance optimizer status
        optimizer = get_model_optimizer()
        perf_summary = optimizer.get_performance_summary()
        
        # Health assessment
        health_score = 100
        issues = []
        
        if cpu_percent > 80:
            health_score -= 20
            issues.append("High CPU usage")
        
        if memory.percent > 85:
            health_score -= 25
            issues.append("High memory usage")
        
        if perf_summary.get("avg_total_time_ms", 0) > 1000:
            health_score -= 15
            issues.append("Slow AI inference")
        
        if perf_summary.get("cache_hit_rate", 0) < 50:
            health_score -= 10
            issues.append("Low cache efficiency")
        
        health_status = "excellent" if health_score >= 90 else \
                       "good" if health_score >= 75 else \
                       "fair" if health_score >= 60 else "poor"
        
        return {
            "status": "success",
            "health_score": max(0, health_score),
            "health_status": health_status,
            "issues": issues,
            "system_metrics": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "process_memory_mb": process_memory.rss / (1024**2),
                "process_cpu_percent": process_cpu
            },
            "performance_metrics": {
                "avg_inference_time_ms": perf_summary.get("avg_total_time_ms", 0),
                "cache_hit_rate": perf_summary.get("cache_hit_rate", 0),
                "total_inferences": perf_summary.get("total_inferences", 0)
            }
        }
    except ImportError:
        return {
            "status": "limited",
            "message": "psutil not available - limited system metrics",
            "health_status": "unknown"
        }
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _generate_optimization_recommendations(summary: Dict[str, Any]) -> List[str]:
    """Generate optimization recommendations based on performance data"""
    recommendations = []
    
    avg_latency = summary.get("avg_total_time_ms", 0)
    cache_hit_rate = summary.get("cache_hit_rate", 0)
    total_inferences = summary.get("total_inferences", 0)
    target_latency = summary.get("target_latency_ms", 1000)
    
    # Latency recommendations
    if avg_latency > target_latency:
        recommendations.append(f"Consider increasing parallel workers (current latency: {avg_latency:.1f}ms)")
    
    if avg_latency > target_latency * 2:
        recommendations.append("Enable model quantization for faster inference")
    
    # Cache recommendations
    if cache_hit_rate < 50:
        recommendations.append("Increase cache size or TTL to improve hit rate")
    
    if cache_hit_rate < 30:
        recommendations.append("Review feature preparation - may be too dynamic for caching")
    
    # General recommendations
    if total_inferences < 100:
        recommendations.append("System is warming up - performance will improve with more usage")
    
    if not recommendations:
        recommendations.append("Performance is optimal - no immediate optimizations needed")
    
    return recommendations
