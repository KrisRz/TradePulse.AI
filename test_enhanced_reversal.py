#!/usr/bin/env python3
"""
Test script for Enhanced Reversal Detection
===========================================

Tests the new features:
1. Enhanced Volume Spike Detection
2. Smart Timing Filter

Run this to validate the enhancements before live trading!

Usage:
    python test_enhanced_reversal.py
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'backend'))

import asyncio
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Test scenarios
TEST_SCENARIOS = {
    'STRONG_REVERSAL': {
        'name': 'Strong Reversal Signal (Should PASS)',
        'features': {
            'rsi': 78.0,               # Overbought
            'volatility': 0.055,       # High volatility
            'trend_strength': 0.08,    # Strong trend
            'volume_ratio': 3.5,       # 3.5x volume spike!
            'macd': 0.015,
            'bb_position': 0.95,
            'price_change_24h': 0.025
        },
        'expected': {
            'volume_spike': True,
            'filter_passed': True,
            'boost_range': (0.30, 0.50)  # Should get 30-50% boost
        }
    },
    
    'FALSE_REVERSAL_WEAK_VOLUME': {
        'name': 'False Reversal (Weak Volume, Should FILTER)',
        'features': {
            'rsi': 72.0,               # Overbought
            'volatility': 0.025,       # Normal volatility
            'trend_strength': 0.04,    # Medium trend
            'volume_ratio': 0.9,       # WEAK volume (0.9x)
            'macd': 0.008,
            'bb_position': 0.85,
            'price_change_24h': 0.015
        },
        'expected': {
            'volume_spike': False,
            'filter_passed': False,    # Should be filtered
            'boost_range': (-0.5, 0.0)  # Should get penalty
        }
    },
    
    'FALSE_REVERSAL_NO_TREND': {
        'name': 'False Reversal (No Trend, Should FILTER)',
        'features': {
            'rsi': 74.0,               # Overbought
            'volatility': 0.03,        # Normal volatility
            'trend_strength': 0.01,    # VERY WEAK trend (nothing to reverse!)
            'volume_ratio': 1.8,       # Decent volume
            'macd': 0.005,
            'bb_position': 0.80,
            'price_change_24h': 0.010
        },
        'expected': {
            'volume_spike': False,
            'filter_passed': False,    # Should be filtered (no trend)
            'boost_range': (-0.6, -0.3)  # Should get big penalty
        }
    },
    
    'NEUTRAL_MARKET': {
        'name': 'Neutral Market (No Signal)',
        'features': {
            'rsi': 52.0,               # Neutral RSI
            'volatility': 0.02,        # Low volatility
            'trend_strength': 0.02,    # Weak trend
            'volume_ratio': 1.1,       # Normal volume
            'macd': 0.002,
            'bb_position': 0.50,
            'price_change_24h': 0.005
        },
        'expected': {
            'volume_spike': False,
            'filter_passed': False,
            'boost_range': (-0.5, 0.0)  # Should be filtered
        }
    },
    
    'OVERSOLD_SPIKE': {
        'name': 'Oversold Volume Spike (Buy Signal, Should PASS)',
        'features': {
            'rsi': 24.0,               # OVERSOLD
            'volatility': 0.045,       # High volatility
            'trend_strength': -0.06,   # Strong downtrend (negative)
            'volume_ratio': 2.8,       # Volume spike
            'macd': -0.012,
            'bb_position': 0.05,
            'price_change_24h': -0.020
        },
        'expected': {
            'volume_spike': True,
            'filter_passed': True,     # Should pass
            'boost_range': (0.25, 0.45)  # Should get boost
        }
    },
    
    'FALSE_SPIKE_NO_VOLUME': {
        'name': 'False Spike (High Vol, No Volume, Should FILTER)',
        'features': {
            'rsi': 76.0,               # Overbought
            'volatility': 0.07,        # HIGH volatility
            'trend_strength': 0.05,    # Decent trend
            'volume_ratio': 1.3,       # LOW volume (no real interest!)
            'macd': 0.010,
            'bb_position': 0.90,
            'price_change_24h': 0.018
        },
        'expected': {
            'volume_spike': False,
            'filter_passed': False,    # Should be filtered
            'boost_range': (-0.2, 0.0)  # Penalty for fake spike
        }
    }
}


async def test_enhanced_reversal():
    """Test the enhanced reversal detection system"""
    
    print("=" * 80)
    print("🔥 TESTING ENHANCED REVERSAL DETECTION")
    print("=" * 80)
    print()
    
    try:
        # Import the engine
        from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine
        
        # Create engine instance (without full initialization)
        engine = EnterpriseTradingEngine()
        
        print(f"✅ Enterprise Trading Engine loaded")
        print(f"🎯 Testing {len(TEST_SCENARIOS)} scenarios...")
        print()
        
        passed = 0
        failed = 0
        
        for scenario_id, scenario in TEST_SCENARIOS.items():
            print("─" * 80)
            print(f"📊 TEST: {scenario['name']}")
            print("─" * 80)
            
            features = scenario['features']
            expected = scenario['expected']
            
            # Display input features
            print(f"\n📥 Input Features:")
            print(f"   RSI: {features['rsi']:.1f}")
            print(f"   Volatility: {features['volatility']:.2%}")
            print(f"   Trend Strength: {features['trend_strength']:.2%}")
            print(f"   Volume Ratio: {features['volume_ratio']:.1f}x")
            
            # Test 1: Volume Spike Detection
            print(f"\n🔍 Test 1: Volume Spike Detection")
            volume_spike_data = engine._enhanced_volume_spike_detection(features)
            
            spike_detected = volume_spike_data.get('volume_spike_detected', False)
            spike_type = volume_spike_data.get('spike_type', 'none')
            spike_boost = volume_spike_data.get('reversal_boost', 0.0)
            
            print(f"   Spike Detected: {spike_detected}")
            print(f"   Spike Type: {spike_type}")
            print(f"   Reversal Boost: {spike_boost*100:+.0f}%")
            print(f"   Reasoning: {volume_spike_data.get('reasoning', 'N/A')}")
            
            # Test 2: Smart Timing Filter
            print(f"\n🔍 Test 2: Smart Timing Filter")
            
            # Simulate base reversal probability
            base_prob = 0.70 if features['rsi'] > 70 or features['rsi'] < 30 else 0.50
            
            filter_result = engine._smart_timing_filter(base_prob, features, volume_spike_data)
            
            filtered_prob = filter_result.get('filtered_reversal_prob', 0.0)
            filter_passed = filter_result.get('filter_passed', False)
            adjustments = filter_result.get('confidence_adjustments', [])
            
            print(f"   Base Probability: {base_prob:.1%}")
            print(f"   Filtered Probability: {filtered_prob:.1%}")
            print(f"   Filter Passed: {filter_passed}")
            print(f"   Adjustments:")
            for adj in adjustments:
                print(f"      • {adj}")
            
            # Test 3: Full Dynamic Reversal Risk
            print(f"\n🔍 Test 3: Full Dynamic Reversal Risk Calculation")
            
            raw_prob = 0.60  # Simulated model output
            final_prob = engine._calculate_dynamic_reversal_risk(raw_prob, features)
            
            print(f"   Raw Model Output: {raw_prob:.1%}")
            print(f"   Final Reversal Prob: {final_prob:.1%}")
            print(f"   Total Boost: {(final_prob - raw_prob)*100:+.0f}%")
            
            # Validation
            print(f"\n✅ Validation:")
            
            validation_passed = True
            
            # Check volume spike detection
            if spike_detected != expected['volume_spike']:
                print(f"   ❌ Volume spike detection: Expected {expected['volume_spike']}, got {spike_detected}")
                validation_passed = False
            else:
                print(f"   ✅ Volume spike detection: {spike_detected} (correct)")
            
            # Check filter result
            if filter_passed != expected['filter_passed']:
                print(f"   ❌ Filter result: Expected {expected['filter_passed']}, got {filter_passed}")
                validation_passed = False
            else:
                print(f"   ✅ Filter result: {filter_passed} (correct)")
            
            # Check boost range
            boost_min, boost_max = expected['boost_range']
            total_boost = final_prob - raw_prob
            if not (boost_min <= total_boost <= boost_max):
                print(f"   ❌ Boost range: Expected {boost_min:.1%} to {boost_max:.1%}, got {total_boost:.1%}")
                validation_passed = False
            else:
                print(f"   ✅ Boost range: {total_boost:.1%} (within expected range)")
            
            if validation_passed:
                print(f"\n🎉 TEST PASSED: {scenario['name']}")
                passed += 1
            else:
                print(f"\n❌ TEST FAILED: {scenario['name']}")
                failed += 1
            
            print()
        
        print("=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {len(TEST_SCENARIOS)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {passed/len(TEST_SCENARIOS)*100:.0f}%")
        print("=" * 80)
        
        if failed == 0:
            print()
            print("🎉🎉🎉 ALL TESTS PASSED! 🎉🎉🎉")
            print()
            print("✅ Enhanced Reversal Detection is working correctly!")
            print("✅ Volume Spike Detection validated")
            print("✅ Smart Timing Filter validated")
            print("✅ Ready for live trading tests!")
            print()
            return True
        else:
            print()
            print(f"⚠️ {failed} test(s) failed. Please review the results above.")
            print()
            return False
        
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test entry point"""
    print()
    print("🚀 TradePulse.AI - Enhanced Reversal Detection Test Suite")
    print("=" * 80)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    success = await test_enhanced_reversal()
    
    print()
    print("=" * 80)
    print("🏁 TEST SUITE COMPLETE")
    print("=" * 80)
    print()
    
    if success:
        print("✅ All systems operational - Ready to start backend for live tests!")
        print()
        print("Next steps:")
        print("1. cd app/backend")
        print("2. python main.py")
        print("3. Monitor logs for enhanced reversal detection in action")
        print()
        return 0
    else:
        print("⚠️ Some tests failed - Review and fix before proceeding")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

