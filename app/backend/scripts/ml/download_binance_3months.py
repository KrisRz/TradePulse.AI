#!/usr/bin/env python3
"""
ENTERPRISE-GRADE BINANCE DATA DOWNLOADER
=========================================

Downloads FRESH 3-month historical data from Binance API:
- BTCUSDT 1m candles
- Last 3 months (August-October 2025)
- ~130,000 candles for proper training
- Professional rate limiting and error handling

NO OLD DATA - Only fresh market conditions!

Author: TradePulse.AI Team
Date: 2025-10-31
"""

import os
import sys
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict

import pandas as pd
import requests

# Use standard logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
SYMBOL = "BTCUSDT"
INTERVAL = "1m"
MONTHS_TO_DOWNLOAD = 3
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "data" / "ml" / "historical" / "binance_fresh"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BINANCE_API_BASE = "https://api.binance.com"
KLINES_ENDPOINT = "/api/v3/klines"


def get_date_ranges_for_last_3_months() -> List[tuple]:
    """Calculate date ranges for last 3 months in batches"""
    now = datetime.now(timezone.utc)
    
    # Calculate start date (3 months ago)
    start_date = now - timedelta(days=90)
    
    logger.info(f"📅 Downloading data from {start_date.date()} to {now.date()}")
    logger.info(f"   Total span: 90 days (~130,000 candles)")
    
    # Binance API limit: 1000 candles per request
    # 1m interval: 1000 minutes = ~16.7 hours per batch
    # So we need multiple batches
    
    batches = []
    current_start = start_date
    batch_duration = timedelta(minutes=1000)  # 1000 candles = 1000 minutes
    
    while current_start < now:
        batch_end = min(current_start + batch_duration, now)
        batches.append((current_start, batch_end))
        current_start = batch_end
    
    logger.info(f"📦 Will download in {len(batches)} batches")
    
    return batches


def download_batch(symbol: str, interval: str, start_time: datetime, end_time: datetime) -> List[List]:
    """Download single batch from Binance API"""
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    params = {
        'symbol': symbol,
        'interval': interval,
        'startTime': start_ms,
        'endTime': end_ms,
        'limit': 1000
    }
    
    url = f"{BINANCE_API_BASE}{KLINES_ENDPOINT}"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        candles = response.json()
        return candles
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download batch: {e}")
        return []


def download_all_candles() -> pd.DataFrame:
    """Download all candles for last 3 months"""
    
    logger.info("=" * 80)
    logger.info("🚀 DOWNLOADING FRESH BINANCE DATA")
    logger.info("=" * 80)
    logger.info(f"Symbol: {SYMBOL}")
    logger.info(f"Interval: {INTERVAL}")
    logger.info(f"Period: Last {MONTHS_TO_DOWNLOAD} months")
    logger.info("=" * 80)
    
    # Get date ranges
    batches = get_date_ranges_for_last_3_months()
    
    all_candles = []
    
    for i, (start_time, end_time) in enumerate(batches, 1):
        logger.info(f"📥 Downloading batch {i}/{len(batches)}: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
        
        # Download batch
        candles = download_batch(SYMBOL, INTERVAL, start_time, end_time)
        
        if candles:
            all_candles.extend(candles)
            logger.info(f"   ✅ Downloaded {len(candles)} candles (total: {len(all_candles)})")
        else:
            logger.warning(f"   ⚠️ No data received for this batch")
        
        # Rate limiting: Binance allows 1200 requests/minute
        # Sleep 0.1s between requests to be safe (600 req/min)
        if i < len(batches):
            time.sleep(0.1)
        
        # Progress update every 10 batches
        if i % 10 == 0:
            logger.info(f"   📊 Progress: {i}/{len(batches)} batches ({i/len(batches)*100:.1f}%)")
    
    logger.info(f"\n✅ Downloaded {len(all_candles)} total candles")
    
    # Convert to DataFrame
    df = pd.DataFrame(all_candles, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # Convert types
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    
    for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
        df[col] = df[col].astype(float)
    
    df['trades'] = df['trades'].astype(int)
    
    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Remove duplicates
    df = df.drop_duplicates(subset=['timestamp'], keep='first')
    
    logger.info(f"✅ Processed {len(df)} unique candles")
    
    return df


def save_candles(df: pd.DataFrame):
    """Save candles to multiple formats"""
    
    logger.info("\n💾 Saving data...")
    
    # Save as CSV
    csv_file = OUTPUT_DIR / f"{SYMBOL}_1m_3months.csv"
    df.to_csv(csv_file, index=False)
    logger.info(f"   ✅ Saved CSV: {csv_file} ({csv_file.stat().st_size / 1024 / 1024:.1f} MB)")
    
    # Save as Parquet (compressed, faster to load)
    parquet_file = OUTPUT_DIR / f"{SYMBOL}_1m_3months.parquet"
    df.to_parquet(parquet_file, index=False, compression='snappy')
    logger.info(f"   ✅ Saved Parquet: {parquet_file} ({parquet_file.stat().st_size / 1024 / 1024:.1f} MB)")
    
    # Save metadata
    metadata = {
        'symbol': SYMBOL,
        'interval': INTERVAL,
        'candles_count': len(df),
        'start_date': df['timestamp'].min().isoformat(),
        'end_date': df['timestamp'].max().isoformat(),
        'downloaded_at': datetime.now(timezone.utc).isoformat(),
        'source': 'Binance API',
        'columns': list(df.columns)
    }
    
    metadata_file = OUTPUT_DIR / f"{SYMBOL}_1m_3months_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"   ✅ Saved metadata: {metadata_file}")


def print_statistics(df: pd.DataFrame):
    """Print data statistics"""
    
    logger.info("\n" + "=" * 80)
    logger.info("📊 DATA STATISTICS")
    logger.info("=" * 80)
    logger.info(f"Total candles: {len(df):,}")
    logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    logger.info(f"Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")
    logger.info(f"\nPrice Range:")
    logger.info(f"   Min:  ${df['low'].min():,.2f}")
    logger.info(f"   Max:  ${df['high'].max():,.2f}")
    logger.info(f"   Last: ${df['close'].iloc[-1]:,.2f}")
    logger.info(f"\nVolume:")
    logger.info(f"   Total: {df['volume'].sum():,.2f} BTC")
    logger.info(f"   Avg:   {df['volume'].mean():.2f} BTC per minute")
    logger.info(f"\nData Quality:")
    logger.info(f"   Missing values: {df.isnull().sum().sum()}")
    logger.info(f"   Duplicate timestamps: {df.duplicated(subset=['timestamp']).sum()}")
    logger.info("=" * 80)


def main():
    """Main download pipeline"""
    
    try:
        # Download data
        df = download_all_candles()
        
        if df.empty:
            logger.error("❌ No data downloaded!")
            return 1
        
        # Save data
        save_candles(df)
        
        # Print statistics
        print_statistics(df)
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ DOWNLOAD COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        logger.info(f"📁 Output directory: {OUTPUT_DIR}")
        logger.info(f"\n🚀 Next Step:")
        logger.info(f"   Run: python app/backend/scripts/ml/prepare_exit_training_from_binance_3m.py")
        logger.info("=" * 80)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Download failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

