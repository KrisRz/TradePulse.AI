#!/usr/bin/env python3
"""
Comprehensive Analysis of Closed Trading Positions
===================================================

Analyzes patterns in closed positions to identify:
- Win/loss distribution
- Hold time patterns
- Session performance
- Exit reason analysis
- PnL distribution
- Technical indicator correlations

Author: TradePulse.AI
Date: 2025-10-31
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, List, Any
import statistics

# Setup paths
script_dir = Path(__file__).parent
backend_dir = script_dir.parent
app_dir = backend_dir.parent
sys.path.insert(0, str(app_dir))

import boto3
import os

def analyze_closed_positions() -> Dict[str, Any]:
    """Comprehensive analysis of all closed positions"""
    
    print("=" * 80)
    print("🔍 CLOSED POSITIONS ANALYSIS - AWS PRODUCTION DATA")
    print("=" * 80)
    print()
    
    # AWS credentials are resolved by boto3's default provider chain
    # (environment variables, shared config/credentials file, or IAM role).
    # Never hard-code access keys in source.
    aws_region = os.getenv("AWS_REGION", "eu-west-2")

    # Initialize AWS DynamoDB client
    print(f"📡 Connecting to AWS DynamoDB ({aws_region})...")
    dynamodb = boto3.resource('dynamodb', region_name=aws_region)
    
    # Fetch all closed positions from AWS
    print("📂 Fetching closed positions from AWS DynamoDB...")
    positions = []
    
    try:
        table = dynamodb.Table('portfolio_closed_positions')
        
        # Scan table (pagination handled)
        response = table.scan()
        positions = response.get('Items', [])
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            positions.extend(response.get('Items', []))
        
        print(f"✅ Loaded {len(positions)} closed positions from AWS")
    except Exception as e:
        print(f"❌ Error fetching positions: {e}")
        import traceback
        traceback.print_exc()
        return {}
    
    if not positions:
        print("⚠️ No closed positions found!")
        return {}
    
    print()
    print("=" * 80)
    print("📊 OVERALL STATISTICS")
    print("=" * 80)
    
    # Separate winning and losing trades
    winning_trades = [p for p in positions if float(p.get('pnl_percentage', 0)) > 0]
    losing_trades = [p for p in positions if float(p.get('pnl_percentage', 0)) < 0]
    breakeven_trades = [p for p in positions if float(p.get('pnl_percentage', 0)) == 0]
    
    total_trades = len(positions)
    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
    
    print(f"Total Trades:       {total_trades:,}")
    print(f"Winning Trades:     {win_count:,} ({win_rate:.1f}%)")
    print(f"Losing Trades:      {loss_count:,} ({(loss_count/total_trades*100):.1f}%)")
    print(f"Breakeven Trades:   {len(breakeven_trades):,}")
    
    # Calculate total P&L
    total_pnl = sum(float(p.get('pnl_usdt', 0)) for p in positions)
    total_pnl_pct = sum(float(p.get('pnl_percentage', 0)) for p in positions)
    
    print(f"\nTotal P&L (USDT):   ${total_pnl:,.2f}")
    print(f"Total P&L (%):      {total_pnl_pct:.2f}%")
    
    # Average win/loss
    if winning_trades:
        avg_win = statistics.mean([float(p.get('pnl_percentage', 0)) for p in winning_trades])
        max_win = max([float(p.get('pnl_percentage', 0)) for p in winning_trades])
        print(f"\nAverage Win:        +{avg_win:.2f}%")
        print(f"Largest Win:        +{max_win:.2f}%")
    
    if losing_trades:
        avg_loss = statistics.mean([float(p.get('pnl_percentage', 0)) for p in losing_trades])
        max_loss = min([float(p.get('pnl_percentage', 0)) for p in losing_trades])
        print(f"Average Loss:       {avg_loss:.2f}%")
        print(f"Largest Loss:       {max_loss:.2f}%")
    
    # Risk/Reward ratio
    if winning_trades and losing_trades:
        rr_ratio = abs(avg_win / avg_loss)
        print(f"Risk/Reward Ratio:  1:{rr_ratio:.2f}")
    
    # Expectancy
    if total_trades > 0:
        expectancy = (win_rate/100 * (avg_win if winning_trades else 0)) + ((100-win_rate)/100 * (avg_loss if losing_trades else 0))
        print(f"Expectancy:         {expectancy:.2f}%")
    
    print()
    print("=" * 80)
    print("⏱️  HOLD TIME ANALYSIS")
    print("=" * 80)
    
    # Hold time analysis
    winning_times = [float(p.get('hold_time_minutes', 0)) for p in winning_trades if p.get('hold_time_minutes')]
    losing_times = [float(p.get('hold_time_minutes', 0)) for p in losing_trades if p.get('hold_time_minutes')]
    
    if winning_times:
        print(f"Winning Trades:")
        print(f"  Average:          {statistics.mean(winning_times):.1f} minutes ({statistics.mean(winning_times)/60:.1f} hours)")
        print(f"  Median:           {statistics.median(winning_times):.1f} minutes")
        print(f"  Range:            {min(winning_times):.1f} - {max(winning_times):.1f} minutes")
    
    if losing_times:
        print(f"\nLosing Trades:")
        print(f"  Average:          {statistics.mean(losing_times):.1f} minutes ({statistics.mean(losing_times)/60:.1f} hours)")
        print(f"  Median:           {statistics.median(losing_times):.1f} minutes")
        print(f"  Range:            {min(losing_times):.1f} - {max(losing_times):.1f} minutes")
    
    print()
    print("=" * 80)
    print("🕐 SESSION ANALYSIS")
    print("=" * 80)
    
    # Session analysis
    session_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0.0})
    
    for p in positions:
        session = p.get('entry_session', 'unknown')
        pnl_pct = float(p.get('pnl_percentage', 0))
        
        if pnl_pct > 0:
            session_stats[session]['wins'] += 1
        else:
            session_stats[session]['losses'] += 1
        
        session_stats[session]['pnl'] += pnl_pct
    
    print("Session Performance:")
    for session, stats in sorted(session_stats.items(), key=lambda x: x[1]['wins'] + x[1]['losses'], reverse=True):
        total = stats['wins'] + stats['losses']
        win_rate_session = (stats['wins'] / total * 100) if total > 0 else 0
        print(f"  {session:15s} → {stats['wins']:3d}W / {stats['losses']:3d}L ({win_rate_session:5.1f}% WR) | P&L: {stats['pnl']:+7.2f}%")
    
    print()
    print("=" * 80)
    print("🚪 EXIT REASON ANALYSIS")
    print("=" * 80)
    
    # Exit reason analysis
    exit_reasons = Counter([p.get('exit_reason', 'unknown') for p in positions])
    
    print("Exit Reason Distribution:")
    for reason, count in exit_reasons.most_common():
        pct = (count / total_trades * 100)
        
        # Calculate win rate for this exit reason
        reason_trades = [p for p in positions if p.get('exit_reason') == reason]
        reason_wins = len([p for p in reason_trades if float(p.get('pnl_percentage', 0)) > 0])
        reason_win_rate = (reason_wins / len(reason_trades) * 100) if reason_trades else 0
        
        print(f"  {reason:30s} → {count:4d} ({pct:5.1f}%) | WR: {reason_win_rate:5.1f}%")
    
    print()
    print("=" * 80)
    print("📈 P&L DISTRIBUTION")
    print("=" * 80)
    
    # P&L buckets
    pnl_buckets = {
        'Large Loss (<-2%)': 0,
        'Medium Loss (-2% to -1%)': 0,
        'Small Loss (-1% to -0.5%)': 0,
        'Tiny Loss (-0.5% to 0%)': 0,
        'Breakeven (0%)': 0,
        'Tiny Win (0% to +0.5%)': 0,
        'Small Win (+0.5% to +1%)': 0,
        'Medium Win (+1% to +2%)': 0,
        'Large Win (>+2%)': 0,
    }
    
    for p in positions:
        pnl_pct = float(p.get('pnl_percentage', 0))
        
        if pnl_pct < -2:
            pnl_buckets['Large Loss (<-2%)'] += 1
        elif pnl_pct < -1:
            pnl_buckets['Medium Loss (-2% to -1%)'] += 1
        elif pnl_pct < -0.5:
            pnl_buckets['Small Loss (-1% to -0.5%)'] += 1
        elif pnl_pct < 0:
            pnl_buckets['Tiny Loss (-0.5% to 0%)'] += 1
        elif pnl_pct == 0:
            pnl_buckets['Breakeven (0%)'] += 1
        elif pnl_pct < 0.5:
            pnl_buckets['Tiny Win (0% to +0.5%)'] += 1
        elif pnl_pct < 1:
            pnl_buckets['Small Win (+0.5% to +1%)'] += 1
        elif pnl_pct < 2:
            pnl_buckets['Medium Win (+1% to +2%)'] += 1
        else:
            pnl_buckets['Large Win (>+2%)'] += 1
    
    for bucket, count in pnl_buckets.items():
        pct = (count / total_trades * 100) if total_trades > 0 else 0
        bar = '█' * int(pct / 2)
        print(f"  {bucket:30s} {count:4d} ({pct:5.1f}%) {bar}")
    
    print()
    print("=" * 80)
    print("🎯 EXIT MARKET DATA ANALYSIS (if available)")
    print("=" * 80)
    
    # Check for exit market data (new feature from earlier fix)
    positions_with_exit_data = [p for p in positions if 'exit_rsi' in p]
    
    if positions_with_exit_data:
        print(f"Found {len(positions_with_exit_data)} positions with exit market data")
        print()
        
        # RSI at exit
        winning_exit_rsi = [float(p.get('exit_rsi', 50)) for p in winning_trades if 'exit_rsi' in p]
        losing_exit_rsi = [float(p.get('exit_rsi', 50)) for p in losing_trades if 'exit_rsi' in p]
        
        if winning_exit_rsi:
            print(f"Winning Trades - Exit RSI:")
            print(f"  Average:          {statistics.mean(winning_exit_rsi):.1f}")
            print(f"  Median:           {statistics.median(winning_exit_rsi):.1f}")
        
        if losing_exit_rsi:
            print(f"\nLosing Trades - Exit RSI:")
            print(f"  Average:          {statistics.mean(losing_exit_rsi):.1f}")
            print(f"  Median:           {statistics.median(losing_exit_rsi):.1f}")
        
        # Volatility at exit
        winning_exit_vol = [float(p.get('exit_volatility', 0.02)) for p in winning_trades if 'exit_volatility' in p]
        losing_exit_vol = [float(p.get('exit_volatility', 0.02)) for p in losing_trades if 'exit_volatility' in p]
        
        if winning_exit_vol and losing_exit_vol:
            print(f"\nVolatility at Exit:")
            print(f"  Winning Trades:   {statistics.mean(winning_exit_vol):.4f}")
            print(f"  Losing Trades:    {statistics.mean(losing_exit_vol):.4f}")
    else:
        print("⚠️ No exit market data found (needs recent backend update)")
    
    print()
    print("=" * 80)
    print("🔍 KEY INSIGHTS & RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    # Generate insights
    insights = []
    
    if win_rate < 30:
        insights.append(f"🚨 CRITICAL: Win rate ({win_rate:.1f}%) is below 30% - system needs immediate attention")
        insights.append("   → Check if exit engine is cutting losses too late")
        insights.append("   → Verify entry signals are not too aggressive")
    elif win_rate < 45:
        insights.append(f"⚠️ WARNING: Win rate ({win_rate:.1f}%) is below target (49%)")
        insights.append("   → Review entry criteria and market regime adaptation")
    else:
        insights.append(f"✅ Win rate ({win_rate:.1f}%) is healthy")
    
    if winning_trades and losing_trades:
        if abs(avg_loss) > avg_win:
            insights.append(f"⚠️ Average loss ({avg_loss:.2f}%) > average win ({avg_win:.2f}%)")
            insights.append("   → Exit engine may be holding losers too long")
            insights.append("   → Consider tighter stop losses")
        else:
            insights.append(f"✅ Positive risk/reward: avg win ({avg_win:.2f}%) > avg loss ({avg_loss:.2f}%)")
    
    if losing_times and winning_times:
        if statistics.mean(losing_times) > statistics.mean(winning_times) * 1.5:
            insights.append(f"⚠️ Losing trades held {statistics.mean(losing_times)/statistics.mean(winning_times):.1f}x longer than winners")
            insights.append("   → Exit engine is not cutting losses fast enough")
            insights.append("   → Review Layer 3 reversal detection sensitivity")
    
    # Session insights
    best_session = max(session_stats.items(), key=lambda x: x[1]['wins'] / (x[1]['wins'] + x[1]['losses']) if (x[1]['wins'] + x[1]['losses']) > 0 else 0)
    worst_session = min(session_stats.items(), key=lambda x: x[1]['wins'] / (x[1]['wins'] + x[1]['losses']) if (x[1]['wins'] + x[1]['losses']) > 0 else 0)
    
    insights.append(f"📊 Best session: {best_session[0]} ({best_session[1]['wins'] / (best_session[1]['wins'] + best_session[1]['losses']) * 100:.1f}% WR)")
    insights.append(f"📊 Worst session: {worst_session[0]} ({worst_session[1]['wins'] / (worst_session[1]['wins'] + worst_session[1]['losses']) * 100:.1f}% WR)")
    
    for insight in insights:
        print(insight)
    
    print()
    print("=" * 80)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 80)
    
    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_win': avg_win if winning_trades else 0,
        'avg_loss': avg_loss if losing_trades else 0,
        'total_pnl': total_pnl,
        'insights': insights
    }


if __name__ == "__main__":
    analyze_closed_positions()

