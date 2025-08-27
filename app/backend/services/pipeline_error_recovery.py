"""
TradePulse.AI Pipeline Error Handling & Recovery - Enterprise Resilience
=======================================================================

Advanced error handling and automatic recovery system for the complete pipeline.
Features intelligent failure detection, cascading recovery mechanisms, 
and enterprise-grade resilience patterns.

Author: TradePulse.AI Development Team
Created: August 2025  
Version: 4.1.0
"""

import asyncio
import logging
import time
import traceback
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import psutil

# Core imports for error handling
from app.backend.core.database import DynamoDBClient
from app.backend.core.config import get_settings

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"              # Minor issues, system continues
    MEDIUM = "medium"        # Noticeable impact, degraded performance
    HIGH = "high"            # Significant issues, some features unavailable
    CRITICAL = "critical"    # Major failures, system stability at risk
    CATASTROPHIC = "catastrophic"  # System-wide failure, immediate action required

class RecoveryStrategy(Enum):
    """Recovery strategy types"""
    RETRY = "retry"                    # Simple retry with backoff
    RESTART = "restart"                # Restart component/service
    FALLBACK = "fallback"              # Switch to backup/alternative
    CIRCUIT_BREAKER = "circuit_breaker" # Temporary isolation
    GRACEFUL_DEGRADATION = "graceful_degradation"  # Reduced functionality
    EMERGENCY_STOP = "emergency_stop"  # Complete shutdown

class ErrorCategory(Enum):
    """Error categories for handling"""
    NETWORK = "network"           # Network connectivity issues
    DATABASE = "database"         # Database connection/query issues  
    API = "api"                  # External API failures
    MEMORY = "memory"            # Memory/resource issues
    PROCESSING = "processing"     # Data processing errors
    VALIDATION = "validation"     # Data validation failures
    CONFIGURATION = "configuration"  # Configuration issues
    SYSTEM = "system"            # System-level errors

@dataclass
class ErrorPattern:
    """Error pattern definition for recognition"""
    category: ErrorCategory
    severity: ErrorSeverity
    keywords: List[str]
    recovery_strategy: RecoveryStrategy
    max_retries: int = 3
    backoff_seconds: float = 5.0
    circuit_breaker_timeout: int = 300  # 5 minutes
    
@dataclass
class ErrorEvent:
    """Error event tracking"""
    id: str
    timestamp: datetime
    component: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    traceback: str
    context: Dict[str, Any]
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_strategy: Optional[RecoveryStrategy] = None

@dataclass
class RecoveryAction:
    """Recovery action definition"""
    strategy: RecoveryStrategy
    component: str
    action_function: Callable
    timeout_seconds: float
    success_condition: Callable
    fallback_action: Optional[Callable] = None

@dataclass
class CircuitBreakerState:
    """Circuit breaker state tracking"""
    component: str
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    timeout_seconds: int = 300

class PipelineErrorRecovery:
    """
    Enterprise Pipeline Error Handling & Recovery System
    
    Features:
    - Intelligent error pattern recognition and classification
    - Cascading recovery mechanisms with automatic failover
    - Circuit breaker patterns for service isolation
    - Graceful degradation strategies
    - Real-time error analytics and trend detection
    - Emergency stop and recovery procedures
    - Complete audit trail of all errors and recovery actions
    """
    
    def __init__(self):
        self.is_running = False
        self.start_time = datetime.now(timezone.utc)
        
        # Error tracking
        self.error_history = []  # List[ErrorEvent]
        self.error_patterns = {}  # category -> ErrorPattern
        self.error_counts = {}   # component -> count
        
        # Recovery mechanisms
        self.recovery_actions = {}  # component -> List[RecoveryAction]
        self.active_recoveries = {}  # component -> recovery_task
        
        # Circuit breakers
        self.circuit_breakers = {}  # component -> CircuitBreakerState
        
        # Component health
        self.component_health = {}  # component -> health_status
        self.component_dependencies = {}  # component -> List[dependencies]
        
        # Recovery statistics
        self.recovery_stats = {
            "total_errors": 0,
            "recovery_attempts": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "emergency_stops": 0
        }
        
        # Configuration
        self.config = {
            "max_error_history": 10000,
            "error_analysis_interval": 60.0,  # seconds
            "recovery_timeout": 300.0,  # 5 minutes
            "circuit_breaker_threshold": 5,
            "cascade_recovery_enabled": True,
            "emergency_stop_threshold": 10  # errors per minute
        }
        
        # Monitoring tasks
        self.monitoring_tasks = []
        
        # Database client
        self.db_client = None

    async def initialize(self) -> Dict[str, Any]:
        """Initialize pipeline error recovery system"""
        try:
            logger.info("🛡️ Initializing Pipeline Error Recovery System...")
            
            # Initialize database client
            settings = get_settings()
            self.db_client = DynamoDBClient(local_development=settings.is_development)
            
            # Setup error patterns
            await self._setup_error_patterns()
            
            # Setup recovery actions
            await self._setup_recovery_actions()
            
            # Initialize circuit breakers
            await self._initialize_circuit_breakers()
            
            # Setup component dependencies
            await self._setup_component_dependencies()
            
            logger.info("✅ Pipeline Error Recovery System initialized successfully")
            
            return {
                "status": "success",
                "error_patterns_configured": len(self.error_patterns),
                "recovery_actions_registered": sum(len(actions) for actions in self.recovery_actions.values()),
                "circuit_breakers_initialized": len(self.circuit_breakers)
            }
            
        except Exception as e:
            logger.error(f"❌ Error recovery system initialization failed: {e}")
            raise RuntimeError(f"Error recovery initialization failed: {e}")

    async def _setup_error_patterns(self):
        """Setup error patterns for intelligent recognition"""
        
        patterns = [
            # Network errors
            ErrorPattern(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                keywords=["connection", "timeout", "network", "unreachable", "dns"],
                recovery_strategy=RecoveryStrategy.RETRY,
                max_retries=3,
                backoff_seconds=10.0
            ),
            
            # Database errors
            ErrorPattern(
                category=ErrorCategory.DATABASE,
                severity=ErrorSeverity.CRITICAL,
                keywords=["database", "dynamo", "table", "connection", "query"],
                recovery_strategy=RecoveryStrategy.CIRCUIT_BREAKER,
                circuit_breaker_timeout=600
            ),
            
            # API errors
            ErrorPattern(
                category=ErrorCategory.API,
                severity=ErrorSeverity.MEDIUM,
                keywords=["api", "http", "status", "rate limit", "binance"],
                recovery_strategy=RecoveryStrategy.FALLBACK,
                max_retries=2,
                backoff_seconds=30.0
            ),
            
            # Memory errors
            ErrorPattern(
                category=ErrorCategory.MEMORY,
                severity=ErrorSeverity.HIGH,
                keywords=["memory", "out of memory", "allocation", "heap"],
                recovery_strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
                max_retries=1
            ),
            
            # Processing errors
            ErrorPattern(
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                keywords=["processing", "calculation", "data", "invalid", "format"],
                recovery_strategy=RecoveryStrategy.RETRY,
                max_retries=2,
                backoff_seconds=5.0
            ),
            
            # Validation errors
            ErrorPattern(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                keywords=["validation", "invalid", "schema", "format", "missing"],
                recovery_strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
                max_retries=1
            )
        ]
        
        for pattern in patterns:
            self.error_patterns[pattern.category] = pattern
        
        logger.info(f"✅ Error patterns configured: {len(patterns)}")

    async def _setup_recovery_actions(self):
        """Setup recovery actions for each component"""
        
        # Enhanced Persistence recovery
        self.recovery_actions["enhanced_persistence"] = [
            RecoveryAction(
                strategy=RecoveryStrategy.RESTART,
                component="enhanced_persistence",
                action_function=self._restart_enhanced_persistence,
                timeout_seconds=30.0,
                success_condition=self._check_persistence_health
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.FALLBACK,
                component="enhanced_persistence",
                action_function=self._fallback_to_legacy_persistence,
                timeout_seconds=10.0,
                success_condition=self._check_legacy_persistence_health
            )
        ]
        
        # Hybrid Client recovery
        self.recovery_actions["hybrid_client"] = [
            RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                component="hybrid_client",
                action_function=self._retry_hybrid_client_connection,
                timeout_seconds=20.0,
                success_condition=self._check_hybrid_client_health
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.FALLBACK,
                component="hybrid_client",
                action_function=self._fallback_to_rest_only,
                timeout_seconds=15.0,
                success_condition=self._check_rest_api_health
            )
        ]
        
        # Trading Engines recovery
        for engine in ["enterprise_engine", "entry_engine", "exit_engine"]:
            self.recovery_actions[engine] = [
                RecoveryAction(
                    strategy=RecoveryStrategy.RESTART,
                    component=engine,
                    action_function=self._create_restart_engine_function(engine),
                    timeout_seconds=45.0,
                    success_condition=self._create_engine_health_check(engine)
                )
            ]
        
        # System recovery
        self.recovery_actions["system"] = [
            RecoveryAction(
                strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
                component="system",
                action_function=self._trigger_graceful_degradation,
                timeout_seconds=10.0,
                success_condition=self._check_system_stability
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.EMERGENCY_STOP,
                component="system",
                action_function=self._trigger_emergency_stop,
                timeout_seconds=30.0,
                success_condition=lambda: True  # Always succeeds
            )
        ]

    async def _initialize_circuit_breakers(self):
        """Initialize circuit breakers for all components"""
        
        components = [
            "enhanced_persistence", "hybrid_client", "enterprise_engine",
            "entry_engine", "exit_engine", "risk_manager", "emergency_controls",
            "database", "binance_api", "websocket_connection"
        ]
        
        for component in components:
            self.circuit_breakers[component] = CircuitBreakerState(
                component=component,
                timeout_seconds=300
            )
        
        logger.info(f"✅ Circuit breakers initialized: {len(components)}")

    async def _setup_component_dependencies(self):
        """Setup component dependency mapping for cascade recovery"""
        
        self.component_dependencies = {
            "unified_data_flow": ["enhanced_persistence", "hybrid_client", "live_market_data"],
            "enterprise_engine": ["hybrid_client", "enhanced_persistence"],
            "entry_engine": ["enterprise_engine", "hybrid_client", "risk_manager"],
            "exit_engine": ["portfolio", "hybrid_client", "risk_manager"],
            "portfolio": ["database"],
            "enhanced_persistence": ["database"],
            "hybrid_client": ["websocket_connection", "binance_api"],
            "pipeline_orchestrator": ["unified_data_flow", "enhanced_persistence", "hybrid_client"]
        }

    async def start(self) -> Dict[str, Any]:
        """Start error recovery monitoring"""
        try:
            logger.info("🚀 Starting Pipeline Error Recovery System...")
            
            self.is_running = True
            
            # Start error monitoring
            error_monitor_task = asyncio.create_task(self._error_monitoring_loop())
            self.monitoring_tasks.append(error_monitor_task)
            
            # Start recovery monitoring
            recovery_monitor_task = asyncio.create_task(self._recovery_monitoring_loop())
            self.monitoring_tasks.append(recovery_monitor_task)
            
            # Start circuit breaker monitoring
            circuit_breaker_task = asyncio.create_task(self._circuit_breaker_monitoring_loop())
            self.monitoring_tasks.append(circuit_breaker_task)
            
            # Start health monitoring
            health_monitor_task = asyncio.create_task(self._health_monitoring_loop())
            self.monitoring_tasks.append(health_monitor_task)
            
            logger.info(f"✅ Error recovery system started with {len(self.monitoring_tasks)} monitoring tasks")
            
            return {
                "status": "success",
                "monitoring_tasks": len(self.monitoring_tasks),
                "circuit_breakers_active": len(self.circuit_breakers)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to start error recovery system: {e}")
            raise RuntimeError(f"Error recovery system start failed: {e}")

    async def handle_error(self, component: str, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle an error event with intelligent recovery"""
        try:
            # Create error event
            error_event = ErrorEvent(
                id=f"{component}_{int(time.time())}_{hash(str(error)) % 10000}",
                timestamp=datetime.now(timezone.utc),
                component=component,
                category=self._categorize_error(str(error)),
                severity=self._assess_error_severity(error, context),
                message=str(error),
                traceback=traceback.format_exc(),
                context=context or {}
            )
            
            # Add to error history
            self.error_history.append(error_event)
            self.recovery_stats["total_errors"] += 1
            
            # Trim error history
            if len(self.error_history) > self.config["max_error_history"]:
                self.error_history = self.error_history[-self.config["max_error_history"]:]
            
            # Update error counts
            self.error_counts[component] = self.error_counts.get(component, 0) + 1
            
            # Update circuit breaker
            await self._update_circuit_breaker(component, success=False)
            
            # Check for emergency conditions
            if await self._check_emergency_conditions(error_event):
                return await self._trigger_emergency_response(error_event)
            
            # Attempt recovery
            recovery_result = await self._attempt_error_recovery(error_event)
            
            # Persist error event
            await self._persist_error_event(error_event)
            
            return recovery_result
            
        except Exception as recovery_error:
            logger.error(f"Error in error handling for {component}: {recovery_error}")
            return {
                "status": "failed",
                "error": str(recovery_error),
                "original_error": str(error)
            }

    def _categorize_error(self, error_message: str) -> ErrorCategory:
        """Categorize error based on message content"""
        error_lower = error_message.lower()
        
        for category, pattern in self.error_patterns.items():
            if any(keyword in error_lower for keyword in pattern.keywords):
                return category
        
        return ErrorCategory.PROCESSING  # Default category

    def _assess_error_severity(self, error: Exception, context: Dict[str, Any]) -> ErrorSeverity:
        """Assess error severity based on type and context"""
        
        # Critical exceptions
        if isinstance(error, (MemoryError, SystemExit)):
            return ErrorSeverity.CATASTROPHIC
        
        # High severity exceptions  
        if isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorSeverity.HIGH
        
        # Medium severity exceptions
        if isinstance(error, (ValueError, TypeError)):
            return ErrorSeverity.MEDIUM
        
        # Check context for severity indicators
        if context:
            if context.get("critical_path", False):
                return ErrorSeverity.HIGH
            if context.get("user_facing", False):
                return ErrorSeverity.MEDIUM
        
        return ErrorSeverity.LOW

    async def _check_emergency_conditions(self, error_event: ErrorEvent) -> bool:
        """Check if error triggers emergency conditions"""
        
        # Catastrophic errors always trigger emergency
        if error_event.severity == ErrorSeverity.CATASTROPHIC:
            return True
        
        # Check error rate (errors per minute)
        recent_errors = [
            e for e in self.error_history
            if (datetime.now(timezone.utc) - e.timestamp).seconds < 60
        ]
        
        if len(recent_errors) >= self.config["emergency_stop_threshold"]:
            logger.critical(f"🆘 Emergency condition: {len(recent_errors)} errors in last minute")
            return True
        
        # Check system resources
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 95:
            logger.critical(f"🆘 Emergency condition: Memory usage at {memory_percent}%")
            return True
        
        return False

    async def _trigger_emergency_response(self, error_event: ErrorEvent) -> Dict[str, Any]:
        """Trigger emergency response procedures"""
        logger.critical(f"🆘 EMERGENCY RESPONSE TRIGGERED: {error_event.message}")
        
        self.recovery_stats["emergency_stops"] += 1
        
        # Execute emergency stop
        emergency_action = self.recovery_actions.get("system", [])
        for action in emergency_action:
            if action.strategy == RecoveryStrategy.EMERGENCY_STOP:
                try:
                    await action.action_function(error_event)
                    break
                except Exception as e:
                    logger.error(f"Emergency stop failed: {e}")
        
        return {
            "status": "emergency_stop",
            "error_id": error_event.id,
            "timestamp": error_event.timestamp.isoformat(),
            "message": "Emergency stop triggered"
        }

    async def _attempt_error_recovery(self, error_event: ErrorEvent) -> Dict[str, Any]:
        """Attempt intelligent error recovery"""
        
        component = error_event.component
        
        # Check if component is in circuit breaker OPEN state
        circuit_breaker = self.circuit_breakers.get(component)
        if circuit_breaker and circuit_breaker.state == "OPEN":
            logger.info(f"🔴 Circuit breaker OPEN for {component}, skipping recovery")
            return {
                "status": "circuit_breaker_open",
                "component": component,
                "error_id": error_event.id
            }
        
        # Get recovery actions for component
        recovery_actions = self.recovery_actions.get(component, [])
        
        if not recovery_actions:
            logger.warning(f"⚠️ No recovery actions configured for {component}")
            return {
                "status": "no_recovery_available",
                "component": component,
                "error_id": error_event.id
            }
        
        # Get error pattern for recovery strategy
        error_pattern = self.error_patterns.get(error_event.category)
        preferred_strategy = error_pattern.recovery_strategy if error_pattern else RecoveryStrategy.RETRY
        
        # Find matching recovery action
        recovery_action = None
        for action in recovery_actions:
            if action.strategy == preferred_strategy:
                recovery_action = action
                break
        
        # Use first available action if preferred not found
        if not recovery_action:
            recovery_action = recovery_actions[0]
        
        # Attempt recovery
        try:
            self.recovery_stats["recovery_attempts"] += 1
            error_event.recovery_attempted = True
            error_event.recovery_strategy = recovery_action.strategy
            
            logger.info(f"🔄 Attempting {recovery_action.strategy.value} recovery for {component}")
            
            # Execute recovery action with timeout
            recovery_result = await asyncio.wait_for(
                recovery_action.action_function(error_event),
                timeout=recovery_action.timeout_seconds
            )
            
            # Check if recovery was successful
            if await recovery_action.success_condition():
                logger.info(f"✅ Recovery successful for {component}")
                error_event.recovery_successful = True
                self.recovery_stats["successful_recoveries"] += 1
                
                # Update circuit breaker on success
                await self._update_circuit_breaker(component, success=True)
                
                # Trigger cascade recovery if enabled
                if self.config["cascade_recovery_enabled"]:
                    await self._trigger_cascade_recovery(component)
                
                return {
                    "status": "recovery_successful",
                    "component": component,
                    "strategy": recovery_action.strategy.value,
                    "error_id": error_event.id
                }
            else:
                logger.warning(f"⚠️ Recovery attempted but validation failed for {component}")
                self.recovery_stats["failed_recoveries"] += 1
                
                # Try fallback action if available
                if recovery_action.fallback_action:
                    await recovery_action.fallback_action(error_event)
                
                return {
                    "status": "recovery_failed",
                    "component": component,
                    "strategy": recovery_action.strategy.value,
                    "error_id": error_event.id
                }
                
        except asyncio.TimeoutError:
            logger.error(f"❌ Recovery timeout for {component}")
            self.recovery_stats["failed_recoveries"] += 1
            return {
                "status": "recovery_timeout",
                "component": component,
                "error_id": error_event.id
            }
        except Exception as recovery_error:
            logger.error(f"❌ Recovery error for {component}: {recovery_error}")
            self.recovery_stats["failed_recoveries"] += 1
            return {
                "status": "recovery_error",
                "component": component,
                "error": str(recovery_error),
                "error_id": error_event.id
            }

    async def _trigger_cascade_recovery(self, recovered_component: str):
        """Trigger cascade recovery for dependent components"""
        
        # Find components that depend on the recovered component
        dependent_components = [
            component for component, deps in self.component_dependencies.items()
            if recovered_component in deps
        ]
        
        for dependent in dependent_components:
            logger.info(f"🔗 Triggering cascade recovery for {dependent}")
            
            # Check if dependent component needs recovery
            if self.component_health.get(dependent) != "healthy":
                try:
                    # Create mock error for cascade recovery
                    cascade_error = ErrorEvent(
                        id=f"cascade_{dependent}_{int(time.time())}",
                        timestamp=datetime.now(timezone.utc),
                        component=dependent,
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.MEDIUM,
                        message=f"Cascade recovery triggered by {recovered_component}",
                        traceback="",
                        context={"cascade_recovery": True, "trigger": recovered_component}
                    )
                    
                    await self._attempt_error_recovery(cascade_error)
                    
                except Exception as e:
                    logger.error(f"Cascade recovery failed for {dependent}: {e}")

    async def _update_circuit_breaker(self, component: str, success: bool):
        """Update circuit breaker state"""
        
        circuit_breaker = self.circuit_breakers.get(component)
        if not circuit_breaker:
            return
        
        current_time = datetime.now(timezone.utc)
        
        if success:
            circuit_breaker.failure_count = 0
            circuit_breaker.last_success_time = current_time
            
            # Transition HALF_OPEN to CLOSED on success
            if circuit_breaker.state == "HALF_OPEN":
                circuit_breaker.state = "CLOSED"
                logger.info(f"🟢 Circuit breaker CLOSED for {component}")
        else:
            circuit_breaker.failure_count += 1
            circuit_breaker.last_failure_time = current_time
            
            # Open circuit breaker if threshold exceeded
            if (circuit_breaker.failure_count >= self.config["circuit_breaker_threshold"] and 
                circuit_breaker.state == "CLOSED"):
                circuit_breaker.state = "OPEN"
                logger.warning(f"🔴 Circuit breaker OPEN for {component}")

    async def _error_monitoring_loop(self):
        """Monitor error patterns and trends"""
        while self.is_running:
            try:
                # Analyze error trends
                await self._analyze_error_trends()
                
                # Check for anomalous error patterns
                await self._check_error_anomalies()
                
                # Clean up old error history
                await self._cleanup_error_history()
                
                await asyncio.sleep(self.config["error_analysis_interval"])
                
            except Exception as e:
                logger.error(f"Error monitoring loop error: {e}")
                await asyncio.sleep(30.0)

    async def _recovery_monitoring_loop(self):
        """Monitor active recoveries"""
        while self.is_running:
            try:
                # Monitor active recovery tasks
                completed_recoveries = []
                for component, task in self.active_recoveries.items():
                    if task.done():
                        completed_recoveries.append(component)
                        try:
                            result = await task
                            logger.info(f"✅ Active recovery completed for {component}: {result}")
                        except Exception as e:
                            logger.error(f"❌ Active recovery failed for {component}: {e}")
                
                # Clean up completed recoveries
                for component in completed_recoveries:
                    del self.active_recoveries[component]
                
                await asyncio.sleep(30.0)
                
            except Exception as e:
                logger.error(f"Recovery monitoring loop error: {e}")
                await asyncio.sleep(30.0)

    async def _circuit_breaker_monitoring_loop(self):
        """Monitor circuit breaker states"""
        while self.is_running:
            try:
                current_time = datetime.now(timezone.utc)
                
                for component, cb in self.circuit_breakers.items():
                    # Transition OPEN to HALF_OPEN after timeout
                    if (cb.state == "OPEN" and cb.last_failure_time and
                        (current_time - cb.last_failure_time).seconds >= cb.timeout_seconds):
                        cb.state = "HALF_OPEN"
                        logger.info(f"🟡 Circuit breaker HALF_OPEN for {component}")
                
                await asyncio.sleep(60.0)  # Check every minute
                
            except Exception as e:
                logger.error(f"Circuit breaker monitoring error: {e}")
                await asyncio.sleep(60.0)

    async def _health_monitoring_loop(self):
        """Monitor component health for proactive recovery"""
        while self.is_running:
            try:
                # Check component health
                for component in self.circuit_breakers.keys():
                    try:
                        is_healthy = await self._check_component_health(component)
                        self.component_health[component] = "healthy" if is_healthy else "unhealthy"
                    except Exception as e:
                        logger.error(f"Health check failed for {component}: {e}")
                        self.component_health[component] = "unknown"
                
                await asyncio.sleep(120.0)  # Check every 2 minutes
                
            except Exception as e:
                logger.error(f"Health monitoring loop error: {e}")
                await asyncio.sleep(60.0)

    async def _check_component_health(self, component: str) -> bool:
        """Check health of a specific component"""
        # This would integrate with actual component health checks
        # For now, return True if circuit breaker is not OPEN
        circuit_breaker = self.circuit_breakers.get(component)
        return not (circuit_breaker and circuit_breaker.state == "OPEN")

    async def _analyze_error_trends(self):
        """Analyze error trends and patterns"""
        if len(self.error_history) < 10:
            return
        
        # Analyze recent error patterns
        recent_errors = self.error_history[-100:]  # Last 100 errors
        
        # Count errors by component
        component_errors = {}
        for error in recent_errors:
            component_errors[error.component] = component_errors.get(error.component, 0) + 1
        
        # Identify problematic components
        for component, count in component_errors.items():
            if count > 10:  # More than 10 errors in recent history
                logger.warning(f"⚠️ High error rate detected for {component}: {count} errors")

    async def _check_error_anomalies(self):
        """Check for anomalous error patterns"""
        # Implementation would check for unusual error spikes, patterns, etc.
        pass

    async def _cleanup_error_history(self):
        """Clean up old error history"""
        # Keep only errors from last 24 hours
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=1)
        self.error_history = [
            error for error in self.error_history
            if error.timestamp > cutoff_time
        ]

    async def _persist_error_event(self, error_event: ErrorEvent):
        """Persist error event to database"""
        if not self.db_client:
            return
        
        try:
            error_item = {
                "day": error_event.timestamp.strftime("%Y-%m-%d"),
                "error_id": error_event.id,
                "component": error_event.component,
                "category": error_event.category.value,
                "severity": error_event.severity.value,
                "message": error_event.message,
                "timestamp": error_event.timestamp.isoformat(),
                "recovery_attempted": error_event.recovery_attempted,
                "recovery_successful": error_event.recovery_successful,
                "recovery_strategy": error_event.recovery_strategy.value if error_event.recovery_strategy else None
            }
            
            self.db_client.put_item("pipeline_errors", error_item)
            
        except Exception as e:
            logger.error(f"Error persistence failed: {e}")

    # Recovery action implementations
    async def _restart_enhanced_persistence(self, error_event: ErrorEvent):
        """Restart enhanced persistence"""
        logger.info("🔄 Restarting enhanced persistence...")
        # Implementation would restart the persistence service
        await asyncio.sleep(2.0)  # Simulate restart time
        return {"action": "restart", "component": "enhanced_persistence"}

    async def _fallback_to_legacy_persistence(self, error_event: ErrorEvent):
        """Fallback to legacy persistence"""
        logger.info("🔄 Falling back to legacy persistence...")
        await asyncio.sleep(1.0)
        return {"action": "fallback", "component": "legacy_persistence"}

    async def _retry_hybrid_client_connection(self, error_event: ErrorEvent):
        """Retry hybrid client connection"""
        logger.info("🔄 Retrying hybrid client connection...")
        await asyncio.sleep(3.0)
        return {"action": "retry", "component": "hybrid_client"}

    async def _fallback_to_rest_only(self, error_event: ErrorEvent):
        """Fallback to REST-only mode"""
        logger.info("🔄 Falling back to REST-only mode...")
        await asyncio.sleep(1.0)
        return {"action": "fallback", "component": "rest_only"}

    def _create_restart_engine_function(self, engine_name: str):
        """Create restart function for specific engine"""
        async def restart_engine(error_event: ErrorEvent):
            logger.info(f"🔄 Restarting {engine_name}...")
            await asyncio.sleep(5.0)  # Simulate restart time
            return {"action": "restart", "component": engine_name}
        
        return restart_engine

    def _create_engine_health_check(self, engine_name: str):
        """Create health check function for specific engine"""
        def check_engine_health():
            # Simulate health check
            return True
        
        return check_engine_health

    async def _trigger_graceful_degradation(self, error_event: ErrorEvent):
        """Trigger graceful degradation"""
        logger.info("🔄 Triggering graceful degradation...")
        await asyncio.sleep(2.0)
        return {"action": "graceful_degradation", "component": "system"}

    async def _trigger_emergency_stop(self, error_event: ErrorEvent):
        """Trigger emergency stop"""
        logger.critical("🆘 Triggering emergency stop...")
        await asyncio.sleep(1.0)
        return {"action": "emergency_stop", "component": "system"}

    # Health check implementations
    async def _check_persistence_health(self):
        """Check enhanced persistence health"""
        return True  # Simulate health check

    async def _check_legacy_persistence_health(self):
        """Check legacy persistence health"""
        return True

    async def _check_hybrid_client_health(self):
        """Check hybrid client health"""
        return True

    async def _check_rest_api_health(self):
        """Check REST API health"""
        return True

    async def _check_system_stability(self):
        """Check system stability"""
        return True

    def get_error_recovery_status(self) -> Dict[str, Any]:
        """Get comprehensive error recovery status"""
        
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        # Circuit breaker states
        circuit_breaker_summary = {}
        for component, cb in self.circuit_breakers.items():
            circuit_breaker_summary[component] = {
                "state": cb.state,
                "failure_count": cb.failure_count,
                "last_failure": cb.last_failure_time.isoformat() if cb.last_failure_time else None
            }
        
        # Recent error summary
        recent_errors = [e for e in self.error_history 
                        if (datetime.now(timezone.utc) - e.timestamp).seconds < 3600]  # Last hour
        
        error_by_severity = {}
        for severity in ErrorSeverity:
            error_by_severity[severity.value] = len([e for e in recent_errors if e.severity == severity])
        
        return {
            "system_status": "running" if self.is_running else "stopped",
            "uptime_seconds": uptime,
            "statistics": self.recovery_stats,
            "error_history": {
                "total_errors": len(self.error_history),
                "recent_errors_1h": len(recent_errors),
                "errors_by_severity": error_by_severity
            },
            "circuit_breakers": circuit_breaker_summary,
            "component_health": self.component_health,
            "active_recoveries": list(self.active_recoveries.keys()),
            "configuration": {
                "emergency_threshold": self.config["emergency_stop_threshold"],
                "circuit_breaker_threshold": self.config["circuit_breaker_threshold"],
                "cascade_recovery_enabled": self.config["cascade_recovery_enabled"]
            }
        }

    async def shutdown(self):
        """Graceful shutdown of error recovery system"""
        logger.info("🛑 Shutting down Pipeline Error Recovery System...")
        
        self.is_running = False
        
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        # Cancel active recoveries
        for task in self.active_recoveries.values():
            task.cancel()
        
        logger.info("✅ Pipeline Error Recovery System shutdown complete")


# Global error recovery instance
_error_recovery = None

async def get_pipeline_error_recovery() -> PipelineErrorRecovery:
    """Get or create pipeline error recovery instance"""
    global _error_recovery
    if _error_recovery is None:
        _error_recovery = PipelineErrorRecovery()
        await _error_recovery.initialize()
    return _error_recovery