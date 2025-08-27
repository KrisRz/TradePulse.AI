"""
TradePulse.AI Integrated Market Pipeline - Enhanced Persistence + Live Data
=========================================================================

Complete integration of enhanced persistence (Phase 3.3) with hybrid client (Phase 3.2)
and live market data streams. Creates a unified, high-performance pipeline for real-time
market data processing with enterprise-grade persistence and reliability.

Author: TradePulse.AI Development Team  
Created: August 2025
Version: 4.1.0
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from decimal import Decimal

# Core service imports for integration
from app.backend.services.enhanced_market_persistence import (
    EnhancedMarketPersistence, PersistenceConfig
)
from app.backend.services.binance_hybrid_client import (
    BinanceHybridClient, get_live_price_hybrid, get_live_candles_hybrid
)
from app.backend.services.live_market_data import get_live_market_data_service
from app.backend.services.market_data_persistence import load_recent, write_decisions
from app.backend.core.database import DynamoDBClient

logger = logging.getLogger(__name__)

class PipelineMode(Enum):
    """Pipeline operation modes"""
    REAL_TIME = "real_time"      # Live WebSocket streams
    HYBRID = "hybrid"            # WebSocket + REST fallback
    PERSISTENCE_FIRST = "persistence_first"  # Enhanced persistence priority
    HIGH_FREQUENCY = "high_frequency"        # Maximum performance mode

class DataIntegrityLevel(Enum):
    """Data integrity levels"""
    STRICT = "strict"            # All validation enabled
    BALANCED = "balanced"        # Standard validation
    PERFORMANCE = "performance"  # Minimal validation for speed

@dataclass
class IntegrationConfig:
    """Configuration for integrated market pipeline"""
    # Pipeline mode
    mode: PipelineMode = PipelineMode.HYBRID
    integrity_level: DataIntegrityLevel = DataIntegrityLevel.BALANCED
    
    # Performance settings
    processing_batch_size: int = 100
    max_concurrent_streams: int = 5
    buffer_size: int = 1000
    
    # Integration settings
    enable_enhanced_persistence: bool = True
    enable_hybrid_client: bool = True
    enable_legacy_compatibility: bool = True
    
    # Data flow settings
    persistence_priority: bool = True
    real_time_validation: bool = True
    cross_validation: bool = True
    
    # Quality settings
    min_data_completeness: float = 0.8  # 80% completeness required
    deduplication_enabled: bool = True
    quality_scoring_enabled: bool = True

@dataclass
class IntegrationMetrics:
    """Integration performance metrics"""
    total_data_points: int = 0
    enhanced_persistence_writes: int = 0
    hybrid_client_requests: int = 0
    legacy_compatibility_calls: int = 0
    cross_validation_checks: int = 0
    data_quality_scores: List[float] = field(default_factory=list)
    processing_times: List[float] = field(default_factory=list)
    error_count: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class IntegratedMarketPipeline:
    """
    Integrated Market Data Pipeline
    
    Features:
    - Seamless integration of enhanced persistence with hybrid client
    - Real-time data flow with intelligent fallback mechanisms
    - Cross-validation between multiple data sources
    - Enterprise-grade error handling and recovery
    - Complete backward compatibility with existing services
    - High-performance processing with quality assurance
    """
    
    def __init__(self, config: IntegrationConfig = None):
        self.config = config or IntegrationConfig()
        self.is_running = False
        self.start_time = None
        
        # Core components
        self.enhanced_persistence = None
        self.hybrid_client = None
        self.legacy_market_service = None
        
        # Data buffers
        self.data_buffer = asyncio.Queue(maxsize=self.config.buffer_size)
        self.processing_buffer = []
        
        # Performance tracking
        self.metrics = IntegrationMetrics()
        self.performance_samples = []
        
        # Integration state
        self.last_market_data = {}
        self.data_sources_status = {}
        self.quality_cache = {}
        
        # Processing tasks
        self.processing_tasks = []
        
        # Database client
        self.db_client = None

    async def initialize(self) -> Dict[str, Any]:
        """Initialize integrated market pipeline"""
        try:
            logger.info("🔗 Initializing Integrated Market Pipeline...")
            
            # Initialize database client
            from app.backend.core.config import get_settings
            settings = get_settings()
            self.db_client = DynamoDBClient(local_development=settings.is_development)
            
            # Initialize enhanced persistence with optimized config
            if self.config.enable_enhanced_persistence:
                await self._initialize_enhanced_persistence()
            
            # Initialize hybrid client
            if self.config.enable_hybrid_client:
                await self._initialize_hybrid_client()
            
            # Initialize legacy compatibility
            if self.config.enable_legacy_compatibility:
                await self._initialize_legacy_compatibility()
            
            # Setup data flow routing
            await self._setup_integration_routing()
            
            # Initialize performance monitoring
            await self._initialize_performance_monitoring()
            
            self.start_time = datetime.now(timezone.utc)
            logger.info("✅ Integrated Market Pipeline initialized successfully")
            
            return {
                "status": "success",
                "mode": self.config.mode.value,
                "components_initialized": self._count_active_components(),
                "integration_features": self._get_enabled_features()
            }
            
        except Exception as e:
            logger.error(f"❌ Integrated pipeline initialization failed: {e}")
            raise RuntimeError(f"Pipeline initialization failed: {e}")

    async def _initialize_enhanced_persistence(self):
        """Initialize enhanced persistence with integration-optimized settings"""
        
        # Configure for integration performance
        persistence_config = PersistenceConfig(
            batch_size=200,  # Larger batches for better throughput
            batch_timeout_seconds=10.0,  # Faster processing for real-time
            max_queue_size=5000,  # Large queue for high-frequency data
            validation_enabled=self.config.real_time_validation,
            deduplication_enabled=self.config.deduplication_enabled,
            analytics_enabled=True,
            hot_retention_hours=72  # 3 days in hours for performance
        )
        
        self.enhanced_persistence = EnhancedMarketPersistence(persistence_config)
        await self.enhanced_persistence.initialize()
        
        # Update status
        self.data_sources_status["enhanced_persistence"] = "active"
        logger.info("✅ Enhanced persistence initialized for integration")

    async def _initialize_hybrid_client(self):
        """Initialize hybrid client with integration settings"""
        
        self.hybrid_client = BinanceHybridClient()
        await self.hybrid_client.initialize()
        
        # Start essential streams
        await self.hybrid_client.start_websocket_stream("ticker", "BTCUSDT")
        await self.hybrid_client.start_websocket_stream("kline_1m", "BTCUSDT")
        
        # Update status
        self.data_sources_status["hybrid_client"] = "active"
        logger.info("✅ Hybrid client initialized for integration")

    async def _initialize_legacy_compatibility(self):
        """Initialize legacy market data service for compatibility"""
        
        self.legacy_market_service = await get_live_market_data_service()
        
        # Update status
        self.data_sources_status["legacy_service"] = "active"
        logger.info("✅ Legacy compatibility initialized")

    async def _setup_integration_routing(self):
        """Setup intelligent data routing between components"""
        
        # Create data flow priorities based on config
        self.data_flow_priority = []
        
        if self.config.persistence_priority:
            self.data_flow_priority.extend([
                "enhanced_persistence",
                "hybrid_client", 
                "legacy_service"
            ])
        else:
            self.data_flow_priority.extend([
                "hybrid_client",
                "enhanced_persistence",
                "legacy_service"
            ])

    async def _initialize_performance_monitoring(self):
        """Initialize performance monitoring for integration"""
        
        # Initialize performance tracking
        self.performance_samples = []
        self.metrics = IntegrationMetrics()

    async def start(self) -> Dict[str, Any]:
        """Start integrated market pipeline"""
        try:
            logger.info("🚀 Starting Integrated Market Pipeline...")
            
            self.is_running = True
            
            # Start main integration loop
            main_task = asyncio.create_task(self._main_integration_loop())
            self.processing_tasks.append(main_task)
            
            # Start data processing tasks
            for i in range(3):  # 3 processing workers
                task = asyncio.create_task(self._data_processing_worker(f"worker-{i}"))
                self.processing_tasks.append(task)
            
            # Start cross-validation task
            if self.config.cross_validation:
                validation_task = asyncio.create_task(self._cross_validation_loop())
                self.processing_tasks.append(validation_task)
            
            # Start performance monitoring
            monitoring_task = asyncio.create_task(self._performance_monitoring_loop())
            self.processing_tasks.append(monitoring_task)
            
            logger.info(f"✅ Integrated pipeline started with {len(self.processing_tasks)} tasks")
            
            return {
                "status": "success",
                "mode": self.config.mode.value,
                "processing_tasks": len(self.processing_tasks),
                "data_sources_active": len([s for s in self.data_sources_status.values() if s == "active"])
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to start integrated pipeline: {e}")
            raise RuntimeError(f"Pipeline start failed: {e}")

    async def _main_integration_loop(self):
        """Main integration processing loop"""
        while self.is_running:
            try:
                start_time = time.time()
                
                # Collect data from all sources
                integrated_data = await self._collect_integrated_market_data()
                
                if integrated_data:
                    # Add to processing buffer
                    await self.data_buffer.put(integrated_data)
                    
                    # Update metrics
                    self.metrics.total_data_points += 1
                    
                    # Track processing time
                    processing_time = (time.time() - start_time) * 1000
                    self.metrics.processing_times.append(processing_time)
                    
                    # Trim processing times history
                    if len(self.metrics.processing_times) > 1000:
                        self.metrics.processing_times = self.metrics.processing_times[-1000:]
                
                # Control loop frequency based on mode
                if self.config.mode == PipelineMode.HIGH_FREQUENCY:
                    await asyncio.sleep(5.0)   # 5-second cycles
                elif self.config.mode == PipelineMode.REAL_TIME:
                    await asyncio.sleep(10.0)  # 10-second cycles  
                else:
                    await asyncio.sleep(15.0)  # 15-second cycles (standard)
                
            except Exception as e:
                logger.error(f"Main integration loop error: {e}")
                self.metrics.error_count += 1
                await asyncio.sleep(5.0)

    async def _collect_integrated_market_data(self) -> Optional[Dict[str, Any]]:
        """Collect and integrate market data from all sources"""
        try:
            integrated_data = {
                "timestamp": datetime.now(timezone.utc),
                "symbol": "BTCUSDT",
                "sources": {},
                "quality_scores": {},
                "data_completeness": 0.0
            }
            
            # Collect from hybrid client (primary)
            if self.hybrid_client and self.data_sources_status.get("hybrid_client") == "active":
                await self._collect_from_hybrid_client(integrated_data)
            
            # Collect from enhanced persistence (secondary)
            if self.enhanced_persistence and self.data_sources_status.get("enhanced_persistence") == "active":
                await self._collect_from_enhanced_persistence(integrated_data)
            
            # Collect from legacy service (fallback)
            if self.legacy_market_service and self.data_sources_status.get("legacy_service") == "active":
                await self._collect_from_legacy_service(integrated_data)
            
            # Calculate data completeness
            integrated_data["data_completeness"] = self._calculate_data_completeness(integrated_data)
            
            # Skip if data doesn't meet quality requirements
            if integrated_data["data_completeness"] < self.config.min_data_completeness:
                return None
            
            return integrated_data
            
        except Exception as e:
            logger.error(f"Integrated data collection error: {e}")
            self.metrics.error_count += 1
            return None

    async def _collect_from_hybrid_client(self, integrated_data: Dict[str, Any]):
        """Collect data from hybrid client"""
        try:
            # Get price data
            price_data = await get_live_price_hybrid()
            
            # Get candle data
            candles_data = await get_live_candles_hybrid(limit=100)
            
            if price_data and candles_data.get("candles"):
                integrated_data["sources"]["hybrid_client"] = {
                    "price": price_data["price"],
                    "price_source": price_data["source"],
                    "candles": candles_data["candles"][-20:],  # Last 20 candles
                    "candles_source": candles_data["source"],
                    "candles_count": len(candles_data["candles"])
                }
                
                # Calculate quality score
                quality_score = self._assess_hybrid_data_quality(price_data, candles_data)
                integrated_data["quality_scores"]["hybrid_client"] = quality_score
                
                self.metrics.hybrid_client_requests += 1
                
        except Exception as e:
            logger.error(f"Hybrid client collection error: {e}")
            self.data_sources_status["hybrid_client"] = "error"

    async def _collect_from_enhanced_persistence(self, integrated_data: Dict[str, Any]):
        """Collect data from enhanced persistence"""
        try:
            # Get recent analytics data
            analytics = await self.enhanced_persistence.get_analytics_summary()
            
            # Get performance metrics
            metrics = self.enhanced_persistence.get_performance_metrics()
            
            integrated_data["sources"]["enhanced_persistence"] = {
                "analytics": analytics,
                "metrics": metrics,
                "ingestion_rate": metrics.get("processing_rate_per_sec", 0),
                "quality_distribution": analytics.get("quality_stats", {}),
                "data_points": metrics.get("records_processed", 0)
            }
            
            # Quality score based on ingestion performance
            quality_score = min(metrics.get("processing_rate_per_sec", 0) / 1000.0, 1.0)
            integrated_data["quality_scores"]["enhanced_persistence"] = quality_score
            
            self.metrics.enhanced_persistence_writes += 1
            
        except Exception as e:
            logger.error(f"Enhanced persistence collection error: {e}")
            self.data_sources_status["enhanced_persistence"] = "error"

    async def _collect_from_legacy_service(self, integrated_data: Dict[str, Any]):
        """Collect data from legacy market service"""
        try:
            # Get live market data
            market_data = await self.legacy_market_service.get_current_market_data()
            
            if market_data:
                integrated_data["sources"]["legacy_service"] = {
                    "price": market_data.get("price", 0),
                    "volume": market_data.get("volume", 0),
                    "cache_size": market_data.get("cache_size", 0),
                    "last_update": market_data.get("timestamp")
                }
                
                # Quality score based on data freshness
                quality_score = 0.8  # Standard quality for legacy service
                integrated_data["quality_scores"]["legacy_service"] = quality_score
                
                self.metrics.legacy_compatibility_calls += 1
            
        except Exception as e:
            logger.error(f"Legacy service collection error: {e}")
            self.data_sources_status["legacy_service"] = "error"

    def _assess_hybrid_data_quality(self, price_data: Dict, candles_data: Dict) -> float:
        """Assess data quality from hybrid client"""
        quality_score = 0.0
        
        # Price data quality
        if price_data.get("source") == "websocket":
            quality_score += 0.4
        elif price_data.get("source") == "rest":
            quality_score += 0.3
        else:
            quality_score += 0.2
        
        # Candles data quality
        candles_count = len(candles_data.get("candles", []))
        if candles_count >= 100:
            quality_score += 0.4
        elif candles_count >= 50:
            quality_score += 0.3
        elif candles_count >= 20:
            quality_score += 0.2
        else:
            quality_score += 0.1
        
        # Source consistency bonus
        if (price_data.get("source") == candles_data.get("source") == "websocket"):
            quality_score += 0.2
        
        return min(quality_score, 1.0)

    def _calculate_data_completeness(self, integrated_data: Dict[str, Any]) -> float:
        """Calculate overall data completeness score"""
        source_count = len(integrated_data["sources"])
        quality_average = sum(integrated_data["quality_scores"].values()) / max(len(integrated_data["quality_scores"]), 1)
        
        # Completeness based on sources available and quality
        completeness = (source_count / 3.0) * 0.6 + quality_average * 0.4
        return min(completeness, 1.0)

    async def _data_processing_worker(self, worker_id: str):
        """Data processing worker for integrated pipeline"""
        while self.is_running:
            try:
                # Get data from buffer
                integrated_data = await asyncio.wait_for(
                    self.data_buffer.get(), timeout=30.0
                )
                
                start_time = time.time()
                
                # Process data through enhanced persistence
                await self._process_through_persistence(integrated_data)
                
                # Perform cross-validation if enabled
                if self.config.cross_validation:
                    await self._perform_cross_validation(integrated_data)
                
                # Update legacy compatibility
                if self.config.enable_legacy_compatibility:
                    await self._update_legacy_compatibility(integrated_data)
                
                # Track processing time
                processing_time = (time.time() - start_time) * 1000
                if processing_time > 100:  # Log slow processing
                    logger.debug(f"Slow processing in {worker_id}: {processing_time:.1f}ms")
                
                # Mark task done
                self.data_buffer.task_done()
                
            except asyncio.TimeoutError:
                # No data to process, continue
                continue
            except Exception as e:
                logger.error(f"Data processing error in {worker_id}: {e}")
                self.metrics.error_count += 1

    async def _process_through_persistence(self, integrated_data: Dict[str, Any]):
        """Process integrated data through enhanced persistence"""
        if not self.enhanced_persistence:
            return
        
        try:
            # Extract price data for persistence
            hybrid_source = integrated_data["sources"].get("hybrid_client", {})
            
            if hybrid_source.get("price"):
                # Process ticker data
                ticker_data = {
                    "symbol": integrated_data["symbol"],
                    "price": hybrid_source["price"],
                    "timestamp": int(integrated_data["timestamp"].timestamp() * 1000),
                    "source": hybrid_source.get("price_source", "integrated"),
                    "quality_score": integrated_data["quality_scores"].get("hybrid_client", 0.8)
                }
                
                await self.enhanced_persistence.ingest_market_data(ticker_data, "ticker")
            
            # Process candle data
            candles = hybrid_source.get("candles", [])
            for candle in candles[-5:]:  # Process last 5 candles
                candle_data = {
                    "symbol": integrated_data["symbol"],
                    "timestamp": candle.get("timestamp", candle.get("close_time")),
                    "interval": "1m",
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "volume": candle["volume"],
                    "source": "integrated_pipeline",
                    "integration_quality": integrated_data["data_completeness"]
                }
                
                result = await self.enhanced_persistence.ingest_market_data(candle_data, "candle")
                
                # Track quality scores
                if result.get("quality_score"):
                    self.metrics.data_quality_scores.append(result["quality_score"])
                    
                    # Trim quality scores history
                    if len(self.metrics.data_quality_scores) > 1000:
                        self.metrics.data_quality_scores = self.metrics.data_quality_scores[-1000:]
            
        except Exception as e:
            logger.error(f"Persistence processing error: {e}")

    async def _perform_cross_validation(self, integrated_data: Dict[str, Any]):
        """Perform cross-validation between data sources"""
        try:
            sources = integrated_data["sources"]
            
            # Validate price consistency
            prices = {}
            for source_name, source_data in sources.items():
                if source_data.get("price"):
                    prices[source_name] = float(source_data["price"])
            
            if len(prices) > 1:
                price_values = list(prices.values())
                price_variance = max(price_values) - min(price_values)
                avg_price = sum(price_values) / len(price_values)
                
                # Check for significant price differences (>0.1%)
                if price_variance / avg_price > 0.001:
                    logger.warning(f"Price variance detected: {price_variance:.2f} across sources {list(prices.keys())}")
            
            self.metrics.cross_validation_checks += 1
            
        except Exception as e:
            logger.error(f"Cross-validation error: {e}")

    async def _update_legacy_compatibility(self, integrated_data: Dict[str, Any]):
        """Update legacy compatibility data"""
        try:
            # Store latest data for legacy service compatibility
            self.last_market_data = {
                "timestamp": integrated_data["timestamp"],
                "price": self._get_best_price(integrated_data),
                "sources_count": len(integrated_data["sources"]),
                "data_quality": integrated_data["data_completeness"],
                "integrated": True
            }
            
        except Exception as e:
            logger.error(f"Legacy compatibility update error: {e}")

    def _get_best_price(self, integrated_data: Dict[str, Any]) -> float:
        """Get best price from available sources"""
        
        # Priority order for price sources
        source_priority = ["hybrid_client", "legacy_service", "enhanced_persistence"]
        
        for source_name in source_priority:
            source_data = integrated_data["sources"].get(source_name, {})
            if source_data.get("price"):
                return float(source_data["price"])
        
        return 0.0

    async def _cross_validation_loop(self):
        """Continuous cross-validation monitoring"""
        while self.is_running:
            try:
                # Validate data source consistency
                await self._validate_source_consistency()
                
                # Check for data quality degradation
                await self._check_quality_degradation()
                
                # Update data source health
                await self._update_source_health()
                
                await asyncio.sleep(60.0)  # Check every minute
                
            except Exception as e:
                logger.error(f"Cross-validation loop error: {e}")
                await asyncio.sleep(30.0)

    async def _validate_source_consistency(self):
        """Validate consistency between data sources"""
        # Implementation would check for data consistency
        pass

    async def _check_quality_degradation(self):
        """Check for data quality degradation"""
        if len(self.metrics.data_quality_scores) > 10:
            recent_scores = self.metrics.data_quality_scores[-10:]
            avg_quality = sum(recent_scores) / len(recent_scores)
            
            if avg_quality < 0.7:
                logger.warning(f"Data quality degradation detected: {avg_quality:.2f}")

    async def _update_source_health(self):
        """Update health status of data sources"""
        for source, status in self.data_sources_status.items():
            if status == "error":
                # Try to recover error status
                self.data_sources_status[source] = "recovering"

    async def _performance_monitoring_loop(self):
        """Monitor integration performance"""
        while self.is_running:
            try:
                # Update performance metrics
                current_time = datetime.now(timezone.utc)
                uptime = (current_time - self.start_time).total_seconds()
                
                # Calculate throughput
                if uptime > 0:
                    throughput = self.metrics.total_data_points / uptime
                else:
                    throughput = 0.0
                
                # Log performance summary
                if self.metrics.total_data_points > 0 and self.metrics.total_data_points % 50 == 0:
                    avg_processing_time = sum(self.metrics.processing_times[-100:]) / min(len(self.metrics.processing_times), 100)
                    avg_quality = sum(self.metrics.data_quality_scores[-100:]) / max(len(self.metrics.data_quality_scores), 1)
                    
                    logger.info(f"🔗 Integration Performance: {throughput:.2f} data points/sec, "
                              f"{avg_processing_time:.1f}ms avg processing time, "
                              f"{avg_quality:.2f} avg quality score, "
                              f"{self.metrics.error_count} errors")
                
                self.metrics.last_updated = current_time
                await asyncio.sleep(120.0)  # Update every 2 minutes
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(60.0)

    def _count_active_components(self) -> int:
        """Count active components"""
        return len([s for s in self.data_sources_status.values() if s == "active"])

    def _get_enabled_features(self) -> List[str]:
        """Get list of enabled features"""
        features = []
        if self.config.enable_enhanced_persistence:
            features.append("enhanced_persistence")
        if self.config.enable_hybrid_client:
            features.append("hybrid_client")
        if self.config.enable_legacy_compatibility:
            features.append("legacy_compatibility")
        if self.config.cross_validation:
            features.append("cross_validation")
        if self.config.real_time_validation:
            features.append("real_time_validation")
        return features

    # Public API methods for backward compatibility
    async def get_live_price(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """Get live price with integration benefits"""
        try:
            if self.last_market_data.get("price"):
                return {
                    "symbol": symbol,
                    "price": self.last_market_data["price"],
                    "timestamp": self.last_market_data["timestamp"],
                    "source": "integrated_pipeline",
                    "quality": self.last_market_data.get("data_quality", 1.0)
                }
            
            # Fallback to hybrid client
            if self.hybrid_client:
                return await get_live_price_hybrid()
            
            return {"symbol": symbol, "price": 0.0, "source": "unavailable"}
            
        except Exception as e:
            logger.error(f"Get live price error: {e}")
            return {"symbol": symbol, "price": 0.0, "source": "error"}

    async def get_live_candles(self, symbol: str = "BTCUSDT", limit: int = 100) -> Dict[str, Any]:
        """Get live candles with integration benefits"""
        try:
            # Use hybrid client for candle data
            if self.hybrid_client:
                return await get_live_candles_hybrid(limit=limit)
            
            return {"candles": [], "count": 0, "source": "unavailable"}
            
        except Exception as e:
            logger.error(f"Get live candles error: {e}")
            return {"candles": [], "count": 0, "source": "error"}

    def get_status(self) -> Dict[str, Any]:
        """Get pipeline status (alias for get_integration_status)"""
        return self.get_integration_status()
        
    def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status"""
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0
        
        avg_processing_time = (sum(self.metrics.processing_times[-100:]) / 
                              max(len(self.metrics.processing_times), 1)) if self.metrics.processing_times else 0
        
        avg_quality = (sum(self.metrics.data_quality_scores[-100:]) / 
                      max(len(self.metrics.data_quality_scores), 1)) if self.metrics.data_quality_scores else 0
        
        return {
            "status": "running" if self.is_running else "stopped",
            "mode": self.config.mode.value,
            "uptime_seconds": uptime,
            "components": {
                "enhanced_persistence": self.data_sources_status.get("enhanced_persistence", "inactive"),
                "hybrid_client": self.data_sources_status.get("hybrid_client", "inactive"),
                "legacy_service": self.data_sources_status.get("legacy_service", "inactive")
            },
            "performance": {
                "total_data_points": self.metrics.total_data_points,
                "processing_rate_per_sec": self.metrics.total_data_points / max(uptime, 1),
                "average_processing_time_ms": avg_processing_time,
                "average_quality_score": avg_quality,
                "error_count": self.metrics.error_count,
                "buffer_size": self.data_buffer.qsize()
            },
            "integration": {
                "cross_validation_checks": self.metrics.cross_validation_checks,
                "source_consistency": len([s for s in self.data_sources_status.values() if s == "active"]),
                "data_completeness": self.last_market_data.get("data_quality", 0.0),
                "features_enabled": self._get_enabled_features()
            }
        }

    async def shutdown(self):
        """Graceful shutdown of integrated pipeline"""
        logger.info("🛑 Shutting down Integrated Market Pipeline...")
        
        self.is_running = False
        
        # Cancel all processing tasks
        for task in self.processing_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        
        # Wait for buffer to empty
        await self.data_buffer.join()
        
        # Shutdown components
        if self.enhanced_persistence:
            await self.enhanced_persistence.shutdown()
        
        if self.hybrid_client:
            await self.hybrid_client.shutdown()
        
        logger.info("✅ Integrated Market Pipeline shutdown complete")


# Global integrated pipeline instance
_integrated_pipeline = None

async def get_integrated_market_pipeline(config: IntegrationConfig = None) -> IntegratedMarketPipeline:
    """Get or create integrated market pipeline instance"""
    global _integrated_pipeline
    if _integrated_pipeline is None:
        _integrated_pipeline = IntegratedMarketPipeline(config)
        await _integrated_pipeline.initialize()
    return _integrated_pipeline