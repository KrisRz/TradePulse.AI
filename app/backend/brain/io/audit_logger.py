"""
Audit Logger - TradePulse.AI BRAIN
=================================

Complete decision tracking and audit trail for all BRAIN operations.
Provides professional logging with DynamoDB persistence and performance analytics.

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import uuid
import json

from app.backend.core.database import DynamoDBClient
from app.backend.core.config import get_settings

logger = logging.getLogger(__name__)

class AuditLogger:
    """
    Professional audit logger for complete decision tracking
    
    Features:
    - Complete decision audit trail
    - Performance analytics
    - Error tracking and analysis
    - DynamoDB persistence with TTL
    - Real-time monitoring integration
    """
    
    def __init__(self):
        self.is_initialized = False
        self.db_client: Optional[DynamoDBClient] = None
        
        # Table names
        self.decisions_table = "brain_decisions"
        self.cycles_table = "brain_cycles"
        self.errors_table = "brain_errors"
        self.performance_table = "brain_performance_log"
        
        # Performance tracking
        self.logs_written = 0
        self.errors_logged = 0
        self.last_flush_time: Optional[datetime] = None
        
        # Buffer for batch writes
        self.decision_buffer: List[Dict[str, Any]] = []
        self.buffer_size = 10
        self.buffer_timeout_seconds = 60
        
        logger.info("📝 Audit Logger initialized")
        
    async def initialize(self):
        """Initialize audit logger"""
        if self.is_initialized:
            return
            
        logger.info("🚀 Initializing Audit Logger...")
        
        try:
            # Initialize database client
            settings = get_settings()
            self.db_client = DynamoDBClient(local_development=settings.is_development)
            
            # Start background flush task
            asyncio.create_task(self._background_flush_task())
            
            self.is_initialized = True
            logger.info("✅ Audit Logger initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Audit Logger: {e}")
            raise
            
    async def log_decision(
        self, 
        signal: Optional[Dict[str, Any]], 
        entry_decision: Optional[Dict[str, Any]], 
        exit_decision: Optional[Dict[str, Any]], 
        risk_assessment: Optional[Dict[str, Any]], 
        order_result: Optional[Dict[str, Any]], 
        context: Dict[str, Any]
    ):
        """Log complete trading decision with full context"""
        try:
            timestamp = datetime.now(timezone.utc)
            decision_id = f"decision_{uuid.uuid4().hex[:8]}"
            
            decision_record = {
                "decision_id": decision_id,
                "timestamp": timestamp.isoformat(),
                "day": timestamp.strftime('%Y-%m-%d'),  # Partition key
                "symbol": context.get("symbol", "BTCUSDT"),
                "cycle_count": context.get("cycle_count", 0),
                "trading_session": context.get("session", "unknown"),
                
                # Signal data
                "signal_action": signal.get("action") if signal else None,
                "signal_confidence": str(signal.get("confidence", 0)) if signal else "0",
                "signal_reasoning": signal.get("reasoning") if signal else None,
                "signal_type": signal.get("signal_type", "primary") if signal else "none",
                "layer_analysis": signal.get("layer_analysis", {}) if signal else {},
                
                # Entry decision
                "entry_should_enter": entry_decision.get("should_enter", False) if entry_decision else False,
                "entry_confidence": str(entry_decision.get("confidence", 0)) if entry_decision else "0",
                "entry_quality": entry_decision.get("entry_quality") if entry_decision else None,
                "entry_reasoning": entry_decision.get("reasoning") if entry_decision else None,
                
                # Exit decision
                "exit_should_exit": exit_decision.get("should_exit", False) if exit_decision else False,
                "exit_confidence": str(exit_decision.get("confidence", 0)) if exit_decision else "0",
                "exit_reason": exit_decision.get("exit_reason") if exit_decision else None,
                "exit_pnl_percent": str(exit_decision.get("pnl_percent", 0)) if exit_decision else "0",
                
                # Risk assessment
                "risk_score": str(risk_assessment.get("risk_score", 0.5)) if risk_assessment else "0.5",
                "risk_level": risk_assessment.get("risk_level") if risk_assessment else "MODERATE",
                "risk_block_reason": risk_assessment.get("block_reason") if risk_assessment else None,
                "risk_volatility": str(risk_assessment.get("volatility_current", 0)) if risk_assessment else "0",
                
                # Order execution
                "order_executed": order_result is not None,
                "order_id": order_result.get("order_id") if order_result else None,
                "order_price": str(order_result.get("price", 0)) if order_result else "0",
                "order_quantity": str(order_result.get("quantity", 0)) if order_result else "0",
                "order_slippage": str(order_result.get("slippage_pct", 0)) if order_result else "0",
                "order_latency_ms": order_result.get("latency_ms") if order_result else None,
                
                # Context
                "market_price": str(context.get("current_price", 0)),
                "portfolio_cash": str(context.get("portfolio_cash", 0)),
                "portfolio_positions": context.get("active_positions", 0),
                "avg_cycle_time_ms": str(context.get("avg_cycle_time_ms", 0)),
                
                # Outcome
                "outcome": context.get("outcome", "no_action"),
                "position_id": context.get("position_id"),
                
                # TTL (30 days)
                "ttl": int((timestamp + timedelta(days=30)).timestamp())
            }
            
            # Add to buffer for batch writing
            self.decision_buffer.append(decision_record)
            
            # Flush if buffer is full
            if len(self.decision_buffer) >= self.buffer_size:
                await self._flush_decision_buffer()
                
            logger.debug(f"📝 Decision logged: {decision_id}")
            
        except Exception as e:
            logger.error(f"Failed to log decision: {e}")
            self.errors_logged += 1
            
    async def log_cycle_performance(
        self, 
        cycle_count: int, 
        cycle_time_ms: float, 
        components_timing: Dict[str, float],
        context: Dict[str, Any]
    ):
        """Log cycle performance metrics"""
        try:
            timestamp = datetime.now(timezone.utc)
            
            performance_record = {
                "cycle_id": f"cycle_{cycle_count}_{int(timestamp.timestamp())}",
                "timestamp": timestamp.isoformat(),
                "day": timestamp.strftime('%Y-%m-%d'),
                "cycle_count": cycle_count,
                "cycle_time_ms": str(cycle_time_ms),
                "trading_session": context.get("session", "unknown"),
                
                # Component timing breakdown
                "data_fetch_ms": str(components_timing.get("data_fetch", 0)),
                "safety_check_ms": str(components_timing.get("safety_check", 0)),
                "signal_generation_ms": str(components_timing.get("signal_generation", 0)),
                "risk_assessment_ms": str(components_timing.get("risk_assessment", 0)),
                "entry_analysis_ms": str(components_timing.get("entry_analysis", 0)),
                "exit_analysis_ms": str(components_timing.get("exit_analysis", 0)),
                "position_management_ms": str(components_timing.get("position_management", 0)),
                "audit_logging_ms": str(components_timing.get("audit_logging", 0)),
                
                # Performance flags
                "is_slow_cycle": cycle_time_ms > 1000,  # >1 second
                "is_fast_cycle": cycle_time_ms < 500,   # <500ms
                "has_errors": context.get("has_errors", False),
                
                # System context
                "memory_usage_mb": context.get("memory_usage_mb", 0),
                "cpu_usage_pct": context.get("cpu_usage_pct", 0),
                "active_positions": context.get("active_positions", 0),
                
                # TTL (7 days for performance logs)
                "ttl": int((timestamp + timedelta(days=7)).timestamp())
            }
            
            # Write immediately for performance tracking
            try:
                self.db_client.put_item(self.performance_table, performance_record)
                logger.debug(f"📊 Cycle performance logged: {cycle_count} ({cycle_time_ms:.1f}ms)")
            except Exception as e:
                logger.warning(f"Performance logging failed: {e}")
                
        except Exception as e:
            logger.error(f"Failed to log cycle performance: {e}")
            
    async def log_error(
        self, 
        error_type: str, 
        error_message: str, 
        component: str, 
        context: Dict[str, Any],
        stack_trace: Optional[str] = None
    ):
        """Log system errors with context"""
        try:
            timestamp = datetime.now(timezone.utc)
            error_id = f"error_{uuid.uuid4().hex[:8]}"
            
            error_record = {
                "error_id": error_id,
                "timestamp": timestamp.isoformat(),
                "day": timestamp.strftime('%Y-%m-%d'),
                "error_type": error_type,
                "error_message": error_message[:1000],  # Truncate long messages
                "component": component,
                "stack_trace": stack_trace[:2000] if stack_trace else None,  # Truncate stack trace
                
                # Context
                "cycle_count": context.get("cycle_count", 0),
                "trading_session": context.get("session", "unknown"),
                "symbol": context.get("symbol", "BTCUSDT"),
                "current_state": context.get("current_state", "unknown"),
                
                # System state
                "active_positions": context.get("active_positions", 0),
                "emergency_stop_active": context.get("emergency_stop_active", False),
                "uptime_seconds": context.get("uptime_seconds", 0),
                
                # Error tracking
                "is_critical": error_type in ["EMERGENCY_STOP", "SYSTEM_FAILURE", "DATA_LOSS"],
                "requires_attention": error_type in ["API_FAILURE", "RISK_VIOLATION", "PERFORMANCE_DEGRADATION"],
                
                # TTL (14 days for error logs)
                "ttl": int((timestamp + timedelta(days=14)).timestamp())
            }
            
            # Write immediately for errors
            try:
                self.db_client.put_item(self.errors_table, error_record)
                self.errors_logged += 1
                
                # Log to console based on severity
                if error_record["is_critical"]:
                    logger.critical(f"🚨 Critical error logged: {error_id} - {error_message}")
                elif error_record["requires_attention"]:
                    logger.error(f"❌ Error logged: {error_id} - {error_message}")
                else:
                    logger.warning(f"⚠️ Warning logged: {error_id} - {error_message}")
                    
            except Exception as e:
                logger.error(f"Failed to write error to database: {e}")
                
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
            
    async def get_decision_analytics(self, days: int = 1) -> Dict[str, Any]:
        """Get decision analytics for specified period"""
        try:
            # Calculate time range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)
            
            # Get decisions from DynamoDB
            decisions = []
            try:
                items = self.db_client.scan_table(self.decisions_table)
                for item in items:
                    decision_time = datetime.fromisoformat(item.get("timestamp", ""))
                    if start_time <= decision_time <= end_time:
                        decisions.append(item)
            except Exception as e:
                logger.warning(f"Could not fetch decisions: {e}")
                return {}
                
            if not decisions:
                return {
                    "period_days": days,
                    "total_decisions": 0,
                    "signals_generated": 0,
                    "entry_decisions": 0,
                    "exit_decisions": 0,
                    "positions_opened": 0,
                    "risk_blocks": 0,
                    "avg_signal_confidence": 0,
                    "avg_entry_confidence": 0,
                    "timestamp": end_time.isoformat()
                }
                
            # Calculate analytics
            total_decisions = len(decisions)
            signals_generated = sum(1 for d in decisions if d.get("signal_action") != "HOLD")
            entry_decisions = sum(1 for d in decisions if d.get("entry_should_enter", False))
            exit_decisions = sum(1 for d in decisions if d.get("exit_should_exit", False))
            positions_opened = sum(1 for d in decisions if d.get("outcome") == "position_opened")
            risk_blocks = sum(1 for d in decisions if d.get("risk_block_reason"))
            
            # Average confidences
            signal_confidences = [float(d.get("signal_confidence", 0)) for d in decisions if d.get("signal_confidence")]
            entry_confidences = [float(d.get("entry_confidence", 0)) for d in decisions if d.get("entry_confidence")]
            
            return {
                "period_days": days,
                "total_decisions": total_decisions,
                "signals_generated": signals_generated,
                "entry_decisions": entry_decisions,
                "exit_decisions": exit_decisions,
                "positions_opened": positions_opened,
                "risk_blocks": risk_blocks,
                "signal_generation_rate": signals_generated / total_decisions if total_decisions > 0 else 0,
                "entry_rate": entry_decisions / total_decisions if total_decisions > 0 else 0,
                "position_opening_rate": positions_opened / entry_decisions if entry_decisions > 0 else 0,
                "risk_block_rate": risk_blocks / total_decisions if total_decisions > 0 else 0,
                "avg_signal_confidence": sum(signal_confidences) / len(signal_confidences) if signal_confidences else 0,
                "avg_entry_confidence": sum(entry_confidences) / len(entry_confidences) if entry_confidences else 0,
                "decisions_per_hour": total_decisions / (days * 24) if days > 0 else 0,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get decision analytics: {e}")
            return {}
            
    async def get_performance_analytics(self, days: int = 1) -> Dict[str, Any]:
        """Get performance analytics for specified period"""
        try:
            # Calculate time range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)
            
            # Get performance records
            performance_records = []
            try:
                items = self.db_client.scan_table(self.performance_table)
                for item in items:
                    record_time = datetime.fromisoformat(item.get("timestamp", ""))
                    if start_time <= record_time <= end_time:
                        performance_records.append(item)
            except Exception as e:
                logger.warning(f"Could not fetch performance records: {e}")
                return {}
                
            if not performance_records:
                return {
                    "period_days": days,
                    "total_cycles": 0,
                    "avg_cycle_time_ms": 0,
                    "slow_cycles": 0,
                    "fast_cycles": 0,
                    "error_cycles": 0,
                    "timestamp": end_time.isoformat()
                }
                
            # Calculate performance metrics
            cycle_times = [float(record.get("cycle_time_ms", 0)) for record in performance_records]
            slow_cycles = sum(1 for record in performance_records if record.get("is_slow_cycle", False))
            fast_cycles = sum(1 for record in performance_records if record.get("is_fast_cycle", False))
            error_cycles = sum(1 for record in performance_records if record.get("has_errors", False))
            
            # Component timing averages
            component_timings = {}
            timing_fields = [
                "data_fetch_ms", "safety_check_ms", "signal_generation_ms",
                "risk_assessment_ms", "entry_analysis_ms", "exit_analysis_ms",
                "position_management_ms", "audit_logging_ms"
            ]
            
            for field in timing_fields:
                times = [float(record.get(field, 0)) for record in performance_records if record.get(field)]
                component_timings[field] = sum(times) / len(times) if times else 0
                
            return {
                "period_days": days,
                "total_cycles": len(performance_records),
                "avg_cycle_time_ms": sum(cycle_times) / len(cycle_times) if cycle_times else 0,
                "min_cycle_time_ms": min(cycle_times) if cycle_times else 0,
                "max_cycle_time_ms": max(cycle_times) if cycle_times else 0,
                "slow_cycles": slow_cycles,
                "fast_cycles": fast_cycles,
                "error_cycles": error_cycles,
                "slow_cycle_rate": slow_cycles / len(performance_records) if performance_records else 0,
                "error_rate": error_cycles / len(performance_records) if performance_records else 0,
                "cycles_per_hour": len(performance_records) / (days * 24) if days > 0 else 0,
                "component_timings": component_timings,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance analytics: {e}")
            return {}
            
    async def get_error_summary(self, days: int = 1) -> Dict[str, Any]:
        """Get error summary for specified period"""
        try:
            # Calculate time range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)
            
            # Get error records
            error_records = []
            try:
                items = self.db_client.scan_table(self.errors_table)
                for item in items:
                    error_time = datetime.fromisoformat(item.get("timestamp", ""))
                    if start_time <= error_time <= end_time:
                        error_records.append(item)
            except Exception as e:
                logger.warning(f"Could not fetch error records: {e}")
                return {}
                
            if not error_records:
                return {
                    "period_days": days,
                    "total_errors": 0,
                    "critical_errors": 0,
                    "attention_required": 0,
                    "error_types": {},
                    "component_errors": {},
                    "timestamp": end_time.isoformat()
                }
                
            # Analyze errors
            total_errors = len(error_records)
            critical_errors = sum(1 for e in error_records if e.get("is_critical", False))
            attention_required = sum(1 for e in error_records if e.get("requires_attention", False))
            
            # Group by type and component
            error_types = {}
            component_errors = {}
            
            for error in error_records:
                error_type = error.get("error_type", "unknown")
                component = error.get("component", "unknown")
                
                error_types[error_type] = error_types.get(error_type, 0) + 1
                component_errors[component] = component_errors.get(component, 0) + 1
                
            return {
                "period_days": days,
                "total_errors": total_errors,
                "critical_errors": critical_errors,
                "attention_required": attention_required,
                "critical_rate": critical_errors / total_errors if total_errors > 0 else 0,
                "error_types": error_types,
                "component_errors": component_errors,
                "most_common_error": max(error_types.items(), key=lambda x: x[1]) if error_types else None,
                "most_error_prone_component": max(component_errors.items(), key=lambda x: x[1]) if component_errors else None,
                "errors_per_hour": total_errors / (days * 24) if days > 0 else 0,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get error summary: {e}")
            return {}
            
    async def _flush_decision_buffer(self):
        """Flush decision buffer to DynamoDB"""
        if not self.decision_buffer:
            return
            
        try:
            # Write all buffered decisions
            for decision in self.decision_buffer:
                self.db_client.put_item(self.decisions_table, decision)
                
            self.logs_written += len(self.decision_buffer)
            self.last_flush_time = datetime.now(timezone.utc)
            
            logger.debug(f"📝 Flushed {len(self.decision_buffer)} decisions to database")
            self.decision_buffer.clear()
            
        except Exception as e:
            logger.error(f"Failed to flush decision buffer: {e}")
            
    async def _background_flush_task(self):
        """Background task to flush buffer periodically"""
        while True:
            try:
                await asyncio.sleep(self.buffer_timeout_seconds)
                if self.decision_buffer:
                    await self._flush_decision_buffer()
            except Exception as e:
                logger.error(f"Background flush task error: {e}")
                
    def get_logger_stats(self) -> Dict[str, Any]:
        """Get audit logger statistics"""
        return {
            "is_initialized": self.is_initialized,
            "logs_written": self.logs_written,
            "errors_logged": self.errors_logged,
            "buffer_size": len(self.decision_buffer),
            "max_buffer_size": self.buffer_size,
            "last_flush_time": self.last_flush_time.isoformat() if self.last_flush_time else None,
            "tables": {
                "decisions": self.decisions_table,
                "cycles": self.cycles_table,
                "errors": self.errors_table,
                "performance": self.performance_table
            }
        }

# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None

async def get_audit_logger() -> AuditLogger:
    """Get or create global audit logger"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
        await _audit_logger.initialize()
    return _audit_logger

# Export classes and functions
__all__ = [
    "AuditLogger",
    "get_audit_logger"
]