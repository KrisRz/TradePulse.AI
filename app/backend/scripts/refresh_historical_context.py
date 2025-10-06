"""
TradePulse.AI - Historical Context Refresh Job
Fetches 90 days of data from Binance API and updates market_context_cache

Run: Daily (via EventBridge schedule)
Purpose: Keep historical context fresh for day trading
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any

import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


async def fetch_historical_data_from_binance(symbol: str = "BTCUSDT", days: int = 90) -> pd.DataFrame:
    """Fetch 90 days of 1-hour candles from Binance API"""
    import aiohttp
    
    logger.info(f"📥 Fetching {days} days of historical data for {symbol}...")
    
    # Binance klines endpoint
    url = "https://api.binance.com/api/v3/klines"
    
    # Calculate timestamps
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    
    params = {
        'symbol': symbol,
        'interval': '1h',  # 1-hour candles (90 days = ~2160 candles)
        'startTime': int(start_time.timestamp() * 1000),
        'endTime': int(end_time.timestamp() * 1000),
        'limit': 1000  # Max per request
    }
    
    all_candles = []
    
    async with aiohttp.ClientSession() as session:
        # Binance limit: 1000 candles per request
        # 90 days * 24h = 2160 candles → need 3 requests
        current_start = int(start_time.timestamp() * 1000)
        
        while current_start < int(end_time.timestamp() * 1000):
            params['startTime'] = current_start
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"Binance API error: {response.status}")
                
                data = await response.json()
                
                if not data:
                    break
                
                all_candles.extend(data)
                
                # Update start time for next batch (last candle close time + 1ms)
                current_start = int(data[-1][6]) + 1
                
                logger.info(f"   Fetched {len(data)} candles (total: {len(all_candles)})")
                
                # Rate limiting (be nice to Binance API)
                await asyncio.sleep(0.2)
    
    # Convert to DataFrame
    df = pd.DataFrame(all_candles, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # Convert types
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    df['timestamp'] = pd.to_datetime(df['close_time'], unit='ms')
    
    logger.info(f"✅ Fetched {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    return df


def calculate_support_resistance_levels(df: pd.DataFrame, period: str = "30D") -> Dict[str, List[float]]:
    """Calculate support/resistance levels from historical data"""
    logger.info(f"📊 Calculating S/R levels for {period}...")
    
    support_levels = []
    resistance_levels = []
    
    # Method 1: Historical touch points (strict)
    lows = df['low'].rolling(window=20).min()
    highs = df['high'].rolling(window=20).max()
    
    for i in range(20, len(lows) - 20):
        # Support
        if lows.iloc[i] == lows.iloc[i-10:i+10].min():
            price_level = float(lows.iloc[i])
            touches = 0
            
            for j in range(i+1, min(i+50, len(df))):
                if abs(df['low'].iloc[j] - price_level) / price_level < 0.03:
                    touches += 1
            
            if touches >= 1:
                support_levels.append(price_level)
        
        # Resistance
        if highs.iloc[i] == highs.iloc[i-10:i+10].max():
            price_level = float(highs.iloc[i])
            touches = 0
            
            for j in range(i+1, min(i+50, len(df))):
                if abs(df['high'].iloc[j] - price_level) / price_level < 0.03:
                    touches += 1
            
            if touches >= 1:
                resistance_levels.append(price_level)
    
    # Method 2: Recent swing points (last 48h)
    recent_data = df.tail(48)  # Last 48 hours
    
    for i in range(5, len(recent_data) - 5):
        low = recent_data['low'].iloc[i]
        high = recent_data['high'].iloc[i]
        
        if low == recent_data['low'].iloc[i-5:i+5].min():
            support_levels.append(float(low))
        
        if high == recent_data['high'].iloc[i-5:i+5].max():
            resistance_levels.append(float(high))
    
    # Deduplicate and sort
    support_levels = sorted(list(set(support_levels)))[-15:]
    resistance_levels = sorted(list(set(resistance_levels)))[-15:]
    
    logger.info(f"✅ Found {len(support_levels)} support, {len(resistance_levels)} resistance levels")
    
    return {
        "support": support_levels,
        "resistance": resistance_levels
    }


def calculate_price_ranges(df: pd.DataFrame) -> Dict[str, Dict]:
    """Calculate price ranges for different periods"""
    logger.info("📊 Calculating price ranges...")
    
    ranges = {}
    current_price = float(df['close'].iloc[-1])
    
    for period_name, days in [("7D", 7), ("30D", 30), ("90D", 90)]:
        period_data = df.tail(days * 24)  # 24 hours per day
        
        if len(period_data) == 0:
            continue
        
        high = float(period_data['high'].max())
        low = float(period_data['low'].min())
        range_pct = ((high - low) / low) * 100
        current_position = (current_price - low) / (high - low) if high != low else 0.5
        
        # Get S/R for this period
        sr_levels = calculate_support_resistance_levels(period_data, period_name)
        
        ranges[period_name] = {
            "period": period_name,
            "high": high,
            "low": low,
            "range_pct": range_pct,
            "current_position": current_position,
            "support_levels": sr_levels["support"],
            "resistance_levels": sr_levels["resistance"],
            "last_updated": int(datetime.now(timezone.utc).timestamp())
        }
        
        logger.info(f"   {period_name}: ${low:.2f} - ${high:.2f} (range: {range_pct:.1f}%)")
    
    return ranges


async def save_to_dynamodb(data: Dict[str, Any]):
    """Save historical context to DynamoDB with TTL"""
    from app.backend.core.database import DynamoDBClient
    from app.backend.core.config import get_settings
    
    logger.info("💾 Saving to DynamoDB...")
    
    settings = get_settings()
    client = DynamoDBClient(local_development=settings.is_development)
    
    # Calculate TTL (90 days from now)
    ttl_timestamp = int((datetime.now(timezone.utc) + timedelta(days=90)).timestamp())
    
    # Prepare DynamoDB item
    item = {
        "symbol": "BTCUSDT",
        "period": "90D",
        "cache_key": "market_context_90d",
        "price_ranges": data["price_ranges"],
        "support_levels": data["price_ranges"]["30D"]["support_levels"],
        "resistance_levels": data["price_ranges"]["30D"]["resistance_levels"],
        "pattern_success_rates": {},  # TODO: Calculate from closed positions
        "last_updated": int(datetime.now(timezone.utc).timestamp()),
        "ttl": ttl_timestamp  # Auto-delete after 90 days
    }
    
    # Save to DynamoDB
    success = client.put_item("market_context_cache", item)
    
    if success:
        logger.info(f"✅ Saved to DynamoDB (TTL: {datetime.fromtimestamp(ttl_timestamp, tz=timezone.utc)})")
    else:
        logger.error("❌ Failed to save to DynamoDB")
    
    return success


async def refresh_historical_context():
    """Main refresh function"""
    try:
        logger.info("=" * 80)
        logger.info("🔄 HISTORICAL CONTEXT REFRESH JOB STARTED")
        logger.info(f"⏰ Time: {datetime.now(timezone.utc).isoformat()}")
        logger.info("=" * 80)
        
        # 1. Fetch data from Binance
        df = await fetch_historical_data_from_binance("BTCUSDT", days=90)
        
        # 2. Calculate price ranges and S/R levels
        price_ranges = calculate_price_ranges(df)
        
        # 3. Prepare data structure
        historical_context = {
            "symbol": "BTCUSDT",
            "price_ranges": price_ranges,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
            "data_points": len(df)
        }
        
        # 4. Save to DynamoDB
        success = await save_to_dynamodb(historical_context)
        
        logger.info("=" * 80)
        if success:
            logger.info("✅ HISTORICAL CONTEXT REFRESH COMPLETED SUCCESSFULLY")
        else:
            logger.error("❌ HISTORICAL CONTEXT REFRESH FAILED")
        logger.info("=" * 80)
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Historical context refresh failed: {e}", exc_info=True)
        return False


def lambda_handler(event, context):
    """AWS Lambda handler for EventBridge scheduled execution"""
    try:
        # Run async refresh
        success = asyncio.run(refresh_historical_context())
        
        return {
            'statusCode': 200 if success else 500,
            'body': json.dumps({
                'status': 'success' if success else 'error',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'function': 'refresh_historical_context'
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }


# For local testing
if __name__ == "__main__":
    print("🧪 Testing Historical Context Refresh...")
    success = asyncio.run(refresh_historical_context())
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
