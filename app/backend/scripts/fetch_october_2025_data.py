"""
🔄 FETCH OCTOBER 2025 HISTORICAL DATA
======================================

Fetch fresh 1m candles from October 2025 to join with live trades.

This data is needed because:
- Live trades: October 9-22, 2025
- Existing historical data: ends December 2024
- 0/235 trades could be joined due to date mismatch

Author: TradePulse.AI
Date: 2025-10-22
"""

import asyncio
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta
import requests
from time import sleep

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data/ml/historical/processed"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

OUTPUT_FILE = OUTPUT_DIR / "BTCUSDT_1m_october_2025.parquet"


def fetch_klines_from_binance(symbol, interval, start_ms, end_ms, limit=1000):
    """
    Fetch klines directly from Binance REST API
    """
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": limit
    }
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_october_2025_data():
    """
    Fetch 1m candles for October 1-22, 2025 from Binance
    """
    logger.info("=" * 80)
    logger.info("🔄 FETCHING OCTOBER 2025 HISTORICAL DATA")
    logger.info("=" * 80)
    
    # Date range
    start_date = datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_date = datetime(2025, 10, 22, 23, 59, 59, tzinfo=timezone.utc)
    
    logger.info(f"📅 Date range: {start_date} → {end_date}")
    logger.info(f"📊 Expected candles: ~{(end_date - start_date).days * 24 * 60:,}")
    
    all_candles = []
    current_start = start_date
    
    # Binance limit: 1000 candles per request
    # 1000 minutes = ~16.6 hours
    batch_size = timedelta(hours=12)  # Fetch 12h at a time
    
    total_batches = int((end_date - start_date).total_seconds() / batch_size.total_seconds()) + 1
    logger.info(f"🔄 Will fetch {total_batches} batches...")
    
    batch_num = 0
    while current_start < end_date:
        batch_num += 1
        current_end = min(current_start + batch_size, end_date)
        
        try:
            logger.info(f"\n📦 Batch {batch_num}/{total_batches}: {current_start.strftime('%Y-%m-%d %H:%M')} → {current_end.strftime('%Y-%m-%d %H:%M')}")
            
            # Convert to milliseconds
            start_ms = int(current_start.timestamp() * 1000)
            end_ms = int(current_end.timestamp() * 1000)
            
            # Fetch klines from Binance
            klines = fetch_klines_from_binance(
                symbol="BTCUSDT",
                interval="1m",
                start_ms=start_ms,
                end_ms=end_ms,
                limit=1000
            )
            
            if not klines:
                logger.warning(f"   ⚠️ No data returned for this batch")
                current_start = current_end
                continue
            
            # Convert to DataFrame
            df_batch = pd.DataFrame(klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'count', 'taker_buy_volume',
                'taker_buy_quote_volume', 'ignore'
            ])
            
            # Convert timestamps
            df_batch['timestamp'] = pd.to_datetime(df_batch['open_time'], unit='ms')
            
            # Convert prices to float
            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume', 
                       'taker_buy_volume', 'taker_buy_quote_volume']:
                df_batch[col] = df_batch[col].astype(float)
            
            all_candles.append(df_batch)
            
            logger.info(f"   ✅ Fetched {len(df_batch)} candles (total: {sum(len(d) for d in all_candles):,})")
            
            # Move to next batch
            current_start = current_end
            
            # Rate limiting (Binance: 1200 requests/minute)
            sleep(0.1)
            
        except Exception as e:
            logger.error(f"   ❌ Batch failed: {e}")
            # Try to continue
            current_start = current_end
            sleep(2)
    
    if not all_candles:
        logger.error("❌ No data fetched!")
        return None
    
    # Combine all batches
    logger.info(f"\n🔗 Combining {len(all_candles)} batches...")
    df = pd.concat(all_candles, ignore_index=True)
    
    # Remove duplicates (if any)
    original_len = len(df)
    df = df.drop_duplicates(subset=['open_time'])
    df = df.sort_values('timestamp')
    
    if len(df) < original_len:
        logger.info(f"   🧹 Removed {original_len - len(df)} duplicates")
    
    logger.info(f"\n📊 FINAL DATASET:")
    logger.info(f"   Rows: {len(df):,}")
    logger.info(f"   Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
    logger.info(f"   Columns: {list(df.columns)}")
    
    # Save to parquet
    logger.info(f"\n💾 Saving to: {OUTPUT_FILE}")
    df.to_parquet(OUTPUT_FILE, index=False)
    
    file_size_mb = OUTPUT_FILE.stat().st_size / 1024 / 1024
    logger.info(f"   ✅ Saved {file_size_mb:.2f} MB")
    
    return df


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate technical indicators for October 2025 data
    (same as in historical dataset)
    """
    logger.info("\n🔧 Calculating technical indicators...")
    
    import numpy as np
    
    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # SMAs
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    
    # EMAs
    df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_diff'] = df['macd'] - df['macd_signal']
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    bb_std = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
    df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    # Volume indicators
    df['volume_sma'] = df['volume'].rolling(window=20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']
    
    # Price changes
    df['price_change_1h'] = df['close'].pct_change(60) * 100
    df['price_change_4h'] = df['close'].pct_change(240) * 100
    df['price_change_24h'] = df['close'].pct_change(1440) * 100
    
    # Volatility
    df['volatility_20'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
    
    # High/Low ratio
    df['high_low_ratio'] = (df['high'] - df['low']) / df['close']
    
    # Support/Resistance (simplified - rolling min/max)
    df['support'] = df['low'].rolling(window=20).min()
    df['resistance'] = df['high'].rolling(window=20).max()
    df['support_distance'] = (df['close'] - df['support']) / df['close']
    df['resistance_distance'] = (df['resistance'] - df['close']) / df['close']
    
    # ATR (Average True Range)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    # OBV (On Balance Volume)
    df['obv'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
    
    # Stochastic Oscillator
    low_14 = df['low'].rolling(window=14).min()
    high_14 = df['high'].rolling(window=14).max()
    df['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
    df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
    
    # Fill NaN with reasonable defaults
    df['rsi'] = df['rsi'].fillna(50)
    df['macd'] = df['macd'].fillna(0)
    df['macd_signal'] = df['macd_signal'].fillna(0)
    df['stoch_k'] = df['stoch_k'].fillna(50)
    df['stoch_d'] = df['stoch_d'].fillna(50)
    
    logger.info(f"   ✅ Calculated {len([c for c in df.columns if c not in ['open_time', 'timestamp']])} indicators")
    
    return df


def main():
    """Main entry point"""
    try:
        # Check if file already exists
        if OUTPUT_FILE.exists():
            logger.warning(f"⚠️ File already exists: {OUTPUT_FILE}")
            response = input("Overwrite? (y/n): ")
            if response.lower() != 'y':
                logger.info("❌ Aborted")
                return
        
        # Fetch data
        df = fetch_october_2025_data()
        
        if df is None:
            logger.error("❌ Failed to fetch data")
            return
        
        # Calculate indicators
        df_with_indicators = calculate_technical_indicators(df)
        
        # Save final version with indicators
        final_output = OUTPUT_DIR / "BTCUSDT_1m_october_2025_with_indicators.parquet"
        logger.info(f"\n💾 Saving final version with indicators to: {final_output}")
        df_with_indicators.to_parquet(final_output, index=False)
        
        file_size_mb = final_output.stat().st_size / 1024 / 1024
        logger.info(f"   ✅ Saved {file_size_mb:.2f} MB")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ OCTOBER 2025 DATA FETCH COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"\n📊 Files created:")
        logger.info(f"   1. Raw data: {OUTPUT_FILE}")
        logger.info(f"   2. With indicators: {final_output}")
        logger.info(f"\n🎯 Ready for training data preparation!")
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

