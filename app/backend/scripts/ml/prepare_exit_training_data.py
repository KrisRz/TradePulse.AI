#!/usr/bin/env python3
"""
ENTERPRISE-GRADE EXIT MODEL TRAINING DATA PREPARATION
=====================================================

Prepares real training data for Layer 3 Reversal Exit Model by:
1. Fetching all closed positions from DynamoDB (portfolio_closed_positions)
2. Fetching historical market data from tradepulse_market_data (33K+ candles)
3. Calculating technical indicators (RSI, MACD, BB, volatility) from real candles
4. Matching market conditions at exit_time for each position
5. Creating professional training dataset with real features

NO APPROXIMATIONS, NO MOCKS - Only real market data!

Author: TradePulse.AI Team
Date: 2025-10-31
"""

import os
import sys
import json
import pickle
from datetime import datetime, timezone, timedelta
from pathlib import Path
from decimal import Decimal
from typing import Dict, List, Any, Tuple

import numpy as np
import pandas as pd
from scipy import stats

# Add backend to path
current_script_dir = Path(__file__).parent
backend_dir = current_script_dir.parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use standard logging (avoid import issues)
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")

# Output paths
OUTPUT_DIR = backend_dir / "data" / "ml" / "training" / "exit_layer3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def decimal_to_float(obj):
    """Convert Decimal to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
    """Calculate RSI indicator from price series"""
    if len(prices) < period + 1:
        return 50.0
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi)


def calculate_macd(prices: np.ndarray) -> Tuple[float, float]:
    """Calculate MACD (12, 26, 9)"""
    if len(prices) < 26:
        return 0.0, 0.0
    
    # Calculate EMAs
    ema_12 = pd.Series(prices).ewm(span=12, adjust=False).mean()
    ema_26 = pd.Series(prices).ewm(span=26, adjust=False).mean()
    
    macd_line = ema_12.iloc[-1] - ema_26.iloc[-1]
    
    # Calculate signal line (9-period EMA of MACD)
    macd_series = ema_12 - ema_26
    macd_signal = macd_series.ewm(span=9, adjust=False).mean().iloc[-1]
    
    return float(macd_line), float(macd_signal)


def calculate_bollinger_position(prices: np.ndarray, current_price: float, period: int = 20) -> float:
    """Calculate Bollinger Band position (0=lower band, 0.5=middle, 1=upper band)"""
    if len(prices) < period:
        return 0.5
    
    recent_prices = prices[-period:]
    sma = np.mean(recent_prices)
    std = np.std(recent_prices)
    
    if std == 0:
        return 0.5
    
    upper_band = sma + (2 * std)
    lower_band = sma - (2 * std)
    
    if upper_band == lower_band:
        return 0.5
    
    bb_position = (current_price - lower_band) / (upper_band - lower_band)
    return float(np.clip(bb_position, 0.0, 1.0))


def calculate_volatility(prices: np.ndarray, period: int = 20) -> float:
    """Calculate price volatility as std/mean ratio"""
    if len(prices) < period:
        return 0.02
    
    recent_prices = prices[-period:]
    mean_price = np.mean(recent_prices)
    
    if mean_price == 0:
        return 0.02
    
    volatility = np.std(recent_prices) / mean_price
    return float(volatility)


def calculate_trend_strength(prices: np.ndarray, period: int = 20) -> float:
    """Calculate trend strength using linear regression slope"""
    if len(prices) < period:
        return 0.0
    
    recent_prices = prices[-period:]
    x = np.arange(len(recent_prices))
    
    # Linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, recent_prices)
    
    # Normalize slope by price level
    mean_price = np.mean(recent_prices)
    if mean_price == 0:
        return 0.0
    
    normalized_slope = (slope * period) / mean_price
    
    # Clip to reasonable range
    return float(np.clip(normalized_slope, -0.5, 0.5))


def calculate_volume_ratio(volumes: np.ndarray, period: int = 20) -> float:
    """Calculate current volume ratio to moving average"""
    if len(volumes) < period:
        return 1.0
    
    recent_volumes = volumes[-period:]
    avg_volume = np.mean(recent_volumes[:-1])  # Exclude current volume
    current_volume = volumes[-1]
    
    if avg_volume == 0:
        return 1.0
    
    ratio = current_volume / avg_volume
    return float(ratio)


async def fetch_closed_positions_from_dynamodb() -> List[Dict]:
    """Fetch all closed positions from DynamoDB"""
    import boto3
    
    logger.info("📡 Fetching closed positions from DynamoDB...")
    
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table('portfolio_closed_positions')
    
    # Scan all items
    response = table.scan()
    positions = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        positions.extend(response['Items'])
    
    logger.info(f"✅ Fetched {len(positions)} closed positions")
    
    # Convert Decimals to float
    positions = [
        {k: decimal_to_float(v) for k, v in pos.items()}
        for pos in positions
    ]
    
    return positions


async def fetch_historical_candles_from_dynamodb(start_time: datetime, end_time: datetime) -> pd.DataFrame:
    """Fetch historical candles from tradepulse_market_data table"""
    import boto3
    
    logger.info(f"📊 Fetching historical candles from {start_time} to {end_time}...")
    
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table('tradepulse_market_data')
    
    # Scan with filter (timestamp between start and end)
    start_ts = int(start_time.timestamp())
    end_ts = int(end_time.timestamp())
    
    logger.info(f"   Timestamp range: {start_ts} to {end_ts}")
    
    # Scan all items (expensive but necessary for training)
    response = table.scan()
    candles = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        candles.extend(response['Items'])
        
        if len(candles) % 5000 == 0:
            logger.info(f"   Fetched {len(candles)} candles so far...")
    
    logger.info(f"✅ Fetched {len(candles)} total candles from DynamoDB")
    
    # Convert to DataFrame
    df = pd.DataFrame(candles)
    
    # Convert Decimals to float
    for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']:
        if col in df.columns:
            df[col] = df[col].apply(decimal_to_float)
    
    # Filter by timestamp range
    df = df[(df['timestamp'] >= start_ts) & (df['timestamp'] <= end_ts)]
    
    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    logger.info(f"✅ Filtered to {len(df)} candles in date range")
    
    return df


def calculate_technical_indicators_at_timestamp(
    candles_df: pd.DataFrame,
    target_timestamp: int,
    lookback_minutes: int = 100
) -> Dict[str, float]:
    """Calculate technical indicators at specific timestamp using lookback window"""
    
    # Get candles before target timestamp
    mask = candles_df['timestamp'] <= target_timestamp
    historical_candles = candles_df[mask].tail(lookback_minutes)
    
    if len(historical_candles) < 20:  # Minimum for indicators
        logger.warning(f"Insufficient data at timestamp {target_timestamp}: {len(historical_candles)} candles")
        return {
            'close': 0.0,
            'volume': 0.0,
            'rsi': 50.0,
            'macd': 0.0,
            'bb_position': 0.5,
            'volatility': 0.02,
            'trend_strength': 0.0,
            'volume_ratio': 1.0,
        }
    
    prices = historical_candles['close'].values
    volumes = historical_candles['volume'].values
    current_price = prices[-1]
    
    # Calculate all indicators
    rsi = calculate_rsi(prices, period=14)
    macd, macd_signal = calculate_macd(prices)
    bb_position = calculate_bollinger_position(prices, current_price, period=20)
    volatility = calculate_volatility(prices, period=20)
    trend_strength = calculate_trend_strength(prices, period=20)
    volume_ratio = calculate_volume_ratio(volumes, period=20)
    
    return {
        'close': float(current_price),
        'volume': float(volumes[-1]),
        'rsi': rsi,
        'macd': macd,
        'bb_position': bb_position,
        'volatility': volatility,
        'trend_strength': trend_strength,
        'volume_ratio': volume_ratio,
    }


async def prepare_training_data():
    """Main function to prepare training data"""
    
    logger.info("=" * 80)
    logger.info("🚀 ENTERPRISE EXIT MODEL TRAINING DATA PREPARATION")
    logger.info("=" * 80)
    
    # Step 1: Fetch closed positions
    positions = await fetch_closed_positions_from_dynamodb()
    
    if not positions:
        logger.error("❌ No closed positions found!")
        return
    
    # Step 2: Determine date range needed
    exit_times = []
    for pos in positions:
        try:
            exit_time_str = pos.get('exit_time') or pos.get('closed_at')
            if exit_time_str:
                exit_time = datetime.fromisoformat(exit_time_str.replace('Z', '+00:00'))
                exit_times.append(exit_time)
        except Exception as e:
            logger.warning(f"Failed to parse exit time: {e}")
    
    if not exit_times:
        logger.error("❌ No valid exit times found!")
        return
    
    min_exit_time = min(exit_times)
    max_exit_time = max(exit_times)
    
    logger.info(f"📅 Date range: {min_exit_time} to {max_exit_time}")
    logger.info(f"   Span: {(max_exit_time - min_exit_time).days} days")
    
    # Step 3: Fetch historical candles (with extra lookback for indicators)
    lookback_days = 7  # Extra days for indicator calculation
    start_fetch = min_exit_time - timedelta(days=lookback_days)
    end_fetch = max_exit_time + timedelta(hours=1)
    
    candles_df = await fetch_historical_candles_from_dynamodb(start_fetch, end_fetch)
    
    if candles_df.empty:
        logger.error("❌ No historical candles found in DynamoDB!")
        logger.info("💡 Hint: Check if tradepulse_market_data table has data")
        return
    
    # Step 4: Calculate indicators for each position's exit time
    logger.info("🔄 Calculating technical indicators for each position...")
    
    training_data = []
    skipped_count = 0
    
    for i, pos in enumerate(positions):
        if (i + 1) % 50 == 0:
            logger.info(f"   Processing position {i + 1}/{len(positions)}...")
        
        try:
            # Parse exit time
            exit_time_str = pos.get('exit_time') or pos.get('closed_at')
            if not exit_time_str:
                skipped_count += 1
                continue
            
            exit_time = datetime.fromisoformat(exit_time_str.replace('Z', '+00:00'))
            exit_timestamp = int(exit_time.timestamp())
            
            # Calculate indicators at exit time
            indicators = calculate_technical_indicators_at_timestamp(
                candles_df,
                exit_timestamp,
                lookback_minutes=100
            )
            
            # Skip if insufficient data
            if indicators['close'] == 0.0:
                skipped_count += 1
                continue
            
            # Prepare training example
            training_example = {
                'position_id': pos.get('position_id', 'unknown'),
                'exit_time': exit_time_str,
                'exit_price': float(pos.get('exit_price', 0.0)),
                'entry_price': float(pos.get('entry_price', 0.0)),
                'pnl_percentage': float(pos.get('pnl_percentage', 0.0)),
                'duration_minutes': float(pos.get('duration_minutes', 0.0)),
                'ai_confidence': float(pos.get('ai_confidence', 0.0)),
                # Real market features at exit
                **indicators
            }
            
            training_data.append(training_example)
            
        except Exception as e:
            logger.warning(f"Failed to process position {pos.get('position_id')}: {e}")
            skipped_count += 1
    
    logger.info(f"✅ Prepared {len(training_data)} training examples (skipped {skipped_count})")
    
    # Step 5: Save to files
    if not training_data:
        logger.error("❌ No training data prepared!")
        return
    
    # Save as JSON
    output_json = OUTPUT_DIR / "exit_layer3_training_data.json"
    with open(output_json, 'w') as f:
        json.dump(training_data, f, indent=2)
    
    logger.info(f"💾 Saved JSON: {output_json}")
    
    # Save as CSV for easier inspection
    df_training = pd.DataFrame(training_data)
    output_csv = OUTPUT_DIR / "exit_layer3_training_data.csv"
    df_training.to_csv(output_csv, index=False)
    
    logger.info(f"💾 Saved CSV: {output_csv}")
    
    # Print statistics
    logger.info("\n" + "=" * 80)
    logger.info("📊 TRAINING DATA STATISTICS")
    logger.info("=" * 80)
    logger.info(f"Total examples: {len(training_data)}")
    logger.info(f"Date range: {min_exit_time.date()} to {max_exit_time.date()}")
    logger.info(f"\nPnL Distribution:")
    logger.info(f"   Profitable (PnL > 0): {sum(1 for d in training_data if d['pnl_percentage'] > 0)} ({sum(1 for d in training_data if d['pnl_percentage'] > 0) / len(training_data):.1%})")
    logger.info(f"   Losing (PnL < 0): {sum(1 for d in training_data if d['pnl_percentage'] < 0)} ({sum(1 for d in training_data if d['pnl_percentage'] < 0) / len(training_data):.1%})")
    logger.info(f"   Avg PnL: {np.mean([d['pnl_percentage'] for d in training_data]):.2f}%")
    logger.info(f"\nFeature Statistics:")
    logger.info(f"   Avg RSI: {np.mean([d['rsi'] for d in training_data]):.1f}")
    logger.info(f"   Avg MACD: {np.mean([d['macd'] for d in training_data]):.4f}")
    logger.info(f"   Avg BB Position: {np.mean([d['bb_position'] for d in training_data]):.2f}")
    logger.info(f"   Avg Volatility: {np.mean([d['volatility'] for d in training_data]):.4f}")
    logger.info(f"   Avg Trend Strength: {np.mean([d['trend_strength'] for d in training_data]):.4f}")
    logger.info("=" * 80)
    
    return output_json, output_csv


if __name__ == "__main__":
    import asyncio
    
    # Run async preparation
    asyncio.run(prepare_training_data())

