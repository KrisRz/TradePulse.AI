"""
Enhanced Market Data Persistence Engine for TradePulse.AI
========================================================

Professional-grade time-series market data persistence with real-time analytics,
data quality validation, compression, and intelligent archival strategies.

Features:
- High-performance streaming ingestion pipeline
- Real-time data quality validation and deduplication
- Time-series optimized storage with intelligent partitioning
- Automated compression and archival policies
- Real-time analytics and aggregation engine
- Professional monitoring and alerting

Author: TradePulse.AI Development Team
Version: 1.0.0
"""

import asyncio
import logging
import time
import json
import hashlib
import gzip
import io
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import statistics

from app.backend.core.database import DynamoDBClient, MarketCandle
from app.backend.core.config import get_settings

logger = logging.getLogger(__name__)

class DataQuality(Enum):
    """Data quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good" 
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    INVALID = "invalid"

class CompressionLevel(Enum):
    """Data compression levels"""
    NONE = "none"
    LIGHT = "light"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"

class StorageTier(Enum):
    """Storage tier levels"""
    HOT = "hot"          # Real-time access, no compression
    WARM = "warm"        # Recent data, light compression  
    COLD = "cold"        # Historical data, heavy compression
    ARCHIVED = "archived" # Long-term storage, maximum compression

@dataclass
class DataQualityMetrics:
    """Data quality assessment metrics"""
    completeness_score: float = 0.0
    accuracy_score: float = 0.0
    consistency_score: float = 0.0
    timeliness_score: float = 0.0
    overall_quality: DataQuality = DataQuality.INVALID
    issues_detected: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0

@dataclass
class IngestionMetrics:
    """Real-time ingestion performance metrics"""
    records_processed: int = 0
    records_valid: int = 0
    records_invalid: int = 0
    records_duplicate: int = 0
    bytes_ingested: int = 0
    bytes_compressed: int = 0
    records_per_second: float = 0.0  # FIXED: Consistent naming
    processing_rate_per_sec: float = 0.0  # Keep for backward compatibility
    error_rate_percent: float = 0.0
    error_rate: float = 0.0  # ADDED: Consistent naming
    duplicate_rate: float = 0.0  # ADDED: Consistent naming
    quality_distribution: Dict[str, int] = field(default_factory=dict)  # ADDED: Quality tracking
    compression_ratio: float = 0.0
    start_time: float = field(default_factory=time.time)  # ADDED: For uptime calculation
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class AnalyticsSnapshot:
    """Real-time analytics snapshot"""
    timestamp: datetime
    symbol: str
    price_stats: Dict[str, float]
    volume_stats: Dict[str, float]
    volatility_metrics: Dict[str, float]
    trend_indicators: Dict[str, float]
    market_health: Dict[str, Any]

@dataclass
class PersistenceConfig:
    """Enhanced persistence configuration"""
    # Ingestion settings
    batch_size: int = 100
    batch_timeout_seconds: float = 5.0
    max_queue_size: int = 10000
    validation_enabled: bool = True
    deduplication_enabled: bool = True
    
    # Storage tier settings
    hot_retention_hours: int = 24
    warm_retention_days: int = 30
    cold_retention_days: int = 365
    archive_retention_years: int = 7
    
    # Compression settings
    compression_threshold_age_hours: int = 6
    compression_threshold_size_mb: int = 10
    compression_level: CompressionLevel = CompressionLevel.STANDARD
    
    # Analytics settings
    analytics_enabled: bool = True
    analytics_window_minutes: int = 15
    aggregation_intervals: List[str] = field(default_factory=lambda: ["1m", "5m", "15m", "1h", "4h", "1d"])
    
    # Performance settings
    concurrent_writers: int = 10
    memory_buffer_mb: int = 100
    disk_buffer_mb: int = 500

class EnhancedMarketPersistence:
    """
    Enhanced market data persistence engine with enterprise-grade features
    
    Provides:
    - High-performance streaming data ingestion
    - Real-time data quality validation
    - Intelligent compression and tiering
    - Real-time analytics and aggregation
    - Professional monitoring and alerting
    """
    
    def __init__(self, config: Optional[PersistenceConfig] = None):
        """Initialize enhanced persistence engine"""
        self.config = config or PersistenceConfig()
        self.settings = get_settings()
        
        # Database connection
        self.db_client: Optional[DynamoDBClient] = None
        
        # Ingestion pipeline
        self.ingestion_queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.max_queue_size)
        self.batch_buffer: List[Dict[str, Any]] = []
        self.last_batch_time = time.time()
        
        # Data quality and validation
        self.quality_validator = DataQualityValidator()
        self.deduplication_cache: Dict[str, float] = {}  # hash -> timestamp
        self.duplicate_window_seconds = 300  # 5 minutes
        
        # Analytics engine
        self.analytics_engine = RealTimeAnalyticsEngine()
        self.analytics_buffer: Dict[str, AnalyticsSnapshot] = {}
        
        # Performance monitoring
        self.ingestion_metrics = IngestionMetrics()
        self.performance_monitor = PerformanceMonitor()
        
        # Storage management
        self.storage_manager = StorageTierManager(self.config)
        self.compression_manager = CompressionManager(self.config)
        
        # Control tasks
        self.ingestion_task: Optional[asyncio.Task] = None
        self.analytics_task: Optional[asyncio.Task] = None
        self.archival_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Event callbacks
        self.quality_callbacks: List[Callable] = []
        self.analytics_callbacks: List[Callable] = []
        self.alert_callbacks: List[Callable] = []
        
        # Control flags
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        logger.info("🚀 Enhanced Market Persistence Engine initialized")
    
    async def start_ingestion(self, *args, **kwargs):
        """
        Backwards compatibility shim for start_ingestion calls.
        The new pattern is to call initialize() which starts all loops.
        """
        logger.info("📡 start_ingestion called - using initialize() for backwards compatibility")
        if not self.is_running:
            return await self.initialize()
        else:
            logger.info("✅ Enhanced persistence already running")
            return {"status": "already_running", "timestamp": datetime.now(timezone.utc).isoformat()}
    
    async def start(self, *args, **kwargs):
        """New entrypoint - alias for initialize()"""
        return await self.initialize()
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize persistence engine"""
        # Idempotency guard
        if self.is_running:
            logger.info("🔄 Enhanced Persistence Engine already initialized, skipping...")
            return {
                "status": "already_initialized",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        try:
            logger.info("⚡ Initializing Enhanced Persistence Engine...")
            
            # Initialize database connection
            self.db_client = DynamoDBClient(local_development=self.settings.is_development)
            
            # Initialize sub-components
            await self.quality_validator.initialize()
            await self.analytics_engine.initialize()
            await self.storage_manager.initialize(self.db_client)
            await self.compression_manager.initialize(self.db_client)
            
            # Start background tasks
            self.ingestion_task = asyncio.create_task(self._ingestion_loop())
            self.analytics_task = asyncio.create_task(self._analytics_loop())
            self.archival_task = asyncio.create_task(self._archival_loop())
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.is_running = True
            
            logger.info("✅ Enhanced Persistence Engine initialized")
            
            return {
                "status": "initialized",
                "database": self.db_client is not None,
                "config": {
                    "batch_size": self.config.batch_size,
                    "validation_enabled": self.config.validation_enabled,
                    "analytics_enabled": self.config.analytics_enabled,
                    "compression_level": self.config.compression_level.value
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize persistence engine: {e}")
            raise
    
    async def ingest_market_data(self, data: Dict[str, Any], data_type: str = "candle") -> Dict[str, Any]:
        """
        Ingest market data with quality validation and intelligent processing
        
        Args:
            data: Market data (candle, ticker, orderbook, etc.)
            data_type: Type of market data
            
        Returns:
            Ingestion result with quality metrics
        """
        start_time = time.time()
        
        try:
            # Step 1: Data quality validation
            quality_metrics = await self.quality_validator.validate_data(data, data_type)
            
            if quality_metrics.overall_quality == DataQuality.INVALID:
                self.ingestion_metrics.records_invalid += 1
                return {
                    "status": "rejected",
                    "reason": "data_quality_invalid",
                    "quality_metrics": quality_metrics,
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
            
            # Step 2: Deduplication check
            if self.config.deduplication_enabled:
                if await self._is_duplicate(data):
                    self.ingestion_metrics.records_duplicate += 1
                    return {
                        "status": "rejected", 
                        "reason": "duplicate_data",
                        "processing_time_ms": (time.time() - start_time) * 1000
                    }
            
            # Step 3: Enrichment and normalization
            enriched_data = await self._enrich_data(data, data_type, quality_metrics)
            
            # Step 4: Queue for batch processing
            await self.ingestion_queue.put({
                "data": enriched_data,
                "type": data_type,
                "quality": quality_metrics,
                "timestamp": datetime.now(timezone.utc),
                "processing_time": time.time() - start_time
            })
            
            # Step 5: Update metrics
            self.ingestion_metrics.records_processed += 1
            self.ingestion_metrics.records_valid += 1
            self.ingestion_metrics.bytes_ingested += len(json.dumps(data).encode())
            
            # Step 6: Trigger real-time analytics
            if self.config.analytics_enabled and data_type == "candle":
                await self.analytics_engine.process_candle(enriched_data)
            
            return {
                "status": "accepted",
                "quality_score": quality_metrics.overall_quality.value,
                "processing_time_ms": (time.time() - start_time) * 1000,
                "queue_size": self.ingestion_queue.qsize()
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest market data: {e}")
            self.ingestion_metrics.records_invalid += 1
            return {
                "status": "error",
                "error": str(e),
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    async def _is_duplicate(self, data: Dict[str, Any]) -> bool:
        """Check if data is duplicate using hash-based deduplication"""
        try:
            # Create hash of essential data fields
            timestamp = data.get("timestamp", data.get("open_time", 0))
            if isinstance(timestamp, datetime):
                timestamp = int(timestamp.timestamp() * 1000)
            
            hash_fields = {
                "symbol": data.get("symbol", ""),
                "timestamp": timestamp,
                "open": str(data.get("open", 0)),
                "close": str(data.get("close", 0)),
                "volume": str(data.get("volume", 0))
            }
            
            data_hash = hashlib.md5(json.dumps(hash_fields, sort_keys=True).encode()).hexdigest()
            current_time = time.time()
            
            # Check if hash exists within duplicate window
            if data_hash in self.deduplication_cache:
                last_seen = self.deduplication_cache[data_hash]
                if current_time - last_seen < self.duplicate_window_seconds:
                    return True
            
            # Store hash with current timestamp
            self.deduplication_cache[data_hash] = current_time
            
            # Cleanup old hashes
            if len(self.deduplication_cache) > 10000:
                cutoff_time = current_time - self.duplicate_window_seconds
                self.deduplication_cache = {
                    h: t for h, t in self.deduplication_cache.items() 
                    if t > cutoff_time
                }
            
            return False
            
        except Exception as e:
            logger.warning(f"Deduplication check failed: {e}")
            return False
    
    async def _enrich_data(self, data: Dict[str, Any], data_type: str, quality: DataQualityMetrics) -> Dict[str, Any]:
        """Enrich data with metadata and computed fields"""
        enriched = data.copy()
        
        # Add persistence metadata
        enriched["_meta"] = {
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "data_type": data_type,
            "quality_score": quality.overall_quality.value,
            "storage_tier": StorageTier.HOT.value,
            "compression_level": CompressionLevel.NONE.value,
            "partition_key": self._generate_partition_key(data),
            "ttl": self._calculate_ttl(data_type)
        }
        
        # Add computed fields for candles
        if data_type == "candle":
            enriched["_computed"] = {
                "price_range": float(data.get("high", 0)) - float(data.get("low", 0)),
                "price_change": float(data.get("close", 0)) - float(data.get("open", 0)),
                "price_change_percent": ((float(data.get("close", 0)) - float(data.get("open", 0))) / float(data.get("open", 1))) * 100,
                "volume_weighted_price": ((float(data.get("high", 0)) + float(data.get("low", 0)) + float(data.get("close", 0))) / 3),
                "is_bullish": float(data.get("close", 0)) > float(data.get("open", 0)),
                "volatility_estimate": ((float(data.get("high", 0)) - float(data.get("low", 0))) / float(data.get("open", 1))) * 100
            }
        
        return enriched
    
    def _generate_partition_key(self, data: Dict[str, Any]) -> str:
        """Generate optimal partition key for time-series storage"""
        symbol = data.get("symbol", "UNKNOWN")
        timestamp = data.get("timestamp", data.get("open_time", int(time.time() * 1000)))
        
        # Use hourly partitions for optimal DynamoDB performance
        dt = datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.utc)
        hour_key = dt.strftime("%Y-%m-%d-%H")
        
        return f"{symbol}#{hour_key}"
    
    def _calculate_ttl(self, data_type: str) -> int:
        """Calculate TTL based on data type and retention policy"""
        base_time = int(time.time())
        
        if data_type == "candle":
            return base_time + (self.config.archive_retention_years * 365 * 24 * 60 * 60)
        elif data_type == "ticker":
            return base_time + (30 * 24 * 60 * 60)  # 30 days
        elif data_type == "orderbook":
            return base_time + (7 * 24 * 60 * 60)   # 7 days
        else:
            return base_time + (90 * 24 * 60 * 60)  # 90 days default
    
    async def _ingestion_loop(self):
        """Background ingestion processing loop"""
        logger.info("🔄 Starting ingestion processing loop")
        
        while self.is_running:
            try:
                # Process batches
                await self._process_batch()
                
                # Update performance metrics
                await self._update_ingestion_metrics()
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Ingestion loop error: {e}")
                await asyncio.sleep(1)
    
    async def _process_batch(self):
        """Process a batch of queued data"""
        try:
            # Wait for items or timeout
            timeout = self.config.batch_timeout_seconds
            current_time = time.time()
            
            # Collect items for batch
            while (len(self.batch_buffer) < self.config.batch_size and 
                   (current_time - self.last_batch_time) < timeout):
                
                try:
                    item = await asyncio.wait_for(self.ingestion_queue.get(), timeout=0.1)
                    self.batch_buffer.append(item)
                except asyncio.TimeoutError:
                    break
                
                current_time = time.time()
            
            # Process batch if we have items
            if self.batch_buffer:
                await self._persist_batch(self.batch_buffer)
                self.batch_buffer.clear()
                self.last_batch_time = current_time
                
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
    
    async def _persist_batch(self, batch: List[Dict[str, Any]]):
        """Persist a batch of data to storage"""
        if not self.db_client or not batch:
            return
        
        try:
            # Group by storage tier for optimized writes
            tier_groups = defaultdict(list)
            for item in batch:
                tier = item["data"]["_meta"]["storage_tier"]
                tier_groups[tier].append(item)
            
            # Persist each tier group
            for tier, items in tier_groups.items():
                await self._persist_tier_batch(tier, items)
                
            logger.debug(f"✅ Persisted batch of {len(batch)} items")
            
        except Exception as e:
            logger.error(f"Failed to persist batch: {e}")
    
    async def _persist_tier_batch(self, tier: str, items: List[Dict[str, Any]]):
        """Persist items to specific storage tier"""
        try:
            for item in items:
                data = item["data"]
                data_type = item["type"]
                
                # Choose appropriate table based on data type
                if data_type == "candle":
                    table_name = "live_candles_enhanced"
                elif data_type == "ticker": 
                    table_name = "live_tickers_enhanced"
                elif data_type == "orderbook":
                    table_name = "live_orderbooks_enhanced"
                else:
                    table_name = "live_market_data_enhanced"
                
                # Convert to DynamoDB format
                db_item = await self._convert_to_dynamodb_format(data, data_type)
                
                # Apply compression if needed
                if tier in [StorageTier.WARM.value, StorageTier.COLD.value]:
                    db_item = await self.compression_manager.compress_item(db_item)
                
                # Persist to database
                success = self.db_client.put_item(table_name, db_item)
                if not success:
                    logger.warning(f"Failed to persist {data_type} item")
                
        except Exception as e:
            logger.error(f"Failed to persist tier batch: {e}")
    
    async def _convert_to_dynamodb_format(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """Convert enriched data to DynamoDB format"""
        try:
            meta = data.get("_meta", {})
            
            # Base item structure
            db_item = {
                "PK": meta.get("partition_key", "UNKNOWN"),
                "SK": f"TIMESTAMP#{self._normalize_timestamp(data.get('timestamp', int(time.time() * 1000)))}",
                "data_type": data_type,
                "symbol": data.get("symbol", "UNKNOWN"),
                "timestamp": int(self._normalize_timestamp(data.get("timestamp", time.time() * 1000))),
                "storage_tier": meta.get("storage_tier", StorageTier.HOT.value),
                "quality_score": meta.get("quality_score", "unknown"),
                "ingested_at": meta.get("ingested_at"),
                "TTL": meta.get("ttl", int(time.time()) + (365 * 24 * 60 * 60))
            }
            
            # Add data-specific fields
            if data_type == "candle":
                db_item.update({
                    "open": Decimal(str(data.get("open", 0))),
                    "high": Decimal(str(data.get("high", 0))),
                    "low": Decimal(str(data.get("low", 0))),
                    "close": Decimal(str(data.get("close", 0))),
                    "volume": Decimal(str(data.get("volume", 0))),
                    "trades": int(data.get("trades", 0)),
                    "interval": data.get("interval", "1m"),
                    "is_closed": data.get("is_closed", True)
                })
                
                # Add computed fields
                computed = data.get("_computed", {})
                if computed:
                    db_item.update({
                        "price_range": Decimal(str(computed.get("price_range", 0))),
                        "price_change": Decimal(str(computed.get("price_change", 0))),
                        "price_change_percent": Decimal(str(computed.get("price_change_percent", 0))),
                        "volatility_estimate": Decimal(str(computed.get("volatility_estimate", 0))),
                        "is_bullish": computed.get("is_bullish", False)
                    })
            
            elif data_type == "ticker":
                db_item.update({
                    "price": Decimal(str(data.get("price", 0))),
                    "price_change": Decimal(str(data.get("price_change", 0))),
                    "price_change_percent": Decimal(str(data.get("price_change_percent", 0))),
                    "volume": Decimal(str(data.get("volume", 0))),
                    "high": Decimal(str(data.get("high", 0))),
                    "low": Decimal(str(data.get("low", 0)))
                })
            
            elif data_type == "orderbook":
                db_item.update({
                    "bids": json.dumps(data.get("bids", [])),
                    "asks": json.dumps(data.get("asks", [])),
                    "best_bid": Decimal(str(data.get("bids", [[0]])[0][0])) if data.get("bids") else Decimal('0'),
                    "best_ask": Decimal(str(data.get("asks", [[0]])[0][0])) if data.get("asks") else Decimal('0'),
                    "spread": Decimal('0')  # Calculate spread
                })
                
                # Calculate spread
                if data.get("bids") and data.get("asks"):
                    best_bid = Decimal(str(data["bids"][0][0]))
                    best_ask = Decimal(str(data["asks"][0][0]))
                    db_item["spread"] = best_ask - best_bid
            
            return db_item
            
        except Exception as e:
            logger.error(f"Failed to convert to DynamoDB format: {e}")
            raise
    
    def _normalize_timestamp(self, timestamp: Union[int, float, datetime]) -> int:
        """Normalize timestamp to integer milliseconds"""
        if isinstance(timestamp, datetime):
            return int(timestamp.timestamp() * 1000)
        elif isinstance(timestamp, (int, float)):
            # Assume it's already in milliseconds if > 1000000000000 (year 2001)
            if timestamp > 1000000000000:
                return int(timestamp)
            else:
                return int(timestamp * 1000)
        else:
            return int(time.time() * 1000)
    
    async def _analytics_loop(self):
        """Background analytics processing loop"""
        if not self.config.analytics_enabled:
            return
            
        logger.info("📊 Starting analytics processing loop")
        
        while self.is_running:
            try:
                await self.analytics_engine.process_analytics_window()
                await asyncio.sleep(60)  # Process every minute
                
            except Exception as e:
                logger.error(f"Analytics loop error: {e}")
                await asyncio.sleep(30)
    
    async def _archival_loop(self):
        """Background data archival and tier management loop"""
        logger.info("🗄️ Starting archival management loop")
        
        while self.is_running:
            try:
                await self.storage_manager.process_tier_transitions()
                await self.compression_manager.process_compression_candidates()
                await asyncio.sleep(3600)  # Process every hour
                
            except Exception as e:
                logger.error(f"Archival loop error: {e}")
                await asyncio.sleep(1800)
    
    async def _cleanup_loop(self):
        """Background cleanup and maintenance loop"""
        logger.info("🧹 Starting cleanup maintenance loop")
        
        while self.is_running:
            try:
                await self._cleanup_expired_data()
                await self._cleanup_memory_caches()
                await self._optimize_storage()
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(1800)
    
    async def _cleanup_expired_data(self):
        """Cleanup expired data based on TTL and retention policies"""
        # DynamoDB TTL handles most cleanup automatically
        # This handles any additional cleanup needed
        pass
    
    async def _cleanup_memory_caches(self):
        """Cleanup in-memory caches to prevent memory leaks"""
        try:
            # Cleanup deduplication cache
            current_time = time.time()
            cutoff_time = current_time - self.duplicate_window_seconds
            
            before_count = len(self.deduplication_cache)
            self.deduplication_cache = {
                h: t for h, t in self.deduplication_cache.items() 
                if t > cutoff_time
            }
            after_count = len(self.deduplication_cache)
            
            if before_count > after_count:
                logger.debug(f"Cleaned {before_count - after_count} expired cache entries")
            
        except Exception as e:
            logger.error(f"Memory cache cleanup failed: {e}")
    
    async def _optimize_storage(self):
        """Optimize storage performance and costs"""
        # Future implementation for storage optimization
        pass
    
    async def _update_ingestion_metrics(self):
        """Update real-time ingestion metrics"""
        try:
            current_time = time.time()
            time_delta = current_time - self.ingestion_metrics.last_update.timestamp()
            
            if time_delta > 0:
                # Calculate processing rate
                total_processed = self.ingestion_metrics.records_processed
                self.ingestion_metrics.processing_rate_per_sec = total_processed / max(time_delta, 1)
                
                # Calculate error rate
                total_records = self.ingestion_metrics.records_processed + self.ingestion_metrics.records_invalid
                if total_records > 0:
                    self.ingestion_metrics.error_rate_percent = (self.ingestion_metrics.records_invalid / total_records) * 100
                
                # Calculate compression ratio
                if self.ingestion_metrics.bytes_ingested > 0:
                    self.ingestion_metrics.compression_ratio = self.ingestion_metrics.bytes_compressed / self.ingestion_metrics.bytes_ingested
                
                self.ingestion_metrics.last_update = datetime.now(timezone.utc)
                
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
    
    def get_ingestion_metrics(self) -> Dict[str, Any]:
        """Get current ingestion performance metrics"""
        return {
            "records_processed": self.ingestion_metrics.records_processed,
            "records_valid": self.ingestion_metrics.records_valid, 
            "records_invalid": self.ingestion_metrics.records_invalid,
            "records_duplicate": self.ingestion_metrics.records_duplicate,
            "processing_rate_per_sec": round(self.ingestion_metrics.processing_rate_per_sec, 2),
            "error_rate_percent": round(self.ingestion_metrics.error_rate_percent, 2),
            "compression_ratio": round(self.ingestion_metrics.compression_ratio, 3),
            "queue_size": self.ingestion_queue.qsize(),
            "queue_capacity": self.config.max_queue_size,
            "batch_buffer_size": len(self.batch_buffer),
            "last_update": self.ingestion_metrics.last_update.isoformat()
        }
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get real-time analytics summary"""
        if not self.config.analytics_enabled:
            return {"analytics_enabled": False}
        
        return self.analytics_engine.get_summary()
    
    def get_storage_summary(self) -> Dict[str, Any]:
        """Get storage tier and compression summary"""
        return {
            "storage_tiers": self.storage_manager.get_tier_stats(),
            "compression": self.compression_manager.get_compression_stats(),
            "retention_policies": {
                "hot_hours": self.config.hot_retention_hours,
                "warm_days": self.config.warm_retention_days, 
                "cold_days": self.config.cold_retention_days,
                "archive_years": self.config.archive_retention_years
            }
        }
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics - FIXED for correct attributes"""
        try:
            return {
                "records_processed": self.ingestion_metrics.records_processed,
                "records_per_second": self.ingestion_metrics.records_per_second,
                "quality_distribution": self.ingestion_metrics.quality_distribution,
                "error_rate": self.ingestion_metrics.error_rate,
                "duplicate_rate": self.ingestion_metrics.duplicate_rate,
                "compression_ratio": self.ingestion_metrics.compression_ratio,
                "uptime_seconds": time.time() - self.ingestion_metrics.start_time
            }
        except Exception as e:
            logger.error(f"Performance metrics calculation failed: {e}")
            return {"error": str(e)}
    
    async def shutdown(self):
        """Graceful shutdown of persistence engine"""
        logger.info("🛑 Shutting down Enhanced Persistence Engine...")
        
        self.is_running = False
        self.shutdown_event.set()
        
        # Cancel background tasks
        tasks = [self.ingestion_task, self.analytics_task, self.archival_task, self.cleanup_task]
        for task in tasks:
            if task and not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*[t for t in tasks if t], return_exceptions=True)
        
        # Final batch processing
        if self.batch_buffer:
            try:
                await self._persist_batch(self.batch_buffer)
            except Exception as e:
                logger.warning(f"Final batch persistence failed: {e}")
        
        logger.info("✅ Enhanced Persistence Engine shutdown complete")


class DataQualityValidator:
    """Data quality validation engine"""
    
    def __init__(self):
        self.validation_rules = {
            "candle": self._validate_candle_data,
            "ticker": self._validate_ticker_data,
            "orderbook": self._validate_orderbook_data
        }
    
    async def initialize(self):
        """Initialize validator"""
        logger.info("🔍 Data Quality Validator initialized")
    
    async def validate_data(self, data: Dict[str, Any], data_type: str) -> DataQualityMetrics:
        """Validate data quality and return metrics"""
        start_time = time.time()
        metrics = DataQualityMetrics()
        
        try:
            # Get appropriate validation function
            validator = self.validation_rules.get(data_type, self._validate_generic_data)
            
            # Run validation
            metrics = await validator(data)
            
            # Calculate processing time
            metrics.processing_time_ms = (time.time() - start_time) * 1000
            
            return metrics
            
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            metrics.overall_quality = DataQuality.INVALID
            metrics.issues_detected.append(f"validation_error: {str(e)}")
            return metrics
    
    async def _validate_candle_data(self, data: Dict[str, Any]) -> DataQualityMetrics:
        """Validate candle data quality"""
        metrics = DataQualityMetrics()
        issues = []
        
        # Required fields check
        required_fields = ["symbol", "open", "high", "low", "close", "volume"]
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            issues.append(f"missing_fields: {missing_fields}")
        
        # Data range validation
        try:
            open_price = float(data.get("open", 0))
            high_price = float(data.get("high", 0))
            low_price = float(data.get("low", 0))
            close_price = float(data.get("close", 0))
            volume = float(data.get("volume", 0))
            
            # Price validation
            if not (0 < open_price < 1000000):
                issues.append(f"invalid_open_price: {open_price}")
            if not (0 < high_price < 1000000):
                issues.append(f"invalid_high_price: {high_price}")
            if not (0 < low_price < 1000000):
                issues.append(f"invalid_low_price: {low_price}")
            if not (0 < close_price < 1000000):
                issues.append(f"invalid_close_price: {close_price}")
            
            # OHLC relationship validation
            if not (low_price <= open_price <= high_price):
                issues.append("invalid_ohlc_relationship_open")
            if not (low_price <= close_price <= high_price):
                issues.append("invalid_ohlc_relationship_close")
            if high_price < low_price:
                issues.append("high_less_than_low")
            
            # Volume validation
            if volume < 0:
                issues.append(f"negative_volume: {volume}")
            
            # Extreme price movement check (>50% is suspicious)
            if open_price > 0:
                price_change_pct = abs(close_price - open_price) / open_price
                if price_change_pct > 0.5:
                    issues.append(f"extreme_price_movement: {price_change_pct:.2%}")
            
        except (ValueError, TypeError) as e:
            issues.append(f"numeric_conversion_error: {e}")
        
        # Calculate quality scores
        metrics.completeness_score = 1.0 - (len(missing_fields) / len(required_fields))
        metrics.accuracy_score = 1.0 - (len([i for i in issues if "invalid_" in i]) / 10)  # Max 10 accuracy issues
        metrics.consistency_score = 1.0 - (len([i for i in issues if "relationship" in i or "extreme" in i]) / 5)
        metrics.timeliness_score = 1.0  # Assume timely for real-time data
        
        # Overall quality assessment
        avg_score = (metrics.completeness_score + metrics.accuracy_score + 
                    metrics.consistency_score + metrics.timeliness_score) / 4
        
        if avg_score >= 0.95:
            metrics.overall_quality = DataQuality.EXCELLENT
        elif avg_score >= 0.85:
            metrics.overall_quality = DataQuality.GOOD
        elif avg_score >= 0.70:
            metrics.overall_quality = DataQuality.ACCEPTABLE
        elif avg_score >= 0.50:
            metrics.overall_quality = DataQuality.POOR
        else:
            metrics.overall_quality = DataQuality.INVALID
        
        metrics.issues_detected = issues
        return metrics
    
    async def _validate_ticker_data(self, data: Dict[str, Any]) -> DataQualityMetrics:
        """Validate ticker data quality"""
        metrics = DataQualityMetrics()
        issues = []
        
        # Basic validation for ticker data
        required_fields = ["symbol", "price"]
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            issues.append(f"missing_fields: {missing_fields}")
        
        try:
            price = float(data.get("price", 0))
            if not (0 < price < 1000000):
                issues.append(f"invalid_price: {price}")
        except (ValueError, TypeError):
            issues.append("price_conversion_error")
        
        # Simple quality assessment
        metrics.completeness_score = 1.0 - (len(missing_fields) / len(required_fields))
        metrics.accuracy_score = 1.0 - (len(issues) / 5)
        metrics.consistency_score = 1.0
        metrics.timeliness_score = 1.0
        
        avg_score = (metrics.completeness_score + metrics.accuracy_score + 
                    metrics.consistency_score + metrics.timeliness_score) / 4
        
        if avg_score >= 0.90:
            metrics.overall_quality = DataQuality.EXCELLENT
        elif avg_score >= 0.75:
            metrics.overall_quality = DataQuality.GOOD
        elif avg_score >= 0.60:
            metrics.overall_quality = DataQuality.ACCEPTABLE
        else:
            metrics.overall_quality = DataQuality.POOR
        
        metrics.issues_detected = issues
        return metrics
    
    async def _validate_orderbook_data(self, data: Dict[str, Any]) -> DataQualityMetrics:
        """Validate orderbook data quality"""
        metrics = DataQualityMetrics()
        issues = []
        
        # Orderbook validation
        if "bids" not in data or "asks" not in data:
            issues.append("missing_orderbook_sides")
        
        try:
            bids = data.get("bids", [])
            asks = data.get("asks", [])
            
            if not bids or not asks:
                issues.append("empty_orderbook_sides")
            
            # Validate bid/ask structure
            for i, bid in enumerate(bids[:5]):  # Check first 5
                if len(bid) < 2 or not isinstance(bid[0], (int, float, str)) or not isinstance(bid[1], (int, float, str)):
                    issues.append(f"invalid_bid_format: index_{i}")
            
            for i, ask in enumerate(asks[:5]):  # Check first 5
                if len(ask) < 2 or not isinstance(ask[0], (int, float, str)) or not isinstance(ask[1], (int, float, str)):
                    issues.append(f"invalid_ask_format: index_{i}")
            
            # Check spread sanity
            if bids and asks:
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
                if best_bid >= best_ask:
                    issues.append("invalid_spread_bid_gte_ask")
                    
        except Exception as e:
            issues.append(f"orderbook_validation_error: {e}")
        
        # Quality assessment
        metrics.completeness_score = 1.0 if not any("missing" in i for i in issues) else 0.5
        metrics.accuracy_score = 1.0 - (len([i for i in issues if "invalid" in i]) / 10)
        metrics.consistency_score = 1.0 if not any("spread" in i for i in issues) else 0.5
        metrics.timeliness_score = 1.0
        
        avg_score = (metrics.completeness_score + metrics.accuracy_score + 
                    metrics.consistency_score + metrics.timeliness_score) / 4
        
        if avg_score >= 0.90:
            metrics.overall_quality = DataQuality.EXCELLENT
        elif avg_score >= 0.75:
            metrics.overall_quality = DataQuality.GOOD  
        elif avg_score >= 0.60:
            metrics.overall_quality = DataQuality.ACCEPTABLE
        else:
            metrics.overall_quality = DataQuality.POOR
        
        metrics.issues_detected = issues
        return metrics
    
    async def _validate_generic_data(self, data: Dict[str, Any]) -> DataQualityMetrics:
        """Generic data validation"""
        metrics = DataQualityMetrics()
        
        if not data:
            metrics.overall_quality = DataQuality.INVALID
            metrics.issues_detected = ["empty_data"]
        else:
            metrics.overall_quality = DataQuality.ACCEPTABLE
            metrics.completeness_score = 0.8
            metrics.accuracy_score = 0.8
            metrics.consistency_score = 0.8
            metrics.timeliness_score = 1.0
        
        return metrics


class RealTimeAnalyticsEngine:
    """Real-time market data analytics engine"""
    
    def __init__(self):
        self.analytics_cache: Dict[str, List[Dict]] = defaultdict(list)
        self.cache_limit = 1000
        self.summary_stats: Dict[str, Dict] = {}
    
    async def initialize(self):
        """Initialize analytics engine"""
        logger.info("📊 Real-Time Analytics Engine initialized")
    
    async def process_candle(self, candle_data: Dict[str, Any]):
        """Process candle for real-time analytics"""
        try:
            symbol = candle_data.get("symbol", "UNKNOWN")
            
            # Add to analytics cache
            self.analytics_cache[symbol].append(candle_data)
            
            # Maintain cache size
            if len(self.analytics_cache[symbol]) > self.cache_limit:
                self.analytics_cache[symbol] = self.analytics_cache[symbol][-self.cache_limit:]
            
            # Update summary statistics
            await self._update_summary_stats(symbol)
            
        except Exception as e:
            logger.error(f"Analytics processing failed: {e}")
    
    async def _update_summary_stats(self, symbol: str):
        """Update summary statistics for symbol"""
        try:
            candles = self.analytics_cache[symbol]
            if not candles:
                return
            
            # Extract price data
            prices = [float(c.get("close", 0)) for c in candles[-100:]]  # Last 100 candles
            volumes = [float(c.get("volume", 0)) for c in candles[-100:]]
            
            if not prices:
                return
            
            # Calculate statistics
            self.summary_stats[symbol] = {
                "current_price": prices[-1],
                "price_change_24h": prices[-1] - prices[0] if len(prices) > 1 else 0,
                "price_change_percent": ((prices[-1] - prices[0]) / prices[0] * 100) if len(prices) > 1 and prices[0] > 0 else 0,
                "high_24h": max(prices),
                "low_24h": min(prices), 
                "avg_price": statistics.mean(prices),
                "price_volatility": statistics.stdev(prices) if len(prices) > 1 else 0,
                "total_volume": sum(volumes),
                "avg_volume": statistics.mean(volumes) if volumes else 0,
                "candle_count": len(candles),
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Summary stats update failed: {e}")
    
    async def process_analytics_window(self):
        """Process analytics for time window"""
        # Future implementation for windowed analytics
        pass
    
    def get_summary(self) -> Dict[str, Any]:
        """Get analytics summary"""
        return {
            "symbols_tracked": list(self.analytics_cache.keys()),
            "total_candles": sum(len(candles) for candles in self.analytics_cache.values()),
            "summary_stats": self.summary_stats,
            "last_update": datetime.now(timezone.utc).isoformat()
        }


class StorageTierManager:
    """Manages data storage tiers and lifecycle"""
    
    def __init__(self, config: PersistenceConfig):
        self.config = config
        self.db_client: Optional[DynamoDBClient] = None
    
    async def initialize(self, db_client: DynamoDBClient):
        """Initialize storage tier manager"""
        self.db_client = db_client
        logger.info("🗄️ Storage Tier Manager initialized")
    
    async def process_tier_transitions(self):
        """Process data tier transitions based on age"""
        # Future implementation for automated tier transitions
        pass
    
    def get_tier_stats(self) -> Dict[str, Any]:
        """Get storage tier statistics"""
        return {
            "hot_retention_hours": self.config.hot_retention_hours,
            "warm_retention_days": self.config.warm_retention_days,
            "cold_retention_days": self.config.cold_retention_days,
            "archive_retention_years": self.config.archive_retention_years
        }


class CompressionManager:
    """Manages data compression strategies"""
    
    def __init__(self, config: PersistenceConfig):
        self.config = config
        self.db_client: Optional[DynamoDBClient] = None
        self.compression_stats = {
            "items_compressed": 0,
            "bytes_saved": 0,
            "compression_ratio": 0.0
        }
    
    async def initialize(self, db_client: DynamoDBClient):
        """Initialize compression manager"""
        self.db_client = db_client
        logger.info("🗜️ Compression Manager initialized")
    
    async def compress_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Compress item data"""
        try:
            if self.config.compression_level == CompressionLevel.NONE:
                return item
            
            # Simple compression for now - could be enhanced
            compressed_item = item.copy()
            
            # Compress large text fields
            for key, value in item.items():
                if isinstance(value, str) and len(value) > 100:
                    compressed_data = gzip.compress(value.encode())
                    if len(compressed_data) < len(value):
                        compressed_item[f"{key}_compressed"] = compressed_data
                        compressed_item[f"{key}_is_compressed"] = True
                        del compressed_item[key]
                        self.compression_stats["bytes_saved"] += len(value) - len(compressed_data)
            
            self.compression_stats["items_compressed"] += 1
            return compressed_item
            
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return item
    
    async def process_compression_candidates(self):
        """Process items that are candidates for compression"""
        # Future implementation for batch compression
        pass
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics"""
        return self.compression_stats.copy()


class PerformanceMonitor:
    """Monitors persistence engine performance"""
    
    def __init__(self):
        self.metrics = {
            "start_time": time.time(),
            "total_operations": 0,
            "failed_operations": 0,
            "avg_response_time": 0.0
        }
    
    def record_operation(self, success: bool, response_time: float):
        """Record operation metrics"""
        self.metrics["total_operations"] += 1
        if not success:
            self.metrics["failed_operations"] += 1
        
        # Update average response time
        current_avg = self.metrics["avg_response_time"]
        total_ops = self.metrics["total_operations"]
        self.metrics["avg_response_time"] = ((current_avg * (total_ops - 1)) + response_time) / total_ops
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        uptime = time.time() - self.metrics["start_time"]
        total_ops = self.metrics["total_operations"]
        failed_ops = self.metrics["failed_operations"]
        
        return {
            "uptime_seconds": uptime,
            "total_operations": total_ops,
            "failed_operations": failed_ops,
            "success_rate": ((total_ops - failed_ops) / max(total_ops, 1)) * 100,
            "operations_per_second": total_ops / max(uptime, 1),
            "avg_response_time_ms": self.metrics["avg_response_time"] * 1000
        }
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        try:
            return {
                "records_processed": self.ingestion_metrics.records_processed,
                "records_per_second": self.ingestion_metrics.records_per_second,
                "quality_distribution": self.ingestion_metrics.quality_distribution,
                "error_rate": self.ingestion_metrics.error_rate,
                "duplicate_rate": self.ingestion_metrics.duplicate_rate,
                "compression_ratio": getattr(self.compression_manager, 'compression_ratio', 0.0),
                "storage_tiers": getattr(self.storage_manager, 'tier_stats', {}),
                "uptime_seconds": time.time() - getattr(self.ingestion_metrics, 'start_time', time.time())
            }
        except Exception as e:
            logger.error(f"Performance metrics calculation failed: {e}")
            return {"error": str(e)}


# Global enhanced persistence instance
_enhanced_persistence: Optional[EnhancedMarketPersistence] = None

async def get_enhanced_persistence(config: Optional[PersistenceConfig] = None) -> EnhancedMarketPersistence:
    """Get or create global enhanced persistence engine"""
    global _enhanced_persistence
    if _enhanced_persistence is None:
        _enhanced_persistence = EnhancedMarketPersistence(config)
        await _enhanced_persistence.initialize()
    return _enhanced_persistence

# Convenience functions for data ingestion
async def ingest_candle_data(candle_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest candle data with enhanced processing"""
    engine = await get_enhanced_persistence()
    return await engine.ingest_market_data(candle_data, "candle")

async def ingest_ticker_data(ticker_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest ticker data with enhanced processing"""
    engine = await get_enhanced_persistence()
    return await engine.ingest_market_data(ticker_data, "ticker")

async def ingest_orderbook_data(orderbook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest orderbook data with enhanced processing"""
    engine = await get_enhanced_persistence()
    return await engine.ingest_market_data(orderbook_data, "orderbook")

async def get_persistence_metrics() -> Dict[str, Any]:
    """Get comprehensive persistence metrics"""
    engine = await get_enhanced_persistence()
    return {
        "ingestion": engine.get_ingestion_metrics(),
        "analytics": engine.get_analytics_summary(),
        "storage": engine.get_storage_summary()
    }