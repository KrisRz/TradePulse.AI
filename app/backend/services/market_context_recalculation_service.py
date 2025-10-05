"""
Market Context Recalculation Service

Daily background task to recalculate 90-day market context from live data.
Ensures historical context stays fresh for day trading analysis.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List
import pandas as pd

logger = logging.getLogger(__name__)


class MarketContextRecalculationService:
    """
    Production-grade daily recalculation service
    
    Features:
    - Runs daily at 1 AM UTC
    - Queries last 90 days from market_data table
    - Recalculates price ranges, support/resistance, patterns
    - Updates market_context_cache
    - Automatic retry on failure
    """
    
    def __init__(self):
        self.is_running = False
        self.last_run = None
        self.next_run = None
        self.run_count = 0
        self.error_count = 0
        
        # Schedule: 1 AM UTC daily
        self.schedule_hour = 1
        self.schedule_minute = 0
        
    async def start(self):
        """Start background recalculation task"""
        if self.is_running:
            logger.warning("Recalculation service already running")
            return
        
        self.is_running = True
        logger.info("🚀 Starting Market Context Recalculation Service...")
        logger.info(f"📅 Scheduled daily at {self.schedule_hour:02d}:{self.schedule_minute:02d} UTC")
        
        # Run immediately on startup if last run > 24h ago
        if self.last_run is None or (datetime.now(timezone.utc) - self.last_run) > timedelta(hours=24):
            logger.info("🔄 Running initial recalculation...")
            await self._run_recalculation()
        
        # Start background loop
        asyncio.create_task(self._schedule_loop())
    
    async def stop(self):
        """Stop background task"""
        self.is_running = False
        logger.info("⏹️ Market Context Recalculation Service stopped")
    
    async def _schedule_loop(self):
        """Background loop to run recalculation daily"""
        while self.is_running:
            try:
                # Calculate next run time
                now = datetime.now(timezone.utc)
                next_run = now.replace(hour=self.schedule_hour, minute=self.schedule_minute, second=0, microsecond=0)
                
                # If we've passed today's scheduled time, schedule for tomorrow
                if now >= next_run:
                    next_run += timedelta(days=1)
                
                self.next_run = next_run
                wait_seconds = (next_run - now).total_seconds()
                
                logger.info(f"⏰ Next recalculation in {wait_seconds/3600:.1f} hours ({next_run.strftime('%Y-%m-%d %H:%M UTC')})")
                
                # Wait until scheduled time
                await asyncio.sleep(wait_seconds)
                
                # Run recalculation
                if self.is_running:
                    await self._run_recalculation()
                
            except Exception as e:
                logger.error(f"❌ Schedule loop error: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour
    
    async def _run_recalculation(self):
        """Run full recalculation process"""
        start_time = datetime.now(timezone.utc)
        logger.info("🔄 Starting market context recalculation...")
        
        try:
            # 1. Query last 90 days from market_data
            candles = await self._query_90_day_data()
            
            if not candles:
                logger.error("❌ No data available for recalculation")
                self.error_count += 1
                return
            
            logger.info(f"📊 Loaded {len(candles)} candles from market_data")
            
            # 2. Convert to DataFrame
            df = pd.DataFrame(candles)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df = df.sort_values('timestamp')
            
            # 3. Calculate metrics
            price_ranges = self._calculate_price_ranges(df)
            support, resistance = self._calculate_support_resistance(df)
            patterns = self._calculate_pattern_success_rates(df)
            
            # 4. Update market_context_cache
            await self._update_cache(price_ranges, support, resistance, patterns)
            
            # Success!
            self.last_run = datetime.now(timezone.utc)
            self.run_count += 1
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.info(f"✅ Recalculation completed in {duration:.1f}s")
            logger.info(f"📊 Stats: {len(price_ranges)} ranges, {len(support)} support, {len(resistance)} resistance")
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"❌ Recalculation failed: {e}", exc_info=True)
    
    async def _query_90_day_data(self) -> List[Dict]:
        """Query last 90 days from market_data table"""
        try:
            from app.backend.services.market_data_persistence_service import get_persistence_service
            
            persistence = await get_persistence_service()
            
            # Calculate 90 days ago
            start_time = int((datetime.now(timezone.utc) - timedelta(days=90)).timestamp())
            
            # Query all candles for BTCUSDT
            candles = await persistence.query_candles(
                symbol="BTCUSDT",
                start_time=start_time
            )
            
            return candles
            
        except Exception as e:
            logger.error(f"Failed to query 90-day data: {e}")
            return []
    
    def _calculate_price_ranges(self, df: pd.DataFrame) -> Dict:
        """Calculate price ranges for 7D, 30D, 90D"""
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
                "support_levels": [],  # Will be filled later
                "resistance_levels": [],
                "last_updated": int(current_time.timestamp())
            }
        
        return ranges
    
    def _calculate_support_resistance(self, df: pd.DataFrame) -> tuple:
        """Calculate support and resistance levels"""
        # Find swing highs (resistance)
        swing_highs = df[
            (df['high'] > df['high'].shift(1)) &
            (df['high'] > df['high'].shift(-1))
        ]['high'].tolist()
        
        # Find swing lows (support)
        swing_lows = df[
            (df['low'] < df['low'].shift(1)) &
            (df['low'] < df['low'].shift(-1))
        ]['low'].tolist()
        
        # Sort and get top 5
        resistance = sorted(set(swing_highs), reverse=True)[:5]
        support = sorted(set(swing_lows))[:5]
        
        return support, resistance
    
    def _calculate_pattern_success_rates(self, df: pd.DataFrame) -> Dict:
        """Calculate pattern success rates (simplified)"""
        # For now, return default values
        # TODO: Implement proper pattern recognition
        return {
            "rsi_oversold": {
                "description": "RSI Oversold",
                "success_rate": 0.5,
                "total_signals": 0
            },
            "macd_golden_cross": {
                "description": "MACD Golden Cross",
                "success_rate": 0.5,
                "total_signals": 0
            },
            "bollinger_bounce": {
                "description": "Bollinger Bounce",
                "success_rate": 0.5,
                "total_signals": 0
            }
        }
    
    async def _update_cache(self, price_ranges: Dict, support: List, resistance: List, patterns: Dict):
        """Update market_context_cache in DynamoDB"""
        try:
            from app.backend.core.database import DynamoDBClient
            from app.backend.core.config import get_settings
            
            settings = get_settings()
            client = DynamoDBClient(local_development=settings.is_development)
            
            # Helper to convert floats to Decimal
            def convert_floats(obj):
                if isinstance(obj, float):
                    return Decimal(str(obj))
                elif isinstance(obj, dict):
                    return {k: convert_floats(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_floats(item) for item in obj]
                return obj
            
            # Update support/resistance in price_ranges
            for period in price_ranges.values():
                period["support_levels"] = [Decimal(str(s)) for s in support[:5]]
                period["resistance_levels"] = [Decimal(str(r)) for r in resistance[:5]]
            
            # Create cache item
            cache_item = {
                "cache_key": "market_context_90d",
                "symbol": "BTCUSDT",
                "period": "90D",
                "last_updated": int(datetime.now(timezone.utc).timestamp()),
                "price_ranges": convert_floats(price_ranges),
                "support_levels": [Decimal(str(s)) for s in support],
                "resistance_levels": [Decimal(str(r)) for r in resistance],
                "pattern_success_rates": convert_floats(patterns)
            }
            
            # Save to DynamoDB
            table_name = "market_context_cache"
            client.put_item(table_name, cache_item)
            
            logger.info(f"✅ Updated {table_name} with fresh 90-day context")
            
        except Exception as e:
            logger.error(f"Failed to update cache: {e}")
            raise
    
    def get_status(self) -> Dict:
        """Get service status"""
        return {
            "is_running": self.is_running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "schedule": f"{self.schedule_hour:02d}:{self.schedule_minute:02d} UTC"
        }


# Global service instance
_recalc_service: MarketContextRecalculationService = None


async def get_recalculation_service() -> MarketContextRecalculationService:
    """Get or create global recalculation service"""
    global _recalc_service
    if _recalc_service is None:
        _recalc_service = MarketContextRecalculationService()
    return _recalc_service


__all__ = ["MarketContextRecalculationService", "get_recalculation_service"]
