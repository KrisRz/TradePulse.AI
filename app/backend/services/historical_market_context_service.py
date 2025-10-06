"""
Historical Market Context Service - TradePulse.AI Enterprise
==========================================================

Pre-cached historical analysis service that provides instant market context
for intelligent entry decisions without performance delays.

Features:
- Pre-calculated monthly/weekly/daily price ranges from 3.97M records
- Cached support/resistance levels with historical validation
- Pattern success rates database
- Market regime classification
- Volatility percentile analysis
- Instant lookup for entry engine decisions

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)

class MarketRegime(str, Enum):
    """Market regime classifications"""
    BULL_TREND = "bull_trend"
    BEAR_TREND = "bear_trend"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    CONSOLIDATION = "consolidation"

@dataclass
class PriceRange:
    """Price range data structure"""
    period: str
    high: float
    low: float
    range_pct: float
    current_position: float  # 0.0 = at low, 1.0 = at high
    support_levels: List[float]
    resistance_levels: List[float]
    last_updated: datetime

@dataclass
class PatternSuccessRate:
    """Pattern success rate data"""
    pattern_name: str
    success_rate: float
    total_occurrences: int
    avg_profit: float
    avg_loss: float
    risk_reward_ratio: float
    market_regime: MarketRegime
    price_range_position: str  # "low", "mid", "high"

class HistoricalMarketContextService:
    """
    Pre-cached historical market context for instant entry decisions
    
    Loads 3.97M historical records once and maintains pre-calculated
    market context data for ultra-fast entry analysis.
    """
    
    def __init__(self):
        self.is_initialized = False
        self.is_loading = False
        self.last_updated = None
        
        # Data paths - Fix path resolution
        project_root = Path(__file__).parent.parent.parent.parent  # Go up to project root
        self.data_path = project_root / "data" / "ml" / "historical"
        self.cache_path = self.data_path / "cache"
        
        # Create cache directory if it doesn't exist
        try:
            self.cache_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create cache directory: {e}")
            # Use temp directory as fallback
            import tempfile
            self.cache_path = Path(tempfile.gettempdir()) / "tradepulse_cache"
            self.cache_path.mkdir(exist_ok=True)
        
        # Pre-cached data
        self.price_ranges: Dict[str, PriceRange] = {}
        self.pattern_success_rates: Dict[str, PatternSuccessRate] = {}
        self.support_resistance_levels: Dict[str, List[float]] = {}
        self.market_regime_history: List[Dict[str, Any]] = []
        self.volatility_percentiles: Dict[str, float] = {}
        
        # Performance tracking
        self.total_lookups = 0
        self.cache_hits = 0
        self.last_data_update = None
        
        logger.info("📊 Historical Market Context Service initialized")
    
    async def initialize(self):
        """Initialize service with pre-calculated historical data"""
        if self.is_initialized:
            return
            
        if self.is_loading:
            logger.info("⏳ Service already loading, waiting...")
            while self.is_loading and not self.is_initialized:
                await asyncio.sleep(1)
            return
        
        self.is_loading = True
        logger.info("🚀 Initializing Historical Market Context Service...")
        
        try:
            # DAY TRADING: Try DynamoDB first (90-day fresh data)
            if await self._load_from_dynamodb():
                logger.info("✅ Loaded fresh 90-day data from DynamoDB")
            # Fallback: Check local cache
            elif await self._is_cache_valid():
                logger.info("✅ Loading pre-calculated historical data from cache...")
                await self._load_from_cache()
            # Last resort: Pre-calculate from parquet (if available)
            else:
                logger.info("🔄 Pre-calculating historical data from parquet files...")
                await self._pre_calculate_historical_data()
                await self._save_to_cache()
            
            self.is_initialized = True
            self.is_loading = False
            self.last_updated = datetime.now(timezone.utc)
            
            logger.info("✅ Historical Market Context Service ready for instant lookups")
            
        except Exception as e:
            self.is_loading = False
            logger.error(f"❌ Failed to initialize historical context service: {e}")
            raise
    
    async def _load_from_dynamodb(self) -> bool:
        """Load pre-calculated metrics from DynamoDB (90-day fresh data)"""
        try:
            from app.backend.core.database import DynamoDBClient
            from app.backend.core.config import get_settings
            
            settings = get_settings()
            client = DynamoDBClient(local_development=settings.is_development)
            
            # Get cached metrics
            table_name = "market_context_cache"
            cache_item = client.get_item(table_name, {"symbol": "BTCUSDT", "period": "90D"})
            
            if not cache_item:
                logger.info("   No data in DynamoDB yet")
                return False
            
            # Check freshness (< 72 hours - increased for weekends when data can't refresh)
            last_updated = float(cache_item.get("last_updated", 0))  # Convert Decimal to float
            age_hours = (datetime.now(timezone.utc).timestamp() - last_updated) / 3600
            
            # RELAXED: 72h instead of 24h (weekends + holidays where refresh may fail)
            if age_hours > 72:
                logger.warning(f"   DynamoDB data is {age_hours:.1f} hours old (>72h), refreshing needed")
                return False
            elif age_hours > 24:
                logger.info(f"   ℹ️ Using DynamoDB data ({age_hours:.1f}h old, acceptable for weekends)")
            else:
                logger.info(f"   ✅ Fresh DynamoDB data ({age_hours:.1f}h old)")
            
            # Load price ranges
            for period, data in cache_item.get("price_ranges", {}).items():
                self.price_ranges[period] = PriceRange(
                    period=period,
                    high=float(data["high"]),
                    low=float(data["low"]),
                    range_pct=float(data.get("range_pct", 0.0)),
                    current_position=float(data.get("current_position", 0.5)),
                    support_levels=[float(s) for s in data.get("support_levels", [])],
                    resistance_levels=[float(r) for r in data.get("resistance_levels", [])],
                    last_updated=datetime.fromtimestamp(int(data.get("last_updated", 0)), tz=timezone.utc)
                )
            
            # Load support/resistance
            self.support_resistance_levels["30D"] = {
                "support": [float(s) for s in cache_item.get("support_levels", [])],
                "resistance": [float(r) for r in cache_item.get("resistance_levels", [])]
            }
            
            logger.info(f"✅ Loaded 90-day historical context from DynamoDB ({age_hours:.1f}h old)")
            
            # Load pattern success rates
            for pattern_key, data in cache_item.get("pattern_success_rates", {}).items():
                self.pattern_success_rates[pattern_key] = PatternSuccessRate(
                    pattern_name=data.get("description", pattern_key),
                    success_rate=float(data.get("success_rate", 0.5)),
                    total_occurrences=int(data.get("total_signals", 0)),
                    avg_profit=0.0,  # Not calculated in new format
                    avg_loss=0.0,
                    risk_reward_ratio=0.0,
                    market_regime=MarketRegime.SIDEWAYS,
                    price_range_position="mid"
                )
            
            logger.info(f"   Loaded {len(self.price_ranges)} price ranges")
            logger.info(f"   Loaded {len(self.pattern_success_rates)} pattern success rates")
            logger.info(f"   Data age: {age_hours:.1f} hours")
            
            return True
            
        except Exception as e:
            logger.warning(f"   Failed to load from DynamoDB: {e}")
            return False
    
    async def _is_cache_valid(self) -> bool:
        """Check if cached data exists and is up to date"""
        cache_file = self.cache_path / "market_context_cache.pkl"
        metadata_file = self.cache_path / "cache_metadata.json"
        
        if not cache_file.exists() or not metadata_file.exists():
            return False
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # DAY TRADING: Cache is valid for only 3 hours (not 24 hours)
            # This ensures fresh data for active trading decisions
            cache_time = datetime.fromisoformat(metadata.get("created_at", "2020-01-01"))
            age_hours = (datetime.now(timezone.utc) - cache_time).total_seconds() / 3600
            
            # FORCE INVALIDATION: If cache was created with old logic, invalidate it
            cache_version = metadata.get("version", "0.0.0")
            current_version = "3.0.0"  # UPDATED: Multi-method S/R detection (BB + swing + historical)
            
            if cache_version != current_version:
                logger.info(f"🔄 Cache version mismatch: {cache_version} vs {current_version}, invalidating")
                return False
            
            if age_hours > 3:  # 3 hours max for day trading
                logger.info(f"🔄 Cache is {age_hours:.1f} hours old, needs refresh (max 3h for day trading)")
                return False
            
            logger.info(f"✅ Cache is {age_hours:.1f} hours old, still valid for day trading")
            return True
            
        except Exception as e:
            logger.warning(f"Cache validation failed: {e}")
            return False
    
    async def _pre_calculate_historical_data(self):
        """Pre-calculate all historical market context data from LIVE DynamoDB"""
        logger.info("📈 Loading LIVE historical data from DynamoDB Local...")
        
        # CRITICAL FIX: Use LIVE data from DynamoDB Local instead of stale parquet files
        # The parquet files are 6 weeks old (July 26, 2025) - we need current data!
        
        self._data_source = "unknown"
        try:
            # Try to get live data from DynamoDB Local first
            df = await self._load_live_data_from_dynamodb()
            self._data_source = "DynamoDB_Local"
            logger.info(f"📊 Loaded {len(df):,} LIVE records from DynamoDB Local")
            
        except Exception as db_error:
            logger.warning(f"⚠️ DynamoDB Local not available: {db_error}")
            logger.info("🔄 Falling back to parquet file (may be stale)")
            self._data_source = "BTCUSDT_1m_complete.parquet"
            
            # Fallback to parquet file
            data_file = self.data_path / "BTCUSDT_1m_2025_complete.parquet"
            if not data_file.exists():
                data_file = self.data_path / "processed" / "BTCUSDT_1m_complete.parquet"
            
            if not data_file.exists():
                raise FileNotFoundError("No data source available - neither DynamoDB Local nor parquet files")
            
            df = pd.read_parquet(data_file)
            logger.info(f"📊 Loaded {len(df):,} records from parquet file (STALE DATA WARNING)")
            
            # Check data freshness
            if hasattr(df.index, 'max'):
                latest_data = df.index.max()
                data_age = (pd.Timestamp.now() - latest_data).days
                if data_age > 7:
                    logger.warning(f"⚠️ DATA FRESHNESS WARNING: Latest data is {data_age} days old!")
                    logger.warning(f"📅 Latest data: {latest_data}, Current: {pd.Timestamp.now()}")
                    logger.warning("🔧 Consider starting DynamoDB Local for fresh data")
        
        # DAY TRADING OPTIMIZATION: Use only RECENT data (last 3 days max)
        # For day trading, only recent patterns are relevant - old data creates bias
        # Current issue: $111k looks "cheap" vs $118k recent average, blocking entries
        
        # Strategy: Use only last 3 days of data for day trading decisions
        cutoff_hours = 72  # 3 days = 72 hours
        cutoff_minutes = cutoff_hours * 60  # Convert to minutes for 1m data
        
        pre_filter_count = len(df)
        
        # Keep only last 3 days of data
        df = df.tail(cutoff_minutes)
        
        logger.info(f"🎯 DAY TRADING FILTER: {pre_filter_count:,} → {len(df):,} records (last {cutoff_hours}h only)")
        logger.info(f"📊 Date range after filter: {df.index.min()} to {df.index.max()}")
        
        # Verify we have recent price context
        if 'close' in df.columns and len(df) > 0:
            recent_price_range = f"${df['close'].min():,.0f} - ${df['close'].max():,.0f}"
            recent_price_mean = df['close'].mean()
            logger.info(f"🚀 DAY TRADING CONTEXT: Price range {recent_price_range}, mean ${recent_price_mean:,.0f}")
        
        logger.info(f"✅ OPTIMIZED FOR DAY TRADING: Using only {len(df):,} records from last {cutoff_hours} hours")
        
        # CRITICAL FIX: Add technical indicators before pattern calculation
        logger.info("🔧 Adding technical indicators to historical data...")
        df = await self._add_technical_indicators_to_dataframe(df)
        logger.info("✅ Technical indicators added successfully")
        
        # Pre-calculate price ranges
        await self._calculate_price_ranges(df)
        
        # Pre-calculate support/resistance levels
        await self._calculate_support_resistance_levels(df)
        
        # Pre-calculate pattern success rates
        await self._calculate_pattern_success_rates(df)
        
        # Pre-calculate market regime history
        await self._calculate_market_regime_history(df)
        
        # Pre-calculate volatility percentiles
        await self._calculate_volatility_percentiles(df)
        
        logger.info("✅ Historical data pre-calculation completed")
    
    async def _add_technical_indicators_to_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators (RSI, MACD, Bollinger Bands) to historical data"""
        try:
            import numpy as np
            
            if len(df) < 50:  # Need minimum data for indicators
                logger.warning("Insufficient data for technical indicators")
                return df
            
            # Sort by timestamp to ensure proper calculation
            df = df.sort_index()
            
            # 1. RSI Calculation (14-period)
            logger.info("   Calculating RSI...")
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # 2. MACD Calculation (12, 26, 9)
            logger.info("   Calculating MACD...")
            ema_12 = df['close'].ewm(span=12).mean()
            ema_26 = df['close'].ewm(span=26).mean()
            df['macd'] = ema_12 - ema_26
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # 3. Bollinger Bands (20-period, 2 std)
            logger.info("   Calculating Bollinger Bands...")
            bb_middle = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = bb_middle + (bb_std * 2)
            df['bb_lower'] = bb_middle - (bb_std * 2)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # 4. Volume indicators
            logger.info("   Calculating Volume indicators...")
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Fill NaN values with neutral defaults
            df['rsi'] = df['rsi'].fillna(50.0)
            df['macd'] = df['macd'].fillna(0.0)
            df['macd_signal'] = df['macd_signal'].fillna(0.0)
            df['bb_position'] = df['bb_position'].fillna(0.5)
            df['volume_ratio'] = df['volume_ratio'].fillna(1.0)
            
            indicators_added = ['rsi', 'macd', 'macd_signal', 'bb_position', 'volume_ratio']
            logger.info(f"✅ Added technical indicators: {', '.join(indicators_added)}")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to add technical indicators: {e}")
            # Return original dataframe if indicators fail
            return df
    
    async def _load_live_data_from_dynamodb(self) -> pd.DataFrame:
        """Load live data from DynamoDB Local for fresh historical context"""
        try:
            # Import DynamoDB client directly
            from app.backend.core.database import DynamoDBClient
            
            # Get DynamoDB client
            db_client = DynamoDBClient()
            
            # Get last 3 days of 1-minute candles (4320 records)
            hours_back = 72  # 3 days
            minutes_back = hours_back * 60
            
            # Query recent candles from DynamoDB Local
            logger.info(f"📡 Querying last {hours_back}h ({minutes_back} minutes) from DynamoDB Local...")
            
            # Get candles from live_candles table
            candles = db_client.scan_table('live_candles')
            
            if not candles or len(candles) < 100:
                raise ValueError(f"Insufficient live data: {len(candles) if candles else 0} candles")
            
            # Convert to DataFrame
            df_data = []
            for candle in candles:
                # Convert timestamp from milliseconds to seconds if needed
                timestamp = candle['timestamp']
                if isinstance(timestamp, (int, str)) and len(str(timestamp)) == 13:
                    # Timestamp is in milliseconds, convert to seconds
                    timestamp = int(timestamp) / 1000
                
                df_data.append({
                    'timestamp': pd.to_datetime(timestamp, unit='s'),
                    'open': float(candle['open']),
                    'high': float(candle['high']),
                    'low': float(candle['low']),
                    'close': float(candle['close']),
                    'volume': float(candle['volume'])
                })
            
            df = pd.DataFrame(df_data)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            logger.info(f"✅ LIVE DATA: {len(df)} candles from {df.index.min()} to {df.index.max()}")
            logger.info(f"📊 LIVE PRICE RANGE: ${df['close'].min():,.0f} - ${df['close'].max():,.0f}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load live data from DynamoDB: {e}")
            raise
    
    async def _calculate_price_ranges(self, df: pd.DataFrame):
        """Calculate price ranges for different time periods"""
        logger.info("📊 Pre-calculating price ranges...")
        
        # Ensure datetime index
        if 'open_time' in df.columns:
            df['datetime'] = pd.to_datetime(df['open_time'])
            df.set_index('datetime', inplace=True)
        
        current_price = float(df['close'].iloc[-1])
        
        # Calculate ranges for RELEVANT periods (recent data only)
        periods = {
            "1D": 1,
            "3D": 3,
            "7D": 7, 
            "14D": 14,
            "30D": 30,
            "60D": 60  # Max 60 days - beyond this, price context becomes irrelevant at $110k+ levels
        }
        
        for period_name, days in periods.items():
            try:
                # Get data for the period
                end_date = df.index[-1]
                start_date = end_date - timedelta(days=days)
                period_data = df[df.index >= start_date]
                
                if len(period_data) > 0:
                    high = float(period_data['high'].max())
                    low = float(period_data['low'].min())
                    range_pct = ((high - low) / low) * 100
                    current_position = (current_price - low) / (high - low) if high != low else 0.5
                    
                    # Calculate support and resistance from the period
                    support_levels = self._find_support_levels(period_data)
                    resistance_levels = self._find_resistance_levels(period_data)
                    
                    self.price_ranges[period_name] = PriceRange(
                        period=period_name,
                        high=high,
                        low=low,
                        range_pct=range_pct,
                        current_position=current_position,
                        support_levels=support_levels,
                        resistance_levels=resistance_levels,
                        last_updated=datetime.now(timezone.utc)
                    )
                    
                    logger.info(f"   {period_name}: ${low:,.0f} - ${high:,.0f} (current: {current_position:.1%})")
                    
                    # DIAGNOSTIC: Log data source details for debugging inconsistencies
                    logger.info(f"   {period_name} DATA SOURCE: symbol={getattr(self, 'symbol', 'unknown')}, bars_count={len(period_data)}, date_range={start_date.date()} to {end_date.date()}")
                    
                    # CONSISTENCY CHECK: Compare with current RSI/BB if available
                    if hasattr(self, '_last_rsi') and hasattr(self, '_last_bb_pos'):
                        if current_position > 0.9 and getattr(self, '_last_rsi', 50) < 10:
                            logger.warning(f"⚠️ INCONSISTENCY: {period_name} position {current_position:.1%} vs RSI {getattr(self, '_last_rsi', 50):.1f}")
                        if current_position > 0.9 and getattr(self, '_last_bb_pos', 0.5) < 0.1:
                            logger.warning(f"⚠️ INCONSISTENCY: {period_name} position {current_position:.1%} vs BB_pos {getattr(self, '_last_bb_pos', 0.5):.3f}")
                    
            except Exception as e:
                logger.warning(f"Failed to calculate {period_name} range: {e}")
    
    def _find_support_levels(self, df: pd.DataFrame) -> List[float]:
        """Find significant support levels - DAY TRADING OPTIMIZED"""
        logger.info(f"📊 S/R DEBUG: Finding support levels from {len(df)} candles")
        support_candidates = []
        
        # METHOD 1: STRONG LEVELS (historical touch points - strict)
        lows = df['low'].rolling(window=20).min()
        method1_count = 0
        for i in range(20, len(lows) - 20):
            if lows.iloc[i] == lows.iloc[i-10:i+10].min():
                price_level = float(lows.iloc[i])
                
                # Count touches (relaxed: 1+ instead of 2+)
                touches = 0
                for j in range(i+1, min(i+50, len(df))):  # Reduced from 100 to 50
                    if abs(df['low'].iloc[j] - price_level) / price_level < 0.03:  # 3% tolerance (day trading)
                        touches += 1
                
                if touches >= 1:  # At least 1 touch (relaxed from 2)
                    support_candidates.append(price_level)
                    method1_count += 1
        
        logger.info(f"📊 S/R DEBUG: Method 1 (historical) found {method1_count} support levels")
        
        # METHOD 2: RECENT SWING LOWS (last 48h - micro levels for day trading)
        recent_window = min(len(df), 2880)  # Last 48h (2880 = 48*60 for 1m data)
        method2_count = 0
        if recent_window >= 20:  # Need minimum data
            recent_data = df.tail(recent_window)
            swing_lows = []
            for i in range(5, len(recent_data) - 5):
                low = recent_data['low'].iloc[i]
                # Is this a local minimum? (5-candle window)
                if low == recent_data['low'].iloc[i-5:i+5].min():
                    swing_lows.append(float(low))
                    method2_count += 1
            logger.info(f"📊 S/R DEBUG: Method 2 (swing lows) found {method2_count} levels from {recent_window} candles")
        else:
            swing_lows = []
            logger.warning(f"⚠️ S/R DEBUG: Method 2 skipped - insufficient data ({recent_window} < 20 candles)")
        
        # Add recent swing lows (deduplicate if too close)
        method2_added = 0
        for swing_low in swing_lows:
            # Only add if not too close to existing candidates (0.5% apart)
            if not any(abs(swing_low - c) / c < 0.005 for c in support_candidates):
                support_candidates.append(swing_low)
                method2_added += 1
        logger.info(f"📊 S/R DEBUG: Method 2 added {method2_added} unique levels (after dedup)")
        
        # METHOD 3: BOLLINGER BAND LOWER (statistical support)
        method3_added = 0
        if 'bb_lower' in df.columns and len(df) > 0:
            bb_lower = float(df['bb_lower'].iloc[-1])
            if bb_lower > 0:
                support_candidates.append(bb_lower)
                method3_added = 1
        logger.info(f"📊 S/R DEBUG: Method 3 (Bollinger) added {method3_added} levels")
        
        # Deduplicate, sort, return TOP 15 (was 5)
        unique_supports = sorted(list(set(support_candidates)))
        final_supports = unique_supports[-15:] if len(unique_supports) > 15 else unique_supports
        logger.info(f"📊 S/R DEBUG: TOTAL SUPPORT LEVELS: {len(final_supports)} (from {len(support_candidates)} candidates)")
        return final_supports
    
    def _find_resistance_levels(self, df: pd.DataFrame) -> List[float]:
        """Find significant resistance levels - DAY TRADING OPTIMIZED"""
        logger.info(f"📊 S/R DEBUG: Finding resistance levels from {len(df)} candles")
        resistance_candidates = []
        
        # METHOD 1: STRONG LEVELS (historical rejection points - strict)
        highs = df['high'].rolling(window=20).max()
        method1_count = 0
        for i in range(20, len(highs) - 20):
            if highs.iloc[i] == highs.iloc[i-10:i+10].max():
                price_level = float(highs.iloc[i])
                
                # Count rejections (relaxed: 1+ instead of 2+)
                touches = 0
                for j in range(i+1, min(i+50, len(df))):  # Reduced from 100 to 50
                    if abs(df['high'].iloc[j] - price_level) / price_level < 0.03:  # 3% tolerance (day trading)
                        touches += 1
                
                if touches >= 1:  # At least 1 rejection (relaxed from 2)
                    resistance_candidates.append(price_level)
                    method1_count += 1
        
        logger.info(f"📊 S/R DEBUG: Method 1 (historical) found {method1_count} resistance levels")
        
        # METHOD 2: RECENT SWING HIGHS (last 48h - micro levels for day trading)
        recent_window = min(len(df), 2880)  # Last 48h (2880 = 48*60 for 1m data)
        method2_count = 0
        if recent_window >= 20:  # Need minimum data
            recent_data = df.tail(recent_window)
            swing_highs = []
            for i in range(5, len(recent_data) - 5):
                high = recent_data['high'].iloc[i]
                # Is this a local maximum? (5-candle window)
                if high == recent_data['high'].iloc[i-5:i+5].max():
                    swing_highs.append(float(high))
                    method2_count += 1
            logger.info(f"📊 S/R DEBUG: Method 2 (swing highs) found {method2_count} levels from {recent_window} candles")
        else:
            swing_highs = []
            logger.warning(f"⚠️ S/R DEBUG: Method 2 skipped - insufficient data ({recent_window} < 20 candles)")
        
        # Add recent swing highs (deduplicate if too close)
        method2_added = 0
        for swing_high in swing_highs:
            # Only add if not too close to existing candidates (0.5% apart)
            if not any(abs(swing_high - c) / c < 0.005 for c in resistance_candidates):
                resistance_candidates.append(swing_high)
                method2_added += 1
        logger.info(f"📊 S/R DEBUG: Method 2 added {method2_added} unique levels (after dedup)")
        
        # METHOD 3: BOLLINGER BAND UPPER (statistical resistance)
        method3_added = 0
        if 'bb_upper' in df.columns and len(df) > 0:
            bb_upper = float(df['bb_upper'].iloc[-1])
            if bb_upper > 0:
                resistance_candidates.append(bb_upper)
                method3_added = 1
        logger.info(f"📊 S/R DEBUG: Method 3 (Bollinger) added {method3_added} levels")
        
        # Deduplicate, sort, return TOP 15 (was 5)
        unique_resistances = sorted(list(set(resistance_candidates)))
        final_resistances = unique_resistances[-15:] if len(unique_resistances) > 15 else unique_resistances
        logger.info(f"📊 S/R DEBUG: TOTAL RESISTANCE LEVELS: {len(final_resistances)} (from {len(resistance_candidates)} candidates)")
        return final_resistances
    
    async def _calculate_support_resistance_levels(self, df: pd.DataFrame):
        """Calculate comprehensive support and resistance levels"""
        print(f"📊 S/R CALCULATION: Starting with {len(df)} total candles...")
        logger.info("📊 Pre-calculating support/resistance levels...")
        
        # Calculate for different timeframes
        timeframes = ["1D", "7D", "30D"]
        
        for tf in timeframes:
            days = {"1D": 1, "7D": 7, "30D": 30}[tf]
            end_date = df.index[-1]
            start_date = end_date - timedelta(days=days)
            period_data = df[df.index >= start_date]
            
            print(f"📊 S/R CALCULATION: {tf} timeframe - {len(period_data)} candles from {start_date} to {end_date}")
            logger.info(f"📊 S/R CALCULATION: {tf} timeframe - {len(period_data)} candles")
            
            if len(period_data) > 0:
                print(f"📊 S/R CALCULATION: Calling _find_support_levels for {tf}...")
                support_levels = self._find_support_levels(period_data)
                print(f"📊 S/R CALCULATION: Got {len(support_levels)} support levels for {tf}")
                
                print(f"📊 S/R CALCULATION: Calling _find_resistance_levels for {tf}...")
                resistance_levels = self._find_resistance_levels(period_data)
                print(f"📊 S/R CALCULATION: Got {len(resistance_levels)} resistance levels for {tf}")
                
                self.support_resistance_levels[f"support_{tf}"] = support_levels
                self.support_resistance_levels[f"resistance_{tf}"] = resistance_levels
                
                print(f"✅ S/R CALCULATION: {tf} COMPLETE - {len(support_levels)} support, {len(resistance_levels)} resistance")
                logger.info(f"   {tf}: {len(support_levels)} support, {len(resistance_levels)} resistance levels")
            else:
                print(f"⚠️ S/R CALCULATION: {tf} SKIPPED - no data in period!")
                logger.warning(f"⚠️ S/R CALCULATION: {tf} skipped - no data in period")
    
    async def _calculate_pattern_success_rates(self, df: pd.DataFrame):
        """Pre-calculate pattern success rates for instant lookup"""
        logger.info("📊 Pre-calculating pattern success rates...")
        
        # Calculate RSI pattern success rates
        await self._calculate_rsi_pattern_success(df)
        
        # Calculate MACD pattern success rates
        await self._calculate_macd_pattern_success(df)
        
        # Calculate Bollinger Band pattern success rates
        await self._calculate_bollinger_pattern_success(df)
        
        # Calculate volume breakout success rates
        await self._calculate_volume_pattern_success(df)
        
        logger.info(f"✅ Pre-calculated {len(self.pattern_success_rates)} pattern success rates")
    
    async def _calculate_rsi_pattern_success(self, df: pd.DataFrame):
        """Calculate RSI pattern success rates by price range position"""
        if 'rsi' not in df.columns:
            return
        
        # Define RSI ranges
        rsi_ranges = {
            "oversold": (0, 30),
            "oversold_moderate": (30, 40),
            "neutral": (40, 60),
            "overbought_moderate": (60, 70),
            "overbought": (70, 100)
        }
        
        for range_name, (rsi_low, rsi_high) in rsi_ranges.items():
            # Find all instances where RSI was in this range
            rsi_signals = df[(df['rsi'] >= rsi_low) & (df['rsi'] <= rsi_high)].copy()
            
            if len(rsi_signals) < 10:  # Need minimum sample size
                continue
            
            # Calculate success rate for BUY signals in this RSI range
            successes = 0
            total_signals = 0
            profits = []
            losses = []
            
            for i in range(len(rsi_signals) - 10):
                entry_price = rsi_signals['close'].iloc[i]
                
                # Check outcome in next 10 periods (10 minutes for 1m data)
                future_prices = rsi_signals['close'].iloc[i+1:i+11]
                if len(future_prices) > 0:
                    max_profit = (future_prices.max() - entry_price) / entry_price
                    max_loss = (entry_price - future_prices.min()) / entry_price
                    
                    total_signals += 1
                    
                    # Define success for oversold (BUY) vs overbought (SELL)
                    if "oversold" in range_name:
                        # For oversold, success = price goes up
                        if max_profit > 0.01:  # 1% profit
                            successes += 1
                            profits.append(max_profit)
                        else:
                            losses.append(max_loss)
                    else:
                        # For overbought, success = price goes down
                        if max_loss > 0.01:  # 1% drop
                            successes += 1
                            profits.append(max_loss)
                        else:
                            losses.append(max_profit)
            
            if total_signals > 0:
                success_rate = successes / total_signals
                avg_profit = np.mean(profits) if profits else 0.0
                avg_loss = np.mean(losses) if losses else 0.0
                risk_reward = avg_profit / max(avg_loss, 0.001)
                
                # Map range names to expected pattern names
                pattern_name_map = {
                    "oversold": "rsi_oversold",
                    "oversold_moderate": "rsi_oversold_moderate", 
                    "neutral": "rsi_neutral",
                    "overbought_moderate": "rsi_overbought_moderate",
                    "overbought": "rsi_overbought"
                }
                pattern_key = pattern_name_map.get(range_name, f"rsi_{range_name}")
                
                self.pattern_success_rates[pattern_key] = PatternSuccessRate(
                    pattern_name=f"RSI {range_name}",
                    success_rate=success_rate,
                    total_occurrences=total_signals,
                    avg_profit=avg_profit,
                    avg_loss=avg_loss,
                    risk_reward_ratio=risk_reward,
                    market_regime=MarketRegime.SIDEWAYS,  # Default
                    price_range_position="mid"  # Default
                )
                
                logger.info(f"   RSI {range_name}: {success_rate:.1%} success ({total_signals} samples)")
    
    async def _calculate_macd_pattern_success(self, df: pd.DataFrame):
        """Calculate MACD crossover success rates"""
        if 'macd' not in df.columns or 'macd_signal' not in df.columns:
            return
        
        # Find MACD crossovers
        df['macd_diff'] = df['macd'] - df['macd_signal']
        df['macd_cross_bull'] = (df['macd_diff'] > 0) & (df['macd_diff'].shift(1) <= 0)
        df['macd_cross_bear'] = (df['macd_diff'] < 0) & (df['macd_diff'].shift(1) >= 0)
        
        # Calculate success rates for each crossover type
        for cross_type, signal_col in [("bullish", "macd_cross_bull"), ("bearish", "macd_cross_bear")]:
            crossovers = df[df[signal_col]].copy()
            
            if len(crossovers) < 10:
                continue
            
            successes = 0
            total_signals = len(crossovers)
            profits = []
            losses = []
            
            for idx in crossovers.index:
                try:
                    entry_price = df.loc[idx, 'close']
                    
                    # Check outcome in next 20 periods (20 minutes)
                    future_idx = df.index[df.index > idx][:20]
                    if len(future_idx) > 0:
                        future_prices = df.loc[future_idx, 'close']
                        max_profit = (future_prices.max() - entry_price) / entry_price
                        max_loss = (entry_price - future_prices.min()) / entry_price
                        
                        if cross_type == "bullish":
                            if max_profit > 0.015:  # 1.5% profit for bullish
                                successes += 1
                                profits.append(max_profit)
                            else:
                                losses.append(max_loss)
                        else:
                            if max_loss > 0.015:  # 1.5% drop for bearish
                                successes += 1
                                profits.append(max_loss)
                            else:
                                losses.append(max_profit)
                                
                except Exception:
                    continue
            
            if total_signals > 0:
                success_rate = successes / total_signals
                avg_profit = np.mean(profits) if profits else 0.0
                avg_loss = np.mean(losses) if losses else 0.0
                
                # Map cross types to expected pattern names  
                pattern_name_map = {
                    "bullish": "macd_bullish",
                    "bearish": "macd_bearish"
                }
                pattern_key = pattern_name_map.get(cross_type, f"macd_{cross_type}")
                
                self.pattern_success_rates[pattern_key] = PatternSuccessRate(
                    pattern_name=f"MACD {cross_type} crossover",
                    success_rate=success_rate,
                    total_occurrences=total_signals,
                    avg_profit=avg_profit,
                    avg_loss=avg_loss,
                    risk_reward_ratio=avg_profit / max(avg_loss, 0.001),
                    market_regime=MarketRegime.SIDEWAYS,
                    price_range_position="mid"
                )
                
                logger.info(f"   MACD {cross_type}: {success_rate:.1%} success ({total_signals} samples)")
    
    async def _calculate_bollinger_pattern_success(self, df: pd.DataFrame):
        """Calculate Bollinger Band pattern success rates"""
        if 'bb_upper' not in df.columns or 'bb_lower' not in df.columns:
            return
        
        # Calculate Bollinger Band position
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Find touches at bands
        df['bb_lower_touch'] = df['bb_position'] <= 0.1  # Near lower band
        df['bb_upper_touch'] = df['bb_position'] >= 0.9  # Near upper band
        
        # Calculate success rates for band touches
        for touch_type, signal_col in [("support", "bb_lower_touch"), ("resistance", "bb_upper_touch")]:
            touches = df[df[signal_col]].copy()
            
            if len(touches) < 10:
                continue
            
            successes = 0
            total_signals = len(touches)
            profits = []
            losses = []
            
            for idx in touches.index:
                try:
                    entry_price = df.loc[idx, 'close']
                    
                    # Check outcome in next 15 periods
                    future_idx = df.index[df.index > idx][:15]
                    if len(future_idx) > 0:
                        future_prices = df.loc[future_idx, 'close']
                        max_profit = (future_prices.max() - entry_price) / entry_price
                        max_loss = (entry_price - future_prices.min()) / entry_price
                        
                        if touch_type == "support":
                            # Support touch should bounce up
                            if max_profit > 0.01:  # 1% bounce
                                successes += 1
                                profits.append(max_profit)
                            else:
                                losses.append(max_loss)
                        else:
                            # Resistance touch should reject down
                            if max_loss > 0.01:  # 1% rejection
                                successes += 1
                                profits.append(max_loss)
                            else:
                                losses.append(max_profit)
                                
                except Exception:
                    continue
            
            if total_signals > 0:
                success_rate = successes / total_signals
                avg_profit = np.mean(profits) if profits else 0.0
                avg_loss = np.mean(losses) if losses else 0.0
                
                # Map touch types to expected pattern names
                pattern_name_map = {
                    "support": "bollinger_support", 
                    "resistance": "bollinger_resistance"
                }
                pattern_key = pattern_name_map.get(touch_type, f"bollinger_{touch_type}")
                
                self.pattern_success_rates[pattern_key] = PatternSuccessRate(
                    pattern_name=f"Bollinger {touch_type}",
                    success_rate=success_rate,
                    total_occurrences=total_signals,
                    avg_profit=avg_profit,
                    avg_loss=avg_loss,
                    risk_reward_ratio=avg_profit / max(avg_loss, 0.001),
                    market_regime=MarketRegime.SIDEWAYS,
                    price_range_position="mid"
                )
                
                logger.info(f"   Bollinger {touch_type}: {success_rate:.1%} success ({total_signals} samples)")
    
    async def _calculate_volume_pattern_success(self, df: pd.DataFrame):
        """Calculate volume breakout success rates"""
        if 'volume_ratio' not in df.columns:
            return
        
        # Find high volume periods
        high_volume = df[df['volume_ratio'] > 1.5].copy()
        
        if len(high_volume) < 10:
            return
        
        successes = 0
        total_signals = len(high_volume)
        profits = []
        losses = []
        
        for idx in high_volume.index:
            try:
                entry_price = df.loc[idx, 'close']
                
                # Check if volume led to significant price movement
                future_idx = df.index[df.index > idx][:10]
                if len(future_idx) > 0:
                    future_prices = df.loc[future_idx, 'close']
                    max_profit = (future_prices.max() - entry_price) / entry_price
                    max_loss = (entry_price - future_prices.min()) / entry_price
                    
                    # Success = any significant movement (up or down)
                    if max(max_profit, max_loss) > 0.015:  # 1.5% movement
                        successes += 1
                        profits.append(max(max_profit, max_loss))
                    else:
                        losses.append(min(max_profit, max_loss))
                        
            except Exception:
                continue
        
        if total_signals > 0:
            success_rate = successes / total_signals
            avg_profit = np.mean(profits) if profits else 0.0
            avg_loss = np.mean(losses) if losses else 0.0
            
            self.pattern_success_rates["volume_breakout"] = PatternSuccessRate(
                pattern_name="Volume breakout",
                success_rate=success_rate,
                total_occurrences=total_signals,
                avg_profit=avg_profit,
                avg_loss=avg_loss,
                risk_reward_ratio=avg_profit / max(avg_loss, 0.001),
                market_regime=MarketRegime.BREAKOUT,
                price_range_position="mid"
            )
            
            logger.info(f"   Volume breakout: {success_rate:.1%} success ({total_signals} samples)")
    
    async def _calculate_market_regime_history(self, df: pd.DataFrame):
        """Calculate market regime classification history"""
        logger.info("📊 Pre-calculating market regime history...")
        
        # Calculate trend strength using EMAs
        if 'ema_12' in df.columns and 'ema_26' in df.columns:
            df['trend_strength'] = (df['ema_12'] - df['ema_26']) / df['ema_26']
            
            # Classify regimes
            regimes = []
            for i in range(100, len(df)):  # Skip first 100 for indicators
                row = df.iloc[i]
                
                trend = row['trend_strength']
                volatility = row.get('volatility_20', 0.02)
                volume_ratio = row.get('volume_ratio', 1.0)
                
                # Classify regime
                if abs(trend) > 0.05 and volatility < 0.03:
                    regime = MarketRegime.BULL_TREND if trend > 0 else MarketRegime.BEAR_TREND
                elif volatility > 0.08:
                    regime = MarketRegime.HIGH_VOLATILITY
                elif volatility < 0.015:
                    regime = MarketRegime.LOW_VOLATILITY
                elif volume_ratio > 2.0:
                    regime = MarketRegime.BREAKOUT
                else:
                    regime = MarketRegime.SIDEWAYS
                
                regimes.append({
                    "timestamp": row.name.isoformat() if hasattr(row.name, 'isoformat') else str(row.name),
                    "regime": regime.value,
                    "trend_strength": trend,
                    "volatility": volatility,
                    "volume_ratio": volume_ratio
                })
            
            # Keep last 1000 regime classifications for analysis
            self.market_regime_history = regimes[-1000:]
            logger.info(f"✅ Classified {len(regimes)} market regime periods")
    
    async def _calculate_volatility_percentiles(self, df: pd.DataFrame):
        """Calculate volatility percentiles for current market assessment"""
        logger.info("📊 Pre-calculating volatility percentiles...")
        
        if 'volatility_20' not in df.columns:
            return
        
        volatility_data = df['volatility_20'].dropna()
        
        # Calculate percentiles
        percentiles = [10, 25, 50, 75, 90, 95, 99]
        for p in percentiles:
            self.volatility_percentiles[f"p{p}"] = float(np.percentile(volatility_data, p))
        
        logger.info(f"✅ Volatility percentiles calculated (median: {self.volatility_percentiles.get('p50', 0):.3f})")
    
    async def _save_to_cache(self):
        """Save pre-calculated data to cache for fast loading"""
        logger.info("💾 Saving pre-calculated data to cache...")
        
        cache_data = {
            "price_ranges": {k: {
                "period": v.period,
                "high": v.high,
                "low": v.low,
                "range_pct": v.range_pct,
                "current_position": v.current_position,
                "support_levels": v.support_levels,
                "resistance_levels": v.resistance_levels,
                "last_updated": v.last_updated.isoformat()
            } for k, v in self.price_ranges.items()},
            
            "pattern_success_rates": {k: {
                "pattern_name": v.pattern_name,
                "success_rate": v.success_rate,
                "total_occurrences": v.total_occurrences,
                "avg_profit": v.avg_profit,
                "avg_loss": v.avg_loss,
                "risk_reward_ratio": v.risk_reward_ratio,
                "market_regime": v.market_regime.value,
                "price_range_position": v.price_range_position
            } for k, v in self.pattern_success_rates.items()},
            
            "support_resistance_levels": self.support_resistance_levels,
            "market_regime_history": self.market_regime_history,
            "volatility_percentiles": self.volatility_percentiles
        }
        
        # Save to pickle for fast loading
        cache_file = self.cache_path / "market_context_cache.pkl"
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)
        
        # Save metadata
        metadata = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "records_processed": len(self.price_ranges),
            "patterns_calculated": len(self.pattern_success_rates),
            "data_source": getattr(self, '_data_source', "unknown"),
            "version": "3.0.0",  # UPDATED: Multi-method S/R (BB + swing + historical)
            "optimization": "day_trading_multi_method_sr",
            "cutoff_hours": 72,
            "sr_methods": "historical+swing+bollinger"
        }
        
        metadata_file = self.cache_path / "cache_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("✅ Historical data cached for instant access")
    
    async def _load_from_cache(self):
        """Load pre-calculated data from cache"""
        cache_file = self.cache_path / "market_context_cache.pkl"
        
        with open(cache_file, 'rb') as f:
            cache_data = pickle.load(f)
        
        # Restore price ranges
        for k, v in cache_data["price_ranges"].items():
            self.price_ranges[k] = PriceRange(
                period=v["period"],
                high=v["high"],
                low=v["low"],
                range_pct=v["range_pct"],
                current_position=v["current_position"],
                support_levels=v["support_levels"],
                resistance_levels=v["resistance_levels"],
                last_updated=datetime.fromisoformat(v["last_updated"])
            )
        
        # Restore pattern success rates
        for k, v in cache_data["pattern_success_rates"].items():
            self.pattern_success_rates[k] = PatternSuccessRate(
                pattern_name=v["pattern_name"],
                success_rate=v["success_rate"],
                total_occurrences=v["total_occurrences"],
                avg_profit=v["avg_profit"],
                avg_loss=v["avg_loss"],
                risk_reward_ratio=v["risk_reward_ratio"],
                market_regime=MarketRegime(v["market_regime"]),
                price_range_position=v["price_range_position"]
            )
        
        # Restore other data
        self.support_resistance_levels = cache_data["support_resistance_levels"]
        self.market_regime_history = cache_data["market_regime_history"]
        self.volatility_percentiles = cache_data["volatility_percentiles"]
        
        logger.info(f"✅ Loaded {len(self.price_ranges)} price ranges and {len(self.pattern_success_rates)} pattern success rates from cache")
    
    # ===== INSTANT LOOKUP METHODS =====
    
    def get_price_range_position(self, current_price: float, period: str = "30D") -> Optional[float]:
        """Get current price position within historical range (0.0 = low, 1.0 = high)"""
        self.total_lookups += 1
        
        if period in self.price_ranges:
            self.cache_hits += 1
            range_data = self.price_ranges[period]
            
            # Update current position
            if range_data.high != range_data.low:
                position = (current_price - range_data.low) / (range_data.high - range_data.low)
                return max(0.0, min(1.0, position))
        
        return None
    
    def set_current_indicators(self, rsi: float, bb_position: float):
        """Set current RSI and BB position for consistency checking"""
        self._last_rsi = rsi
        self._last_bb_pos = bb_position
    
    def get_pattern_success_rate(self, pattern_name: str) -> Optional[PatternSuccessRate]:
        """Get pre-calculated pattern success rate"""
        self.total_lookups += 1
        
        if pattern_name in self.pattern_success_rates:
            self.cache_hits += 1
            return self.pattern_success_rates[pattern_name]
        
        return None
    
    def get_support_resistance_levels(self, timeframe: str = "30D") -> Tuple[List[float], List[float]]:
        """Get pre-calculated support and resistance levels"""
        self.total_lookups += 1
        
        support_key = f"support_{timeframe}"
        resistance_key = f"resistance_{timeframe}"
        
        support = self.support_resistance_levels.get(support_key, [])
        resistance = self.support_resistance_levels.get(resistance_key, [])
        
        if support or resistance:
            self.cache_hits += 1
        
        return support, resistance
    
    def get_volatility_percentile(self, current_volatility: float) -> float:
        """Get current volatility percentile vs historical data"""
        self.total_lookups += 1
        
        if not self.volatility_percentiles:
            return 0.5
        
        self.cache_hits += 1
        
        # Find which percentile current volatility falls into
        for percentile in [99, 95, 90, 75, 50, 25, 10]:
            threshold = self.volatility_percentiles.get(f"p{percentile}", 0)
            if current_volatility >= threshold:
                return percentile / 100.0
        
        return 0.1  # Below 10th percentile
    
    def get_current_market_regime(self) -> MarketRegime:
        """Get current market regime based on recent history"""
        if not self.market_regime_history:
            return MarketRegime.SIDEWAYS
        
        # Get most recent regime
        recent_regimes = self.market_regime_history[-10:]  # Last 10 classifications
        regime_counts = {}
        
        for regime_data in recent_regimes:
            regime = regime_data["regime"]
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        # Return most common recent regime
        most_common_regime = max(regime_counts.items(), key=lambda x: x[1])[0]
        return MarketRegime(most_common_regime)
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status and performance metrics"""
        cache_hit_rate = self.cache_hits / max(self.total_lookups, 1)
        
        return {
            "is_initialized": self.is_initialized,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "total_lookups": self.total_lookups,
            "cache_hit_rate": cache_hit_rate,
            "price_ranges_available": len(self.price_ranges),
            "pattern_success_rates_available": len(self.pattern_success_rates),
            "support_resistance_levels": len(self.support_resistance_levels),
            "market_regime_history_length": len(self.market_regime_history),
            "volatility_percentiles_available": len(self.volatility_percentiles),
            "status": "operational" if self.is_initialized else "initializing"
        }

# Global service instance
_historical_context_service: Optional[HistoricalMarketContextService] = None

async def get_historical_context_service() -> HistoricalMarketContextService:
    """Get or create global historical context service"""
    global _historical_context_service
    if _historical_context_service is None:
        _historical_context_service = HistoricalMarketContextService()
        await _historical_context_service.initialize()
    return _historical_context_service

# Export the service
__all__ = ["HistoricalMarketContextService", "get_historical_context_service", "PriceRange", "PatternSuccessRate", "MarketRegime"]

# VERSION 3.0.1 - Cache bust Mon Oct  6 21:34:15 BST 2025
