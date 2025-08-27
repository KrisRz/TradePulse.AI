#!/usr/bin/env python3
"""
TradePulse.AI Overnight Monitoring Script
========================================

24/7 monitoring script for overnight live trading test.
Tracks system performance, trading activity, and session transitions.

Features:
- Continuous system health monitoring
- Trading performance tracking
- Session transition logging
- Error detection and alerting
- Performance metrics collection

Author: TradePulse.AI Development Team
Created: August 2025
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def monitor_overnight_trading():
    """Monitor overnight trading system"""
    
    print("🌙 TRADEPULSE.AI OVERNIGHT MONITORING STARTED")
    print("=" * 60)
    print(f"Start time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)
    
    start_time = datetime.now(timezone.utc)
    last_analysis_count = 0
    last_position_count = 0
    
    while True:
        try:
            current_time = datetime.now(timezone.utc)
            uptime_hours = (current_time - start_time).total_seconds() / 3600
            
            # Check system status
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:9002/api/trading/modes/status') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        engine_data = data["day_trading_engine"]
                        
                        # Extract metrics
                        analyses = engine_data["performance"]["analyses_completed"]
                        positions = engine_data["performance"]["positions_opened"]
                        avg_time = engine_data["performance"]["avg_analysis_time_ms"]
                        is_running = engine_data["is_running"]
                        mode = engine_data["current_mode"]
                        session = engine_data["current_session"]
                        
                        # Calculate rates
                        new_analyses = analyses - last_analysis_count
                        new_positions = positions - last_position_count
                        
                        # Update counters
                        last_analysis_count = analyses
                        last_position_count = positions
                        
                        # Log status
                        status_icon = "✅" if is_running else "❌"
                        print(f"\\n{current_time.strftime('%H:%M:%S')} | {status_icon} SYSTEM STATUS")
                        print(f"  Mode: {mode} | Session: {session} | Running: {is_running}")
                        print(f"  Analyses: {analyses} total (+{new_analyses} last 5min)")
                        print(f"  Positions: {positions} total (+{new_positions} last 5min)")
                        print(f"  Avg decision: {avg_time:.0f}ms | Uptime: {uptime_hours:.1f}h")
                        
                        # Session transition detection
                        if uptime_hours > 0:
                            expected_analyses = int(uptime_hours * 240)  # 240 per hour at 15s
                            efficiency = (analyses / max(expected_analyses, 1)) * 100
                            print(f"  Efficiency: {efficiency:.1f}% ({analyses}/{expected_analyses} expected)")
                        
                        # Alerts
                        if not is_running:
                            print("  🚨 ALERT: Trading engine stopped!")
                        elif avg_time > 2000:
                            print(f"  ⚠️ WARNING: Slow decisions ({avg_time:.0f}ms)")
                        elif new_analyses == 0 and uptime_hours > 0.1:
                            print("  ⚠️ WARNING: No new analyses in 5 minutes")
                    else:
                        print(f"❌ API Error: {resp.status}")
            
            # Wait 5 minutes before next check
            await asyncio.sleep(300)
            
        except KeyboardInterrupt:
            print(f"\\n🛑 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Monitoring error: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error
    
    # Final summary
    end_time = datetime.now(timezone.utc)
    total_uptime = (end_time - start_time).total_seconds() / 3600
    
    print("\\n" + "=" * 60)
    print("🌙 OVERNIGHT MONITORING SUMMARY")
    print("=" * 60)
    print(f"Total uptime: {total_uptime:.1f} hours")
    print(f"Final analyses: {last_analysis_count}")
    print(f"Final positions: {last_position_count}")
    print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(monitor_overnight_trading())
