"""
High-Performance Market Data Service for TradePulse.AI
Optimized for <5-second trading cycles with parallel fetching and caching
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from collections import deque
import numpy as np
import json
from dataclasses import dataclass, field

from app.backend.core.logging import get_logger
from app.backend.services.binance_hybrid_client import get_hybrid_client

logger = get_logger(__name__)


@dataclass
class MarketDataCache:
    """High-performance market data cache"""
    price: float = 0.0
    volume: float = 0.0
    candles: List[Dict] = field(default_factory=list)
    indicators: Dict[str, float] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=lambda: datetime.min)
    cache_duration: int = 5  # Cache valid for 5 seconds


class HighPerformanceMarketDataService:
    """
    Ultra-fast market data service optimized for <5-second cycles
    
    Features:
    - Parallel data fetching (price + candles + indicators)
    - Intelligent caching with TTL
    - Incremental indicator updates
    - Connection pooling
    - Circuit breaker protection
    - Sub-second response times
    """
    
    def __init__(self):
        self.cache = MarketDataCache()
        self.session: Optional[aiohttp.ClientSession] = None
        self.hybrid_client = None
        
        # Performance tracking
        self.fetch_times = deque(maxlen=100)
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Circuit breaker
        self.failure_count = 0
        self.circuit_open = False
        self.last_failure_time = datetime.min
        
        # Parallel fetching semaphore
        self.fetch_semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests
        
    async def initialize(self):
        """Initialize high-performance service"""
        try:
            # Create optimized HTTP session
            connector = aiohttp.TCPConnector(
                limit=10,  # Connection pool size
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(
                total=3.0,  # 3-second total timeout
                connect=1.0,  # 1-second connect timeout
                sock_read=1.0  # 1-second read timeout
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'TradePulse-Pro/1.0',
                    'Accept': 'application/json',
                    'Connection': 'keep-alive'
                }
            )
            
            # Initialize hybrid client
            self.hybrid_client = await get_hybrid_client()
            
            logger.info("✅ High-performance market data service initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize high-performance service: {e}")
            raise
    
    async def get_market_data_fast(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """
        Get market data optimized for speed (<1 second target)
        
        Returns comprehensive market data with indicators
        """
        start_time = time.time()
        
        try:
            # Check cache first
            if self._is_cache_valid():
                self.cache_hits += 1
                logger.debug(f"⚡ Cache hit for {symbol}")
                return self._format_cached_data()
            
            self.cache_misses += 1
            
            # Circuit breaker check
            if self.circuit_open:
                if time.time() - self.last_failure_time.timestamp() > 30:  # Reset after 30s
                    self.circuit_open = False
                    self.failure_count = 0
                else:
                    raise Exception("Circuit breaker open - market data service unavailable")
            
            # Parallel data fetching
            async with self.fetch_semaphore:
                price_task = self._fetch_price_fast(symbol)
                candles_task = self._fetch_candles_fast(symbol)
                
                # Execute in parallel
                price_data, candles_data = await asyncio.gather(
                    price_task, candles_task, return_exceptions=True
                )
            
            # Handle results
            if isinstance(price_data, Exception):
                raise price_data
            if isinstance(candles_data, Exception):
                raise candles_data
            
            # Update cache
            await self._update_cache(price_data, candles_data)
            
            # Calculate performance
            fetch_time = time.time() - start_time
            self.fetch_times.append(fetch_time)
            
            logger.debug(f"⚡ Market data fetched in {fetch_time:.3f}s")
            
            return self._format_cached_data()
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= 3:
                self.circuit_open = True
                logger.error(f"🚨 Circuit breaker opened after {self.failure_count} failures")
            
            logger.error(f"❌ Fast market data fetch failed: {e}")
            raise
    
    async def _fetch_price_fast(self, symbol: str) -> Dict[str, Any]:
        """Fetch current price with optimized request"""
        try:
            if self.hybrid_client:
                result = await self.hybrid_client.get_data_hybrid("ticker", symbol)
                return result["data"]
            else:
                # Direct API call as fallback
                url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"price": float(data["price"]), "symbol": symbol}
                    else:
                        raise Exception(f"Price API returned {response.status}")
                        
        except Exception as e:
            logger.error(f"Price fetch failed: {e}")
            raise
    
    async def _fetch_candles_fast(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Fetch candles with optimized request"""
        try:
            if self.hybrid_client:
                result = await self.hybrid_client.get_data_hybrid("candles", symbol, interval="1m", limit=limit)
                return result["data"]
            else:
                # Direct API call as fallback
                url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit={limit}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [{"close": float(k[4]), "volume": float(k[5]), "timestamp": k[0]} for k in data]
                    else:
                        raise Exception(f"Candles API returned {response.status}")
                        
        except Exception as e:
            logger.error(f"Candles fetch failed: {e}")
            raise
    
    async def _update_cache(self, price_data: Dict, candles_data: List[Dict]):
        """Update cache with new data and calculate indicators incrementally"""
        try:
            # Update basic data
            self.cache.price = float(price_data.get("price", 0))
            self.cache.volume = float(candles_data[-1].get("volume", 0)) if candles_data else 0
            self.cache.candles = candles_data
            self.cache.last_updated = datetime.now(timezone.utc)
            
            # Calculate indicators incrementally
            if candles_data:
                await self._calculate_indicators_fast(candles_data)
                
        except Exception as e:
            logger.error(f"Cache update failed: {e}")
    
    async def _calculate_indicators_fast(self, candles: List[Dict]):
        """Calculate technical indicators optimized for speed"""
        try:
            if len(candles) < 20:
                return
            
            # Extract prices efficiently
            prices = np.array([float(c.get("close", 0)) for c in candles[-50:]])  # Last 50 for calculations
            volumes = np.array([float(c.get("volume", 0)) for c in candles[-50:]])
            
            current_price = prices[-1]
            
            # Fast RSI calculation (vectorized)
            deltas = np.diff(prices[-15:])  # Last 14 periods
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains) if len(gains) > 0 else 0
            avg_loss = np.mean(losses) if len(losses) > 0 else 0
            
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 100
            
            # Fast MACD calculation
            if len(prices) >= 26:
                ema_12 = self._ema_fast(prices, 12)
                ema_26 = self._ema_fast(prices, 26)
                macd = ema_12 - ema_26
            else:
                macd = 0
            
            # Fast Bollinger Bands
            if len(prices) >= 20:
                sma_20 = np.mean(prices[-20:])
                std_20 = np.std(prices[-20:])
                bb_upper = sma_20 + (2 * std_20)
                bb_lower = sma_20 - (2 * std_20)
                bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
            else:
                bb_position = 0.5
            
            # Fast volatility
            volatility = float(np.std(prices) / np.mean(prices)) if len(prices) > 1 else 0.02
            
            # Fast trend strength
            if len(prices) >= 10:
                x = np.arange(len(prices[-10:]))
                y = prices[-10:]
                slope = np.polyfit(x, y, 1)[0]
                trend_strength = float(np.tanh(abs(slope) / np.mean(y) * 100))
            else:
                trend_strength = 0.5
            
            # Volume analysis
            avg_volume = float(np.mean(volumes)) if len(volumes) > 0 else 1.0
            volume_ratio = float(volumes[-1] / avg_volume) if avg_volume > 0 else 1.0
            
            # Update cache indicators
            self.cache.indicators = {
                "rsi": float(np.clip(rsi, 0, 100)),
                "macd": float(macd),
                "bb_position": float(np.clip(bb_position, 0, 1)),
                "volatility": float(np.clip(volatility, 0.001, 0.5)),
                "trend_strength": float(np.clip(trend_strength, 0, 1)),
                "volume_ratio": float(np.clip(volume_ratio, 0.1, 10.0)),
                "price_change_24h": float(price_data.get("price_change_percent", 0)) if 'price_data' in locals() else 0
            }
            
        except Exception as e:
            logger.error(f"Fast indicator calculation failed: {e}")
            # Set safe defaults
            self.cache.indicators = {
                "rsi": 50.0, "macd": 0.0, "bb_position": 0.5,
                "volatility": 0.02, "trend_strength": 0.5, "volume_ratio": 1.0,
                "price_change_24h": 0.0
            }
    
    def _ema_fast(self, prices: np.ndarray, period: int) -> float:
        """Fast EMA calculation"""
        if len(prices) < period:
            return float(np.mean(prices))
        
        alpha = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        return float(ema)
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if self.cache.last_updated == datetime.min:
            return False
        
        age = (datetime.now(timezone.utc) - self.cache.last_updated).total_seconds()
        return age < self.cache.cache_duration
    
    def _format_cached_data(self) -> Dict[str, Any]:
        """Format cached data for consumption"""
        return {
            "price": self.cache.price,
            "volume": self.cache.volume,
            "candles": self.cache.candles,
            "indicators": self.cache.indicators.copy(),
            "last_updated": self.cache.last_updated.isoformat(),
            "cache_age": (datetime.now(timezone.utc) - self.cache.last_updated).total_seconds()
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        avg_fetch_time = np.mean(self.fetch_times) if self.fetch_times else 0
        
        return {
            "average_fetch_time": float(avg_fetch_time),
            "cache_hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "failure_count": self.failure_count,
            "circuit_open": self.circuit_open,
            "recent_fetch_times": list(self.fetch_times)[-10:]  # Last 10 fetch times
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        if self.session:
            await self.session.close()


# Global high-performance service instance
_hp_market_service: Optional[HighPerformanceMarketDataService] = None

async def get_hp_market_service() -> HighPerformanceMarketDataService:
    """Get global high-performance market data service"""
    global _hp_market_service
    
    if _hp_market_service is None:
        _hp_market_service = HighPerformanceMarketDataService()
        await _hp_market_service.initialize()
    
    return _hp_market_service
