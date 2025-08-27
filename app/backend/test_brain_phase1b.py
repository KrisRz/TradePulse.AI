#!/usr/bin/env python3
"""
Phase 1B BRAIN Controller Test - TradePulse.AI
==============================================

Test script for Phase 1B BRAIN Controller integration.
Verifies FSM architecture, event system, and service orchestration.

Usage:
    python test_brain_phase1b.py

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.backend.brain_integration import get_brain_integration, test_brain_day_integration

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BrainPhase1BTest:
    """Phase 1B BRAIN Controller test suite"""
    
    def __init__(self):
        self.integration = None
        self.test_results = {
            "phase": "1B",
            "test_started": datetime.now(timezone.utc).isoformat(),
            "tests": {}
        }
        
    async def run_all_tests(self):
        """Run complete Phase 1B test suite"""
        logger.info("🧪 Starting Phase 1B BRAIN Controller Tests")
        logger.info("=" * 60)
        
        try:
            # Initialize integration
            await self._test_initialization()
            
            # Test BRAIN components
            await self._test_brain_state_management()
            await self._test_brain_events()
            await self._test_market_data_manager()
            await self._test_portfolio_store()
            await self._test_audit_logger()
            
            # Test integration
            await self._test_brain_day_integration()
            
            # Test FSM transitions
            await self._test_fsm_transitions()
            
            # Generate summary
            self._generate_test_summary()
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            self.test_results["error"] = str(e)
            
        finally:
            self.test_results["test_completed"] = datetime.now(timezone.utc).isoformat()
            
        return self.test_results
        
    async def _test_initialization(self):
        """Test BRAIN integration initialization"""
        logger.info("🧪 Test 1: BRAIN Integration Initialization")
        
        try:
            self.integration = await get_brain_integration()
            
            if self.integration:
                self.test_results["tests"]["initialization"] = {
                    "status": "passed",
                    "integration_mode": self.integration.integration_mode,
                    "components_initialized": {
                        "brain_controller": self.integration.brain_controller is not None,
                        "day_engine": self.integration.day_engine is not None,
                        "market_data_manager": self.integration.market_data_manager is not None,
                        "portfolio_store": self.integration.portfolio_store is not None,
                        "audit_logger": self.integration.audit_logger is not None
                    }
                }
                logger.info("✅ BRAIN Integration initialized successfully")
            else:
                raise Exception("Integration initialization returned None")
                
        except Exception as e:
            self.test_results["tests"]["initialization"] = {
                "status": "failed",
                "error": str(e)
            }
            logger.error(f"❌ Initialization test failed: {e}")
            
    async def _test_brain_state_management(self):
        """Test BRAIN state management"""
        logger.info("🧪 Test 2: BRAIN State Management")
        
        try:
            if not self.integration or not self.integration.brain_controller:
                raise Exception("BRAIN controller not available")
                
            # Get current state
            status = self.integration.brain_controller.get_status()
            
            required_fields = [
                "current_state", "cycle_count", "uptime_seconds",
                "services", "trading_context", "configuration"
            ]
            
            missing_fields = [field for field in required_fields if field not in status]
            
            if not missing_fields:
                self.test_results["tests"]["state_management"] = {
                    "status": "passed",
                    "current_state": status["current_state"],
                    "cycle_count": status["cycle_count"],
                    "services_initialized": all(status["services"].values()),
                    "has_trading_context": status["trading_context"]["has_tick"] or 
                                          status["trading_context"]["has_signal"] or
                                          status["trading_context"]["has_risk_context"]
                }
                logger.info(f"✅ State Management: {status['current_state']} state, {status['cycle_count']} cycles")
            else:
                raise Exception(f"Missing state fields: {missing_fields}")
                
        except Exception as e:
            self.test_results["tests"]["state_management"] = {
                "status": "failed",
                "error": str(e)
            }
            logger.error(f"❌ State management test failed: {e}")
            
    async def _test_brain_events(self):
        """Test BRAIN event system"""
        logger.info("🧪 Test 3: BRAIN Event System")
        
        try:
            if not self.integration:
                raise Exception("Integration not available")
                
            # Get event bus stats
            event_stats = self.integration.event_bus.get_event_stats()
            
            # Check if events are being processed
            has_events = event_stats["total_events"] > 0
            has_handlers = event_stats["active_handlers"] > 0
            is_active = event_stats["is_active"]
            
            if is_active and has_handlers:
                self.test_results["tests"]["event_system"] = {
                    "status": "passed",
                    "total_events": event_stats["total_events"],
                    "active_handlers": event_stats["active_handlers"],
                    "event_types": event_stats["event_types"],
                    "is_active": is_active
                }
                logger.info(f"✅ Event System: {event_stats['total_events']} events, {event_stats['active_handlers']} handlers")
            else:
                raise Exception(f"Event system not properly configured: active={is_active}, handlers={has_handlers}")
                
        except Exception as e:
            self.test_results["tests"]["event_system"] = {
                "status": "failed", 
                "error": str(e)
            }
            logger.error(f"❌ Event system test failed: {e}")
            
    async def _test_market_data_manager(self):
        """Test Market Data Manager"""
        logger.info("🧪 Test 4: Market Data Manager")
        
        try:
            if not self.integration or not self.integration.market_data_manager:
                raise Exception("Market Data Manager not available")
                
            mdm = self.integration.market_data_manager
            
            # Test data retrieval
            tick = await mdm.get_latest_tick()
            candles = await mdm.get_recent_candles("BTCUSDT", "1m", 10)
            market_data = await mdm.get_market_data()
            
            # Get cache stats
            cache_stats = mdm.get_cache_stats()
            
            data_available = (
                tick is not None and
                candles is not None and len(candles) > 0 and
                market_data is not None
            )
            
            if data_available:
                self.test_results["tests"]["market_data_manager"] = {
                    "status": "passed",
                    "tick_available": tick is not None,
                    "candles_count": len(candles),
                    "market_data_available": market_data is not None,
                    "cache_hit_rate": cache_stats["cache_hit_rate"],
                    "requests_made": cache_stats["requests_made"]
                }
                logger.info(f"✅ Market Data: tick=${tick.get('price') if tick else 'N/A'}, {len(candles)} candles")
            else:
                raise Exception("Market data not available from any source")
                
        except Exception as e:
            self.test_results["tests"]["market_data_manager"] = {
                "status": "failed",
                "error": str(e)
            }
            logger.error(f"❌ Market Data Manager test failed: {e}")
            
    async def _test_portfolio_store(self):
        """Test Portfolio Store"""
        logger.info("🧪 Test 5: Portfolio Store")
        
        try:
            if not self.integration or not self.integration.portfolio_store:
                raise Exception("Portfolio Store not available")
                
            ps = self.integration.portfolio_store
            
            # Test portfolio state retrieval
            current_state = await ps.get_current_state()
            store_stats = ps.get_store_stats()
            
            # Test performance metrics
            performance_metrics = await ps.get_performance_metrics(days=1)
            
            state_available = (
                current_state and
                "cash_balance" in current_state and
                "active_positions" in current_state
            )
            
            if state_available:
                self.test_results["tests"]["portfolio_store"] = {
                    "status": "passed",
                    "cash_balance": current_state.get("cash_balance", "0"),
                    "active_positions": current_state.get("total_positions", 0),
                    "operations_count": store_stats["operations_count"],
                    "is_initialized": store_stats["is_initialized"]
                }
                logger.info(f"✅ Portfolio Store: ${current_state.get('cash_balance', '0')} cash, {current_state.get('total_positions', 0)} positions")
            else:
                raise Exception("Portfolio state not available")
                
        except Exception as e:
            self.test_results["tests"]["portfolio_store"] = {
                "status": "failed",
                "error": str(e)
            }
            logger.error(f"❌ Portfolio Store test failed: {e}")
            
    async def _test_audit_logger(self):
        """Test Audit Logger"""
        logger.info("🧪 Test 6: Audit Logger")
        
        try:
            if not self.integration or not self.integration.audit_logger:
                raise Exception("Audit Logger not available")
                
            al = self.integration.audit_logger
            
            # Get logger stats
            logger_stats = al.get_logger_stats()
            
            # Test analytics (should work even with no data)
            decision_analytics = await al.get_decision_analytics(days=1)
            performance_analytics = await al.get_performance_analytics(days=1)
            error_summary = await al.get_error_summary(days=1)
            
            logger_working = (
                logger_stats["is_initialized"] and
                decision_analytics is not None and
                performance_analytics is not None and
                error_summary is not None
            )
            
            if logger_working:
                self.test_results["tests"]["audit_logger"] = {
                    "status": "passed",
                    "is_initialized": logger_stats["is_initialized"],
                    "logs_written": logger_stats["logs_written"],
                    "errors_logged": logger_stats["errors_logged"],
                    "buffer_size": logger_stats["buffer_size"],
                    "analytics_available": decision_analytics is not None
                }
                logger.info(f"✅ Audit Logger: {logger_stats['logs_written']} logs, {logger_stats['errors_logged']} errors")
            else:
                raise Exception("Audit Logger not working properly")
                
        except Exception as e:
            self.test_results["tests"]["audit_logger"] = {
                "status": "failed",
                "error": str(e)
            }
            logger.error(f"❌ Audit Logger test failed: {e}")
            
    async def _test_brain_day_integration(self):
        """Test BRAIN-Day Engine integration"""
        logger.info("🧪 Test 7: BRAIN-Day Engine Integration")
        
        try:
            # Run integration test
            integration_results = await test_brain_day_integration()
            
            if integration_results and "summary" in integration_results:
                summary = integration_results["summary"]
                success_rate = summary.get("success_rate", 0)
                overall_status = summary.get("overall_status", "failed")
                
                self.test_results["tests"]["brain_day_integration"] = {
                    "status": "passed" if overall_status == "passed" else "partial" if success_rate > 0.5 else "failed",
                    "integration_test_results": integration_results,
                    "success_rate": success_rate,
                    "passed_tests": summary.get("passed_tests", 0),
                    "total_tests": summary.get("total_tests", 0)
                }
                
                logger.info(f"✅ Integration: {summary.get('passed_tests', 0)}/{summary.get('total_tests', 0)} tests passed ({success_rate:.1%})")
            else:
                raise Exception("Integration test failed to run")
                
        except Exception as e:
            self.test_results["tests"]["brain_day_integration"] = {
                "status": "failed",
                "error": str(e)
            }
            logger.error(f"❌ BRAIN-Day integration test failed: {e}")
            
    async def _test_fsm_transitions(self):
        """Test BRAIN FSM state transitions"""
        logger.info("🧪 Test 8: BRAIN FSM State Transitions")
        
        try:
            if not self.integration or not self.integration.brain_controller:
                raise Exception("BRAIN controller not available")
                
            brain = self.integration.brain_controller
            
            # Get initial state
            initial_status = brain.get_status()
            initial_state = initial_status["current_state"]
            
            # Test transitions based on current state
            transitions_tested = 0
            transitions_successful = 0
            
            if initial_state in ["warmup", "halt"]:
                # Test start trading
                try:
                    start_result = await brain.start_trading()
                    if start_result.get("status") == "trading_started":
                        transitions_successful += 1
                    transitions_tested += 1
                    
                    # Test stop trading
                    stop_result = await brain.stop_trading()
                    if stop_result.get("status") == "trading_stopped":
                        transitions_successful += 1
                    transitions_tested += 1
                    
                except Exception as e:
                    logger.warning(f"FSM transition error: {e}")
                    transitions_tested += 1
                    
            # Record results
            final_status = brain.get_status()
            final_state = final_status["current_state"]
            
            self.test_results["tests"]["fsm_transitions"] = {
                "status": "passed" if transitions_successful > 0 else "partial",
                "initial_state": initial_state,
                "final_state": final_state,
                "transitions_tested": transitions_tested,
                "transitions_successful": transitions_successful,
                "state_changed": initial_state != final_state
            }
            
            logger.info(f"✅ FSM Transitions: {initial_state} → {final_state}, {transitions_successful}/{transitions_tested} successful")
            
        except Exception as e:
            self.test_results["tests"]["fsm_transitions"] = {
                "status": "failed",
                "error": str(e)
            }
            logger.error(f"❌ FSM transitions test failed: {e}")
            
    def _generate_test_summary(self):
        """Generate comprehensive test summary"""
        logger.info("=" * 60)
        logger.info("🧪 Phase 1B BRAIN Controller Test Summary")
        logger.info("=" * 60)
        
        tests = self.test_results["tests"]
        passed_tests = sum(1 for test in tests.values() if test.get("status") == "passed")
        partial_tests = sum(1 for test in tests.values() if test.get("status") == "partial")
        failed_tests = sum(1 for test in tests.values() if test.get("status") == "failed")
        total_tests = len(tests)
        
        success_rate = (passed_tests + partial_tests * 0.5) / total_tests if total_tests > 0 else 0
        
        # Test results
        for test_name, result in tests.items():
            status_icon = "✅" if result["status"] == "passed" else "⚠️" if result["status"] == "partial" else "❌"
            logger.info(f"{status_icon} {test_name.replace('_', ' ').title()}: {result['status']}")
            
        # Summary
        logger.info("-" * 60)
        logger.info(f"📊 Tests Passed: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
        logger.info(f"⚠️ Tests Partial: {partial_tests}/{total_tests} ({partial_tests/total_tests*100:.1f}%)")
        logger.info(f"❌ Tests Failed: {failed_tests}/{total_tests} ({failed_tests/total_tests*100:.1f}%)")
        logger.info(f"🎯 Overall Success Rate: {success_rate*100:.1f}%")
        
        # Phase 1B Assessment
        if success_rate >= 0.9:
            logger.info("🎉 PHASE 1B: EXCELLENT - BRAIN Controller fully operational")
            phase_status = "EXCELLENT"
        elif success_rate >= 0.7:
            logger.info("✅ PHASE 1B: GOOD - BRAIN Controller mostly operational")
            phase_status = "GOOD"
        elif success_rate >= 0.5:
            logger.info("⚠️ PHASE 1B: PARTIAL - BRAIN Controller partially operational")
            phase_status = "PARTIAL"
        else:
            logger.info("❌ PHASE 1B: FAILED - BRAIN Controller not operational")
            phase_status = "FAILED"
            
        self.test_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "partial_tests": partial_tests, 
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "phase_status": phase_status
        }
        
        logger.info("=" * 60)

async def main():
    """Main test execution"""
    print("🧠 TradePulse.AI - Phase 1B BRAIN Controller Test")
    print("=" * 60)
    
    test_suite = BrainPhase1BTest()
    results = await test_suite.run_all_tests()
    
    # Save results to file
    import json
    results_file = Path(__file__).parent / "test_results_phase1b.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
        
    logger.info(f"📄 Test results saved to: {results_file}")
    
    # Exit with appropriate code
    summary = results.get("summary", {})
    success_rate = summary.get("success_rate", 0)
    
    if success_rate >= 0.7:
        return 0  # Success
    elif success_rate >= 0.5:
        return 1  # Partial success
    else:
        return 2  # Failure

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)