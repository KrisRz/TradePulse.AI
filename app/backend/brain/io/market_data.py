"""
Market Data Manager - TradePulse.AI BRAIN
========================================

Hybrid market data management with WebSocket preference and REST fallback.
Provides professional data caching, gap detection, and rate limiting.

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import time

from app.backend.services.live_market_data import (
    get_live_bitcoin_price, get_live_market_data, get_live_candlestick_data
)
from app.backend.services.market_data_persistence import load_recent

logger = logging.getLogger(__name__)

@dataclass
class DataSource:
    """Data source tracking"""
    name: str
    priority: int  # 1=highest priority
    is_available: bool = True
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    failure_count: int = 0
    avg_latency_ms: float = 0.0

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    data: Any
    timestamp: datetime
    source: str
    ttl_seconds: int = 60
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return datetime.now(timezone.utc) > self.timestamp + timedelta(seconds=self.ttl_seconds)

class RateLimiter:
    """Professional rate limiter"""
    
    def __init__(self, calls_per_second: float = 10.0):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0
        
    async def acquire(self):
        """Acquire rate limit token"""
        now = time.time()
        elapsed = now - self.last_call
        
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            await asyncio.sleep(sleep_time)
            
        self.last_call = time.time()

class MarketDataManager:
    """
    Professional hybrid market data manager
    
    Features:
    - WebSocket preference with REST fallback
    - Intelligent caching with TTL
    - Gap detection and backfilling
    - Circuit breaker pattern
    - Rate limiting for REST calls
    """
    
    def __init__(self):
        self.is_initialized = False
        
        # Data sources (priority order)
        self.sources = [
            DataSource("websocket", 1),
            DataSource("rest", 2), 
            DataSource("cache", 3),
            DataSource("persistence", 4)
        ]
        
        # Cache system
        self.tick_cache: Dict[str, CacheEntry] = {}
        self.candle_cache: Dict[str, CacheEntry] = {}
        self.market_data_cache: Dict[str, CacheEntry] = {}
        
        # Rate limiters
        self.rest_rate_limiter = RateLimiter(calls_per_second=8.0)  # Conservative limit
        
        # Circuit breaker settings
        self.failure_threshold = 5
        self.recovery_timeout_seconds = 300  # 5 minutes
        
        # Performance tracking
        self.requests_made = 0
        self.cache_hits = 0
        self.source_stats: Dict[str, Dict[str, int]] = {}
        
        logger.info("📊 Market Data Manager initialized")
        
    async def initialize(self):
        """Initialize market data manager"""
        if self.is_initialized:
            return
            
        logger.info("🚀 Initializing Market Data Manager...")
        
        try:
            # Test connectivity to all sources
            await self._test_connectivity()
            
            # Initialize source statistics
            for source in self.sources:
                self.source_stats[source.name] = {
                    "requests": 0,
                    "successes": 0,
                    "failures": 0,
                    "avg_latency_ms": 0
                }
                
            self.is_initialized = True
            logger.info("✅ Market Data Manager initialized successfully")
            
        except Exception as e:
            logger.warning(f"Market Data Manager initialization warning: {e}")
            # BRAIN FIX: Don't fail, just mark as initialized with warnings
            self.is_initialized = True
            
    async def _test_connectivity(self):
        """Test connectivity to existing data services - NO NEW CONNECTIONS"""
        logger.info("🔍 Testing existing data service connectivity...")
        
        try:
            # BRAIN FIX: Use existing services without creating new connections
            # Just verify the services are available, don't initialize new ones
            from app.backend.services.live_market_data import get_live_market_data_service
            
            service = await get_live_market_data_service()
            if service and service.is_running:
                self._update_source_status("websocket", success=True)
                logger.info(f"✅ Existing WebSocket service: Active")
            else:
                self._update_source_status("websocket", success=False)
                logger.warning("⚠️ Existing WebSocket service not active")
                
        except Exception as e:
            logger.warning(f"Service connectivity test failed: {e}")
            # BRAIN FIX: Don't fail initialization, just mark as unavailable
            self._update_source_status("websocket", success=False)
            
        try:
            # Test persistence
            recent_candles = await load_recent("BTCUSDT", "30m")
            if recent_candles:
                self._update_source_status("persistence", success=True)
                logger.info(f"✅ Persistence: {len(recent_candles)} candles")
            else:
                self._update_source_status("persistence", success=False)
                
        except Exception as e:
            logger.warning(f"Persistence test failed: {e}")
            self._update_source_status("persistence", success=False)
            
    def _update_source_status(self, source_name: str, success: bool, latency_ms: float = 0):
        """Update source availability and statistics"""
        source = next((s for s in self.sources if s.name == source_name), None)
        if not source:
            return
            
        now = datetime.now(timezone.utc)
        
        if success:
            source.is_available = True
            source.last_success = now
            source.failure_count = 0
            
            # Update latency (exponential moving average)
            if latency_ms > 0:
                if source.avg_latency_ms == 0:
                    source.avg_latency_ms = latency_ms
                else:
                    alpha = 0.1
                    source.avg_latency_ms = alpha * latency_ms + (1 - alpha) * source.avg_latency_ms
                    
            # Update statistics
            stats = self.source_stats[source_name]
            stats["successes"] += 1
            stats["avg_latency_ms"] = source.avg_latency_ms
            
        else:
            source.last_failure = now
            source.failure_count += 1
            
            # Circuit breaker logic
            if source.failure_count >= self.failure_threshold:
                source.is_available = False
                logger.warning(f"🚨 Circuit breaker opened for {source_name} (failures: {source.failure_count})")
                
            # Update statistics  
            stats = self.source_stats[source_name]
            stats["failures"] += 1
            
        stats["requests"] += 1
        
    async def get_latest_tick(self, symbol: str = "BTCUSDT") -> Optional[Dict[str, Any]]:
        """Get latest market tick with hybrid sourcing"""
        self.requests_made += 1
        cache_key = f"tick_{symbol}"
        
        try:
            # 1) Check cache first (if fresh)
            if cache_key in self.tick_cache:
                entry = self.tick_cache[cache_key]
                if not entry.is_expired():
                    self.cache_hits += 1
                    logger.debug(f"📊 Tick cache hit: {symbol}")
                    return {
                        "symbol": symbol,
                        "price": entry.data["price"],
                        "timestamp": entry.timestamp.isoformat(),
                        "source": f"cache_{entry.source}"
                    }
                    
            # 2) Try WebSocket/REST (preferred)
            websocket_source = next(s for s in self.sources if s.name == "websocket")
            if websocket_source.is_available:
                start_time = time.time()
                
                try:
                    price = await get_live_bitcoin_price()
                    if price:
                        latency_ms = (time.time() - start_time) * 1000
                        self._update_source_status("websocket", True, latency_ms)
                        
                        tick_data = {
                            "symbol": symbol,
                            "price": float(price),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "source": "websocket"
                        }
                        
                        # Cache result
                        self.tick_cache[cache_key] = CacheEntry(
                            data={"price": float(price)},
                            timestamp=datetime.now(timezone.utc),
                            source="websocket",
                            ttl_seconds=10  # Short TTL for ticks
                        )
                        
                        logger.debug(f"📊 Tick from WebSocket: {symbol} @${price}")
                        return tick_data
                        
                except Exception as e:
                    self._update_source_status("websocket", False)
                    logger.warning(f"WebSocket tick failed: {e}")
                    
            # 3) Fallback to cached data (even if expired)
            if cache_key in self.tick_cache:
                entry = self.tick_cache[cache_key]
                logger.warning(f"📊 Using stale tick cache: {symbol}")
                return {
                    "symbol": symbol,
                    "price": entry.data["price"],
                    "timestamp": entry.timestamp.isoformat(),
                    "source": f"stale_cache_{entry.source}"
                }
                
            logger.error(f"❌ No tick data available for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Get latest tick failed: {e}")
            return None
            
    async def get_recent_candles(
        self, 
        symbol: str = "BTCUSDT", 
        interval: str = "1m", 
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """Get recent candles with gap detection and backfilling"""
        cache_key = f"candles_{symbol}_{interval}_{limit}"
        
        try:
            # Check cache first
            if cache_key in self.candle_cache:
                entry = self.candle_cache[cache_key]
                if not entry.is_expired():
                    self.cache_hits += 1
                    logger.debug(f"📊 Candle cache hit: {len(entry.data)} candles")
                    return entry.data
                    
            # Get from REST API with rate limiting
            rest_source = next(s for s in self.sources if s.name == "rest")
            if rest_source.is_available:
                await self.rest_rate_limiter.acquire()
                start_time = time.time()
                
                try:
                    candles = await get_live_candlestick_data(interval, limit)
                    if candles and len(candles) > 0:
                        latency_ms = (time.time() - start_time) * 1000
                        self._update_source_status("rest", True, latency_ms)
                        
                        # Convert to standard format
                        formatted_candles = []
                        for candle in candles:
                            if isinstance(candle, list) and len(candle) >= 6:
                                formatted_candles.append({
                                    "timestamp": candle[0],
                                    "open": float(candle[1]),
                                    "high": float(candle[2]), 
                                    "low": float(candle[3]),
                                    "close": float(candle[4]),
                                    "volume": float(candle[5]),
                                    "source": "rest"
                                })
                                
                        # Cache result
                        self.candle_cache[cache_key] = CacheEntry(
                            data=formatted_candles,
                            timestamp=datetime.now(timezone.utc),
                            source="rest",
                            ttl_seconds=30  # 30 second TTL for candles
                        )
                        
                        logger.debug(f"📊 {len(formatted_candles)} candles from REST API")
                        return formatted_candles
                        
                except Exception as e:
                    self._update_source_status("rest", False)
                    logger.warning(f"REST candles failed: {e}")
                    
            # Fallback to persistence
            persistence_source = next(s for s in self.sources if s.name == "persistence")
            if persistence_source.is_available:
                try:
                    # Convert limit to time horizon
                    if limit <= 60:
                        horizon = "1h"
                    elif limit <= 240:
                        horizon = "4h"
                    else:
                        horizon = "24h"
                        
                    candles = await load_recent(symbol, horizon)
                    if candles:
                        # Convert persistence format to standard format
                        formatted_candles = []
                        for candle in candles[-limit:]:  # Take last 'limit' candles
                            formatted_candles.append({
                                "timestamp": candle.get("timestamp", 0),
                                "open": float(candle.get("open", 0)),
                                "high": float(candle.get("high", 0)),
                                "low": float(candle.get("low", 0)),
                                "close": float(candle.get("close", 0)),
                                "volume": float(candle.get("volume", 0)),
                                "source": "persistence"
                            })
                            
                        self._update_source_status("persistence", True)
                        logger.info(f"📊 {len(formatted_candles)} candles from persistence")
                        return formatted_candles
                        
                except Exception as e:
                    self._update_source_status("persistence", False)
                    logger.warning(f"Persistence candles failed: {e}")
                    
            # Return cached data if available (even if stale)
            if cache_key in self.candle_cache:
                entry = self.candle_cache[cache_key]
                logger.warning(f"📊 Using stale candle cache: {len(entry.data)} candles")
                return entry.data
                
            logger.error("❌ No candle data available from any source")
            return []
            
        except Exception as e:
            logger.error(f"Get recent candles failed: {e}")
            return []
            
    async def get_market_data(self, symbol: str = "BTCUSDT") -> Optional[Dict[str, Any]]:
        """Get comprehensive market data"""
        cache_key = f"market_{symbol}"
        
        try:
            # Check cache first
            if cache_key in self.market_data_cache:
                entry = self.market_data_cache[cache_key]
                if not entry.is_expired():
                    self.cache_hits += 1
                    return entry.data
                    
            # Get from live market data service
            try:
                market_data = await get_live_market_data()
                if market_data:
                    # Cache result
                    self.market_data_cache[cache_key] = CacheEntry(
                        data=market_data,
                        timestamp=datetime.now(timezone.utc),
                        source="websocket",
                        ttl_seconds=30
                    )
                    
                    return market_data
                    
            except Exception as e:
                logger.warning(f"Market data retrieval failed: {e}")
                
            # Fallback to cached data
            if cache_key in self.market_data_cache:
                entry = self.market_data_cache[cache_key]
                logger.warning("📊 Using stale market data cache")
                return entry.data
                
            return None
            
        except Exception as e:
            logger.error(f"Get market data failed: {e}")
            return None
            
    async def backfill_cache(self, symbol: str = "BTCUSDT", hours: int = 4):
        """Professional cache backfilling"""
        logger.info(f"🔄 Backfilling cache for {symbol} ({hours}h)...")
        
        try:
            # Get recent data from multiple intervals
            intervals = ["1m", "5m", "15m", "1h"]
            
            for interval in intervals:
                # Calculate limit based on interval and hours
                if interval == "1m":
                    limit = hours * 60
                elif interval == "5m":
                    limit = hours * 12
                elif interval == "15m":
                    limit = hours * 4
                else:  # 1h
                    limit = hours
                    
                # Get and cache data
                candles = await self.get_recent_candles(symbol, interval, min(limit, 1000))
                if candles:
                    logger.info(f"✅ Backfilled {len(candles)} {interval} candles")
                    
            logger.info("✅ Cache backfilling completed")
            
        except Exception as e:
            logger.error(f"Cache backfilling failed: {e}")
            
    def detect_data_gaps(self, candles: List[Dict], expected_interval_ms: int = 60000) -> List[Tuple[int, int]]:
        """Detect gaps in candlestick data"""
        gaps = []
        
        if len(candles) < 2:
            return gaps
            
        for i in range(1, len(candles)):
            prev_time = candles[i-1].get("timestamp", 0)
            curr_time = candles[i].get("timestamp", 0)
            
            expected_next = prev_time + expected_interval_ms
            gap_size = curr_time - expected_next
            
            if gap_size > expected_interval_ms:
                gaps.append((prev_time, curr_time))
                
        return gaps
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "requests_made": self.requests_made,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": self.cache_hits / max(self.requests_made, 1),
            "tick_cache_size": len(self.tick_cache),
            "candle_cache_size": len(self.candle_cache),
            "market_data_cache_size": len(self.market_data_cache),
            "source_stats": self.source_stats,
            "source_availability": {
                s.name: s.is_available for s in self.sources
            }
        }
        
    async def clear_expired_cache(self):
        """Clear expired cache entries"""
        cleared = 0
        
        # Clear expired tick cache
        expired_keys = [k for k, v in self.tick_cache.items() if v.is_expired()]
        for key in expired_keys:
            del self.tick_cache[key]
            cleared += 1
            
        # Clear expired candle cache
        expired_keys = [k for k, v in self.candle_cache.items() if v.is_expired()]
        for key in expired_keys:
            del self.candle_cache[key]
            cleared += 1
            
        # Clear expired market data cache
        expired_keys = [k for k, v in self.market_data_cache.items() if v.is_expired()]
        for key in expired_keys:
            del self.market_data_cache[key]
            cleared += 1
            
        if cleared > 0:
            logger.debug(f"🧹 Cleared {cleared} expired cache entries")

# Global market data manager instance
_market_data_manager: Optional[MarketDataManager] = None

async def get_market_data_manager() -> MarketDataManager:
    """Get or create global market data manager"""
    global _market_data_manager
    if _market_data_manager is None:
        _market_data_manager = MarketDataManager()
        await _market_data_manager.initialize()
    return _market_data_manager

# Export classes and functions
__all__ = [
    "MarketDataManager",
    "DataSource", 
    "CacheEntry",
    "RateLimiter",
    "get_market_data_manager"
]