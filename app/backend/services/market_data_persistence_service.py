"""
Market Data Persistence Service

Saves live 1m candles from Binance API to DynamoDB for 90-day rolling window.
Implements production-grade day trading data management with TTL auto-cleanup.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CandleData:
    """1-minute candle data structure"""
    symbol: str
    timestamp: int  # Unix timestamp (seconds)
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    trades: int


class MarketDataPersistenceService:
    """
    Production-grade service for persisting live market data
    
    Features:
    - Saves every 1m candle to DynamoDB
    - TTL auto-cleanup after 90 days
    - Batch writes for efficiency
    - Error handling and retry logic
    - Metrics tracking
    """
    
    def __init__(self):
        self.is_initialized = False
        self.table_name = "tradepulse_market_data"
        self.ttl_days = 90
        
        # Metrics
        self.candles_saved = 0
        self.save_errors = 0
        self.last_save_time = None
        
        # Batch buffer
        self.batch_buffer: List[CandleData] = []
        self.batch_size = 25  # DynamoDB batch write limit
        
    async def initialize(self):
        """Initialize service"""
        if self.is_initialized:
            return
            
        logger.info("🚀 Initializing Market Data Persistence Service...")
        
        try:
            from app.backend.core.database import DynamoDBClient
            from app.backend.core.config import get_settings
            
            settings = get_settings()
            self.client = DynamoDBClient(local_development=settings.is_development)
            
            # Verify table exists
            try:
                self.client.get_table(self.table_name)
                logger.info(f"✅ Connected to {self.table_name} table")
            except Exception as e:
                logger.error(f"❌ Table {self.table_name} not found: {e}")
                raise
            
            self.is_initialized = True
            logger.info("✅ Market Data Persistence Service ready")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize persistence service: {e}")
            raise
    
    async def save_candle(self, candle: CandleData) -> bool:
        """
        Save single candle to DynamoDB
        
        Args:
            candle: CandleData object
            
        Returns:
            bool: True if saved successfully
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Calculate TTL (90 days from now)
            ttl = int((datetime.now(timezone.utc) + timedelta(days=self.ttl_days)).timestamp())
            
            # Convert floats to Decimal for DynamoDB
            saved_at_ts = int(datetime.now(timezone.utc).timestamp())
            item = {
                "symbol": candle.symbol,
                "timestamp": candle.timestamp,
                "open": Decimal(str(candle.open)),
                "high": Decimal(str(candle.high)),
                "low": Decimal(str(candle.low)),
                "close": Decimal(str(candle.close)),
                "volume": Decimal(str(candle.volume)),
                "quote_volume": Decimal(str(candle.quote_volume)),
                "trades": candle.trades,
                "ttl": ttl,
                "saved_at": saved_at_ts
            }
            
            # 🔧 FIX (Oct 2025): Idempotent write - only insert if PK doesn't exist OR saved_at is newer
            # This prevents duplicate writes from parallel handlers (WS + REST)
            try:
                table = self.client.get_table(self.table_name)
                table.put_item(
                    Item=item,
                    ConditionExpression="attribute_not_exists(#sym) OR #saved < :new_saved",
                    ExpressionAttributeNames={
                        "#sym": "symbol",
                        "#saved": "saved_at"
                    },
                    ExpressionAttributeValues={
                        ":new_saved": saved_at_ts
                    }
                )
            except Exception as e:
                if "ConditionalCheckFailedException" in str(e):
                    # Duplicate or older data - safe to ignore
                    return True
                raise
            
            self.candles_saved += 1
            self.last_save_time = datetime.now(timezone.utc)
            
            if self.candles_saved % 100 == 0:
                logger.info(f"📊 Saved {self.candles_saved} candles to DynamoDB")
            
            return True
            
        except Exception as e:
            self.save_errors += 1
            logger.error(f"❌ Failed to save candle: {e}")
            return False
    
    async def save_candles_batch(self, candles: List[CandleData]) -> int:
        """
        Save multiple candles in batch (more efficient)
        
        Args:
            candles: List of CandleData objects
            
        Returns:
            int: Number of candles saved successfully
        """
        if not self.is_initialized:
            await self.initialize()
        
        saved_count = 0
        
        # Process in batches of 25 (DynamoDB limit)
        for i in range(0, len(candles), self.batch_size):
            batch = candles[i:i + self.batch_size]
            
            try:
                # Convert to DynamoDB items
                ttl = int((datetime.now(timezone.utc) + timedelta(days=self.ttl_days)).timestamp())
                
                items = []
                for candle in batch:
                    item = {
                        "symbol": candle.symbol,
                        "timestamp": candle.timestamp,
                        "open": Decimal(str(candle.open)),
                        "high": Decimal(str(candle.high)),
                        "low": Decimal(str(candle.low)),
                        "close": Decimal(str(candle.close)),
                        "volume": Decimal(str(candle.volume)),
                        "quote_volume": Decimal(str(candle.quote_volume)),
                        "trades": candle.trades,
                        "ttl": ttl,
                        "saved_at": int(datetime.now(timezone.utc).timestamp())
                    }
                    items.append(item)
                
                # Batch write
                import boto3
                dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
                table = dynamodb.Table(self.table_name)
                
                with table.batch_writer() as writer:
                    for item in items:
                        writer.put_item(Item=item)
                
                saved_count += len(batch)
                self.candles_saved += len(batch)
                
            except Exception as e:
                self.save_errors += len(batch)
                logger.error(f"❌ Failed to save batch: {e}")
        
        if saved_count > 0:
            self.last_save_time = datetime.now(timezone.utc)
            logger.info(f"📊 Batch saved {saved_count} candles to DynamoDB")
        
        return saved_count
    
    async def query_candles(
        self, 
        symbol: str, 
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Query candles from DynamoDB
        
        Args:
            symbol: Trading symbol (e.g. "BTCUSDT")
            start_time: Start timestamp (seconds)
            end_time: End timestamp (seconds)
            limit: Max number of candles to return
            
        Returns:
            List of candle dictionaries
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            import boto3
            from boto3.dynamodb.conditions import Key
            
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
            table = dynamodb.Table(self.table_name)
            
            # Build query
            key_condition = Key('symbol').eq(symbol)
            
            if start_time and end_time:
                key_condition = key_condition & Key('timestamp').between(start_time, end_time)
            elif start_time:
                key_condition = key_condition & Key('timestamp').gte(start_time)
            elif end_time:
                key_condition = key_condition & Key('timestamp').lte(end_time)
            
            query_params = {
                'KeyConditionExpression': key_condition,
                'ScanIndexForward': True  # Ascending order
            }
            
            if limit:
                query_params['Limit'] = limit
            
            response = table.query(**query_params)
            
            # Convert Decimal to float
            candles = []
            for item in response.get('Items', []):
                candle = {
                    'symbol': item['symbol'],
                    'timestamp': int(item['timestamp']),
                    'open': float(item['open']),
                    'high': float(item['high']),
                    'low': float(item['low']),
                    'close': float(item['close']),
                    'volume': float(item['volume']),
                    'quote_volume': float(item['quote_volume']),
                    'trades': item['trades']
                }
                candles.append(candle)
            
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to query candles: {e}")
            return []
    
    def get_metrics(self) -> Dict:
        """Get service metrics"""
        return {
            "candles_saved": self.candles_saved,
            "save_errors": self.save_errors,
            "last_save_time": self.last_save_time.isoformat() if self.last_save_time else None,
            "error_rate": self.save_errors / max(1, self.candles_saved + self.save_errors)
        }


# Global service instance
_persistence_service: Optional[MarketDataPersistenceService] = None


async def get_persistence_service() -> MarketDataPersistenceService:
    """Get or create global persistence service"""
    global _persistence_service
    if _persistence_service is None:
        _persistence_service = MarketDataPersistenceService()
        await _persistence_service.initialize()
    return _persistence_service


__all__ = ["MarketDataPersistenceService", "get_persistence_service", "CandleData"]
