"""
Finite State Machine for Brain Controller
Fixes: FSM re-warmup while RUNNING
"""

from enum import Enum
import logging

logger = logging.getLogger(__name__)

class BrainState(Enum):
    """Brain controller states"""
    INIT = "init"
    WARMUP = "warmup"
    RUNNING = "running"
    HALT = "halt"
    ERROR = "error"

class BrainFSM:
    """Finite State Machine with idempotent transitions"""
    
    def __init__(self):
        self._state = BrainState.INIT
        
    def state(self) -> BrainState:
        """Get current state"""
        return self._state
        
    def transition(self, to: BrainState) -> bool:
        """
        Transition to new state with validation
        Returns True if transition occurred, False if blocked/unnecessary
        """
        # Idempotent - no change needed
        if self._state == to:
            logger.debug(f"State already {to.value}, no transition needed")
            return False
            
        # Prevent backward transitions from RUNNING to WARMUP
        if self._state == BrainState.RUNNING and to == BrainState.WARMUP:
            logger.warning("Cannot transition RUNNING → WARMUP (blocked)")
            return False
            
        # Valid transition
        old_state = self._state
        self._state = to
        logger.info(f"State transition: {old_state.value} → {to.value}")
        return True
        
    def can_start_warmup(self) -> bool:
        """Check if warmup can be started"""
        return self._state in [BrainState.INIT, BrainState.ERROR]
        
    def is_operational(self) -> bool:
        """Check if brain is in operational state"""
        return self._state == BrainState.RUNNING

# Global FSM instance
_brain_fsm = BrainFSM()

def get_brain_fsm() -> BrainFSM:
    """Get global brain FSM instance"""
    return _brain_fsm
