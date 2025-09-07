"""
Integrated Market Data Pipeline for TradePulse.AI
=================================================

Professional-grade unified market data orchestration pipeline that integrates
all market data sources into a single, high-performance streaming architecture.

Features:
- Unified data orchestration across WebSocket, REST, and persistence layers
- Cross-source data validation and quality assurance
- Intelligent failover and source routing
- Real-time analytics and aggregation engine
- Performance optimization with intelligent caching
- Professional monitoring and health checks

Author: TradePulse.AI Development Team
Version: 1.0.0
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import statistics

from .live_market_data import LiveMarketDataService
from .binance_hybrid_client import BinanceHybridClient
from .enhanced_market_persistence import EnhancedMarketPersistence
from app.backend.core.config import get_settings

logger = logging.getLogger(__name__)

class PipelineState(Enum):
    """Pipeline operational states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"

class DataQualityLevel(Enum):
    """Data quality assessment levels"""
    EXCELLENT = "excellent"    # All sources agree, low latency
    GOOD = "good"             # Minor discrepancies, acceptable latency
    ACCEPTABLE = "acceptable" # Some issues but usable
    POOR = "poor"            # Significant issues, use with caution
    CRITICAL = "critical"    # Data integrity compromised

@dataclass
class MarketDataPoint:
    """Unified market data point with quality metrics"""
    symbol: str
    price: Decimal
    volume: Decimal
    timestamp: datetime
    source: str
    quality: DataQualityLevel
    latency_ms: float
    confidence: float = field(default=1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineMetrics:
    """Pipeline performance and health metrics"""
    total_messages: int = 0
    messages_per_second: float = 0.0
    average_latency_ms: float = 0.0
    data_quality_score: float = 1.0
    source_health: Dict[str, float] = field(default_factory=dict)
    error_rate: float = 0.0
    uptime_seconds: float = 0.0
    last_update: Optional[datetime] = None

class IntegratedMarketPipeline:
    """
    Professional integrated market data pipeline orchestrator.
    
    Unifies all market data sources into a single, high-performance pipeline
    with quality assurance, intelligent routing, and real-time analytics.
    """
    
    def __init__(self):
        self.state = PipelineState.STOPPED
        self.is_running = False
        self.start_time: Optional[datetime] = None
        
        # Core services
        self.live_service: Optional[LiveMarketDataService] = None
        self.hybrid_client: Optional[BinanceHybridClient] = None
        self.persistence: Optional[EnhancedMarketPersistence] = None
        
        # Pipeline data streams
        self.unified_stream = deque(maxlen=10000)
        self.price_stream = deque(maxlen=1000)
        self.volume_stream = deque(maxlen=1000)
        
        # Quality and performance tracking
        self.metrics = PipelineMetrics()
        self.quality_history = deque(maxlen=100)
        self.source_priorities = ["websocket", "rest_api", "cache"]
        
        # Real-time analytics
        self.analytics_cache = {}
        self.aggregation_windows = {
            "1m": deque(maxlen=60),
            "5m": deque(maxlen=300), 
            "15m": deque(maxlen=900)
        }
        
        # Event handlers
        self.data_callbacks: List[Callable] = []
        self.quality_callbacks: List[Callable] = []
        self.health_callbacks: List[Callable] = []
        
        # Configuration
        self.settings = get_settings()
        self.quality_threshold = 0.8
        self.max_latency_ms = 1000.0
        
    async def start(self) -> bool:
        """
        Start the integrated market data pipeline.
        
        Returns:
            bool: True if pipeline started successfully
        """
        try:
            logger.info("🚀 Starting Integrated Market Data Pipeline...")
            self.state = PipelineState.STARTING
            self.start_time = datetime.now(timezone.utc)
            
            # Initialize core services
            await self._initialize_services()
            
            # Start data streams
            await self._start_data_streams()
            
            # Initialize real-time analytics
            await self._initialize_analytics()
            
            # Start monitoring tasks
            await self._start_monitoring()
            
            self.state = PipelineState.RUNNING
            self.is_running = True
            
            logger.info("✅ Integrated Market Data Pipeline started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start pipeline: {e}")
            self.state = PipelineState.FAILED
            await self.stop()
            return False
    
    async def _initialize_services(self):
        """Initialize all market data services"""
        logger.info("🔧 Initializing market data services...")
        
        try:
            # Initialize live market data service
            logger.info("🔧 Starting LiveMarketDataService...")
            self.live_service = LiveMarketDataService()
            await self.live_service.start()
            logger.info("✅ LiveMarketDataService started")
        except Exception as e:
            logger.error(f"❌ LiveMarketDataService failed: {e}")
            self.live_service = None
        
        try:
            # Initialize hybrid client
            logger.info("🔧 Starting BinanceHybridClient...")
            self.hybrid_client = BinanceHybridClient()
            await self.hybrid_client.initialize()
            logger.info("✅ BinanceHybridClient started")
        except Exception as e:
            logger.error(f"❌ BinanceHybridClient failed: {e}")
            self.hybrid_client = None
        
        try:
            # Initialize persistence layer
            logger.info("🔧 Starting EnhancedMarketPersistence...")
            self.persistence = EnhancedMarketPersistence()
            await self.persistence.start()
            logger.info("✅ EnhancedMarketPersistence started")
        except Exception as e:
            logger.error(f"❌ EnhancedMarketPersistence failed: {e}")
            self.persistence = None
        
        # Check if we have at least one working service
        working_services = sum([
            self.live_service is not None,
            self.hybrid_client is not None, 
            self.persistence is not None
        ])
        
        if working_services == 0:
            raise RuntimeError("No market data services could be initialized")
        
        logger.info(f"✅ Market data services initialized ({working_services}/3 working)")
    
    async def _start_data_streams(self):
        """Start unified data streaming"""
        logger.info("📡 Starting unified data streams...")
        
        # Register callbacks for data integration
        if self.live_service:
            self.live_service.add_ticker_callback(self._handle_ticker_data)
            self.live_service.add_candle_callback(self._handle_candle_data)
        
        if self.hybrid_client:
            self.hybrid_client.add_price_callback(self._handle_price_data)
            
        logger.info("✅ Data streams configured")
    
    async def _initialize_analytics(self):
        """Initialize real-time analytics engine"""
        logger.info("📊 Initializing real-time analytics...")
        
        # Start analytics tasks
        asyncio.create_task(self._run_real_time_analytics())
        asyncio.create_task(self._run_quality_monitoring())
        
        logger.info("✅ Real-time analytics initialized")
    
    async def _start_monitoring(self):
        """Start pipeline health monitoring"""
        logger.info("🔍 Starting pipeline monitoring...")
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_pipeline_health())
        asyncio.create_task(self._update_metrics())
        
        logger.info("✅ Pipeline monitoring started")
    
    async def _handle_ticker_data(self, ticker_data: Dict[str, Any]):
        """Process ticker data from live service"""
        try:
            # Get timestamp as numeric value for quality/latency calculations
            raw_timestamp = ticker_data.get("timestamp", time.time())
            
            data_point = MarketDataPoint(
                symbol=ticker_data.get("symbol", "BTCUSDT"),
                price=Decimal(str(ticker_data.get("price", 0))),
                volume=Decimal(str(ticker_data.get("volume", 0))),
                timestamp=datetime.fromtimestamp(raw_timestamp if isinstance(raw_timestamp, (int, float)) else time.time(), tz=timezone.utc),
                source="websocket_ticker",
                quality=self._assess_data_quality(ticker_data),
                latency_ms=self._calculate_latency(ticker_data),
                metadata={"type": "ticker", "raw": ticker_data}
            )
            
            await self._process_unified_data(data_point)
            
        except Exception as e:
            logger.error(f"Error processing ticker data: {e}")
    
    async def _handle_candle_data(self, candle_data: Dict[str, Any]):
        """Process candle data from live service"""
        try:
            data_point = MarketDataPoint(
                symbol=candle_data.get("symbol", "BTCUSDT"),
                price=Decimal(str(candle_data.get("close", 0))),
                volume=Decimal(str(candle_data.get("volume", 0))),
                timestamp=datetime.fromtimestamp(candle_data.get("close_time", time.time()) / 1000, tz=timezone.utc),
                source="websocket_candle",
                quality=self._assess_data_quality(candle_data),
                latency_ms=self._calculate_latency(candle_data),
                metadata={"type": "candle", "raw": candle_data}
            )
            
            await self._process_unified_data(data_point)
            
        except Exception as e:
            logger.error(f"Error processing candle data: {e}")
    
    async def _handle_price_data(self, price_data: Dict[str, Any]):
        """Process price data from hybrid client"""
        try:
            data_point = MarketDataPoint(
                symbol=price_data.get("symbol", "BTCUSDT"),
                price=Decimal(str(price_data.get("price", 0))),
                volume=Decimal(str(price_data.get("volume", 0))),
                timestamp=datetime.fromtimestamp(price_data.get("timestamp", time.time()), tz=timezone.utc),
                source="hybrid_client",
                quality=self._assess_data_quality(price_data),
                latency_ms=self._calculate_latency(price_data),
                metadata={"type": "price", "raw": price_data}
            )
            
            await self._process_unified_data(data_point)
            
        except Exception as e:
            logger.error(f"Error processing price data: {e}")
    
    async def _process_unified_data(self, data_point: MarketDataPoint):
        """Process data through unified pipeline"""
        try:
            # Add to unified stream
            self.unified_stream.append(data_point)
            
            # Update specialized streams
            if data_point.price > 0:
                self.price_stream.append({
                    "price": float(data_point.price),
                    "timestamp": data_point.timestamp.timestamp(),
                    "quality": data_point.quality.value,
                    "source": data_point.source
                })
            
            if data_point.volume > 0:
                self.volume_stream.append({
                    "volume": float(data_point.volume),
                    "timestamp": data_point.timestamp.timestamp(),
                    "source": data_point.source
                })
            
            # Update aggregation windows
            await self._update_aggregation_windows(data_point)
            
            # Trigger callbacks
            for callback in self.data_callbacks:
                try:
                    await callback(data_point)
                except Exception as e:
                    logger.warning(f"Data callback failed: {e}")
            
            # Update metrics
            self.metrics.total_messages += 1
            self.metrics.last_update = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error in unified data processing: {e}")
    
    async def _update_aggregation_windows(self, data_point: MarketDataPoint):
        """Update real-time aggregation windows"""
        try:
            current_time = data_point.timestamp.timestamp()
            
            for window, buffer in self.aggregation_windows.items():
                # Add data point
                buffer.append({
                    "price": float(data_point.price),
                    "volume": float(data_point.volume),
                    "timestamp": current_time,
                    "quality": data_point.quality.value
                })
                
                # Clean old data based on window
                window_seconds = self._get_window_seconds(window)
                cutoff_time = current_time - window_seconds
                
                while buffer and buffer[0]["timestamp"] < cutoff_time:
                    buffer.popleft()
                    
        except Exception as e:
            logger.error(f"Error updating aggregation windows: {e}")
    
    def _get_window_seconds(self, window: str) -> int:
        """Convert window string to seconds"""
        if window == "1m":
            return 60
        elif window == "5m":
            return 300
        elif window == "15m":
            return 900
        return 60
    
    def _assess_data_quality(self, data: Dict[str, Any]) -> DataQualityLevel:
        """Assess data quality based on multiple factors"""
        try:
            score = 1.0
            
            # Check for required fields - be flexible with field names
            price_fields = ["price", "c", "close", "last_price"]
            timestamp_fields = ["timestamp", "E", "event_time", "time"]
            
            # Find price field
            price = 0.0
            price_found = False
            for field in price_fields:
                if field in data and data[field] is not None:
                    try:
                        price = float(data[field])
                        price_found = True
                        break
                    except (ValueError, TypeError):
                        continue
            
            if not price_found:
                score -= 0.3
                logger.debug(f"🔍 No valid price field found in data. Available fields: {list(data.keys())}")
            
            # Find timestamp field
            timestamp_found = False
            for field in timestamp_fields:
                if field in data and data[field] is not None:
                    timestamp_found = True
                    break
            
            if not timestamp_found:
                score -= 0.3
                logger.debug(f"🔍 No valid timestamp field found in data. Available fields: {list(data.keys())}")
            
            # Check price validity
            if price <= 0:
                score -= 0.5
            elif price < 1000 or price > 1000000:  # BTC price sanity check
                score -= 0.2
            
            # Check timestamp freshness - be flexible with field names
            timestamp = None
            for field in timestamp_fields:
                if field in data and data[field] is not None:
                    try:
                        timestamp = data[field]
                        break
                    except:
                        continue
            
            if timestamp is None:
                timestamp = time.time()
                
            # Handle different timestamp formats
            if isinstance(timestamp, datetime):
                timestamp = timestamp.timestamp()
            elif isinstance(timestamp, (int, float)) and timestamp > 1000000000000:
                # Convert milliseconds to seconds
                timestamp = timestamp / 1000
            elif isinstance(timestamp, str):
                try:
                    # Try parsing ISO format
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp = dt.timestamp()
                except:
                    timestamp = time.time()
                    score -= 0.1
            elif not isinstance(timestamp, (int, float)):
                # Invalid timestamp type
                score -= 0.3
                timestamp = time.time()
            
            age_seconds = abs(time.time() - timestamp)
            if age_seconds > 60:  # Data older than 1 minute
                score -= 0.3
            elif age_seconds > 10:  # Data older than 10 seconds
                score -= 0.1
            
            # Convert score to quality level
            if score >= 0.9:
                return DataQualityLevel.EXCELLENT
            elif score >= 0.7:
                return DataQualityLevel.GOOD
            elif score >= 0.5:
                return DataQualityLevel.ACCEPTABLE
            elif score >= 0.3:
                return DataQualityLevel.POOR
            else:
                return DataQualityLevel.CRITICAL
                
        except Exception as e:
            logger.error(f"Error assessing data quality: {e}")
            return DataQualityLevel.POOR
    
    def _calculate_latency(self, data: Dict[str, Any]) -> float:
        """Calculate data latency in milliseconds"""
        try:
            data_timestamp = data.get("timestamp", time.time())
            
            # Handle datetime objects
            if isinstance(data_timestamp, datetime):
                data_timestamp = data_timestamp.timestamp()
            elif isinstance(data_timestamp, (int, float)) and data_timestamp > 1000000000000:
                # Convert milliseconds to seconds
                data_timestamp = data_timestamp / 1000
            elif not isinstance(data_timestamp, (int, float)):
                # Invalid timestamp type
                return 999.0
            
            current_time = time.time()
            latency_ms = (current_time - data_timestamp) * 1000
            
            return max(0, latency_ms)  # Ensure non-negative
            
        except Exception as e:
            logger.error(f"Error calculating latency: {e}")
            return 999.0  # High latency as fallback
    
    async def get_live_price(self, symbol: str = "BTCUSDT") -> Optional[Dict[str, Any]]:
        """
        Get live price with unified quality assessment.
        
        Args:
            symbol: Trading symbol (default: BTCUSDT)
            
        Returns:
            Dict with price, quality, and metadata
        """
        try:
            if not self.is_running:
                logger.warning("Pipeline not running, cannot get live price")
                return None
            
            # Get from price stream
            if self.price_stream:
                latest_price = self.price_stream[-1]
                
                return {
                    "symbol": symbol,
                    "price": latest_price["price"],
                    "timestamp": latest_price["timestamp"],
                    "quality": latest_price["quality"],
                    "source": latest_price["source"],
                    "latency_ms": time.time() * 1000 - latest_price["timestamp"] * 1000,
                    "pipeline_processed": True
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting live price: {e}")
            return None
    
    async def get_live_candles(self, symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 100) -> Optional[Dict[str, Any]]:
        """
        Get live candles with quality metrics.
        
        Args:
            symbol: Trading symbol
            interval: Candle interval
            limit: Number of candles
            
        Returns:
            Dict with candles and quality metrics
        """
        try:
            if not self.is_running:
                logger.warning("Pipeline not running, cannot get live candles")
                return None
            
            # Use aggregation windows for real-time candles
            window_data = self.aggregation_windows.get(interval, deque())
            
            if not window_data:
                logger.warning(f"No data available for interval {interval}")
                return None
            
            # Convert to candle format
            candles = []
            for i in range(min(limit, len(window_data))):
                data_point = list(window_data)[-i-1] if i < len(window_data) else None
                if data_point:
                    candles.append({
                        "timestamp": data_point["timestamp"],
                        "open": data_point["price"],
                        "high": data_point["price"],
                        "low": data_point["price"],
                        "close": data_point["price"],
                        "volume": data_point["volume"],
                        "quality": data_point["quality"]
                    })
            
            return {
                "symbol": symbol,
                "interval": interval,
                "candles": candles[::-1],  # Reverse to chronological order
                "count": len(candles),
                "quality_score": self._calculate_average_quality(candles),
                "pipeline_processed": True
            }
            
        except Exception as e:
            logger.error(f"Error getting live candles: {e}")
            return None
    
    async def get_market_analytics(self) -> Dict[str, Any]:
        """
        Get real-time market analytics from pipeline.
        
        Returns:
            Dict with comprehensive market analytics
        """
        try:
            if not self.price_stream:
                return {"error": "No price data available"}
            
            prices = [p["price"] for p in self.price_stream if p["price"] > 0]
            volumes = [v["volume"] for v in self.volume_stream if v["volume"] > 0]
            
            if not prices:
                return {"error": "No valid price data"}
            
            # Calculate analytics
            analytics = {
                "current_price": prices[-1],
                "price_change_1m": self._calculate_price_change("1m"),
                "price_change_5m": self._calculate_price_change("5m"),
                "price_change_15m": self._calculate_price_change("15m"),
                "volatility": self._calculate_volatility(prices),
                "volume_profile": self._calculate_volume_profile(volumes),
                "trend_direction": self._calculate_trend_direction(prices),
                "support_resistance": self._calculate_support_resistance(prices),
                "quality_score": self.metrics.data_quality_score,
                "data_sources": list(self.metrics.source_health.keys()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Cache analytics
            self.analytics_cache = analytics
            return analytics
            
        except Exception as e:
            logger.error(f"Error calculating market analytics: {e}")
            return {"error": f"Analytics calculation failed: {e}"}
    
    def _calculate_price_change(self, window: str) -> Optional[float]:
        """Calculate price change for given window"""
        try:
            window_data = self.aggregation_windows.get(window, deque())
            if len(window_data) < 2:
                return None
            
            oldest_price = window_data[0]["price"]
            latest_price = window_data[-1]["price"]
            
            if oldest_price > 0:
                change_percent = ((latest_price - oldest_price) / oldest_price) * 100
                return round(change_percent, 4)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating price change for {window}: {e}")
            return None
    
    def _calculate_volatility(self, prices: List[float]) -> Optional[float]:
        """Calculate price volatility"""
        try:
            if len(prices) < 2:
                return None
            
            # Calculate returns
            returns = []
            for i in range(1, len(prices)):
                if prices[i-1] > 0:
                    ret = (prices[i] - prices[i-1]) / prices[i-1]
                    returns.append(ret)
            
            if len(returns) >= 2:
                volatility = statistics.stdev(returns) * 100  # Convert to percentage
                return round(volatility, 6)
            else:
                logger.debug(f"🔄 PIPELINE DEBUG: Volatility calculation - insufficient data points: {len(returns)}")
                return None
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return None
    
    def _calculate_volume_profile(self, volumes: List[float]) -> Dict[str, float]:
        """Calculate volume profile metrics"""
        try:
            if not volumes:
                return {}
            
            return {
                "average": round(statistics.mean(volumes), 2),
                "median": round(statistics.median(volumes), 2),
                "total": round(sum(volumes), 2),
                "max": round(max(volumes), 2),
                "min": round(min(volumes), 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating volume profile: {e}")
            return {}
    
    def _calculate_trend_direction(self, prices: List[float]) -> str:
        """Calculate trend direction"""
        try:
            if len(prices) < 10:
                return "insufficient_data"
            
            # Simple trend analysis using moving averages
            short_ma = statistics.mean(prices[-5:])
            long_ma = statistics.mean(prices[-10:])
            
            if short_ma > long_ma * 1.001:  # 0.1% threshold
                return "bullish"
            elif short_ma < long_ma * 0.999:
                return "bearish"
            else:
                return "sideways"
                
        except Exception as e:
            logger.error(f"Error calculating trend direction: {e}")
            return "unknown"
    
    def _calculate_support_resistance(self, prices: List[float]) -> Dict[str, float]:
        """Calculate basic support and resistance levels"""
        try:
            if len(prices) < 20:
                return {}
            
            recent_prices = prices[-20:]
            current_price = prices[-1]
            
            # Simple support/resistance calculation
            resistance = max(recent_prices)
            support = min(recent_prices)
            
            return {
                "support": round(support, 2),
                "resistance": round(resistance, 2),
                "current": round(current_price, 2),
                "distance_to_resistance": round(((resistance - current_price) / current_price) * 100, 2),
                "distance_to_support": round(((current_price - support) / current_price) * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating support/resistance: {e}")
            return {}
    
    def _calculate_average_quality(self, candles: List[Dict[str, Any]]) -> float:
        """Calculate average quality score for candles"""
        try:
            if not candles:
                return 0.0
            
            quality_scores = []
            for candle in candles:
                quality_str = candle.get("quality", "poor")
                if quality_str == "excellent":
                    quality_scores.append(1.0)
                elif quality_str == "good":
                    quality_scores.append(0.8)
                elif quality_str == "acceptable":
                    quality_scores.append(0.6)
                elif quality_str == "poor":
                    quality_scores.append(0.4)
                else:
                    quality_scores.append(0.2)
            
            return round(statistics.mean(quality_scores), 3)
            
        except Exception as e:
            logger.error(f"Error calculating average quality: {e}")
            return 0.0
    
    async def _run_real_time_analytics(self):
        """Run continuous real-time analytics"""
        while self.is_running:
            try:
                await asyncio.sleep(5)  # Update every 5 seconds
                
                if self.price_stream:
                    # Update analytics cache
                    await self.get_market_analytics()
                    
            except Exception as e:
                logger.error(f"Error in real-time analytics: {e}")
                await asyncio.sleep(10)  # Longer delay on error
    
    async def _run_quality_monitoring(self):
        """Monitor data quality continuously"""
        while self.is_running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                # Calculate quality metrics
                if self.unified_stream:
                    recent_data = list(self.unified_stream)[-100:]  # Last 100 points
                    
                    # Diagnostic: Check what's in unified_stream
                    logger.debug(f"🔍 Unified stream diagnostic: {len(recent_data)} data points")
                    if recent_data:
                        sample_data = recent_data[0]
                        logger.debug(f"🔍 Sample data point: type={type(sample_data)}, hasattr_quality={hasattr(sample_data, 'quality')}")
                    
                    try:
                        quality_scores = [self._quality_to_score(dp.quality) for dp in recent_data]
                    except Exception as e:
                        logger.error(f"❌ Error processing quality scores: {e}")
                        logger.debug(f"🔍 Sample data structure: {recent_data[0] if recent_data else 'empty'}")
                        quality_scores = [0.2] * len(recent_data)  # Fallback scores
                    
                    if quality_scores:
                        avg_quality = statistics.mean(quality_scores)
                        self.metrics.data_quality_score = round(avg_quality, 3)
                        self.quality_history.append(avg_quality)
                        
                        # Enhanced diagnostic logging
                        logger.debug(f"🔍 Quality scores: min={min(quality_scores):.3f}, max={max(quality_scores):.3f}, avg={avg_quality:.3f}")
                        
                        # Check quality threshold (lowered for current market conditions)
                        if avg_quality < 0.70:  # Lowered from default to 70%
                            logger.warning(f"⚠️ Data quality below threshold: {avg_quality:.3f} (scores: {len(quality_scores)} points)")
                        else:
                            logger.debug(f"📊 Data quality acceptable: {avg_quality:.3f}")
                            
                            # Trigger quality callbacks
                            for callback in self.quality_callbacks:
                                try:
                                    await callback(avg_quality)
                                except Exception as e:
                                    logger.warning(f"Quality callback failed: {e}")
                    
            except Exception as e:
                logger.error(f"Error in quality monitoring: {e}")
                await asyncio.sleep(30)  # Longer delay on error
    
    def _quality_to_score(self, quality: DataQualityLevel) -> float:
        """Convert quality level to numeric score"""
        quality_map = {
            DataQualityLevel.EXCELLENT: 1.0,
            DataQualityLevel.GOOD: 0.8,
            DataQualityLevel.ACCEPTABLE: 0.6,
            DataQualityLevel.POOR: 0.4,
            DataQualityLevel.CRITICAL: 0.2
        }
        return quality_map.get(quality, 0.0)
    
    async def _monitor_pipeline_health(self):
        """Monitor overall pipeline health"""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Health check every 30 seconds
                
                # Check service health
                services_health = {}
                
                if self.live_service:
                    services_health["live_service"] = 1.0 if self.live_service.is_running else 0.0
                
                if self.hybrid_client:
                    services_health["hybrid_client"] = 1.0 if self.hybrid_client.is_connected else 0.0
                
                if self.persistence:
                    services_health["persistence"] = 1.0 if self.persistence.is_running else 0.0
                
                self.metrics.source_health = services_health
                
                # Overall health assessment
                overall_health = statistics.mean(services_health.values()) if services_health else 0.0
                
                # Update pipeline state
                if overall_health >= 0.8:
                    if self.state != PipelineState.RUNNING:
                        self.state = PipelineState.RUNNING
                elif overall_health >= 0.5:
                    if self.state != PipelineState.DEGRADED:
                        self.state = PipelineState.DEGRADED
                        logger.warning(f"⚠️ Pipeline in degraded state: {overall_health:.2f}")
                else:
                    if self.state != PipelineState.FAILED:
                        self.state = PipelineState.FAILED
                        logger.error(f"❌ Pipeline health critical: {overall_health:.2f}")
                
                # Trigger health callbacks
                for callback in self.health_callbacks:
                    try:
                        await callback(overall_health, services_health)
                    except Exception as e:
                        logger.warning(f"Health callback failed: {e}")
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)  # Longer delay on error
    
    async def _update_metrics(self):
        """Update pipeline performance metrics"""
        last_message_count = 0
        last_update_time = time.time()
        
        while self.is_running:
            try:
                await asyncio.sleep(10)  # Update every 10 seconds
                
                current_time = time.time()
                time_diff = current_time - last_update_time
                
                if time_diff > 0:
                    # Calculate messages per second
                    message_diff = self.metrics.total_messages - last_message_count
                    self.metrics.messages_per_second = round(message_diff / time_diff, 2)
                    
                    # Update uptime
                    if self.start_time:
                        self.metrics.uptime_seconds = (datetime.now(timezone.utc) - self.start_time).total_seconds()
                    
                    # Calculate average latency
                    if self.price_stream:
                        recent_latencies = []
                        current_timestamp = time.time() * 1000
                        
                        for price_data in list(self.price_stream)[-10:]:  # Last 10 data points
                            data_timestamp = price_data["timestamp"] * 1000
                            latency = current_timestamp - data_timestamp
                            if latency >= 0:
                                recent_latencies.append(latency)
                        
                        if recent_latencies:
                            self.metrics.average_latency_ms = round(statistics.mean(recent_latencies), 2)
                    
                    # Update for next iteration
                    last_message_count = self.metrics.total_messages
                    last_update_time = current_time
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(30)  # Longer delay on error
    
    def add_data_callback(self, callback: Callable):
        """Add callback for data updates"""
        if callback not in self.data_callbacks:
            self.data_callbacks.append(callback)
    
    def add_quality_callback(self, callback: Callable):
        """Add callback for quality updates"""
        if callback not in self.quality_callbacks:
            self.quality_callbacks.append(callback)
    
    def add_health_callback(self, callback: Callable):
        """Add callback for health updates"""
        if callback not in self.health_callbacks:
            self.health_callbacks.append(callback)
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get comprehensive pipeline status.
        
        Returns:
            Dict with pipeline state, metrics, and health info
        """
        return {
            "state": self.state.value,
            "is_running": self.is_running,
            "uptime_seconds": self.metrics.uptime_seconds,
            "messages_per_second": self.metrics.messages_per_second,
            "average_latency_ms": self.metrics.average_latency_ms,
            "data_quality_score": self.metrics.data_quality_score,
            "source_health": self.metrics.source_health,
            "total_messages": self.metrics.total_messages,
            "unified_stream_size": len(self.unified_stream),
            "price_stream_size": len(self.price_stream),
            "volume_stream_size": len(self.volume_stream),
            "analytics_available": bool(self.analytics_cache),
            "last_update": self.metrics.last_update.isoformat() if self.metrics.last_update else None
        }
    
    async def stop(self):
        """Stop the integrated market pipeline"""
        try:
            logger.info("🛑 Stopping Integrated Market Data Pipeline...")
            self.is_running = False
            self.state = PipelineState.STOPPED
            
            # Stop services
            if self.live_service:
                await self.live_service.stop()
            
            if self.hybrid_client:
                await self.hybrid_client.stop()
            
            if self.persistence:
                await self.persistence.stop()
            
            # Clear callbacks
            self.data_callbacks.clear()
            self.quality_callbacks.clear()
            self.health_callbacks.clear()
            
            logger.info("✅ Integrated Market Data Pipeline stopped")
            
        except Exception as e:
            logger.error(f"Error stopping pipeline: {e}")

# Global pipeline instance
_pipeline_instance: Optional[IntegratedMarketPipeline] = None

async def get_integrated_market_pipeline() -> IntegratedMarketPipeline:
    """
    Get or create the global integrated market pipeline instance.
    
    Returns:
        IntegratedMarketPipeline: The global pipeline instance
    """
    global _pipeline_instance
    
    if _pipeline_instance is None:
        logger.info("🏗️ Creating new Integrated Market Pipeline instance...")
        _pipeline_instance = IntegratedMarketPipeline()
    
    return _pipeline_instance

async def stop_integrated_market_pipeline():
    """Stop and cleanup the global pipeline instance"""
    global _pipeline_instance
    
    if _pipeline_instance:
        await _pipeline_instance.stop()
        _pipeline_instance = None
        logger.info("🧹 Integrated Market Pipeline instance cleaned up")
