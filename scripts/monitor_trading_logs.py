#!/usr/bin/env python3
"""
Real-time trading log monitor
Shows important events: signals, entries, exits, volume spikes, etc.
"""

import sys
import time
import re
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Important log patterns
PATTERNS = {
    'kalman': r'🔧 Kalman.*',
    'volume_spike': r'🔥 VOLUME SPIKE.*',
    'real_reversal': r'✅ REAL REVERSAL.*',
    'filtered': r'⚠️ FILTERED.*',
    'entry': r'(🚀|🔵).*ENTRY.*',
    'exit': r'(🔴|💰).*EXIT.*',
    'position': r'📊.*Position.*',
    'learning': r'🧠.*learning.*',
    'optimization': r'📈.*optimization.*',
    'error': r'(❌|ERROR).*',
    'warning': r'(⚠️|WARNING).*'
}

def colorize(text, color):
    """Add color to text"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'reset': '\033[0m'
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"

def monitor_logs(log_file_path: Path = None, follow: bool = True):
    """Monitor trading logs in real-time"""
    
    if log_file_path is None:
        # Try to find latest log file
        log_dir = project_root / "logs"
        if not log_dir.exists():
            print(f"❌ Log directory not found: {log_dir}")
            print("   Starting backend will create logs")
            return
        
        log_files = sorted(log_dir.glob("trading_*.log"), key=lambda x: x.stat().st_mtime)
        if not log_files:
            print(f"❌ No log files found in: {log_dir}")
            print("   Starting backend will create logs")
            return
        
        log_file_path = log_files[-1]
    
    print("=" * 80)
    print(f"📊 MONITORING TRADING LOGS")
    print("=" * 80)
    print(f"File: {log_file_path}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    print("Legend:")
    print("  🔥 = Volume Spike Detected")
    print("  ✅ = Real Reversal Confirmed")
    print("  ⚠️  = Signal Filtered")
    print("  🚀 = Entry Signal")
    print("  💰 = Exit with Profit")
    print("  🔴 = Exit with Loss")
    print("  🧠 = Continuous Learning")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 80)
    print()
    
    try:
        with open(log_file_path, 'r') as f:
            # Go to end if following
            if follow:
                f.seek(0, 2)
            
            while True:
                line = f.readline()
                
                if not line:
                    if follow:
                        time.sleep(0.1)
                        continue
                    else:
                        break
                
                # Check patterns
                matched = False
                for pattern_name, pattern in PATTERNS.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        matched = True
                        
                        # Colorize based on pattern
                        if pattern_name in ['volume_spike', 'real_reversal', 'entry']:
                            print(colorize(line.strip(), 'green'))
                        elif pattern_name in ['filtered', 'warning']:
                            print(colorize(line.strip(), 'yellow'))
                        elif pattern_name == 'error':
                            print(colorize(line.strip(), 'red'))
                        elif pattern_name in ['learning', 'optimization']:
                            print(colorize(line.strip(), 'cyan'))
                        elif pattern_name == 'exit':
                            if '💰' in line or 'profit' in line.lower():
                                print(colorize(line.strip(), 'green'))
                            else:
                                print(colorize(line.strip(), 'red'))
                        else:
                            print(line.strip())
                        
                        break
                
                # If no pattern matched but line has emoji, show it anyway
                if not matched and any(emoji in line for emoji in ['🔥', '✅', '⚠️', '🚀', '💰', '🔴', '🧠', '📊', '📈']):
                    print(line.strip())
    
    except KeyboardInterrupt:
        print()
        print("=" * 80)
        print("Monitoring stopped")
        print("=" * 80)
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor TradePulse.AI trading logs')
    parser.add_argument('--file', '-f', type=Path, help='Log file to monitor')
    parser.add_argument('--no-follow', action='store_true', help='Don\'t follow new lines')
    
    args = parser.parse_args()
    
    monitor_logs(args.file, follow=not args.no_follow)

if __name__ == "__main__":
    main()

