"""
BRAIN Integration Layer - TradePulse.AI
======================================

Integration layer between BRAIN Controller and existing Day Trading Engine.
Demonstrates Phase 1B orchestration capabilities with existing services.

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# BRAIN components
from app.backend.brain.brain_controller import get_brain_controller
from app.backend.brain.brain_events import get_event_bus, EventType, publish_system_event, EventSeverity
from app.backend.brain.io.market_data import get_market_data_manager
from app.backend.brain.io.portfolio_store import get_portfolio_store
from app.backend.brain.io.audit_logger import get_audit_logger

# Existing services (unchanged)
from app.backend.services.day_trading_engine import get_day_trading_engine, TradingMode

logger = logging.getLogger(__name__)

class BrainTradingIntegration:
    """
    Integration layer between BRAIN Controller and Day Trading Engine
    
    Demonstrates how BRAIN can orchestrate existing services:
    - Uses BRAIN for centralized state management
    - Maintains existing day_trading_engine functionality
    - Adds professional event system
    - Enhanced audit trail and monitoring
    """
    
    def __init__(self):
        self.brain_controller = None
        self.day_engine = None
        self.market_data_manager = None
        self.portfolio_store = None
        self.audit_logger = None
        self.event_bus = get_event_bus()
        
        self.integration_mode = "hybrid"  # "brain_only", "hybrid", "legacy"
        
        logger.info("🧠🤝 BRAIN-Day Engine Integration initialized")
        
    async def initialize(self) -> Dict[str, Any]:
        """Initialize both BRAIN and Day Trading Engine"""
        logger.info("🚀 Initializing BRAIN-Day Engine Integration...")
        
        try:
            # Initialize BRAIN components
            logger.info("🧠 Initializing BRAIN Controller...")
            self.brain_controller = await get_brain_controller()
            
            logger.info("📊 Initializing Market Data Manager...")
            self.market_data_manager = await get_market_data_manager()
            
            logger.info("💰 Initializing Portfolio Store...")
            self.portfolio_store = await get_portfolio_store()
            
            logger.info("📝 Initializing Audit Logger...")
            self.audit_logger = await get_audit_logger()
            
            # Initialize existing Day Trading Engine
            logger.info("⚡ Initializing Day Trading Engine...")
            self.day_engine = await get_day_trading_engine()
            
            # Set day trading mode (15-second cycles)
            mode_result = self.day_engine.set_trading_mode(TradingMode.DAY_TRADING)
            logger.info(f"📊 Trading mode: {mode_result['new_mode']} ({mode_result['config']['analysis_interval']}s cycles)")
            
            # Subscribe to BRAIN events
            self._setup_event_integration()
            
            logger.info("✅ BRAIN-Day Engine Integration initialized successfully")
            
            return {
                "status": "initialized",
                "integration_mode": self.integration_mode,
                "brain_status": self.brain_controller.get_status(),
                "day_engine_status": self.day_engine.get_engine_status(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Integration initialization failed: {e}")
            raise
            
    def _setup_event_integration(self):
        """Setup event integration between BRAIN and Day Engine"""
        # Subscribe to key BRAIN events
        self.event_bus.subscribe(EventType.SIGNAL_GENERATED, self._on_signal_generated)
        self.event_bus.subscribe(EventType.POSITION_OPENED, self._on_position_opened)
        self.event_bus.subscribe(EventType.POSITION_CLOSED, self._on_position_closed)
        self.event_bus.subscribe(EventType.RISK_BLOCKED, self._on_risk_blocked)
        self.event_bus.subscribe(EventType.EMERGENCY_TRIGGERED, self._on_emergency)
        
        logger.info("📡 Event integration configured")
        
    def _on_signal_generated(self, event):
        """Handle signal generation events"""
        logger.info(f"🧠→⚡ BRAIN Signal: {event.signal.action} {event.signal.symbol} conf={event.signal.confidence:.2f}")
        
    def _on_position_opened(self, event):
        """Handle position opening events"""
        logger.info(f"🧠→💰 BRAIN Position Opened: {event.position.position_id} {event.position.side}")
        
    def _on_position_closed(self, event):
        """Handle position closing events"""
        logger.info(f"🧠→📈 BRAIN Position Closed: {event.position.position_id} PnL={event.position.pnl_percent:.2f}%")
        
    def _on_risk_blocked(self, event):
        """Handle risk blocking events"""
        logger.warning(f"🧠→🛡️ BRAIN Risk Block: {event.risk_context.block_reason}")
        
    def _on_emergency(self, event):
        """Handle emergency events"""
        logger.critical(f"🧠→🚨 BRAIN Emergency: {event.message}")
        
    async def start_hybrid_trading(self) -> Dict[str, Any]:
        """Start hybrid trading (BRAIN + Day Engine coordination)"""
        logger.info("🚀 Starting Hybrid Trading (BRAIN + Day Engine)...")
        
        try:
            if self.integration_mode == "brain_only":
                # Use BRAIN controller exclusively
                logger.info("🧠 Starting BRAIN-only trading...")
                result = await self.brain_controller.start_trading()
                
            elif self.integration_mode == "hybrid":
                # Use both BRAIN coordination and Day Engine execution
                logger.info("🧠⚡ Starting Hybrid trading...")
                
                # Start BRAIN controller for orchestration
                brain_result = await self.brain_controller.start_trading()
                logger.info(f"🧠 BRAIN Controller: {brain_result['status']}")
                
                # Start Day Trading Engine for execution
                day_result = await self.day_engine.start_analysis_loop()
                logger.info(f"⚡ Day Engine: {day_result['status']}")
                
                result = {
                    "status": "hybrid_trading_started",
                    "brain_result": brain_result,
                    "day_engine_result": day_result,
                    "coordination_active": True
                }
                
            else:  # legacy mode
                # Use Day Engine only
                logger.info("⚡ Starting Legacy Day Engine trading...")
                result = await self.day_engine.start_analysis_loop()
                
            publish_system_event(
                EventType.BRAIN_STARTED,
                f"Hybrid trading started in {self.integration_mode} mode",
                "brain_integration",
                EventSeverity.INFO
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to start hybrid trading: {e}")
            raise
            
    async def stop_hybrid_trading(self) -> Dict[str, Any]:
        """Stop hybrid trading"""
        logger.info("🛑 Stopping Hybrid Trading...")
        
        try:
            results = {}
            
            # Stop BRAIN controller
            if self.brain_controller:
                try:
                    brain_result = await self.brain_controller.stop_trading()
                    results["brain_stop"] = brain_result
                    logger.info(f"🧠 BRAIN Controller stopped: {brain_result.get('cycles_completed', 0)} cycles")
                except Exception as e:
                    logger.error(f"BRAIN stop error: {e}")
                    
            # Stop Day Trading Engine
            if self.day_engine:
                try:
                    day_result = await self.day_engine.stop_analysis_loop()
                    results["day_engine_stop"] = day_result
                    logger.info(f"⚡ Day Engine stopped: {day_result.get('analyses_completed', 0)} analyses")
                except Exception as e:
                    logger.error(f"Day Engine stop error: {e}")
                    
            publish_system_event(
                EventType.BRAIN_STOPPED,
                "Hybrid trading stopped",
                "brain_integration",
                EventSeverity.INFO
            )
            
            return {
                "status": "hybrid_trading_stopped",
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to stop hybrid trading: {e}")
            return {"status": "stop_failed", "error": str(e)}
            
    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status from all components"""
        try:
            status = {
                "integration_mode": self.integration_mode,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # BRAIN Controller status
            if self.brain_controller:
                status["brain_controller"] = self.brain_controller.get_status()
                
            # Day Trading Engine status
            if self.day_engine:
                status["day_trading_engine"] = self.day_engine.get_engine_status()
                
            # Market Data Manager status
            if self.market_data_manager:
                status["market_data_manager"] = self.market_data_manager.get_cache_stats()
                
            # Portfolio Store status
            if self.portfolio_store:
                status["portfolio_store"] = self.portfolio_store.get_store_stats()
                
            # Audit Logger status
            if self.audit_logger:
                status["audit_logger"] = self.audit_logger.get_logger_stats()
                
            # Event Bus status
            status["event_bus"] = self.event_bus.get_event_stats()
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive status: {e}")
            return {"error": str(e)}
            
    async def run_integration_test(self) -> Dict[str, Any]:
        """Run integration test to verify all components work together"""
        logger.info("🧪 Running BRAIN-Day Engine Integration Test...")
        
        test_results = {
            "test_started": datetime.now(timezone.utc).isoformat(),
            "tests": {}
        }
        
        try:
            # Test 1: Market Data Retrieval
            logger.info("🧪 Test 1: Market Data Retrieval...")
            try:
                tick = await self.market_data_manager.get_latest_tick()
                candles = await self.market_data_manager.get_recent_candles("BTCUSDT", "1m", 10)
                
                test_results["tests"]["market_data"] = {
                    "status": "passed",
                    "tick_available": tick is not None,
                    "candles_count": len(candles) if candles else 0,
                    "tick_price": tick.get("price") if tick else None
                }
                logger.info(f"✅ Market Data: tick=${tick.get('price') if tick else 'N/A'}, {len(candles) if candles else 0} candles")
                
            except Exception as e:
                test_results["tests"]["market_data"] = {"status": "failed", "error": str(e)}
                logger.error(f"❌ Market Data Test: {e}")
                
            # Test 2: Portfolio Operations
            logger.info("🧪 Test 2: Portfolio State...")
            try:
                portfolio_state = await self.portfolio_store.get_current_state()
                
                test_results["tests"]["portfolio"] = {
                    "status": "passed",
                    "cash_balance": portfolio_state.get("cash_balance", "0"),
                    "active_positions": portfolio_state.get("total_positions", 0)
                }
                logger.info(f"✅ Portfolio: ${portfolio_state.get('cash_balance', '0')} cash, {portfolio_state.get('total_positions', 0)} positions")
                
            except Exception as e:
                test_results["tests"]["portfolio"] = {"status": "failed", "error": str(e)}
                logger.error(f"❌ Portfolio Test: {e}")
                
            # Test 3: Event System
            logger.info("🧪 Test 3: Event System...")
            try:
                # Publish test event
                publish_system_event(
                    EventType.BRAIN_STARTED,
                    "Integration test event",
                    "integration_test",
                    EventSeverity.INFO
                )
                
                # Get recent events
                recent_events = self.event_bus.get_recent_events(limit=5)
                
                test_results["tests"]["events"] = {
                    "status": "passed",
                    "recent_events": len(recent_events),
                    "event_stats": self.event_bus.get_event_stats()
                }
                logger.info(f"✅ Events: {len(recent_events)} recent events")
                
            except Exception as e:
                test_results["tests"]["events"] = {"status": "failed", "error": str(e)}
                logger.error(f"❌ Events Test: {e}")
                
            # Test 4: BRAIN-Day Engine Coordination
            logger.info("🧪 Test 4: BRAIN-Day Engine Coordination...")
            try:
                brain_status = self.brain_controller.get_status() if self.brain_controller else {}
                day_status = self.day_engine.get_engine_status() if self.day_engine else {}
                
                coordination_working = (
                    brain_status.get("current_state") in ["init", "warmup", "running", "halt"] and
                    day_status.get("is_initialized", False)
                )
                
                test_results["tests"]["coordination"] = {
                    "status": "passed" if coordination_working else "failed",
                    "brain_state": brain_status.get("current_state", "unknown"),
                    "day_engine_initialized": day_status.get("is_initialized", False),
                    "coordination_working": coordination_working
                }
                logger.info(f"✅ Coordination: BRAIN={brain_status.get('current_state', 'unknown')}, Day Engine={day_status.get('is_initialized', False)}")
                
            except Exception as e:
                test_results["tests"]["coordination"] = {"status": "failed", "error": str(e)}
                logger.error(f"❌ Coordination Test: {e}")
                
            # Summary
            passed_tests = sum(1 for test in test_results["tests"].values() if test.get("status") == "passed")
            total_tests = len(test_results["tests"])
            
            test_results["summary"] = {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "overall_status": "passed" if passed_tests == total_tests else "partial" if passed_tests > 0 else "failed"
            }
            
            test_results["test_completed"] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"🧪 Integration Test Complete: {passed_tests}/{total_tests} passed ({test_results['summary']['success_rate']:.1%})")
            
            return test_results
            
        except Exception as e:
            logger.error(f"❌ Integration test failed: {e}")
            test_results["error"] = str(e)
            return test_results

# Global integration instance
_brain_integration: Optional[BrainTradingIntegration] = None

async def get_brain_integration() -> BrainTradingIntegration:
    """Get or create global BRAIN integration"""
    global _brain_integration
    if _brain_integration is None:
        _brain_integration = BrainTradingIntegration()
        await _brain_integration.initialize()
    return _brain_integration

# Convenience functions for external use

async def start_brain_day_trading():
    """Start BRAIN-coordinated day trading"""
    integration = await get_brain_integration()
    return await integration.start_hybrid_trading()

async def stop_brain_day_trading():
    """Stop BRAIN-coordinated day trading"""
    integration = await get_brain_integration()
    return await integration.stop_hybrid_trading()

async def get_brain_day_status():
    """Get comprehensive BRAIN-Day trading status"""
    integration = await get_brain_integration()
    return await integration.get_comprehensive_status()

async def test_brain_day_integration():
    """Test BRAIN-Day integration"""
    integration = await get_brain_integration()
    return await integration.run_integration_test()

# Export classes and functions
__all__ = [
    "BrainTradingIntegration",
    "get_brain_integration",
    "start_brain_day_trading",
    "stop_brain_day_trading", 
    "get_brain_day_status",
    "test_brain_day_integration"
]