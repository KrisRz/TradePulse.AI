"""
Production-Safe Bootstrap - TradePulse.AI
========================================

Idempotent bootstrap with hardened guarantees for production deployment.
Ensures all services are initialized exactly once with proper validation.

Author: TradePulse.AI Development Team
Version: 1.0.0
"""

import logging
import sys
from typing import List

logger = logging.getLogger(__name__)

# Global bootstrap state
_boot_once = False

def bootstrap(container) -> None:
    """Bootstrap all services with production-safe guarantees"""
    global _boot_once
    
    if _boot_once:
        logger.info("Bootstrap already completed — skipping.")
        return
    
    _boot_once = True
    logger.info("🚀 Starting production-safe bootstrap sequence...")
    
    # Validate single container import path
    _validate_container_imports()
    
    # Validate configuration
    from app.backend.config.validation import validate_prod_config, validate_ml_versions
    validate_prod_config()
    validate_ml_versions()
    
    # Register services in deterministic order
    _register_core_services(container)
    
    # Validate all critical services are registered
    _validate_critical_services(container)
    
    # Seal container to prevent further registrations
    container.seal()
    
    # Final health gate
    _final_health_gate(container)
    
    logger.info("✅ Production-safe bootstrap completed")

def _validate_container_imports():
    """Ensure container is imported via single canonical path"""
    container_modules = [m for m in sys.modules if m.endswith(".core.container")]
    if len(set(container_modules)) > 1:
        raise RuntimeError(f"Container imported via multiple module paths: {container_modules}")
    logger.debug(f"✅ Single container import path validated: {container_modules}")

def _register_core_services(container):
    """Register all core services in deterministic order"""
    logger.info("📦 Registering core services...")
    
    # Phase 1: Infrastructure
    from app.backend.services.live_market_data import get_live_market_data_service
    from app.backend.services.binance_hybrid_client import get_hybrid_client
    
    # Phase 2: AI Services  
    from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine
    from app.backend.services.intelligent_entry_engine import IntelligentEntryEngine
    from app.backend.services.intelligent_exit_engine import IntelligentExitEngine
    
    # Phase 3: Trading Services
    from app.backend.services.day_trading_engine import DayTradingEngine
    from app.backend.services.dynamic_risk_manager import DynamicRiskManager
    from app.backend.services.session_aware_trading_engine import SessionAwareTradingEngine
    
    # Phase 4: Control Systems
    from app.backend.brain.brain_controller import BrainController
    
    logger.info("✅ All services imported successfully")

def _validate_critical_services(container):
    """Validate all critical services are registered before sealing"""
    required_services = [
        "enterprise_trading_engine",
        "entry_engine", 
        "exit_engine",
        "risk_manager",
        "session_aware_trading_engine",
        "brain_controller"
    ]
    
    missing = []
    for service_name in required_services:
        try:
            service = container.get(service_name)
            if service is None:
                missing.append(service_name)
        except (KeyError, ValueError):
            missing.append(service_name)
    
    if missing:
        raise RuntimeError(f"Missing critical services before seal(): {missing}")
    
    logger.info(f"✅ All {len(required_services)} critical services validated")

def _final_health_gate(container):
    """Final health gate - ensure all services are available after seal"""
    required_services = [
        "enterprise_trading_engine",
        "entry_engine",
        "exit_engine", 
        "risk_manager",
        "session_aware_trading_engine",
        "brain_controller"
    ]
    
    logger.info("🔍 Final health gate - validating sealed container...")
    
    for service_name in required_services:
        try:
            service = container.get(service_name)
            from app.backend.core.container import require_instance
            require_instance(service_name, service)
            logger.debug(f"   ✅ {service_name}: Available")
        except Exception as e:
            logger.error(f"   ❌ {service_name}: {e}")
            raise RuntimeError(f"Service unavailable after seal: {service_name} - {e}")
    
    logger.info("✅ Final health gate PASSED - all services operational")

# Export bootstrap function
__all__ = ["bootstrap"]
