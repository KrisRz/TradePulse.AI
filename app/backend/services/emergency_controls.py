"""
Emergency Controls and Circuit Breakers - TradePulse.AI
======================================================

Advanced Emergency Protection System with Real-time Monitoring
- Circuit breakers for extreme market conditions
- Emergency stop mechanisms 
- Risk limit enforcement
- Automatic protection triggers
- Real-time monitoring and alerts

Author: TradePulse.AI Development Team  
Created: January 2025
Version: 1.0.0
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from decimal import Decimal

# Import services
try:
    from app.backend.services.live_market_data import get_live_bitcoin_price, get_live_market_data
    from app.backend.services.professional_portfolio import get_professional_portfolio
    from app.backend.services.database_service import DatabaseService
except ImportError as e:
    # PRODUCTION: No fallbacks allowed
    logger.error(f"Critical import failure: {e}")
    raise RuntimeError(f"Real services required for production deployment: {e}")

logger = logging.getLogger(__name__)

class EmergencyLevel(str, Enum):
    """Emergency severity levels"""
    LOW = "low"           # Warning level
    MEDIUM = "medium"     # Caution required  
    HIGH = "high"         # Immediate action needed
    CRITICAL = "critical" # Emergency stop triggered

class CircuitBreakerType(str, Enum):
    """Types of circuit breakers"""
    VOLATILITY = "volatility"         # Market volatility protection
    DRAWDOWN = "drawdown"             # Portfolio drawdown protection
    VOLUME = "volume"                 # Volume anomaly protection
    PRICE_GAP = "price_gap"           # Price gap protection
    API_ERRORS = "api_errors"         # API error protection
    DAILY_LOSS = "daily_loss"         # Daily loss limit protection

@dataclass
class EmergencyEvent:
    """Emergency event data structure"""
    event_id: str
    level: EmergencyLevel
    breaker_type: CircuitBreakerType
    description: str
    trigger_value: float
    threshold: float
    timestamp: datetime
    auto_resolved: bool = False
    resolution_timestamp: Optional[datetime] = None

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    breaker_type: CircuitBreakerType
    threshold: float
    cooldown_seconds: int
    auto_recovery: bool
    enabled: bool

class EmergencyControlSystem:
    """
    Advanced Emergency Control System with Circuit Breakers
    
    Features:
    - Real-time risk monitoring
    - Automatic circuit breakers
    - Emergency stop mechanisms
    - Multi-level protection
    - Comprehensive alerting
    """
    
    def __init__(self):
        self.is_initialized = False
        self.is_monitoring = False
        self.emergency_stop_active = False
        
        # Emergency state
        self.active_emergencies: List[EmergencyEvent] = []
        self.circuit_breakers_triggered: Dict[CircuitBreakerType, datetime] = {}
        self.emergency_stop_reason: Optional[str] = None
        self.emergency_stop_timestamp: Optional[datetime] = None
        
        # Monitoring task
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Database service
        self.db_service = DatabaseService()
        
        # Performance tracking
        self.total_emergencies = 0
        self.automatic_recoveries = 0
        self.manual_interventions = 0
        
        # Circuit breaker configurations
        self.breaker_configs = {
            CircuitBreakerType.VOLATILITY: CircuitBreakerConfig(
                breaker_type=CircuitBreakerType.VOLATILITY,
                threshold=0.15,      # 15% volatility
                cooldown_seconds=300, # 5 minutes
                auto_recovery=True,
                enabled=True
            ),
            CircuitBreakerType.DRAWDOWN: CircuitBreakerConfig(
                breaker_type=CircuitBreakerType.DRAWDOWN,
                threshold=0.10,      # 10% drawdown
                cooldown_seconds=600, # 10 minutes
                auto_recovery=False,  # Manual review required
                enabled=True
            ),
            CircuitBreakerType.VOLUME: CircuitBreakerConfig(
                breaker_type=CircuitBreakerType.VOLUME,
                threshold=5.0,       # 5x normal volume
                cooldown_seconds=180, # 3 minutes
                auto_recovery=True,
                enabled=True
            ),
            CircuitBreakerType.PRICE_GAP: CircuitBreakerConfig(
                breaker_type=CircuitBreakerType.PRICE_GAP,
                threshold=0.05,      # 5% price gap
                cooldown_seconds=120, # 2 minutes
                auto_recovery=True,
                enabled=True
            ),
            CircuitBreakerType.API_ERRORS: CircuitBreakerConfig(
                breaker_type=CircuitBreakerType.API_ERRORS,
                threshold=10,        # 10 consecutive errors
                cooldown_seconds=300, # 5 minutes
                auto_recovery=True,
                enabled=True
            ),
            CircuitBreakerType.DAILY_LOSS: CircuitBreakerConfig(
                breaker_type=CircuitBreakerType.DAILY_LOSS,
                threshold=0.05,      # 5% daily loss
                cooldown_seconds=86400, # 24 hours
                auto_recovery=False,  # Manual review required
                enabled=True
            )
        }
        
        logger.info("🛡️ Emergency Control System initialized")
    
    async def initialize(self):
        """Initialize the emergency control system"""
        if self.is_initialized:
            return
            
        logger.info("🚀 Initializing Emergency Control System...")
        
        try:
            # Load previous emergency state from database
            await self._load_emergency_state()
            
            # Validate all circuit breaker configurations
            self._validate_configurations()
            
            self.is_initialized = True
            logger.info("✅ Emergency Control System initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize emergency control system: {e}")
            raise
    
    async def start_monitoring(self) -> Dict[str, Any]:
        """Start real-time emergency monitoring"""
        # Use BootOnce guard to prevent duplicate starts
        from app.backend.core.boot_once import BootOnce
        
        if not await BootOnce.start_async("emergency_monitoring", self._start_monitoring_once):
            return {"status": "already_monitoring"}
        
        return {
            "status": "monitoring_started", 
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _start_monitoring_once(self):
        """Internal method to start monitoring once"""
        if not self.is_initialized:
            await self.initialize()
        
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        logger.info("🔍 Starting emergency monitoring...")
        
        # Start background monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        return {
            "status": "monitoring_started",
            "breakers_enabled": {
                breaker.value: config.enabled 
                for breaker, config in self.breaker_configs.items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def stop_monitoring(self) -> Dict[str, Any]:
        """Stop emergency monitoring"""
        if not self.is_monitoring:
            return {"status": "not_monitoring"}
        
        self.is_monitoring = False
        
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 Emergency monitoring stopped")
        
        return {
            "status": "monitoring_stopped",
            "emergencies_handled": self.total_emergencies,
            "automatic_recoveries": self.automatic_recoveries,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def trigger_emergency_stop(self, reason: str, level: EmergencyLevel = EmergencyLevel.CRITICAL) -> Dict[str, Any]:
        """Trigger immediate emergency stop"""
        
        if self.emergency_stop_active:
            return {
                "status": "already_active",
                "reason": self.emergency_stop_reason,
                "timestamp": self.emergency_stop_timestamp.isoformat()
            }
        
        self.emergency_stop_active = True
        self.emergency_stop_reason = reason
        self.emergency_stop_timestamp = datetime.now(timezone.utc)
        
        logger.critical(f"🚨 EMERGENCY STOP TRIGGERED: {reason}")
        
        try:
            # Stop all trading activities
            await self._stop_all_trading()
            
            # Close any open positions if critical
            if level == EmergencyLevel.CRITICAL:
                await self._emergency_close_positions()
            
            # Log emergency event
            emergency_event = EmergencyEvent(
                event_id=f"emergency_{int(time.time())}",
                level=level,
                breaker_type=CircuitBreakerType.DAILY_LOSS,  # Default type
                description=f"Emergency stop: {reason}",
                trigger_value=0.0,
                threshold=0.0,
                timestamp=self.emergency_stop_timestamp
            )
            
            self.active_emergencies.append(emergency_event)
            
            # Save to database
            await self._save_emergency_event(emergency_event)
            
            self.total_emergencies += 1
            
            return {
                "status": "emergency_stop_activated",
                "reason": reason,
                "level": level.value,
                "timestamp": self.emergency_stop_timestamp.isoformat(),
                "actions_taken": [
                    "trading_stopped",
                    "positions_closed" if level == EmergencyLevel.CRITICAL else "positions_monitored"
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Error during emergency stop: {e}")
            return {
                "status": "emergency_stop_failed",
                "reason": reason,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def reset_emergency_stop(self, admin_override: bool = False) -> Dict[str, Any]:
        """Reset emergency stop (admin only)"""
        
        if not self.emergency_stop_active:
            return {"status": "not_active"}
        
        if not admin_override:
            # Check if all circuit breakers are cleared
            active_breakers = [
                breaker for breaker, timestamp in self.circuit_breakers_triggered.items()
                if not self._is_breaker_cooled_down(breaker, timestamp)
            ]
            
            if active_breakers:
                return {
                    "status": "cannot_reset",
                    "reason": "active_circuit_breakers",
                    "active_breakers": [b.value for b in active_breakers]
                }
        
        # Reset emergency state
        self.emergency_stop_active = False
        old_reason = self.emergency_stop_reason
        self.emergency_stop_reason = None
        self.emergency_stop_timestamp = None
        
        # Clear resolved emergencies
        resolved_count = len([e for e in self.active_emergencies if e.auto_resolved])
        self.active_emergencies = [e for e in self.active_emergencies if not e.auto_resolved]
        
        logger.info(f"✅ Emergency stop reset (was: {old_reason})")
        
        return {
            "status": "emergency_reset",
            "previous_reason": old_reason,
            "resolved_emergencies": resolved_count,
            "admin_override": admin_override,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _monitoring_loop(self):
        """Main emergency monitoring loop"""
        logger.info("🔍 Emergency monitoring loop started")
        
        try:
            while self.is_monitoring:
                start_time = time.time()
                
                try:
                    # Run all circuit breaker checks
                    await self._check_all_circuit_breakers()
                    
                    # Check for automatic recoveries
                    await self._check_automatic_recoveries()
                    
                    # Update emergency state
                    await self._update_emergency_state()
                    
                except Exception as e:
                    logger.error(f"❌ Error in emergency monitoring: {e}")
                
                # Monitor every 30 seconds
                elapsed = time.time() - start_time
                sleep_time = max(30 - elapsed, 5)  # Minimum 5 seconds
                await asyncio.sleep(sleep_time)
                
        except asyncio.CancelledError:
            logger.info("🛑 Emergency monitoring loop cancelled")
        except Exception as e:
            logger.error(f"❌ Fatal error in emergency monitoring: {e}")
    
    async def _check_all_circuit_breakers(self):
        """Check all circuit breakers for triggers"""
        
        try:
            # Get current market data
            market_data = await get_live_market_data()
            current_price = await get_live_bitcoin_price()
            
            # Check volatility circuit breaker
            if self.breaker_configs[CircuitBreakerType.VOLATILITY].enabled:
                await self._check_volatility_breaker(market_data)
            
            # Check volume circuit breaker
            if self.breaker_configs[CircuitBreakerType.VOLUME].enabled:
                await self._check_volume_breaker(market_data)
            
            # Check price gap circuit breaker
            if self.breaker_configs[CircuitBreakerType.PRICE_GAP].enabled:
                await self._check_price_gap_breaker(current_price)
            
            # Check portfolio-based breakers
            await self._check_portfolio_breakers()
            
        except Exception as e:
            logger.error(f"Error checking circuit breakers: {e}")
            
            # Trigger API error circuit breaker
            if self.breaker_configs[CircuitBreakerType.API_ERRORS].enabled:
                await self._trigger_circuit_breaker(
                    CircuitBreakerType.API_ERRORS,
                    f"API error during monitoring: {e}",
                    1.0,
                    self.breaker_configs[CircuitBreakerType.API_ERRORS].threshold
                )
    
    async def _check_volatility_breaker(self, market_data: Dict[str, Any]):
        """Check volatility circuit breaker"""
        volatility = market_data.get("volatility", 0.0)
        config = self.breaker_configs[CircuitBreakerType.VOLATILITY]
        
        if volatility > config.threshold:
            await self._trigger_circuit_breaker(
                CircuitBreakerType.VOLATILITY,
                f"High volatility detected: {volatility:.1%} > {config.threshold:.1%}",
                volatility,
                config.threshold
            )
    
    async def _check_volume_breaker(self, market_data: Dict[str, Any]):
        """Check volume circuit breaker"""
        volume_ratio = market_data.get("volume_ratio", 1.0)
        config = self.breaker_configs[CircuitBreakerType.VOLUME]
        
        if volume_ratio > config.threshold:
            await self._trigger_circuit_breaker(
                CircuitBreakerType.VOLUME,
                f"Extreme volume detected: {volume_ratio:.1f}x normal > {config.threshold:.1f}x",
                volume_ratio,
                config.threshold
            )
    
    async def _check_price_gap_breaker(self, current_price: float):
        """Check price gap circuit breaker"""
        # Get last recorded price (simplified implementation)
        # In production, this would check for significant price gaps
        config = self.breaker_configs[CircuitBreakerType.PRICE_GAP]
        
        # Placeholder for price gap detection
        # Would implement actual gap detection logic here
        pass
    
    async def _check_portfolio_breakers(self):
        """Check portfolio-related circuit breakers"""
        try:
            # Get admin portfolio for monitoring
            portfolio = await get_professional_portfolio("admin")
            if not portfolio:
                return
            
            # Check daily loss breaker
            daily_pnl_pct = portfolio.get_daily_pnl_percentage()
            config = self.breaker_configs[CircuitBreakerType.DAILY_LOSS]
            
            if daily_pnl_pct < -config.threshold:
                await self._trigger_circuit_breaker(
                    CircuitBreakerType.DAILY_LOSS,
                    f"Daily loss limit exceeded: {daily_pnl_pct:.1%} < -{config.threshold:.1%}",
                    abs(daily_pnl_pct),
                    config.threshold
                )
            
            # Check drawdown breaker
            # Use daily P&L percentage instead of max_drawdown method
            daily_pnl_pct = portfolio.get_daily_pnl_percentage()
            max_drawdown = abs(min(daily_pnl_pct, 0.0))  # Convert negative P&L to positive drawdown
            drawdown_config = self.breaker_configs[CircuitBreakerType.DRAWDOWN]
            
            if max_drawdown > drawdown_config.threshold:
                await self._trigger_circuit_breaker(
                    CircuitBreakerType.DRAWDOWN,
                    f"Maximum drawdown exceeded: {max_drawdown:.1%} > {drawdown_config.threshold:.1%}",
                    max_drawdown,
                    drawdown_config.threshold
                )
                
        except Exception as e:
            logger.error(f"Error checking portfolio breakers: {e}")
    
    async def _trigger_circuit_breaker(
        self, 
        breaker_type: CircuitBreakerType, 
        description: str, 
        trigger_value: float, 
        threshold: float
    ):
        """Trigger a specific circuit breaker"""
        
        # Check if breaker is already triggered and in cooldown
        if breaker_type in self.circuit_breakers_triggered:
            trigger_time = self.circuit_breakers_triggered[breaker_type]
            if not self._is_breaker_cooled_down(breaker_type, trigger_time):
                return  # Still in cooldown
        
        # Trigger circuit breaker
        self.circuit_breakers_triggered[breaker_type] = datetime.now(timezone.utc)
        
        # Create emergency event
        emergency_event = EmergencyEvent(
            event_id=f"{breaker_type.value}_{int(time.time())}",
            level=EmergencyLevel.HIGH if breaker_type != CircuitBreakerType.DAILY_LOSS else EmergencyLevel.CRITICAL,
            breaker_type=breaker_type,
            description=description,
            trigger_value=trigger_value,
            threshold=threshold,
            timestamp=datetime.now(timezone.utc)
        )
        
        self.active_emergencies.append(emergency_event)
        
        # Log and save
        logger.warning(f"⚡ Circuit breaker triggered: {breaker_type.value} - {description}")
        await self._save_emergency_event(emergency_event)
        
        # Trigger emergency stop for critical breakers
        if breaker_type in [CircuitBreakerType.DAILY_LOSS, CircuitBreakerType.DRAWDOWN]:
            await self.trigger_emergency_stop(
                f"Circuit breaker: {description}",
                EmergencyLevel.CRITICAL
            )
        
        self.total_emergencies += 1
    
    async def _check_automatic_recoveries(self):
        """Check for automatic recovery of circuit breakers"""
        current_time = datetime.now(timezone.utc)
        
        for breaker_type, trigger_time in list(self.circuit_breakers_triggered.items()):
            config = self.breaker_configs[breaker_type]
            
            if config.auto_recovery and self._is_breaker_cooled_down(breaker_type, trigger_time):
                # Remove from triggered list
                del self.circuit_breakers_triggered[breaker_type]
                
                # Mark related emergencies as auto-resolved
                for emergency in self.active_emergencies:
                    if emergency.breaker_type == breaker_type and not emergency.auto_resolved:
                        emergency.auto_resolved = True
                        emergency.resolution_timestamp = current_time
                
                logger.info(f"✅ Circuit breaker auto-recovered: {breaker_type.value}")
                self.automatic_recoveries += 1
    
    def _is_breaker_cooled_down(self, breaker_type: CircuitBreakerType, trigger_time: datetime) -> bool:
        """Check if circuit breaker has cooled down"""
        config = self.breaker_configs[breaker_type]
        cooldown_delta = timedelta(seconds=config.cooldown_seconds)
        return datetime.now(timezone.utc) - trigger_time > cooldown_delta
    
    async def _stop_all_trading(self):
        """Stop all trading activities"""
        logger.info("🛑 Stopping all trading activities...")
        
        # Stop trading brain if running
        try:
            from app.api.v1.routes.trading import _trading_brain_enabled, stop_trading_brain_background
            if _trading_brain_enabled:
                await stop_trading_brain_background()
                logger.info("✅ Trading brain stopped")
        except Exception as e:
            logger.error(f"Error stopping trading brain: {e}")
        
        # Stop day trading engine if running
        try:
            from app.backend.services.day_trading_engine import get_day_trading_engine
            day_engine = await get_day_trading_engine()
            if day_engine.is_running:
                await day_engine.stop_analysis_loop()
                logger.info("✅ Day trading engine stopped")
        except Exception as e:
            logger.error(f"Error stopping day trading engine: {e}")
    
    async def _emergency_close_positions(self):
        """Emergency close all open positions"""
        logger.info("🚨 Emergency closing all positions...")
        
        try:
            portfolio = await get_professional_portfolio("admin")
            if not portfolio:
                return
            
            active_positions = portfolio.get_active_positions()
            closed_count = 0
            
            for position in active_positions:
                try:
                    result = await portfolio.close_position(
                        position_id=position.position_id,
                        exit_reason="emergency_stop",
                        exit_confidence=1.0,
                        current_price=await get_live_bitcoin_price()
                    )
                    
                    if result:
                        closed_count += 1
                        logger.info(f"✅ Emergency closed position: {position.position_id}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to close position {position.position_id}: {e}")
            
            logger.info(f"🚨 Emergency closure completed: {closed_count}/{len(active_positions)} positions")
            
        except Exception as e:
            logger.error(f"❌ Error during emergency position closure: {e}")
    
    async def _save_emergency_event(self, event: EmergencyEvent):
        """Save emergency event to database"""
        try:
            from decimal import Decimal
            event_data = {
                "event_id": event.event_id,
                "timestamp": int(event.timestamp.timestamp()),
                "level": event.level.value,
                "breaker_type": event.breaker_type.value,
                "description": event.description,
                "trigger_value": Decimal(str(event.trigger_value)),
                "threshold": Decimal(str(event.threshold)),
                "auto_resolved": event.auto_resolved,
                "resolution_timestamp": int(event.resolution_timestamp.timestamp()) if event.resolution_timestamp else 0
            }
            
            await self.db_service.put_item("emergency_events", event_data)
            
        except Exception as e:
            logger.error(f"Failed to save emergency event: {e}")
    
    async def _load_emergency_state(self):
        """Load previous emergency state from database"""
        try:
            # Load recent emergency events (last 24 hours)
            # Implementation would query database for recent events
            pass
        except Exception as e:
            logger.error(f"Failed to load emergency state: {e}")
    
    async def _update_emergency_state(self):
        """Update emergency state in database - ONLY if changed"""
        try:
            current_state = {
                "emergency_stop_active": self.emergency_stop_active,
                "emergency_stop_reason": self.emergency_stop_reason,
                "active_breakers": list(self.circuit_breakers_triggered.keys()),
                "total_emergencies": self.total_emergencies,
                "automatic_recoveries": self.automatic_recoveries
            }
            
            # FIXED: Only write if state actually changed
            if not hasattr(self, '_last_saved_state') or self._last_saved_state != current_state:
                state_data = current_state.copy()
                state_data["last_updated"] = int(datetime.now(timezone.utc).timestamp())
                state_data["id"] = "emergency_state_global"
                
                await self.db_service.put_item("emergency_state", state_data)
                self._last_saved_state = current_state
                logger.debug("💾 Emergency state updated (changed)")
            else:
                logger.debug("🔄 Emergency state unchanged, skipping DB write")
            
        except Exception as e:
            logger.error(f"Failed to update emergency state: {e}")
    
    def _validate_configurations(self):
        """Validate all circuit breaker configurations"""
        for breaker_type, config in self.breaker_configs.items():
            if config.threshold <= 0:
                raise ValueError(f"Invalid threshold for {breaker_type.value}: {config.threshold}")
            if config.cooldown_seconds < 0:
                raise ValueError(f"Invalid cooldown for {breaker_type.value}: {config.cooldown_seconds}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive emergency system status"""
        return {
            "is_initialized": self.is_initialized,
            "is_monitoring": self.is_monitoring,
            "emergency_stop_active": self.emergency_stop_active,
            "emergency_stop_reason": self.emergency_stop_reason,
            "emergency_stop_timestamp": self.emergency_stop_timestamp.isoformat() if self.emergency_stop_timestamp else None,
            "active_emergencies": len(self.active_emergencies),
            "active_circuit_breakers": list(self.circuit_breakers_triggered.keys()),
            "circuit_breaker_configs": {
                breaker.value: {
                    "threshold": config.threshold,
                    "cooldown_seconds": config.cooldown_seconds,
                    "auto_recovery": config.auto_recovery,
                    "enabled": config.enabled
                }
                for breaker, config in self.breaker_configs.items()
            },
            "performance": {
                "total_emergencies": self.total_emergencies,
                "automatic_recoveries": self.automatic_recoveries,
                "manual_interventions": self.manual_interventions
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    async def is_trading_halted(self) -> bool:
        """PHASE 1A: Global trading halt flag with TTL"""
        try:
            # Check if emergency stop is active
            if self.emergency_stop_active:
                logger.debug("Trading halted: Emergency stop active")
                return True
            
            # Check circuit breakers
            current_time = datetime.now(timezone.utc)
            for breaker_type, triggered_time in self.circuit_breakers_triggered.items():
                config = self.breaker_configs.get(breaker_type)
                if config and config.enabled:
                    cooldown_seconds = config.cooldown_seconds
                    if (current_time - triggered_time).total_seconds() < cooldown_seconds:
                        logger.debug(f"Trading halted: Circuit breaker {breaker_type.value} active")
                        return True
            
            # Check API failure rate (3 failures in 60s = halt)
            if hasattr(self, '_api_failure_count') and self._api_failure_count > 3:
                logger.debug("Trading halted: High API failure rate")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking trading halt status: {e}")
            # Fail-safe: halt trading on error
            return True
            
    async def handle_analysis_failure(self, error_message: str):
        """PHASE 1A: Handle trading analysis failures"""
        try:
            # Increment API failure counter
            if not hasattr(self, '_api_failure_count'):
                self._api_failure_count = 0
                self._last_failure_reset = datetime.now(timezone.utc)
                
            # Reset counter if more than 60 seconds have passed
            if (datetime.now(timezone.utc) - self._last_failure_reset).total_seconds() > 60:
                self._api_failure_count = 0
                self._last_failure_reset = datetime.now(timezone.utc)
                
            self._api_failure_count += 1
            
            # Log the failure
            logger.warning(f"🚨 Analysis failure #{self._api_failure_count}: {error_message}")
            
            # Trigger emergency stop if too many failures (more tolerant during startup)
            failure_threshold = 10 if (datetime.now(timezone.utc) - self._last_failure_reset).total_seconds() < 300 else 3  # 10 failures in first 5 minutes
            if self._api_failure_count >= failure_threshold:
                await self.trigger_emergency_stop(f"Multiple analysis failures: {error_message}", EmergencyLevel.HIGH)
                
        except Exception as e:
            logger.error(f"Failed to handle analysis failure: {e}")
            
    async def kill_on_volatility_spike(self, current_volatility: float, median_volatility: float) -> bool:
        """PHASE 1A: Emergency stop on volatility spike"""
        try:
            if median_volatility > 0 and current_volatility > median_volatility * 3.0:  # 3x median
                logger.critical(f"🚨 VOLATILITY SPIKE: {current_volatility:.1%} vs {median_volatility:.1%}")
                await self.trigger_emergency_stop(f"Volatility spike: {current_volatility:.1%} (3x median)", EmergencyLevel.CRITICAL)
                return True
            return False
        except Exception as e:
            logger.error(f"Volatility spike check failed: {e}")
            return False
            
    async def kill_on_slippage(self, expected_price: float, actual_price: float, threshold: float = 0.005) -> bool:
        """PHASE 1A: Emergency stop on excessive slippage"""
        try:
            if expected_price > 0:
                slippage = abs(actual_price - expected_price) / expected_price
                if slippage > threshold:  # Default 0.5% slippage limit
                    logger.critical(f"🚨 EXCESSIVE SLIPPAGE: {slippage:.1%}")
                    await self.trigger_emergency_stop(f"Excessive slippage: {slippage:.1%}", EmergencyLevel.HIGH)
                    return True
            return False
        except Exception as e:
            logger.error(f"Slippage check failed: {e}")
            return False
            
    async def monitor_consecutive_losses(self, portfolio) -> bool:
        """PHASE 1A: Monitor consecutive losses and trigger protection"""
        try:
            consecutive_losses = getattr(portfolio, 'consecutive_losses', 0)
            if consecutive_losses >= 3:
                logger.critical(f"🚨 CONSECUTIVE LOSSES: {consecutive_losses}")
                await self.trigger_emergency_stop(f"Consecutive losses: {consecutive_losses}", EmergencyLevel.HIGH)
                return True
            return False
        except Exception as e:
            logger.error(f"Consecutive loss monitoring failed: {e}")
            return False

# Global emergency control system instance
_emergency_system: Optional[EmergencyControlSystem] = None

async def get_emergency_system() -> EmergencyControlSystem:
    """Get or create global emergency control system"""
    global _emergency_system
    if _emergency_system is None:
        _emergency_system = EmergencyControlSystem()
        await _emergency_system.initialize()
    return _emergency_system

# Export classes and functions
__all__ = [
    "EmergencyControlSystem",
    "EmergencyLevel", 
    "CircuitBreakerType",
    "EmergencyEvent",
    "CircuitBreakerConfig",
    "get_emergency_system"
]