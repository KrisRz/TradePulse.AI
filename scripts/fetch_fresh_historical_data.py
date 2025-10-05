#!/usr/bin/env python3
"""
Fetch fresh 90-day historical data from Binance for day trading
Pre-calculate price ranges, support/resistance, and pattern success rates
Store in DynamoDB for instant AWS access
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Any
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_90_day_candles_from_binance(symbol: str = "BTCUSDT", interval: str = "1m") -> pd.DataFrame:
    """
    Fetch last 90 days of 1-minute candles from Binance
    Total: 90 days × 1440 minutes = 129,600 candles
    """
    logger.info(f"📥 Fetching 90-day candles for {symbol} ({interval})...")
    
    import aiohttp
    
    # Calculate start time (90 days ago)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=90)
    
    logger.info(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"   End:   {end_time.strftime('%Y-%m-%d %H:%M')}")
    
    # Fetch in chunks (Binance limit: 1000 candles per request)
    all_candles = []
    current_start = int(start_time.timestamp() * 1000)  # ms
    current_end = int(end_time.timestamp() * 1000)
    chunk_size = 1000  # Max per request
    
    base_url = "https://api.binance.com/api/v3/klines"
    
    async with aiohttp.ClientSession() as session:
        while current_start < current_end:
            try:
                params = {
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": current_start,
                    "limit": chunk_size
                }
                
                async with session.get(base_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"   Binance API error: {response.status}")
                        break
                    
                    candles = await response.json()
                    
                    if not candles:
                        break
                    
                    all_candles.extend(candles)
                    
                    # Move to next chunk
                    last_candle_time = candles[-1][0]  # timestamp
                    current_start = last_candle_time + 60000  # +1 minute (ms)
                    
                    logger.info(f"   Fetched {len(candles)} candles (total: {len(all_candles)})")
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"   Error fetching chunk: {e}")
                break
    
    # Convert to DataFrame
    df = pd.DataFrame(all_candles, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    
    # Convert types
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    logger.info(f"✅ Fetched {len(df)} candles from Binance")
    logger.info(f"   Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
    
    return df


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate RSI, MACD, Bollinger Bands for pattern analysis"""
    logger.info("📊 Calculating technical indicators...")
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    bb_std = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
    df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    logger.info("✅ Technical indicators calculated")
    return df


def calculate_price_ranges(df: pd.DataFrame, support: List[float], resistance: List[float]) -> Dict[str, Dict[str, float]]:
    """Calculate price ranges for 7D, 30D, 90D with all required fields"""
    logger.info("📏 Calculating price ranges...")
    
    ranges = {}
    current_price = df['close'].iloc[-1]
    current_time = datetime.now(timezone.utc)
    
    for period_name, days in [("7D", 7), ("30D", 30), ("90D", 90)]:
        period_data = df[df['timestamp'] >= df['timestamp'].max() - pd.Timedelta(days=days)]
        
        high = period_data['high'].max()
        low = period_data['low'].min()
        range_pct = ((high - low) / low * 100) if low > 0 else 0
        position = (current_price - low) / (high - low) if (high - low) > 0 else 0.5
        
        ranges[period_name] = {
            "period": period_name,
            "high": float(high),
            "low": float(low),
            "range_pct": float(range_pct),
            "current_position": float(position),
            "support_levels": [float(s) for s in support[:5]],  # Top 5
            "resistance_levels": [float(r) for r in resistance[:5]],  # Top 5
            "last_updated": int(current_time.timestamp())
        }
        
        logger.info(f"   {period_name}: ${low:,.2f} - ${high:,.2f} (pos: {position:.1%})")
    
    return ranges


def calculate_support_resistance(df: pd.DataFrame, periods: int = 90) -> tuple:
    """Calculate support and resistance levels using swing highs/lows"""
    logger.info("🎯 Calculating support/resistance levels...")
    
    recent_data = df.tail(periods * 1440)  # Last N days
    
    # Find swing highs (resistance)
    swing_highs = recent_data[
        (recent_data['high'] > recent_data['high'].shift(1)) &
        (recent_data['high'] > recent_data['high'].shift(-1))
    ]['high'].tolist()
    
    # Find swing lows (support)
    swing_lows = recent_data[
        (recent_data['low'] < recent_data['low'].shift(1)) &
        (recent_data['low'] < recent_data['low'].shift(-1))
    ]['low'].tolist()
    
    # Cluster levels (within 0.5%)
    def cluster_levels(levels, threshold=0.005):
        if not levels:
            return []
        levels = sorted(levels)
        clusters = [[levels[0]]]
        for level in levels[1:]:
            if (level - clusters[-1][-1]) / clusters[-1][-1] < threshold:
                clusters[-1].append(level)
            else:
                clusters.append([level])
        return [np.mean(cluster) for cluster in clusters]
    
    resistance = cluster_levels(swing_highs)[-5:]  # Top 5
    support = cluster_levels(swing_lows)[:5]  # Bottom 5
    
    logger.info(f"   Resistance: {[f'${r:,.0f}' for r in resistance]}")
    logger.info(f"   Support: {[f'${s:,.0f}' for s in support]}")
    
    return support, resistance


async def calculate_pattern_success_rates(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Calculate success rates for RSI oversold, MACD cross, etc."""
    logger.info("📈 Calculating pattern success rates...")
    
    patterns = {}
    
    # RSI Oversold pattern (RSI < 30)
    rsi_signals = df[df['rsi'] < 30].copy()
    if len(rsi_signals) > 10:
        # Check if price went up in next 24 hours
        successes = 0
        for idx in rsi_signals.index:
            future_idx = min(idx + 1440, len(df) - 1)  # 24h later
            if df['close'].iloc[future_idx] > df['close'].iloc[idx]:
                successes += 1
        
        success_rate = successes / len(rsi_signals)
        patterns['rsi_oversold'] = {
            "success_rate": float(success_rate),
            "total_signals": len(rsi_signals),
            "description": "RSI < 30 oversold bounce"
        }
        logger.info(f"   RSI Oversold: {success_rate:.1%} ({len(rsi_signals)} signals)")
    
    # MACD Golden Cross (MACD crosses above signal)
    macd_cross = df[(df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))].copy()
    if len(macd_cross) > 10:
        successes = 0
        for idx in macd_cross.index:
            future_idx = min(idx + 1440, len(df) - 1)
            if df['close'].iloc[future_idx] > df['close'].iloc[idx]:
                successes += 1
        
        success_rate = successes / len(macd_cross)
        patterns['macd_golden_cross'] = {
            "success_rate": float(success_rate),
            "total_signals": len(macd_cross),
            "description": "MACD crosses above signal"
        }
        logger.info(f"   MACD Golden Cross: {success_rate:.1%} ({len(macd_cross)} signals)")
    
    # Bollinger Bounce (price touches lower band)
    bb_bounce = df[df['bb_position'] < 0.1].copy()
    if len(bb_bounce) > 10:
        successes = 0
        for idx in bb_bounce.index:
            future_idx = min(idx + 720, len(df) - 1)  # 12h later
            if df['close'].iloc[future_idx] > df['close'].iloc[idx]:
                successes += 1
        
        success_rate = successes / len(bb_bounce)
        patterns['bollinger_bounce'] = {
            "success_rate": float(success_rate),
            "total_signals": len(bb_bounce),
            "description": "Price touches lower Bollinger Band"
        }
        logger.info(f"   Bollinger Bounce: {success_rate:.1%} ({len(bb_bounce)} signals)")
    
    return patterns


async def store_in_dynamodb(price_ranges: Dict, support: List, resistance: List, patterns: Dict):
    """Store pre-calculated metrics in DynamoDB"""
    logger.info("💾 Storing metrics in DynamoDB...")
    
    from app.backend.core.database import DynamoDBClient
    
    client = DynamoDBClient(local_development=False)  # AWS DynamoDB
    
    # Helper to convert floats to Decimal
    def convert_floats(obj):
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: convert_floats(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_floats(item) for item in obj]
        return obj
    
    # Single cache item with all metrics (convert floats to Decimal)
    cache_item = {
        "cache_key": "market_context_90d",
        "symbol": "BTCUSDT",
        "period": "90D",  # Add period for correct key schema
        "last_updated": int(datetime.now(timezone.utc).timestamp()),
        "price_ranges": convert_floats(price_ranges),
        "support_levels": [Decimal(str(s)) for s in support],
        "resistance_levels": [Decimal(str(r)) for r in resistance],
        "pattern_success_rates": convert_floats(patterns)
    }
    
    try:
        # Create table if doesn't exist
        table_name = "market_context_cache"
        try:
            client.get_table(table_name)
        except:
            logger.info(f"   Creating table: {table_name}")
            import boto3
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
            dynamodb.create_table(
                TableName=table_name,
                KeySchema=[{'AttributeName': 'cache_key', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'cache_key', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST'
            )
            await asyncio.sleep(5)  # Wait for table creation
        
        # Put item
        client.put_item(table_name, cache_item)
        logger.info("✅ Metrics stored in DynamoDB")
        
    except Exception as e:
        logger.error(f"❌ Failed to store in DynamoDB: {e}")
        # Save to local file as backup
        import json
        backup_file = "/Applications/Projects/TradePulse.AI/data/ml/historical/cache/market_context_cache.json"
        with open(backup_file, 'w') as f:
            json.dump(cache_item, f, indent=2)
        logger.info(f"💾 Backup saved to: {backup_file}")


async def main():
    """Main execution"""
    logger.info("🚀 Fetching fresh 90-day historical data for day trading...")
    
    # 1. Fetch fresh data
    df = await fetch_90_day_candles_from_binance()
    
    # 2. Calculate indicators
    df = calculate_technical_indicators(df)
    
    # 3. Calculate metrics
    support, resistance = calculate_support_resistance(df)
    price_ranges = calculate_price_ranges(df, support, resistance)
    patterns = await calculate_pattern_success_rates(df)
    
    # 4. Store in DynamoDB
    await store_in_dynamodb(price_ranges, support, resistance, patterns)
    
    logger.info("✅ Fresh historical data ready for day trading!")
    logger.info("   Historical context service will now load from DynamoDB")


if __name__ == "__main__":
    asyncio.run(main())

