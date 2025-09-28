"""
Market Snapshot Service - Single Source of Truth for Market Data
==============================================================

Provides a unified interface for market data with WebSocket priority and REST fallback.
Ensures consistent market snapshots across all trading components.

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from app.backend.services.live_market_data import get_live_bitcoin_price, get_live_market_data
from app.backend.services.binance_hybrid_client import get_hybrid_client

logger = logging.getLogger(__name__)

@dataclass
class MarketSnapshot:
    """Unified market data snapshot"""
    price: float
    symbol: str
    timestamp: datetime
    source: str  # "ws", "rest", "db", "fallback"
    
    # Technical indicators
    rsi: Optional[float] = None
    macd: Optional[float] = None
    bb_position: Optional[float] = None  # Bollinger Band position (0-1)
    volatility: Optional[float] = None
    volume: Optional[float] = None
    volume_ratio: Optional[float] = None
    
    # Price context
    ema_20: Optional[float] = None
    ema_50: Optional[float] = None
    support: Optional[float] = None
    resistance: Optional[float] = None
    trend_strength: Optional[float] = None
    
    # Market metadata
    age_seconds: Optional[float] = None
    is_fresh: Optional[bool] = None
    
    def __post_init__(self):
        """Calculate derived fields"""
        if self.timestamp:
            self.age_seconds = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
            self.is_fresh = self.age_seconds < 5.0  # Fresh if < 5 seconds old
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for compatibility"""
        return {
            "price": self.price,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "rsi": self.rsi,
            "macd": self.macd,
            "bb_position": self.bb_position,
            "volatility": self.volatility,
            "volume": self.volume,
            "volume_ratio": self.volume_ratio,
            "ema_20": self.ema_20,
            "ema_50": self.ema_50,
            "support": self.support,
            "resistance": self.resistance,
            "trend_strength": self.trend_strength,
            "age_seconds": self.age_seconds,
            "is_fresh": self.is_fresh
        }


class MarketSnapshotService:
    """Single Source of Truth for Market Data"""
    
    def __init__(self):
        self._price_cache = {}  # symbol -> (price, timestamp, source)
        self._market_data_cache = {}  # symbol -> (data, timestamp)
        self._last_snapshot_cache = {}  # symbol -> MarketSnapshot
        
        # Freshness thresholds
        self.WS_MAX_AGE_S = 2.0      # WebSocket data valid for 2 seconds
        self.REST_MAX_AGE_S = 5.0    # REST data valid for 5 seconds
        self.DB_MAX_AGE_S = 30.0     # DB data valid for 30 seconds
        
        logger.info("📊 Market Snapshot Service initialized - Single Source of Truth active")
    
    async def get_snapshot(self, symbol: str = "BTCUSDT") -> MarketSnapshot:
        """
        Get unified market snapshot with single source of truth
        
        Priority order:
        1. Fresh WebSocket data (< 2s)
        2. Fresh REST API data (< 5s) 
        3. Cached DB data (< 30s)
        4. Fallback to last known good price
        """
        try:
            # Step 1: Try fresh WebSocket data
            ws_price = await self._get_ws_price(symbol)
            if ws_price and self._is_price_fresh(ws_price, self.WS_MAX_AGE_S):
                market_data = await self._get_market_indicators(symbol)
                return self._create_snapshot(symbol, ws_price[0], "ws", market_data)
            
            # Step 2: Try REST API data
            rest_price = await self._get_rest_price(symbol)
            if rest_price and self._is_price_fresh(rest_price, self.REST_MAX_AGE_S):
                market_data = await self._get_market_indicators(symbol)
                return self._create_snapshot(symbol, rest_price[0], "rest", market_data)
            
            # Step 3: Try cached data
            if symbol in self._last_snapshot_cache:
                cached = self._last_snapshot_cache[symbol]
                if cached.age_seconds and cached.age_seconds < self.DB_MAX_AGE_S:
                    logger.debug(f"📊 Using cached snapshot: {symbol} ({cached.age_seconds:.1f}s old)")
                    return cached
            
            # Step 4: Fallback to any available price
            fallback_price = ws_price[0] if ws_price else (rest_price[0] if rest_price else 0.0)
            if fallback_price > 0:
                logger.warning(f"⚠️ Using stale price data for {symbol}: ${fallback_price:,.2f}")
                return self._create_snapshot(symbol, fallback_price, "fallback", {})
            
            # Step 5: Emergency fallback
            logger.error(f"❌ No price data available for {symbol}")
            raise ValueError(f"No market data available for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Market snapshot failed for {symbol}: {e}")
            raise
    
    async def _get_ws_price(self, symbol: str) -> Optional[tuple]:
        """Get price from WebSocket source"""
        try:
            price = await get_live_bitcoin_price()
            if price and price > 0:
                timestamp = datetime.now(timezone.utc)
                self._price_cache[f"{symbol}_ws"] = (price, timestamp, "ws")
                return (price, timestamp, "ws")
        except Exception as e:
            logger.debug(f"WebSocket price failed: {e}")
        return None
    
    async def _get_rest_price(self, symbol: str) -> Optional[tuple]:
        """Get price from REST API source"""
        try:
            client = await get_hybrid_client()
            ticker = await client.get_ticker_price(symbol)
            if ticker and 'price' in ticker:
                price = float(ticker['price'])
                timestamp = datetime.now(timezone.utc)
                self._price_cache[f"{symbol}_rest"] = (price, timestamp, "rest")
                return (price, timestamp, "rest")
        except Exception as e:
            logger.debug(f"REST API price failed: {e}")
        return None
    
    async def _get_market_indicators(self, symbol: str) -> Dict[str, Any]:
        """Get market indicators from live market data"""
        try:
            market_data = await get_live_market_data()
            if market_data:
                return market_data
        except Exception as e:
            logger.debug(f"Market indicators failed: {e}")
        
        # Return safe defaults
        return {
            "rsi": 50.0,
            "macd": 0.0,
            "bb_position": 0.5,
            "volatility": 0.02,
            "volume": 1000000.0,
            "volume_ratio": 1.0,
            "trend_strength": 0.0
        }
    
    def _is_price_fresh(self, price_data: tuple, max_age_s: float) -> bool:
        """Check if price data is fresh enough"""
        if not price_data or len(price_data) < 2:
            return False
        
        price, timestamp, source = price_data
        age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        return age <= max_age_s and price > 0
    
    def _create_snapshot(self, symbol: str, price: float, source: str, market_data: Dict[str, Any]) -> MarketSnapshot:
        """Create a market snapshot with full data"""
        timestamp = datetime.now(timezone.utc)
        
        snapshot = MarketSnapshot(
            price=price,
            symbol=symbol,
            timestamp=timestamp,
            source=source,
            rsi=market_data.get("rsi"),
            macd=market_data.get("macd"),
            bb_position=market_data.get("bb_position"),
            volatility=market_data.get("volatility"),
            volume=market_data.get("volume"),
            volume_ratio=market_data.get("volume_ratio"),
            ema_20=market_data.get("ema_20"),
            ema_50=market_data.get("ema_50"),
            support=market_data.get("support"),
            resistance=market_data.get("resistance"),
            trend_strength=market_data.get("trend_strength")
        )
        
        # Cache the snapshot
        self._last_snapshot_cache[symbol] = snapshot
        
        logger.debug(f"📊 Created {source} snapshot: {symbol} @ ${price:,.2f}")
        return snapshot
    
    def get_cached_snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        """Get cached snapshot without network calls"""
        return self._last_snapshot_cache.get(symbol)
    
    def clear_cache(self, symbol: Optional[str] = None):
        """Clear price cache for symbol or all symbols"""
        if symbol:
            keys_to_remove = [k for k in self._price_cache.keys() if k.startswith(symbol)]
            for key in keys_to_remove:
                del self._price_cache[key]
            if symbol in self._last_snapshot_cache:
                del self._last_snapshot_cache[symbol]
        else:
            self._price_cache.clear()
            self._last_snapshot_cache.clear()


# Global singleton instance
_market_snapshot_service: Optional[MarketSnapshotService] = None

def get_market_snapshot_service() -> MarketSnapshotService:
    """Get global market snapshot service instance"""
    global _market_snapshot_service
    if _market_snapshot_service is None:
        _market_snapshot_service = MarketSnapshotService()
    return _market_snapshot_service

# Convenience functions for backward compatibility
async def get_market_snapshot(symbol: str = "BTCUSDT") -> MarketSnapshot:
    """Get market snapshot using SSOT service"""
    service = get_market_snapshot_service()
    return await service.get_snapshot(symbol)

async def get_market_price_ssot(symbol: str = "BTCUSDT") -> float:
    """Get just the price using SSOT service"""
    snapshot = await get_market_snapshot(symbol)
    return snapshot.price
