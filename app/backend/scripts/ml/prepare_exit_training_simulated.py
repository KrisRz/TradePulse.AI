#!/usr/bin/env python3
"""
ENTERPRISE-GRADE EXIT MODEL TRAINING - SIMULATION-BASED
========================================================

Advanced training data generation using historical simulation:

1. Load 129,600 fresh 1m candles (Aug-Oct 2025)
2. Sample every 15 minutes (~6,400 potential entry points)
3. For each point, simulate "what if we held position for 1-6h?"
4. Calculate outcome: profit or loss?
5. Label based on outcome:
   - EXIT (1): Max drawdown < -0.5% (would lead to loss)
   - HOLD (0): Stayed profitable (would lead to profit)
6. Generate 30K-50K balanced training examples
7. Calculate technical indicators at each point

NO APPROXIMATIONS - Only real 2025 market data!

Author: TradePulse.AI Team
Date: 2025-10-31
"""

import os
import sys
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd
from scipy import stats

# Use standard logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
BINANCE_DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "ml" / "historical" / "binance_fresh" / "BTCUSDT_1m_3months.parquet"
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "data" / "ml" / "training" / "exit_layer3_simulated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Sampling configuration
SAMPLE_INTERVAL_MINUTES = 15  # Sample every 15 minutes
LOOKBACK_FOR_INDICATORS = 100  # 100 candles for RSI/MACD/BB calculation
LOOKAHEAD_HOURS = [1, 2, 4, 6]  # Check outcomes at 1h, 2h, 4h, 6h
LOSS_THRESHOLD = -0.5  # -0.5% max drawdown = EXIT signal

# Features for the model (8 features)
FEATURE_NAMES = [
    "close", "volume", "rsi", "macd", 
    "bb_position", "volatility", "trend_strength", "volume_ratio"
]


def calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
    """Calculate RSI indicator"""
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


def calculate_macd(prices: np.ndarray) -> float:
    """Calculate MACD (12, 26, 9) - return MACD line only"""
    if len(prices) < 26:
        return 0.0
    
    ema_12 = pd.Series(prices).ewm(span=12, adjust=False).mean()
    ema_26 = pd.Series(prices).ewm(span=26, adjust=False).mean()
    
    macd_line = ema_12.iloc[-1] - ema_26.iloc[-1]
    return float(macd_line)


def calculate_bollinger_position(prices: np.ndarray, current_price: float, period: int = 20) -> float:
    """Calculate Bollinger Band position"""
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
    """Calculate price volatility"""
    if len(prices) < period:
        return 0.02
    
    recent_prices = prices[-period:]
    mean_price = np.mean(recent_prices)
    
    if mean_price == 0:
        return 0.02
    
    volatility = np.std(recent_prices) / mean_price
    return float(volatility)


def calculate_trend_strength(prices: np.ndarray, period: int = 20) -> float:
    """Calculate trend strength using linear regression"""
    if len(prices) < period:
        return 0.0
    
    recent_prices = prices[-period:]
    x = np.arange(len(recent_prices))
    
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, recent_prices)
    
    mean_price = np.mean(recent_prices)
    if mean_price == 0:
        return 0.0
    
    normalized_slope = (slope * period) / mean_price
    return float(np.clip(normalized_slope, -0.5, 0.5))


def calculate_volume_ratio(volumes: np.ndarray, period: int = 20) -> float:
    """Calculate volume ratio"""
    if len(volumes) < period:
        return 1.0
    
    recent_volumes = volumes[-period:]
    avg_volume = np.mean(recent_volumes[:-1])
    current_volume = volumes[-1]
    
    if avg_volume == 0:
        return 1.0
    
    ratio = current_volume / avg_volume
    return float(ratio)


def calculate_technical_indicators(df: pd.DataFrame, idx: int) -> Dict[str, float]:
    """Calculate all technical indicators at specific index"""
    
    # Get lookback window
    start_idx = max(0, idx - LOOKBACK_FOR_INDICATORS)
    window_df = df.iloc[start_idx:idx+1]
    
    if len(window_df) < 20:  # Minimum for indicators
        return None
    
    prices = window_df['close'].values
    volumes = window_df['volume'].values
    current_price = prices[-1]
    
    try:
        indicators = {
            'close': float(current_price),
            'volume': float(volumes[-1]),
            'rsi': calculate_rsi(prices, period=14),
            'macd': calculate_macd(prices),
            'bb_position': calculate_bollinger_position(prices, current_price, period=20),
            'volatility': calculate_volatility(prices, period=20),
            'trend_strength': calculate_trend_strength(prices, period=20),
            'volume_ratio': calculate_volume_ratio(volumes, period=20),
        }
        
        # Validate all values are numbers
        if any(not isinstance(v, (int, float)) or np.isnan(v) for v in indicators.values()):
            return None
        
        return indicators
        
    except Exception as e:
        logger.warning(f"Failed to calculate indicators at idx {idx}: {e}")
        return None


def simulate_position_outcome(df: pd.DataFrame, entry_idx: int, lookahead_hours: int) -> Dict[str, float]:
    """Simulate what would happen if we held a LONG position from entry_idx
    
    Returns:
        - max_drawdown: Worst drawdown during hold period (%)
        - final_pnl: Final PnL at end of hold period (%)
        - exit_needed: True if max_drawdown < LOSS_THRESHOLD
    """
    
    entry_price = df.iloc[entry_idx]['close']
    lookahead_candles = lookahead_hours * 60  # hours to minutes
    
    end_idx = min(entry_idx + lookahead_candles, len(df) - 1)
    
    if end_idx <= entry_idx:
        return None
    
    # Get price movements during hold period
    hold_period = df.iloc[entry_idx:end_idx+1]
    prices = hold_period['close'].values
    
    # Calculate PnL for each candle
    pnl_percent = ((prices - entry_price) / entry_price) * 100
    
    # Find max drawdown (worst loss)
    max_drawdown = float(np.min(pnl_percent))
    
    # Final PnL at end of period
    final_pnl = float(pnl_percent[-1])
    
    # Would we need to exit due to loss?
    exit_needed = max_drawdown < LOSS_THRESHOLD
    
    return {
        'max_drawdown': max_drawdown,
        'final_pnl': final_pnl,
        'exit_needed': exit_needed,
        'entry_price': float(entry_price),
        'exit_price': float(prices[-1]),
        'hold_duration_minutes': len(prices)
    }


def generate_training_examples(df: pd.DataFrame) -> List[Dict]:
    """Generate training examples by simulating positions"""
    
    logger.info(f"📊 Generating training examples from {len(df)} candles...")
    logger.info(f"   Sampling every {SAMPLE_INTERVAL_MINUTES} minutes")
    logger.info(f"   Lookahead periods: {LOOKAHEAD_HOURS} hours")
    logger.info(f"   Loss threshold: {LOSS_THRESHOLD}%")
    
    training_examples = []
    skipped_count = 0
    
    # Sample every N minutes
    sample_indices = list(range(LOOKBACK_FOR_INDICATORS, len(df), SAMPLE_INTERVAL_MINUTES))
    
    logger.info(f"   Total sample points: {len(sample_indices)}")
    logger.info(f"   Expected ~{len(sample_indices) * len(LOOKAHEAD_HOURS)} examples")
    
    for i, idx in enumerate(sample_indices):
        if (i + 1) % 500 == 0:
            logger.info(f"   Processing sample {i + 1}/{len(sample_indices)} ({i/len(sample_indices)*100:.1f}%)")
        
        # Calculate technical indicators at this point
        indicators = calculate_technical_indicators(df, idx)
        
        if indicators is None:
            skipped_count += 1
            continue
        
        # For each lookahead period, simulate position outcome
        for lookahead_h in LOOKAHEAD_HOURS:
            outcome = simulate_position_outcome(df, idx, lookahead_h)
            
            if outcome is None:
                skipped_count += 1
                continue
            
            # Create training example
            example = {
                'timestamp': df.iloc[idx]['timestamp'].isoformat(),
                'lookahead_hours': lookahead_h,
                **indicators,  # All 8 features
                **outcome,     # Outcome metrics
                'target': 1 if outcome['exit_needed'] else 0  # EXIT (1) or HOLD (0)
            }
            
            training_examples.append(example)
    
    logger.info(f"✅ Generated {len(training_examples)} training examples (skipped {skipped_count})")
    
    return training_examples


def balance_dataset(examples: List[Dict], max_ratio: float = 1.5) -> List[Dict]:
    """Balance dataset to avoid extreme class imbalance
    
    Args:
        max_ratio: Maximum ratio between majority/minority class (1.5 = 60/40 split)
    """
    
    exit_examples = [ex for ex in examples if ex['target'] == 1]
    hold_examples = [ex for ex in examples if ex['target'] == 0]
    
    logger.info(f"📊 Original distribution:")
    logger.info(f"   EXIT (1): {len(exit_examples)} ({len(exit_examples)/len(examples)*100:.1f}%)")
    logger.info(f"   HOLD (0): {len(hold_examples)} ({len(hold_examples)/len(examples)*100:.1f}%)")
    
    # If already balanced, return as is
    if len(exit_examples) == 0 or len(hold_examples) == 0:
        return examples
    
    ratio = max(len(exit_examples), len(hold_examples)) / min(len(exit_examples), len(hold_examples))
    
    if ratio <= max_ratio:
        logger.info(f"   ✅ Dataset already balanced (ratio: {ratio:.2f})")
        return examples
    
    # Undersample majority class
    if len(hold_examples) > len(exit_examples):
        # Too many HOLD examples
        target_hold = int(len(exit_examples) * max_ratio)
        hold_examples = np.random.choice(hold_examples, target_hold, replace=False).tolist()
    else:
        # Too many EXIT examples
        target_exit = int(len(hold_examples) * max_ratio)
        exit_examples = np.random.choice(exit_examples, target_exit, replace=False).tolist()
    
    balanced = exit_examples + hold_examples
    np.random.shuffle(balanced)
    
    logger.info(f"📊 Balanced distribution:")
    logger.info(f"   EXIT (1): {len([ex for ex in balanced if ex['target'] == 1])} ({sum(ex['target'] for ex in balanced)/len(balanced)*100:.1f}%)")
    logger.info(f"   HOLD (0): {len([ex for ex in balanced if ex['target'] == 0])} ({(1-sum(ex['target'] for ex in balanced)/len(balanced))*100:.1f}%)")
    
    return balanced


def save_training_data(examples: List[Dict]):
    """Save training data to files"""
    
    logger.info(f"💾 Saving {len(examples)} training examples...")
    
    # Save as JSON
    output_json = OUTPUT_DIR / "exit_layer3_simulated_training_data.json"
    with open(output_json, 'w') as f:
        json.dump(examples, f, indent=2)
    logger.info(f"   ✅ Saved JSON: {output_json} ({output_json.stat().st_size / 1024 / 1024:.1f} MB)")
    
    # Save as CSV
    df = pd.DataFrame(examples)
    output_csv = OUTPUT_DIR / "exit_layer3_simulated_training_data.csv"
    df.to_csv(output_csv, index=False)
    logger.info(f"   ✅ Saved CSV: {output_csv} ({output_csv.stat().st_size / 1024 / 1024:.1f} MB)")
    
    # Save metadata
    metadata = {
        'total_examples': len(examples),
        'exit_examples': sum(ex['target'] for ex in examples),
        'hold_examples': len(examples) - sum(ex['target'] for ex in examples),
        'sample_interval_minutes': SAMPLE_INTERVAL_MINUTES,
        'lookahead_hours': LOOKAHEAD_HOURS,
        'loss_threshold': LOSS_THRESHOLD,
        'features': FEATURE_NAMES,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'source': 'Binance 3-month historical simulation',
        'date_range': {
            'start': df['timestamp'].min(),
            'end': df['timestamp'].max()
        }
    }
    
    metadata_file = OUTPUT_DIR / "exit_layer3_simulated_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"   ✅ Saved metadata: {metadata_file}")


def print_statistics(examples: List[Dict]):
    """Print dataset statistics"""
    
    df = pd.DataFrame(examples)
    
    logger.info("\n" + "=" * 80)
    logger.info("📊 TRAINING DATA STATISTICS")
    logger.info("=" * 80)
    logger.info(f"Total examples: {len(examples):,}")
    logger.info(f"\nTarget Distribution:")
    logger.info(f"   EXIT (1): {sum(ex['target'] for ex in examples):,} ({sum(ex['target'] for ex in examples)/len(examples)*100:.1f}%)")
    logger.info(f"   HOLD (0): {len(examples) - sum(ex['target'] for ex in examples):,} ({(1-sum(ex['target'] for ex in examples)/len(examples))*100:.1f}%)")
    
    logger.info(f"\nOutcome Statistics:")
    logger.info(f"   Avg max drawdown: {df['max_drawdown'].mean():.2f}%")
    logger.info(f"   Avg final PnL: {df['final_pnl'].mean():.2f}%")
    logger.info(f"   Avg hold duration: {df['hold_duration_minutes'].mean():.1f} minutes")
    
    logger.info(f"\nFeature Statistics:")
    logger.info(f"   Avg RSI: {df['rsi'].mean():.1f}")
    logger.info(f"   Avg MACD: {df['macd'].mean():.4f}")
    logger.info(f"   Avg BB Position: {df['bb_position'].mean():.2f}")
    logger.info(f"   Avg Volatility: {df['volatility'].mean():.4f}")
    logger.info(f"   Avg Trend: {df['trend_strength'].mean():.4f}")
    logger.info(f"   Avg Volume Ratio: {df['volume_ratio'].mean():.2f}")
    
    logger.info(f"\nLookahead Distribution:")
    for h in LOOKAHEAD_HOURS:
        count = len([ex for ex in examples if ex['lookahead_hours'] == h])
        logger.info(f"   {h}h: {count:,} examples")
    
    logger.info("=" * 80)


def main():
    """Main training data preparation pipeline"""
    
    logger.info("=" * 80)
    logger.info("🚀 EXIT MODEL TRAINING DATA - SIMULATION-BASED")
    logger.info("=" * 80)
    
    # Load Binance data
    logger.info(f"📂 Loading Binance data from {BINANCE_DATA_PATH}...")
    df = pd.read_parquet(BINANCE_DATA_PATH)
    logger.info(f"✅ Loaded {len(df):,} candles")
    logger.info(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Generate training examples
    examples = generate_training_examples(df)
    
    if not examples:
        logger.error("❌ No training examples generated!")
        return 1
    
    # Balance dataset
    balanced_examples = balance_dataset(examples, max_ratio=1.5)
    
    # Save training data
    save_training_data(balanced_examples)
    
    # Print statistics
    print_statistics(balanced_examples)
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ TRAINING DATA PREPARATION COMPLETED!")
    logger.info("=" * 80)
    logger.info(f"📁 Output directory: {OUTPUT_DIR}")
    logger.info(f"\n🚀 Next Step:")
    logger.info(f"   Run: python app/backend/scripts/ml/retrain_exit_layer3_simulated.py")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    exit(main())

