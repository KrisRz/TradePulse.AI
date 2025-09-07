"""
BTC Price Cache Service
======================

PROFESSIONAL IN-MEMORY CACHE - NO EXTERNAL DEPENDENCIES!

Reduces API noise by caching BTC prices with TTL.
Serves cached prices to multiple consumers simultaneously.

Features:
- 5-second TTL for price freshness
- Thread-safe in-memory storage
- Automatic cleanup of expired entries
- Fallback to live fetch when cache miss
- Detailed cache hit/miss logging

Author: TradePulse.AI Development Team
Created: August 2025
Version: 1.0.0
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with timestamp and TTL tracking"""
    data: Any
    timestamp: float
    ttl_seconds: int

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return time.time() - self.timestamp > self.ttl_seconds

    def age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return time.time() - self.timestamp

class BTCPriceCache:
    """
    Professional in-memory BTC price cache
    """

    def __init__(self, ttl_seconds: int = 5, max_size: int = 100):
        self.cache: Dict[str, CacheEntry] = {}
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self._lock = asyncio.Lock()

        logger.info(f"🧠 BTC Price Cache initialized - TTL: {ttl_seconds}s, Max size: {max_size}")

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value or None if expired/missing"""
        async with self._lock:
            entry = self.cache.get(key)

            if entry and not entry.is_expired():
                self.hits += 1
                age = entry.age_seconds()
                logger.debug(f"💰 Cache HIT for {key} - age: {age:.1f}s")
                return entry.data

            # Cache miss or expired
            if entry:
                self.misses += 1
                logger.debug(f"💰 Cache EXPIRED for {key} - age: {entry.age_seconds():.1f}s")
                del self.cache[key]
            else:
                self.misses += 1
                logger.debug(f"💰 Cache MISS for {key}")

            return None

    async def set(self, key: str, value: Any) -> None:
        """Set cache value with current timestamp"""
        async with self._lock:
            # Clean up expired entries if cache is getting full
            if len(self.cache) >= self.max_size:
                await self._cleanup_expired()

            # If still full, remove oldest entry
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(),
                               key=lambda k: self.cache[k].timestamp)
                del self.cache[oldest_key]
                self.evictions += 1
                logger.debug(f"💰 Cache EVICTION - removed {oldest_key}")

            # Set new entry
            self.cache[key] = CacheEntry(
                data=value,
                timestamp=time.time(),
                ttl_seconds=self.ttl_seconds
            )

            logger.debug(f"💰 Cache SET for {key} - cache size: {len(self.cache)}")

    async def _cleanup_expired(self) -> None:
        """Remove all expired entries"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.debug(f"💰 Cache cleanup - removed {len(expired_keys)} expired entries")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0

        return {
            'cache_size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'evictions': self.evictions,
            'ttl_seconds': self.ttl_seconds,
            'max_size': self.max_size
        }

    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self.cache.clear()
            logger.info("💰 Cache cleared")

# Global cache instance
_btc_price_cache: Optional[BTCPriceCache] = None

def get_btc_price_cache() -> BTCPriceCache:
    """Get global BTC price cache instance"""
    global _btc_price_cache

    if _btc_price_cache is None:
        _btc_price_cache = BTCPriceCache()
        logger.info("🧠 Global BTC Price Cache created")

    return _btc_price_cache

# Convenience function for getting BTC price with caching
async def get_cached_btc_price(symbol: str = "BTCUSDT") -> Optional[Dict[str, Any]]:
    """Get BTC price from cache or fetch if needed"""
    cache = get_btc_price_cache()
    cache_key = f"price_{symbol}"

    # Try cache first
    cached_price = await cache.get(cache_key)
    if cached_price:
        return cached_price

    # Cache miss - fetch live price
    try:
        from app.backend.services.live_market_data import get_live_bitcoin_price
        live_price = await get_live_bitcoin_price()

        if live_price:
            # Format as expected dictionary structure
            price_dict = {
                "price": live_price,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "source": "live_api"
            }
            # Cache the result
            await cache.set(cache_key, price_dict)
            return price_dict

    except Exception as e:
        logger.error(f"❌ Failed to fetch BTC price: {e}")

    return None
