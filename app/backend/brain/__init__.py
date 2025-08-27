"""
BRAIN Controller Architecture - TradePulse.AI
============================================

Finite State Machine (FSM) based orchestration layer for professional trading operations.

This BRAIN overlay provides centralized coordination of existing services without replacing them.
All services remain in app/backend/services/ and are imported and orchestrated by BRAIN components.

BRAIN Architecture:
- brain_state.py: Complete state management with Pydantic models
- brain_controller.py: FSM-based orchestrator (INIT → WARMUP → RUNNING → HALT → COOLDOWN)
- brain_events.py: Professional event system for inter-component communication
- io/: Input/Output layer for data management and persistence

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0 (Phase 1B)
"""

__version__ = "1.0.0"
__all__ = [
    "BrainController",
    "BrainState",
    "BrainEvent",
    "MarketDataManager",
    "PortfolioStore",
    "AuditLogger"
]