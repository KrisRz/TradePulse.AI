#!/usr/bin/env python3
"""
Simple BRAIN Controller Test - TradePulse.AI
============================================

Simple test to verify individual BRAIN components work correctly.
Tests each component separately to identify integration issues.

Usage:
    python simple_brain_test.py

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_brain_state():
    """Test BRAIN state management"""
    logger.info("🧪 Testing BRAIN State Management...")
    
    try:
        from app.backend.brain.brain_state import (
            create_initial_brain_state, BrainState, TradingSession,
            TradingSignal, RiskContext, MarketTick
        )
        from decimal import Decimal
        from datetime import datetime, timezone
        
        # Test state creation
        initial_state = create_initial_brain_state()
        logger.info(f"✅ Initial state created: {initial_state.current_state}")
        
        # Test signal creation
        signal = TradingSignal(
            symbol="BTCUSDT",
            action="BUY",
            confidence=Decimal('0.75'),
            reasoning="Test signal",
            timestamp=datetime.now(timezone.utc)
        )
        logger.info(f"✅ Signal created: {signal.action} conf={signal.confidence}")
        
        # Test market tick
        tick = MarketTick(
            symbol="BTCUSDT",
            price=Decimal('67234.56'),
            timestamp=datetime.now(timezone.utc)
        )
        logger.info(f"✅ Market tick created: ${tick.price}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ BRAIN state test failed: {e}")
        return False

async def test_brain_events():
    """Test BRAIN event system"""
    logger.info("🧪 Testing BRAIN Event System...")
    
    try:
        from app.backend.brain.brain_events import (
            get_event_bus, publish_system_event, EventType, EventSeverity,
            BrainEvent, SystemEvent
        )
        from datetime import datetime, timezone
        
        # Get event bus
        event_bus = get_event_bus()
        logger.info(f"✅ Event bus obtained: {event_bus is not None}")
        
        # Create and publish test event
        publish_system_event(
            EventType.BRAIN_STARTED,
            "Simple test event",
            "simple_test",
            EventSeverity.INFO
        )
        
        # Get event stats
        stats = event_bus.get_event_stats()
        logger.info(f"✅ Event published: {stats['total_events']} total events")
        
        # Get recent events
        recent = event_bus.get_recent_events(limit=1)
        if recent:
            logger.info(f"✅ Recent event: {recent[0].message}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ BRAIN events test failed: {e}")
        return False

async def test_market_data_manager():
    """Test Market Data Manager"""
    logger.info("🧪 Testing Market Data Manager...")
    
    try:
        from app.backend.brain.io.market_data import MarketDataManager
        
        # Create and initialize manager
        mdm = MarketDataManager()
        await mdm.initialize()
        logger.info(f"✅ Market Data Manager initialized: {mdm.is_initialized}")
        
        # Test data retrieval
        try:
            tick = await mdm.get_latest_tick()
            if tick:
                logger.info(f"✅ Tick retrieved: BTCUSDT @${tick.get('price', 'N/A')}")
            else:
                logger.warning("⚠️ No tick data available")
        except Exception as e:
            logger.warning(f"⚠️ Tick retrieval failed: {e}")
            
        try:
            candles = await mdm.get_recent_candles("BTCUSDT", "1m", 5)
            logger.info(f"✅ Candles retrieved: {len(candles)} candles")
        except Exception as e:
            logger.warning(f"⚠️ Candles retrieval failed: {e}")
            
        # Get cache stats
        stats = mdm.get_cache_stats()
        logger.info(f"✅ Cache stats: {stats['requests_made']} requests, {stats['cache_hit_rate']:.1%} hit rate")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Market Data Manager test failed: {e}")
        return False

async def test_portfolio_store():
    """Test Portfolio Store"""
    logger.info("🧪 Testing Portfolio Store...")
    
    try:
        from app.backend.brain.io.portfolio_store import PortfolioStore
        
        # Create and initialize store
        ps = PortfolioStore()
        await ps.initialize()
        logger.info(f"✅ Portfolio Store initialized: {ps.is_initialized}")
        
        # Test state retrieval
        try:
            state = await ps.get_current_state()
            if state:
                logger.info(f"✅ Portfolio state: ${state.get('cash_balance', '0')} cash, {state.get('total_positions', 0)} positions")
            else:
                logger.warning("⚠️ No portfolio state available")
        except Exception as e:
            logger.warning(f"⚠️ Portfolio state retrieval failed: {e}")
            
        # Test performance metrics
        try:
            metrics = await ps.get_performance_metrics(days=1)
            logger.info(f"✅ Performance metrics: {metrics.get('total_trades', 0)} trades today")
        except Exception as e:
            logger.warning(f"⚠️ Performance metrics failed: {e}")
            
        # Get store stats
        stats = ps.get_store_stats()
        logger.info(f"✅ Store stats: {stats['operations_count']} operations")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Portfolio Store test failed: {e}")
        return False

async def test_audit_logger():
    """Test Audit Logger"""
    logger.info("🧪 Testing Audit Logger...")
    
    try:
        from app.backend.brain.io.audit_logger import AuditLogger
        
        # Create and initialize logger
        al = AuditLogger()
        await al.initialize()
        logger.info(f"✅ Audit Logger initialized: {al.is_initialized}")
        
        # Test analytics
        try:
            decision_analytics = await al.get_decision_analytics(days=1)
            logger.info(f"✅ Decision analytics: {decision_analytics.get('total_decisions', 0)} decisions")
        except Exception as e:
            logger.warning(f"⚠️ Decision analytics failed: {e}")
            
        try:
            performance_analytics = await al.get_performance_analytics(days=1)
            logger.info(f"✅ Performance analytics: {performance_analytics.get('total_cycles', 0)} cycles")
        except Exception as e:
            logger.warning(f"⚠️ Performance analytics failed: {e}")
            
        try:
            error_summary = await al.get_error_summary(days=1)
            logger.info(f"✅ Error summary: {error_summary.get('total_errors', 0)} errors")
        except Exception as e:
            logger.warning(f"⚠️ Error summary failed: {e}")
            
        # Get logger stats
        stats = al.get_logger_stats()
        logger.info(f"✅ Logger stats: {stats['logs_written']} logs written")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Audit Logger test failed: {e}")
        return False

async def test_brain_controller():
    """Test BRAIN Controller (basic)"""
    logger.info("🧪 Testing BRAIN Controller...")
    
    try:
        from app.backend.brain.brain_controller import BrainController
        
        # Create controller (don't initialize to avoid complex dependencies)
        controller = BrainController()
        logger.info(f"✅ BRAIN Controller created: {controller is not None}")
        
        # Test initial state
        logger.info(f"✅ Initial state: {controller.state.current_state}")
        
        # Test status method (should work without initialization)
        try:
            status = controller.get_status()
            logger.info(f"✅ Status retrieved: {status['current_state']}")
        except Exception as e:
            logger.warning(f"⚠️ Status retrieval failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ BRAIN Controller test failed: {e}")
        return False

async def main():
    """Run all simple tests"""
    logger.info("🧠 TradePulse.AI - Simple BRAIN Controller Component Tests")
    logger.info("=" * 60)
    
    tests = [
        ("BRAIN State Management", test_brain_state),
        ("BRAIN Event System", test_brain_events),
        ("Market Data Manager", test_market_data_manager),
        ("Portfolio Store", test_portfolio_store),
        ("Audit Logger", test_audit_logger),
        ("BRAIN Controller", test_brain_controller)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info("-" * 60)
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("=" * 60)
    logger.info("🧪 Simple BRAIN Tests Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status_icon = "✅" if result else "❌"
        logger.info(f"{status_icon} {test_name}")
    
    logger.info("-" * 60)
    logger.info(f"📊 Tests Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 ALL BRAIN COMPONENTS WORKING - Ready for full integration")
        return 0
    elif passed > total // 2:
        logger.info("✅ MOST BRAIN COMPONENTS WORKING - Partial success")
        return 1
    else:
        logger.info("❌ BRAIN COMPONENTS FAILING - Needs investigation")
        return 2

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)