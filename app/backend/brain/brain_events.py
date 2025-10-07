"""
BRAIN Events System - TradePulse.AI
==================================

Professional event system for inter-component communication in the BRAIN controller.
Provides type-safe event contracts and logging for all trading operations.

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, TypeVar, Generic
from pydantic import BaseModel

from .brain_state import TradingSignal, RiskContext, EntryAnalysis, ExitAnalysis, Position, MarketTick

logger = logging.getLogger(__name__)

class EventType(str, Enum):
    """Types of BRAIN events"""
    # Lifecycle events
    BRAIN_STARTED = "brain_started"
    BRAIN_STOPPED = "brain_stopped"
    STATE_CHANGED = "state_changed"
    SYSTEM_READY = "system_ready"
    
    # Data events
    TICK_RECEIVED = "tick_received"
    CANDLES_UPDATED = "candles_updated"
    DATA_GAP_DETECTED = "data_gap_detected"
    
    # Signal events
    SIGNAL_GENERATED = "signal_generated"
    SIGNAL_EXPIRED = "signal_expired"
    
    # Risk events
    RISK_ASSESSED = "risk_assessed"
    RISK_BLOCKED = "risk_blocked"
    EMERGENCY_TRIGGERED = "emergency_triggered"
    
    # Trading events
    ENTRY_ANALYZED = "entry_analyzed"
    EXIT_ANALYZED = "exit_analyzed"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    ORDER_EXECUTED = "order_executed"
    
    # System events
    API_FAILURE = "api_failure"
    CONNECTION_LOST = "connection_lost"
    CONNECTION_RESTORED = "connection_restored"
    PERFORMANCE_ALERT = "performance_alert"

class EventSeverity(str, Enum):
    """Event severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

# Base Event Classes

class BrainEvent(BaseModel):
    """Base class for all BRAIN events"""
    event_type: EventType
    timestamp: datetime
    severity: EventSeverity = EventSeverity.INFO
    component: str
    message: str
    metadata: Dict[str, Any] = {}
    
    class Config:
        arbitrary_types_allowed = True

class TickEvent(BrainEvent):
    """Market tick received event"""
    event_type: EventType = EventType.TICK_RECEIVED
    tick_data: MarketTick
    
    def __init__(self, tick_data: MarketTick, component: str = "market_data", **kwargs):
        super().__init__(
            event_type=EventType.TICK_RECEIVED,
            timestamp=datetime.now(timezone.utc),
            component=component,
            message=f"Tick received: {tick_data.symbol} @${tick_data.price}",
            tick_data=tick_data,
            **kwargs
        )

class SignalEvent(BrainEvent):
    """Trading signal generated event"""
    event_type: EventType = EventType.SIGNAL_GENERATED
    signal: TradingSignal
    
    def __init__(self, signal: TradingSignal, component: str = "enterprise_engine", **kwargs):
        super().__init__(
            event_type=EventType.SIGNAL_GENERATED,
            timestamp=datetime.now(timezone.utc),
            component=component,
            message=f"Signal: {signal.action} {signal.symbol} conf={signal.confidence:.2f}",
            signal=signal,
            **kwargs
        )

class RiskEvent(BrainEvent):
    """Risk assessment event"""
    risk_context: RiskContext
    action_taken: str
    
    def __init__(self, risk_context: RiskContext, action_taken: str, component: str = "risk_manager", **kwargs):
        event_type = EventType.RISK_BLOCKED if risk_context.block_reason else EventType.RISK_ASSESSED
        severity = EventSeverity.WARNING if risk_context.block_reason else EventSeverity.INFO
        
        super().__init__(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            severity=severity,
            component=component,
            message=f"Risk: {risk_context.risk_level.value} score={risk_context.risk_score:.2f} action={action_taken}",
            risk_context=risk_context,
            action_taken=action_taken,
            **kwargs
        )

class EntryEvent(BrainEvent):
    """Entry analysis event"""
    event_type: EventType = EventType.ENTRY_ANALYZED
    entry_analysis: EntryAnalysis
    
    def __init__(self, entry_analysis: EntryAnalysis, component: str = "entry_engine", **kwargs):
        action = "ENTER" if entry_analysis.should_enter else "WAIT"
        super().__init__(
            event_type=EventType.ENTRY_ANALYZED,
            timestamp=datetime.now(timezone.utc),
            component=component,
            message=f"Entry: {action} conf={entry_analysis.confidence:.2f} quality={entry_analysis.entry_quality}",
            entry_analysis=entry_analysis,
            **kwargs
        )

class ExitEvent(BrainEvent):
    """Exit analysis event"""
    event_type: EventType = EventType.EXIT_ANALYZED
    exit_analysis: ExitAnalysis
    position_id: str
    
    def __init__(self, exit_analysis: ExitAnalysis, position_id: str, component: str = "exit_engine", **kwargs):
        action = "EXIT" if exit_analysis.should_exit else "HOLD"
        super().__init__(
            event_type=EventType.EXIT_ANALYZED,
            timestamp=datetime.now(timezone.utc),
            component=component,
            message=f"Exit {position_id}: {action} reason={exit_analysis.exit_reason} pnl={exit_analysis.pnl_percent:.2f}%",
            exit_analysis=exit_analysis,
            position_id=position_id,
            **kwargs
        )

class PositionEvent(BrainEvent):
    """Position lifecycle event"""
    position: Position
    
    def __init__(self, position: Position, event_type: EventType, component: str = "portfolio", **kwargs):
        if event_type == EventType.POSITION_OPENED:
            message = f"Position opened: {position.position_id} {position.side} {position.quantity} @${position.entry_price}"
        else:
            message = f"Position closed: {position.position_id} PnL={position.pnl_percent:.2f}%"
            
        super().__init__(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            component=component,
            message=message,
            position=position,
            **kwargs
        )

class SystemEvent(BrainEvent):
    """System-level events"""
    
    def __init__(self, event_type: EventType, message: str, component: str, severity: EventSeverity = EventSeverity.INFO, **kwargs):
        super().__init__(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            severity=severity,
            component=component,
            message=message,
            **kwargs
        )

class StateChangeEvent(BrainEvent):
    """BRAIN state change event"""
    event_type: EventType = EventType.STATE_CHANGED
    old_state: str
    new_state: str
    
    def __init__(self, old_state: str, new_state: str, component: str = "brain_controller", **kwargs):
        super().__init__(
            event_type=EventType.STATE_CHANGED,
            timestamp=datetime.now(timezone.utc),
            component=component,
            message=f"State changed: {old_state} → {new_state}",
            old_state=old_state,
            new_state=new_state,
            **kwargs
        )

# Event Bus Implementation

EventHandler = Callable[[BrainEvent], None]

class BrainEventBus:
    """Professional event bus for BRAIN components"""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._event_history: List[BrainEvent] = []
        self._max_history = 1000  # Keep last 1000 events
        self._is_active = True
        
    def subscribe(self, event_type: EventType, handler: EventHandler):
        """Subscribe to specific event types"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Handler registered for {event_type.value}")
        
    def unsubscribe(self, event_type: EventType, handler: EventHandler):
        """Unsubscribe from event types"""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.debug(f"Handler unregistered for {event_type.value}")
            except ValueError:
                pass
                
    def publish(self, event: BrainEvent):
        """Publish event to all subscribers"""
        if not self._is_active:
            return
            
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
            
        # Log event
        self._log_event(event)
        
        # Notify handlers
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler failed for {event.event_type.value}: {e}")
                
    def _log_event(self, event: BrainEvent):
        """Log event based on severity"""
        log_message = f"[{event.component}] {event.message}"
        
        if event.severity == EventSeverity.DEBUG:
            logger.debug(log_message)
        elif event.severity == EventSeverity.INFO:
            logger.info(log_message)
        elif event.severity == EventSeverity.WARNING:
            logger.warning(log_message)
        elif event.severity == EventSeverity.ERROR:
            logger.error(log_message)
        elif event.severity == EventSeverity.CRITICAL:
            logger.critical(log_message)
            
    def get_recent_events(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[BrainEvent]:
        """Get recent events, optionally filtered by type"""
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
            
        return events[-limit:] if limit else events
        
    def get_event_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        event_counts = {}
        for event in self._event_history:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
        return {
            "total_events": len(self._event_history),
            "active_handlers": sum(len(handlers) for handlers in self._handlers.values()),
            "event_types": len(event_counts),
            "event_counts": event_counts,
            "is_active": self._is_active
        }
        
    def shutdown(self):
        """Shutdown event bus"""
        self._is_active = False
        self._handlers.clear()
        logger.info("BRAIN event bus shutdown")

# Global event bus instance
_event_bus: Optional[BrainEventBus] = None

def get_event_bus() -> BrainEventBus:
    """Get global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = BrainEventBus()
    return _event_bus

# Convenience functions

def publish_tick_event(tick_data: MarketTick, component: str = "market_data"):
    """Publish tick received event"""
    event_bus = get_event_bus()
    event = TickEvent(tick_data=tick_data, component=component)
    event_bus.publish(event)

def publish_signal_event(signal: TradingSignal, component: str = "enterprise_engine"):
    """Publish signal generated event"""
    event_bus = get_event_bus()
    event = SignalEvent(signal=signal, component=component)
    event_bus.publish(event)

def publish_risk_event(risk_context: RiskContext, action_taken: str, component: str = "risk_manager"):
    """Publish risk assessment event"""
    event_bus = get_event_bus()
    event = RiskEvent(risk_context=risk_context, action_taken=action_taken, component=component)
    event_bus.publish(event)

def publish_entry_event(entry_analysis: EntryAnalysis, component: str = "entry_engine"):
    """Publish entry analysis event"""
    event_bus = get_event_bus()
    event = EntryEvent(entry_analysis=entry_analysis, component=component)
    event_bus.publish(event)

def publish_exit_event(exit_analysis: ExitAnalysis, position_id: str, component: str = "exit_engine"):
    """Publish exit analysis event"""
    event_bus = get_event_bus()
    event = ExitEvent(exit_analysis=exit_analysis, position_id=position_id, component=component)
    event_bus.publish(event)

def publish_position_event(position: Position, event_type: EventType, component: str = "portfolio"):
    """Publish position lifecycle event"""
    event_bus = get_event_bus()
    event = PositionEvent(position=position, event_type=event_type, component=component)
    event_bus.publish(event)

def publish_system_event(event_type: EventType, message: str, component: str, severity: EventSeverity = EventSeverity.INFO, **metadata):
    """Publish system event"""
    event_bus = get_event_bus()
    event = SystemEvent(event_type=event_type, message=message, component=component, severity=severity, metadata=metadata)
    event_bus.publish(event)

def publish_state_change_event(old_state: str, new_state: str, component: str = "brain_controller"):
    """Publish BRAIN state change event"""
    event_bus = get_event_bus()
    event = StateChangeEvent(old_state=old_state, new_state=new_state, component=component)
    event_bus.publish(event)

# Export all classes and functions
__all__ = [
    # Enums
    "EventType", "EventSeverity",
    # Event Classes
    "BrainEvent", "TickEvent", "SignalEvent", "RiskEvent",
    "EntryEvent", "ExitEvent", "PositionEvent", "SystemEvent", "StateChangeEvent",
    # Event Bus
    "BrainEventBus", "get_event_bus",
    # Convenience Functions
    "publish_tick_event", "publish_signal_event", "publish_risk_event",
    "publish_entry_event", "publish_exit_event", "publish_position_event",
    "publish_system_event", "publish_state_change_event"
]