"""
Performance Monitoring System for TradePulse.AI
Real-time performance tracking and optimization alerts
"""

import time
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from collections import deque
import statistics
import json
from pathlib import Path

from app.backend.core.logging import get_logger

logger = get_logger(__name__)


class PerformanceMonitor:
    """
    Real-time performance monitoring for <5-second cycles
    
    Tracks:
    - Cycle times and bottlenecks
    - Component performance
    - Cache hit rates
    - Error rates
    - Optimization opportunities
    """
    
    def __init__(self):
        # Performance tracking
        self.cycle_times = deque(maxlen=1000)  # Last 1000 cycles
        self.component_times = {
            "market_data": deque(maxlen=100),
            "ai_inference": deque(maxlen=100),
            "risk_assessment": deque(maxlen=100),
            "database_ops": deque(maxlen=100),
            "total_cycle": deque(maxlen=100)
        }
        
        # Performance targets
        self.targets = {
            "market_data": 1.0,      # 1 second
            "ai_inference": 1.5,     # 1.5 seconds
            "risk_assessment": 0.3,  # 0.3 seconds
            "database_ops": 0.5,     # 0.5 seconds
            "total_cycle": 5.0       # 5 seconds total
        }
        
        # Alerts
        self.performance_alerts = []
        self.last_alert_time = {}
        self.alert_cooldown = 60  # 1 minute between same alerts
        
        # Statistics
        self.start_time = datetime.now(timezone.utc)
        self.total_cycles = 0
        self.slow_cycles = 0
        self.optimization_suggestions = []
    
    def start_cycle(self) -> str:
        """Start timing a new cycle"""
        cycle_id = f"cycle_{int(time.time() * 1000)}"
        self.cycle_start_times = getattr(self, 'cycle_start_times', {})
        self.cycle_start_times[cycle_id] = time.time()
        return cycle_id
    
    def end_cycle(self, cycle_id: str):
        """End cycle timing"""
        if not hasattr(self, 'cycle_start_times') or cycle_id not in self.cycle_start_times:
            return
        
        cycle_time = time.time() - self.cycle_start_times[cycle_id]
        self.cycle_times.append(cycle_time)
        self.component_times["total_cycle"].append(cycle_time)
        
        self.total_cycles += 1
        
        if cycle_time > self.targets["total_cycle"]:
            self.slow_cycles += 1
            self._generate_performance_alert("slow_cycle", cycle_time)
        
        # Cleanup
        del self.cycle_start_times[cycle_id]
    
    def record_component_time(self, component: str, duration: float):
        """Record component execution time"""
        if component in self.component_times:
            self.component_times[component].append(duration)
            
            # Check if component is slow
            if duration > self.targets.get(component, float('inf')):
                self._generate_performance_alert(f"slow_{component}", duration)
    
    def _generate_performance_alert(self, alert_type: str, value: float):
        """Generate performance alert"""
        current_time = time.time()
        
        # Check cooldown
        if alert_type in self.last_alert_time:
            if current_time - self.last_alert_time[alert_type] < self.alert_cooldown:
                return
        
        alert = {
            "type": alert_type,
            "value": value,
            "target": self.targets.get(alert_type.replace("slow_", ""), 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": "high" if value > self.targets.get(alert_type.replace("slow_", ""), 0) * 2 else "medium"
        }
        
        self.performance_alerts.append(alert)
        self.last_alert_time[alert_type] = current_time
        
        logger.warning(f"🚨 Performance alert: {alert_type} = {value:.3f}s")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        summary = {
            "monitoring_duration": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            "total_cycles": self.total_cycles,
            "slow_cycles": self.slow_cycles,
            "slow_cycle_rate": self.slow_cycles / max(self.total_cycles, 1),
            "component_performance": {},
            "recent_alerts": self.performance_alerts[-10:],  # Last 10 alerts
            "optimization_suggestions": self.optimization_suggestions.copy()
        }
        
        # Component performance analysis
        for component, times in self.component_times.items():
            if times:
                summary["component_performance"][component] = {
                    "average_time": statistics.mean(times),
                    "median_time": statistics.median(times),
                    "p95_time": self._percentile(times, 95),
                    "target_time": self.targets.get(component, 0),
                    "performance_ratio": statistics.mean(times) / self.targets.get(component, 1),
                    "recent_times": list(times)[-10:]  # Last 10 measurements
                }
        
        # Overall cycle performance
        if self.cycle_times:
            summary["cycle_performance"] = {
                "average_cycle_time": statistics.mean(self.cycle_times),
                "median_cycle_time": statistics.median(self.cycle_times),
                "p95_cycle_time": self._percentile(self.cycle_times, 95),
                "target_cycle_time": self.targets["total_cycle"],
                "cycles_under_target": sum(1 for t in self.cycle_times if t <= self.targets["total_cycle"]),
                "target_achievement_rate": sum(1 for t in self.cycle_times if t <= self.targets["total_cycle"]) / len(self.cycle_times)
            }
        
        return summary
    
    def _percentile(self, data: deque, percentile: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def generate_optimization_report(self) -> Dict[str, Any]:
        """Generate optimization recommendations"""
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "performance_status": "good",
            "bottlenecks_identified": [],
            "optimization_recommendations": [],
            "priority_actions": []
        }
        
        # Analyze component performance
        for component, times in self.component_times.items():
            if not times:
                continue
            
            avg_time = statistics.mean(times)
            target_time = self.targets.get(component, float('inf'))
            
            if avg_time > target_time:
                bottleneck = {
                    "component": component,
                    "average_time": avg_time,
                    "target_time": target_time,
                    "performance_gap": avg_time - target_time,
                    "severity": "high" if avg_time > target_time * 2 else "medium"
                }
                
                report["bottlenecks_identified"].append(bottleneck)
                
                # Generate specific recommendations
                if component == "market_data":
                    report["optimization_recommendations"].append({
                        "component": component,
                        "recommendation": "Implement aggressive caching and parallel data fetching",
                        "expected_improvement": "50-70% reduction in fetch time"
                    })
                elif component == "ai_inference":
                    report["optimization_recommendations"].append({
                        "component": component,
                        "recommendation": "Use parallel model execution and result caching",
                        "expected_improvement": "40-60% reduction in inference time"
                    })
                elif component == "database_ops":
                    report["optimization_recommendations"].append({
                        "component": component,
                        "recommendation": "Implement connection pooling and batch operations",
                        "expected_improvement": "30-50% reduction in database time"
                    })
        
        # Overall status
        if self.cycle_times:
            avg_cycle = statistics.mean(self.cycle_times)
            if avg_cycle > self.targets["total_cycle"] * 1.5:
                report["performance_status"] = "poor"
            elif avg_cycle > self.targets["total_cycle"]:
                report["performance_status"] = "needs_improvement"
        
        # Priority actions
        if report["bottlenecks_identified"]:
            worst_bottleneck = max(report["bottlenecks_identified"], key=lambda x: x["performance_gap"])
            report["priority_actions"].append(f"Optimize {worst_bottleneck['component']} - highest impact")
        
        return report
    
    async def save_performance_report(self):
        """Save performance report to file"""
        try:
            report = {
                "performance_summary": self.get_performance_summary(),
                "optimization_report": self.generate_optimization_report()
            }
            
            # Save to file
            report_path = Path("logs/performance_report.json")
            report_path.parent.mkdir(exist_ok=True)
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"📊 Performance report saved: {report_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save performance report: {e}")


# Global performance monitor
_performance_monitor: Optional[PerformanceMonitor] = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor"""
    global _performance_monitor
    
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    
    return _performance_monitor
