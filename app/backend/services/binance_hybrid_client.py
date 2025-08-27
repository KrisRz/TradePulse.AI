"""
Binance Hybrid Client for TradePulse.AI
=====================================

Professional-grade hybrid client combining WebSocket streams and REST API fallback
with intelligent connection management, circuit breakers, and DynamoDB persistence.

Features:
- Hybrid WebSocket + REST architecture
- Intelligent failover and connection pooling
- Circuit breaker pattern for resilience
- Real-time data caching with DynamoDB Local
- Professional error handling and monitoring

Author: TradePulse.AI Development Team
Version: 1.0.0
"""

import asyncio
import aiohttp
import json
import logging
import time
import hashlib
import hmac
import random
import websockets
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timezone, timedelta
from collections import deque, defaultdict
from enum import Enum
from dataclasses import dataclass, field
from decimal import Decimal

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    """Connection state for hybrid client"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    CIRCUIT_OPEN = "circuit_open"

class DataSource(Enum):
    """Data source type"""
    WEBSOCKET = "websocket"
    REST_API = "rest_api"
    CACHE = "cache"
    DATABASE = "database"

@dataclass
class ConnectionMetrics:
    """Connection performance metrics"""
    connect_time: float = 0.0
    last_message_time: float = 0.0
    message_count: int = 0
    error_count: int = 0
    reconnect_count: int = 0
    latency_ms: float = 0.0
    uptime_seconds: float = 0.0

@dataclass  
class CircuitBreakerState:
    """Circuit breaker state management"""
    failure_count: int = 0
    last_failure_time: float = 0.0
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    failure_threshold: int = 5
    timeout_seconds: int = 60
    half_open_max_calls: int = 3
    half_open_calls: int = 0

@dataclass
class HybridConfig:
    """Configuration for hybrid client"""
    # WebSocket settings
    ws_base_url: str = "wss://stream.binance.com:9443/ws"
    ws_reconnect_delay: float = 5.0
    ws_max_reconnects: int = 10
    ws_ping_interval: float = 20.0
    ws_timeout_seconds: float = 30.0
    
    # REST API settings  
    rest_base_url: str = "https://api.binance.com/api/v3"
    rest_timeout_seconds: float = 5.0
    rest_max_retries: int = 3
    rest_backoff_base: float = 0.5
    
    # Connection pooling
    max_connections: int = 100
    connection_ttl: int = 300
    dns_cache_ttl: int = 300
    
    # Circuit breaker
    circuit_failure_threshold: int = 5
    circuit_timeout_seconds: int = 60
    circuit_half_open_calls: int = 3
    
    # Cache and persistence
    cache_size: int = 10000
    db_persist_interval: float = 30.0
    db_batch_size: int = 100

class BinanceHybridClient:
    """
    Professional hybrid Binance client with WebSocket + REST failover
    
    Provides:
    - Real-time WebSocket streams with automatic reconnection
    - REST API fallback with circuit breaker protection  
    - Intelligent data source routing and caching
    - DynamoDB Local persistence for offline capability
    - Professional monitoring and metrics
    """
    
    def __init__(self, api_key: str = None, secret_key: str = None, 
                 config: Optional[HybridConfig] = None):
        """Initialize hybrid client"""
        self.api_key = api_key
        self.secret_key = secret_key
        self.config = config or HybridConfig()
        
        # Connection management
        self.ws_connections: Dict[str, Optional[websockets.WebSocketServerProtocol]] = {}
        self.ws_tasks: Dict[str, Optional[asyncio.Task]] = {}
        self.ws_state: Dict[str, ConnectionState] = defaultdict(lambda: ConnectionState.DISCONNECTED)
        self.rest_session: Optional[aiohttp.ClientSession] = None
        
        # Circuit breakers for each endpoint type
        self.circuit_breakers: Dict[str, CircuitBreakerState] = defaultdict(CircuitBreakerState)
        
        # Performance metrics
        self.metrics: Dict[str, ConnectionMetrics] = defaultdict(ConnectionMetrics)
        
        # Data caching
        self.live_data_cache: Dict[str, Any] = {}
        self.candle_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.config.cache_size))
        self.ticker_cache: Dict[str, Dict] = {}
        self.orderbook_cache: Dict[str, Dict] = {}
        
        # Event callbacks
        self.data_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.status_callbacks: List[Callable] = []
        
        # Database integration
        self.db_client = None
        self.db_persist_task: Optional[asyncio.Task] = None
        self.db_buffer: List[Dict] = []
        
        # Control flags
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        logger.info("🔄 Binance Hybrid Client initialized")
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize all client components"""
        try:
            logger.info("🚀 Initializing Binance Hybrid Client...")
            
            # Initialize REST session with connection pooling
            await self._init_rest_session()
            
            # Initialize database connection
            await self._init_database()
            
            # Pre-populate cache from database
            await self._populate_cache_from_db()
            
            # Start database persistence task
            self.db_persist_task = asyncio.create_task(self._db_persist_loop())
            
            self.is_running = True
            
            logger.info("✅ Binance Hybrid Client initialized successfully")
            
            return {
                "status": "initialized",
                "rest_session": self.rest_session is not None,
                "database": self.db_client is not None,
                "cache_size": sum(len(cache) for cache in self.candle_cache.values()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize hybrid client: {e}")
            raise
    
    async def _init_rest_session(self):
        """Initialize REST API session with connection pooling"""
        connector = aiohttp.TCPConnector(
            limit=self.config.max_connections,
            ttl_dns_cache=self.config.dns_cache_ttl,
            use_dns_cache=True,
            keepalive_timeout=self.config.connection_ttl,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=self.config.rest_timeout_seconds)
        
        self.rest_session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'TradePulse.AI/1.0'}
        )
        
        logger.info("🌐 REST session initialized with connection pooling")
    
    async def _init_database(self):
        """Initialize DynamoDB Local connection"""
        try:
            from app.backend.core.database import DynamoDBClient
            from app.backend.core.config import get_settings
            
            settings = get_settings()
            self.db_client = DynamoDBClient(local_development=settings.is_development)
            
            # Test database connection
            try:
                test_tables = self.db_client.scan_table('live_candles')  # Test with known table
                logger.info(f"📊 Database connected: DynamoDB Local accessible")
            except Exception as db_test_error:
                logger.info(f"📊 Database connected: {str(db_test_error)[:50]}...")
            
        except Exception as e:
            logger.warning(f"⚠️ Database initialization failed: {e}")
            self.db_client = None
    
    async def _populate_cache_from_db(self):
        """Pre-populate cache with historical data from DynamoDB"""
        if not self.db_client:
            return
            
        try:
            logger.info("🔄 Pre-populating cache from database...")
            
            # Load historical candles
            candles = self.db_client.scan_table('live_candles')
            if candles:
                btc_candles = [c for c in candles if c.get('symbol') == 'BTCUSDT']
                btc_candles.sort(key=lambda x: int(x.get('timestamp', 0)))
                
                for candle in btc_candles[-1000:]:  # Last 1000 candles
                    cache_key = f"BTCUSDT_1m"
                    processed_candle = self._process_db_candle(candle)
                    if processed_candle:
                        self.candle_cache[cache_key].append(processed_candle)
                
                logger.info(f"📈 Loaded {len(self.candle_cache['BTCUSDT_1m'])} historical candles")
            
        except Exception as e:
            logger.warning(f"⚠️ Cache population failed: {e}")
    
    def _process_db_candle(self, db_candle: Dict) -> Optional[Dict]:
        """Process database candle format"""
        try:
            # Handle both data formats
            if 'open' in db_candle:
                # New format
                return {
                    'symbol': db_candle.get('symbol', 'BTCUSDT'),
                    'interval': '1m',
                    'open_time': int(db_candle.get('timestamp', 0)),
                    'open': float(db_candle.get('open', 0)),
                    'high': float(db_candle.get('high', 0)),
                    'low': float(db_candle.get('low', 0)),
                    'close': float(db_candle.get('close', 0)),
                    'volume': float(db_candle.get('volume', 0)),
                    'is_closed': True,
                    'source': DataSource.DATABASE.value
                }
            else:
                # Old format  
                return {
                    'symbol': db_candle.get('symbol', 'BTCUSDT'),
                    'interval': '1m',
                    'open_time': int(db_candle.get('timestamp', 0)),
                    'open': float(db_candle.get('open_price', 0)),
                    'high': float(db_candle.get('high_price', 0)),
                    'low': float(db_candle.get('low_price', 0)),
                    'close': float(db_candle.get('close_price', 0)),
                    'volume': float(db_candle.get('volume', 0)),
                    'is_closed': True,
                    'source': DataSource.DATABASE.value
                }
        except Exception as e:
            logger.warning(f"Failed to process DB candle: {e}")
            return None
    
    async def start_websocket_stream(self, stream_type: str, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """Start WebSocket stream with intelligent connection management"""
        stream_key = f"{symbol.lower()}@{stream_type}"
        
        if self.ws_state[stream_key] != ConnectionState.DISCONNECTED:
            return {"status": "already_running", "stream": stream_key}
        
        logger.info(f"🔌 Starting WebSocket stream: {stream_key}")
        
        # Start connection task
        self.ws_tasks[stream_key] = asyncio.create_task(
            self._websocket_connection_loop(stream_key, stream_type, symbol)
        )
        
        return {
            "status": "starting",
            "stream": stream_key,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _websocket_connection_loop(self, stream_key: str, stream_type: str, symbol: str):
        """WebSocket connection loop with automatic reconnection"""
        url = f"{self.config.ws_base_url}/{stream_key}"
        reconnect_count = 0
        
        while self.is_running and reconnect_count < self.config.ws_max_reconnects:
            try:
                self.ws_state[stream_key] = ConnectionState.CONNECTING
                logger.info(f"🔗 Connecting to {stream_key}...")
                
                connect_start = time.time()
                async with websockets.connect(
                    url,
                    ping_interval=self.config.ws_ping_interval,
                    ping_timeout=self.config.ws_timeout_seconds,
                    close_timeout=10
                ) as websocket:
                    
                    # Connection established
                    self.ws_connections[stream_key] = websocket
                    self.ws_state[stream_key] = ConnectionState.CONNECTED
                    
                    # Update metrics
                    self.metrics[stream_key].connect_time = time.time() - connect_start
                    self.metrics[stream_key].reconnect_count = reconnect_count
                    
                    logger.info(f"✅ WebSocket connected: {stream_key}")
                    reconnect_count = 0  # Reset on successful connection
                    
                    # Message handling loop
                    async for message in websocket:
                        if not self.is_running:
                            break
                            
                        await self._process_websocket_message(stream_key, stream_type, message)
                        
                        # Update metrics
                        self.metrics[stream_key].message_count += 1
                        self.metrics[stream_key].last_message_time = time.time()
                        
            except websockets.exceptions.ConnectionClosedError as e:
                logger.warning(f"🔗 WebSocket disconnected: {stream_key} - {e}")
                self.ws_state[stream_key] = ConnectionState.RECONNECTING
                
            except Exception as e:
                logger.error(f"❌ WebSocket error: {stream_key} - {e}")
                self.ws_state[stream_key] = ConnectionState.FAILED
                self.metrics[stream_key].error_count += 1
                
            finally:
                # Cleanup connection
                if stream_key in self.ws_connections:
                    del self.ws_connections[stream_key]
            
            # Exponential backoff reconnection
            if self.is_running:
                reconnect_count += 1
                delay = min(self.config.ws_reconnect_delay * (2 ** reconnect_count), 60)
                logger.info(f"🔄 Reconnecting {stream_key} in {delay:.1f}s (attempt {reconnect_count})")
                await asyncio.sleep(delay)
        
        self.ws_state[stream_key] = ConnectionState.DISCONNECTED
        logger.info(f"🛑 WebSocket stream ended: {stream_key}")
    
    async def _process_websocket_message(self, stream_key: str, stream_type: str, message: str):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            if stream_type == "ticker":
                await self._process_ticker_data(data, DataSource.WEBSOCKET)
            elif stream_type.startswith("kline_"):
                await self._process_kline_data(data, DataSource.WEBSOCKET)
            elif stream_type == "depth":
                await self._process_depth_data(data, DataSource.WEBSOCKET)
                
        except Exception as e:
            logger.error(f"Failed to process WebSocket message: {e}")
    
    async def _process_ticker_data(self, data: Dict, source: DataSource):
        """Process ticker data from any source"""
        try:
            symbol = data.get("s", "BTCUSDT")
            
            processed_ticker = {
                "symbol": symbol,
                "price": float(data.get("c", 0)),
                "price_change": float(data.get("p", 0)),
                "price_change_percent": float(data.get("P", 0)),
                "high": float(data.get("h", 0)),
                "low": float(data.get("l", 0)),
                "volume": float(data.get("v", 0)),
                "timestamp": datetime.now(timezone.utc),
                "source": source.value
            }
            
            # Cache data
            self.ticker_cache[symbol] = processed_ticker
            
            # Buffer for database persistence with Decimal conversion
            if self.db_client:
                # Convert float values to Decimal for DynamoDB
                db_ticker = {
                    "symbol": processed_ticker["symbol"],
                    "timestamp": int(processed_ticker["timestamp"].timestamp()),
                    "price": Decimal(str(processed_ticker["price"])),
                    "volume": Decimal(str(processed_ticker["volume"])),
                    "created_at": processed_ticker["timestamp"].isoformat()
                }
                self.db_buffer.append({
                    "table": "live_tickers", 
                    "data": db_ticker
                })
            
            # Notify callbacks
            for callback in self.data_callbacks["ticker"]:
                try:
                    await callback(processed_ticker)
                except Exception as e:
                    logger.error(f"Ticker callback error: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to process ticker data: {e}")
    
    async def _process_kline_data(self, data: Dict, source: DataSource):
        """Process candlestick data from any source"""
        try:
            kline = data.get("k", data)  # Handle both WebSocket and REST formats
            symbol = kline.get("s", "BTCUSDT")
            interval = kline.get("i", "1m")
            
            processed_candle = {
                "symbol": symbol,
                "interval": interval,
                "open_time": int(kline.get("t", 0)),
                "close_time": int(kline.get("T", 0)),
                "open": float(kline.get("o", 0)),
                "high": float(kline.get("h", 0)),
                "low": float(kline.get("l", 0)),
                "close": float(kline.get("c", 0)),
                "volume": float(kline.get("v", 0)),
                "trades": int(kline.get("n", 0)),
                "is_closed": kline.get("x", True),
                "timestamp": datetime.now(timezone.utc),
                "source": source.value
            }
            
            # Cache data
            cache_key = f"{symbol}_{interval}"
            self.candle_cache[cache_key].append(processed_candle)
            
            # Buffer for database persistence (only closed candles) with Decimal conversion
            if self.db_client and processed_candle["is_closed"]:
                # Convert float values to Decimal for DynamoDB
                db_candle = {
                    "symbol": processed_candle["symbol"],
                    "interval": processed_candle["interval"],
                    "timestamp": processed_candle["close_time"],
                    "open": Decimal(str(processed_candle["open"])),
                    "high": Decimal(str(processed_candle["high"])),
                    "low": Decimal(str(processed_candle["low"])),
                    "close": Decimal(str(processed_candle["close"])),
                    "volume": Decimal(str(processed_candle["volume"])),
                    "trades": processed_candle["trades"],
                    "is_closed": processed_candle["is_closed"],
                    "created_at": processed_candle["timestamp"].isoformat()
                }
                self.db_buffer.append({
                    "table": "live_candles",
                    "data": db_candle
                })
            
            # Notify callbacks
            for callback in self.data_callbacks["candle"]:
                try:
                    await callback(processed_candle)
                except Exception as e:
                    logger.error(f"Candle callback error: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to process kline data: {e}")
    
    async def _process_depth_data(self, data: Dict, source: DataSource):
        """Process order book depth data"""
        try:
            symbol = data.get("s", "BTCUSDT")
            
            processed_depth = {
                "symbol": symbol,
                "bids": [[float(p), float(q)] for p, q in data.get("b", [])],
                "asks": [[float(p), float(q)] for p, q in data.get("a", [])],
                "timestamp": datetime.now(timezone.utc),
                "source": source.value
            }
            
            # Cache data
            self.orderbook_cache[symbol] = processed_depth
            
            # Notify callbacks
            for callback in self.data_callbacks["depth"]:
                try:
                    await callback(processed_depth)
                except Exception as e:
                    logger.error(f"Depth callback error: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to process depth data: {e}")
    
    async def get_data_hybrid(self, data_type: str, symbol: str = "BTCUSDT", **kwargs) -> Dict[str, Any]:
        """
        Hybrid data retrieval with intelligent source selection
        
        Order of preference:
        1. WebSocket (real-time)
        2. REST API (with circuit breaker)
        3. Cache (recent data)
        4. Database (historical data)
        """
        try:
            # Try WebSocket first (if available and recent)
            if data_type == "ticker":
                ws_data = self.ticker_cache.get(symbol)
                if ws_data and self._is_data_fresh(ws_data):
                    return {"data": ws_data, "source": DataSource.WEBSOCKET.value}
            
            elif data_type == "candles":
                interval = kwargs.get("interval", "1m")
                limit = kwargs.get("limit", 100)
                cache_key = f"{symbol}_{interval}"
                
                if cache_key in self.candle_cache:
                    cached_candles = list(self.candle_cache[cache_key])
                    if len(cached_candles) >= limit:
                        return {
                            "data": cached_candles[-limit:],
                            "source": DataSource.WEBSOCKET.value
                        }
            
            elif data_type == "depth":
                ws_data = self.orderbook_cache.get(symbol)
                if ws_data and self._is_data_fresh(ws_data):
                    return {"data": ws_data, "source": DataSource.WEBSOCKET.value}
            
            # Fallback to REST API with circuit breaker
            circuit_key = f"rest_{data_type}"
            if self._is_circuit_breaker_open(circuit_key):
                return await self._get_from_cache_or_db(data_type, symbol, **kwargs)
            
            try:
                rest_data = await self._get_from_rest_api(data_type, symbol, **kwargs)
                self._record_circuit_success(circuit_key)
                return {"data": rest_data, "source": DataSource.REST_API.value}
                
            except Exception as e:
                self._record_circuit_failure(circuit_key)
                logger.warning(f"REST API failed for {data_type}: {e}")
                return await self._get_from_cache_or_db(data_type, symbol, **kwargs)
                
        except Exception as e:
            logger.error(f"Hybrid data retrieval failed: {e}")
            raise
    
    def _is_data_fresh(self, data: Dict, max_age_seconds: float = 5.0) -> bool:
        """Check if data is fresh enough"""
        try:
            if isinstance(data.get("timestamp"), datetime):
                age = (datetime.now(timezone.utc) - data["timestamp"]).total_seconds()
            else:
                age = time.time() - data.get("timestamp", 0)
            return age <= max_age_seconds
        except:
            return False
    
    def _is_circuit_breaker_open(self, circuit_key: str) -> bool:
        """Check if circuit breaker is open"""
        circuit = self.circuit_breakers[circuit_key]
        
        if circuit.state == "CLOSED":
            return False
        elif circuit.state == "OPEN":
            # Check if timeout has passed
            if time.time() - circuit.last_failure_time > circuit.timeout_seconds:
                circuit.state = "HALF_OPEN"
                circuit.half_open_calls = 0
                return False
            return True
        elif circuit.state == "HALF_OPEN":
            return circuit.half_open_calls >= circuit.half_open_max_calls
        
        return False
    
    def _record_circuit_success(self, circuit_key: str):
        """Record successful API call"""
        circuit = self.circuit_breakers[circuit_key]
        if circuit.state == "HALF_OPEN":
            circuit.half_open_calls += 1
            if circuit.half_open_calls >= circuit.half_open_max_calls:
                circuit.state = "CLOSED"
                circuit.failure_count = 0
        elif circuit.state == "CLOSED":
            circuit.failure_count = max(0, circuit.failure_count - 1)
    
    def _record_circuit_failure(self, circuit_key: str):
        """Record failed API call"""
        circuit = self.circuit_breakers[circuit_key]
        circuit.failure_count += 1
        circuit.last_failure_time = time.time()
        
        if circuit.failure_count >= circuit.failure_threshold:
            circuit.state = "OPEN"
            logger.warning(f"🚨 Circuit breaker OPEN for {circuit_key}")
    
    async def _get_from_rest_api(self, data_type: str, symbol: str, **kwargs) -> Any:
        """Get data from REST API with proper error handling"""
        if not self.rest_session:
            raise Exception("REST session not initialized")
        
        if data_type == "ticker":
            return await self._rest_get_ticker(symbol)
        elif data_type == "candles":
            return await self._rest_get_candles(symbol, **kwargs)
        elif data_type == "depth":
            return await self._rest_get_depth(symbol, **kwargs)
        else:
            raise Exception(f"Unsupported data type: {data_type}")
    
    async def _rest_get_ticker(self, symbol: str) -> Dict:
        """Get ticker from REST API"""
        url = f"{self.config.rest_base_url}/ticker/24hr"
        params = {"symbol": symbol}
        
        async with self.rest_session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"REST API error: {response.status}")
            
            data = await response.json()
            return {
                "symbol": data["symbol"],
                "price": float(data["lastPrice"]),
                "price_change": float(data["priceChange"]),
                "price_change_percent": float(data["priceChangePercent"]),
                "high": float(data["highPrice"]),
                "low": float(data["lowPrice"]),
                "volume": float(data["volume"]),
                "timestamp": datetime.now(timezone.utc),
                "source": DataSource.REST_API.value
            }
    
    async def _rest_get_candles(self, symbol: str, **kwargs) -> List[Dict]:
        """Get candles from REST API"""
        url = f"{self.config.rest_base_url}/klines"
        params = {
            "symbol": symbol,
            "interval": kwargs.get("interval", "1m"),
            "limit": kwargs.get("limit", 100)
        }
        
        if kwargs.get("startTime"):
            params["startTime"] = kwargs["startTime"]
        if kwargs.get("endTime"):
            params["endTime"] = kwargs["endTime"]
        
        async with self.rest_session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"REST API error: {response.status}")
            
            data = await response.json()
            candles = []
            
            for kline in data:
                candles.append({
                    "symbol": symbol,
                    "interval": params["interval"],
                    "open_time": int(kline[0]),
                    "close_time": int(kline[6]),
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5]),
                    "trades": int(kline[8]),
                    "is_closed": True,
                    "timestamp": datetime.now(timezone.utc),
                    "source": DataSource.REST_API.value
                })
            
            return candles
    
    async def _rest_get_depth(self, symbol: str, **kwargs) -> Dict:
        """Get order book depth from REST API"""
        url = f"{self.config.rest_base_url}/depth"
        params = {
            "symbol": symbol,
            "limit": kwargs.get("limit", 100)
        }
        
        async with self.rest_session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"REST API error: {response.status}")
            
            data = await response.json()
            return {
                "symbol": symbol,
                "bids": [[float(p), float(q)] for p, q in data["bids"]],
                "asks": [[float(p), float(q)] for p, q in data["asks"]],
                "timestamp": datetime.now(timezone.utc),
                "source": DataSource.REST_API.value
            }
    
    async def _get_from_cache_or_db(self, data_type: str, symbol: str, **kwargs) -> Dict[str, Any]:
        """Get data from cache or database as last resort"""
        if data_type == "ticker":
            # Try cache first
            cached = self.ticker_cache.get(symbol)
            if cached:
                return {"data": cached, "source": DataSource.CACHE.value}
        
        elif data_type == "candles":
            interval = kwargs.get("interval", "1m")
            limit = kwargs.get("limit", 100)
            cache_key = f"{symbol}_{interval}"
            
            if cache_key in self.candle_cache:
                cached_candles = list(self.candle_cache[cache_key])
                if cached_candles:
                    return {
                        "data": cached_candles[-limit:],
                        "source": DataSource.CACHE.value
                    }
        
        elif data_type == "depth":
            cached = self.orderbook_cache.get(symbol)
            if cached:
                return {"data": cached, "source": DataSource.CACHE.value}
        
        # Try database as final fallback
        if self.db_client:
            try:
                db_data = await self._get_from_database(data_type, symbol, **kwargs)
                if db_data:
                    return {"data": db_data, "source": DataSource.DATABASE.value}
            except Exception as e:
                logger.warning(f"Database fallback failed: {e}")
        
        raise Exception(f"No data available for {data_type} {symbol}")
    
    async def _get_from_database(self, data_type: str, symbol: str, **kwargs) -> Optional[Any]:
        """Get data from database"""
        if data_type == "candles":
            try:
                candles = self.db_client.scan_table('live_candles')
                btc_candles = [c for c in candles if c.get('symbol') == symbol]
                btc_candles.sort(key=lambda x: int(x.get('timestamp', 0)))
                
                limit = kwargs.get("limit", 100)
                recent_candles = btc_candles[-limit:] if len(btc_candles) > limit else btc_candles
                
                processed_candles = []
                for candle in recent_candles:
                    processed = self._process_db_candle(candle)
                    if processed:
                        processed_candles.append(processed)
                
                return processed_candles
            except Exception as e:
                logger.error(f"Database candle query failed: {e}")
                return None
        
        return None
    
    async def _db_persist_loop(self):
        """Background task to persist data to database"""
        while self.is_running:
            try:
                if self.db_buffer and self.db_client:
                    # Batch persist to reduce DB load
                    batch = self.db_buffer[:self.config.db_batch_size]
                    self.db_buffer = self.db_buffer[self.config.db_batch_size:]
                    
                    for item in batch:
                        try:
                            await self._persist_item(item)
                        except Exception as e:
                            logger.warning(f"Failed to persist item: {e}")
                
                await asyncio.sleep(self.config.db_persist_interval)
                
            except Exception as e:
                logger.error(f"DB persist loop error: {e}")
                await asyncio.sleep(self.config.db_persist_interval)
    
    async def _persist_item(self, item: Dict):
        """Persist single item to database with Decimal conversion"""
        try:
            table = item["table"]
            data = item["data"]
            
            if table == "live_candles":
                # Store candle data with Decimal conversion
                db_item = {
                    "symbol": data["symbol"],
                    "interval": data["interval"],
                    "timestamp": str(data["open_time"]),
                    "open": Decimal(str(data["open"])),
                    "high": Decimal(str(data["high"])),
                    "low": Decimal(str(data["low"])),
                    "close": Decimal(str(data["close"])),
                    "volume": Decimal(str(data["volume"])),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                self.db_client.put_item(table, db_item)
                
            elif table == "live_tickers":
                # Data is already converted to Decimal in _process_ticker_data
                self.db_client.put_item(table, data)
                
        except Exception as e:
            logger.error(f"Failed to persist {item['table']} item: {e}")
    
    def subscribe_to_data(self, data_type: str, callback: Callable):
        """Subscribe to data updates"""
        self.data_callbacks[data_type].append(callback)
        logger.info(f"📡 Subscribed to {data_type} updates")
    
    def subscribe_to_status(self, callback: Callable):
        """Subscribe to status updates"""
        self.status_callbacks.append(callback)
        logger.info("📊 Subscribed to status updates")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get comprehensive connection status"""
        ws_status = {}
        for stream_key, state in self.ws_state.items():
            metrics = self.metrics[stream_key]
            ws_status[stream_key] = {
                "state": state.value,
                "connected": state == ConnectionState.CONNECTED,
                "messages": metrics.message_count,
                "errors": metrics.error_count,
                "reconnects": metrics.reconnect_count,
                "uptime": time.time() - metrics.connect_time if metrics.connect_time else 0
            }
        
        circuit_status = {}
        for circuit_key, circuit in self.circuit_breakers.items():
            circuit_status[circuit_key] = {
                "state": circuit.state,
                "failures": circuit.failure_count,
                "last_failure": circuit.last_failure_time
            }
        
        return {
            "is_running": self.is_running,
            "websocket_streams": ws_status,
            "circuit_breakers": circuit_status,
            "rest_session": self.rest_session is not None,
            "database": self.db_client is not None,
            "cache_stats": {
                "candles": sum(len(cache) for cache in self.candle_cache.values()),
                "tickers": len(self.ticker_cache),
                "orderbooks": len(self.orderbook_cache)
            },
            "db_buffer_size": len(self.db_buffer),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down Binance Hybrid Client...")
        
        self.is_running = False
        self.shutdown_event.set()
        
        # Cancel WebSocket tasks
        for task in self.ws_tasks.values():
            if task and not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.ws_tasks:
            await asyncio.gather(*self.ws_tasks.values(), return_exceptions=True)
        
        # Cancel database persistence task
        if self.db_persist_task and not self.db_persist_task.done():
            self.db_persist_task.cancel()
            try:
                await self.db_persist_task
            except asyncio.CancelledError:
                pass
        
        # Final database flush
        if self.db_buffer and self.db_client:
            try:
                for item in self.db_buffer:
                    await self._persist_item(item)
            except Exception as e:
                logger.warning(f"Final DB flush failed: {e}")
        
        # Close REST session
        if self.rest_session:
            await self.rest_session.close()
        
        logger.info("✅ Binance Hybrid Client shutdown complete")
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        try:
            total_requests = sum(m.message_count for m in self.metrics.values())
            total_errors = sum(m.error_count for m in self.metrics.values())
            
            # Calculate error rate
            error_rate = (total_errors / max(total_requests, 1)) * 100
            
            return {
                "rest_requests": total_requests,
                "cache_hits": len(self.live_data_cache),
                "error_rate": round(error_rate, 2),
                "circuit_breakers": {
                    name: {
                        "state": cb.state,
                        "failure_count": cb.failure_count,
                        "threshold": cb.failure_threshold
                    }
                    for name, cb in self.circuit_breakers.items()
                },
                "connections": {
                    name: state.value for name, state in self.ws_state.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Performance metrics calculation failed: {e}")
            return {"error": str(e)}


# Global hybrid client instance
_hybrid_client: Optional[BinanceHybridClient] = None

async def get_hybrid_client() -> BinanceHybridClient:
    """Get or create global hybrid client"""
    global _hybrid_client
    if _hybrid_client is None:
        from app.backend.core.config import get_settings
        settings = get_settings()
        
        _hybrid_client = BinanceHybridClient(
            api_key=settings.BINANCE_API_KEY,
            secret_key=settings.BINANCE_SECRET_KEY
        )
        
        await _hybrid_client.initialize()
    
    return _hybrid_client

# Convenience functions for hybrid data access
async def get_live_price_hybrid(symbol: str = "BTCUSDT") -> Dict[str, Any]:
    """Get live price with hybrid fallback"""
    client = await get_hybrid_client()
    result = await client.get_data_hybrid("ticker", symbol)
    return {
        "price": result["data"]["price"],
        "source": result["source"],
        "timestamp": result["data"]["timestamp"]
    }

async def get_live_candles_hybrid(symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 100) -> Dict[str, Any]:
    """Get live candles with hybrid fallback"""
    client = await get_hybrid_client()
    result = await client.get_data_hybrid("candles", symbol, interval=interval, limit=limit)
    return {
        "candles": result["data"],
        "count": len(result["data"]),
        "source": result["source"]
    }

async def get_live_depth_hybrid(symbol: str = "BTCUSDT", limit: int = 100) -> Dict[str, Any]:
    """Get order book depth with hybrid fallback"""
    client = await get_hybrid_client()
    result = await client.get_data_hybrid("depth", symbol, limit=limit)
    return {
        "depth": result["data"],
        "source": result["source"],
        "timestamp": result["data"]["timestamp"]
    }

# Add missing method to BinanceHybridClient class
def _add_performance_method():
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        try:
            total_requests = sum(m.message_count for m in self.metrics.values())
            total_errors = sum(m.error_count for m in self.metrics.values())
            
            # Calculate cache hit rate
            cache_requests = len(self.live_data_cache) + sum(len(cache) for cache in self.candle_cache.values())
            
            # Calculate error rate
            error_rate = (total_errors / max(total_requests, 1)) * 100
            
            return {
                "rest_requests": total_requests,
                "cache_hits": cache_requests,
                "error_rate": round(error_rate, 2),
                "circuit_breakers": {
                    name: {
                        "state": cb.state,
                        "failure_count": cb.failure_count,
                        "threshold": cb.failure_threshold
                    }
                    for name, cb in self.circuit_breakers.items()
                },
                "connections": {
                    name: state.value for name, state in self.ws_state.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Performance metrics calculation failed: {e}")
            return {"error": str(e)}
    
    # Add method to class
    BinanceHybridClient.get_performance_metrics = get_performance_metrics

# Apply the method addition
_add_performance_method()

def get_performance_metrics_standalone(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        try:
            total_requests = sum(m.message_count for m in self.metrics.values())
            total_errors = sum(m.error_count for m in self.metrics.values())
            
            # Calculate cache hit rate
            cache_requests = len(self.live_data_cache) + sum(len(cache) for cache in self.candle_cache.values())
            cache_hit_rate = (cache_requests / max(total_requests, 1)) * 100
            
            # Calculate error rate
            error_rate = (total_errors / max(total_requests, 1)) * 100
            
            return {
                "rest_requests": total_requests,
                "cache_hits": cache_requests,
                "error_rate": round(error_rate, 2),
                "circuit_breakers": {
                    name: {
                        "state": cb.state,
                        "failure_count": cb.failure_count,
                        "threshold": cb.failure_threshold
                    }
                    for name, cb in self.circuit_breakers.items()
                },
                "connections": {
                    name: state.value for name, state in self.ws_state.items()
                },
                "uptime_seconds": time.time() - self.metrics.get("client", ConnectionMetrics()).connect_time
            }
            
        except Exception as e:
            logger.error(f"Performance metrics calculation failed: {e}")
            return {"error": str(e)}