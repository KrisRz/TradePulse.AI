"""
Smart Emergency Controller - TradePulse.AI
=========================================

Advanced emergency control system with data-plane vs control-plane separation.
Prevents false halts while maintaining real protection for day trading.

Author: TradePulse.AI Development Team
Version: 1.0.0
"""

import logging
from collections import deque
from time import monotonic
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

# Signed endpoints that affect trading operations
SIGNED_ENDPOINTS = ["/api/v3/order", "/api/v3/openOrders", "/api/v3/account", "/api/v3/allOrders"]

class EmergencyState(str, Enum):
    """Emergency system states"""
    NORMAL = "normal"       # Full trading allowed
    PAUSE = "pause"         # New entries blocked, exits allowed  
    HALT = "halt"          # All trading stopped

class ApiHealth:
    """Track API health for control-plane operations"""
    
    def __init__(self, window: int = 50):
        self.window = window
        self.events = deque(maxlen=window)
        self.first_signed_success = False
    
    def add(self, endpoint: str, ok: bool, status: Optional[int], kind: str):
        """Record API call result"""
        # Only signed REST endpoints affect failure rate
        if kind != "rest_signed":
            return
        
        # Ignore 4xx before first success (common during init/warmup)
        if not self.first_signed_success and status and 400 <= status < 500 and not ok:
            return
        
        if ok and kind == "rest_signed":
            self.first_signed_success = True
        
        self.events.append(1 if not ok else 0)
    
    @property
    def fail_rate(self) -> float:
        """Get current failure rate"""
        if not self.events:
            return 0.0
        return sum(self.events) / len(self.events)

class DataPlaneHealth:
    """Track data-plane health (WebSocket, live data)"""
    
    def __init__(self):
        self.last_ws_ts = 0.0
        self.quality = 0.0
        self.last_price_update = 0.0
    
    def on_ws_tick(self, quality: float):
        """Record WebSocket tick with quality"""
        self.last_ws_ts = monotonic()
        self.quality = quality
    
    def on_price_update(self):
        """Record price update"""
        self.last_price_update = monotonic()
    
    def ok(self, now: Optional[float] = None, max_stale: float = 3.0, min_quality: float = 0.99) -> bool:
        """Check if data plane is healthy"""
        now = now or monotonic()
        fresh = (now - self.last_ws_ts) <= max_stale
        quality_ok = self.quality >= min_quality
        return fresh and quality_ok

class SmartEmergencyController:
    """Smart emergency controller with data/control plane separation"""
    
    def __init__(self):
        self.api = ApiHealth(window=50)
        self.data = DataPlaneHealth()
        self.state = EmergencyState.NORMAL
        self._half_open_at = 0.0
        self._grace_until = monotonic() + 180.0  # 180s grace period for control-plane
        
        # State tracking
        self.last_evaluation = 0.0
        self.state_changes = []
        
        logger.info("🛡️ Smart Emergency Controller initialized")
    
    def evaluate(self) -> EmergencyState:
        """Evaluate current emergency state"""
        now = monotonic()
        self.last_evaluation = now
        
        data_ok = self.data.ok(now)
        control_fail = self.api.fail_rate >= 0.40
        in_grace = now < self._grace_until
        
        old_state = self.state
        
        # HARD HALT: Both data and control plane failed
        if not data_ok and control_fail:
            self.state = EmergencyState.HALT
            self._log_state_change(old_state, "data_plane_failed + control_plane_failed")
            return self.state
        
        # GRACE PERIOD: Don't halt for control-plane issues during startup
        if in_grace and data_ok:
            self.state = EmergencyState.NORMAL
            if old_state != self.state:
                self._log_state_change(old_state, f"grace_period ({(self._grace_until - now):.0f}s remaining)")
            return self.state
        
        # SOFT PAUSE: Control-plane issues with healthy data-plane
        if data_ok and control_fail:
            # Half-open recovery mechanism
            if self._half_open_at == 0.0:
                self._half_open_at = now + 60.0  # 60s cooldown
                self.state = EmergencyState.PAUSE
                self._log_state_change(old_state, f"control_plane_fail_rate={self.api.fail_rate:.2f}")
            elif now >= self._half_open_at and self.api.fail_rate < 0.20:
                # Auto-recovery: failure rate improved
                self.state = EmergencyState.NORMAL
                self._half_open_at = 0.0
                self._log_state_change(old_state, f"auto_recovery (fail_rate={self.api.fail_rate:.2f})")
            else:
                # Still in cooldown
                self.state = EmergencyState.PAUSE
            
            return self.state
        
        # NORMAL: Both planes healthy
        self.state = EmergencyState.NORMAL
        self._half_open_at = 0.0
        if old_state != self.state:
            self._log_state_change(old_state, "both_planes_healthy")
        
        return self.state
    
    def allow_new_entries(self) -> bool:
        """Check if new entries are allowed"""
        return self.state == EmergencyState.NORMAL
    
    def allow_exits(self) -> bool:
        """Check if exits are allowed (always true except full halt)"""
        return self.state in (EmergencyState.NORMAL, EmergencyState.PAUSE)
    
    def _log_state_change(self, old_state: EmergencyState, reason: str):
        """Log emergency state changes"""
        if old_state != self.state:
            logger.info(f"🛡️ Emergency state: {old_state.value} → {self.state.value} ({reason})")
            self.state_changes.append({
                "from": old_state.value,
                "to": self.state.value,
                "reason": reason,
                "timestamp": monotonic()
            })
            
            # Keep last 20 state changes
            if len(self.state_changes) > 20:
                self.state_changes = self.state_changes[-20:]
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive emergency status"""
        now = monotonic()
        return {
            "state": self.state.value,
            "allow_new_entries": self.allow_new_entries(),
            "allow_exits": self.allow_exits(),
            "data_plane_ok": self.data.ok(now),
            "data_plane_quality": self.data.quality,
            "data_freshness_seconds": now - self.data.last_ws_ts,
            "control_plane_fail_rate": self.api.fail_rate,
            "control_plane_first_success": self.api.first_signed_success,
            "grace_remaining_seconds": max(0, self._grace_until - now),
            "half_open_cooldown_seconds": max(0, self._half_open_at - now) if self._half_open_at > 0 else 0,
            "recent_state_changes": self.state_changes[-5:],
            "last_evaluation": self.last_evaluation
        }

# Global smart emergency controller
_smart_emergency_controller: Optional[SmartEmergencyController] = None

def get_smart_emergency_controller() -> SmartEmergencyController:
    """Get global smart emergency controller instance"""
    global _smart_emergency_controller
    if _smart_emergency_controller is None:
        _smart_emergency_controller = SmartEmergencyController()
    return _smart_emergency_controller

# Export classes and functions
__all__ = ["SmartEmergencyController", "get_smart_emergency_controller", "EmergencyState"]
