"""
Live Market Data Service for TradePulse.AI
Real-time market data processing with WebSocket and REST fallback
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timezone
import websockets
from collections import deque
from .binance_hybrid_client import get_hybrid_client
from app.backend.core.config import get_settings
from app.backend.core.runtime_config import runtime_config_store
from .websocket_deduplicator import (
    get_message_deduplicator, get_subscription_manager,
    process_ticker_message, process_kline_message,
    init_websocket_deduplication
)
from ..config.trading_symbols import normalize_symbol, get_binance_streams, get_canonical_symbol
# from app.backend.core.connection_manager import get_bitcoin_price, get_bitcoin_klines  # Removed circular import

logger = logging.getLogger(__name__)

class LiveMarketDataService:
	"""Professional live market data service with WebSocket streams"""
	
	def __init__(self):
		self.is_running = False
		self.connections = {}
		self.tasks = []
		
		# Deduplication system
		self.deduplicator = get_message_deduplicator()
		self.subscription_manager = get_subscription_manager()
		
		# Single subscription tracking to prevent duplicates
		self._subscriptions = set()
		self._subscription_lock = asyncio.Lock()
		
		# Current data cache
		self.current_ticker = None
		self.current_candles = {}
		self.current_orderbook = None
		# Recent closed candle history (increased for enterprise LSTM)
		self.candle_history = {}
		self.max_history = 15000  # 3x more for enterprise accuracy (10+ hours)
		
		# Callbacks for real-time updates
		self.ticker_callbacks = []
		self.candle_callbacks = []
		self.orderbook_callbacks = []
		
		# WebSocket URLs
		self.ws_base_url = "wss://stream.binance.com:9443/ws"
	
	async def _populate_cache_from_db(self):
		"""Pre-populate cache with recent DB data for LSTM performance"""
		try:
			from app.backend.core.database import DynamoDBClient
			from app.backend.core.config import get_settings
			
			logger.info("🔄 Pre-populating cache from DB for LSTM...")
			
			# Use correct table name based on environment
			settings = get_settings()
			if settings.is_development:
				table_name = 'live_candles'
			else:
				table_name = f'tradepulse-live_candles-{settings.ENVIRONMENT}'
			
			# Get recent candles from DB
			db_client = DynamoDBClient(local_development=settings.is_development)
			candles = db_client.scan_table(table_name)
			
			if not candles:
				logger.warning(f"No candles in DB table '{table_name}' - cache will populate from live stream")
				return
				
			logger.info(f"📊 Found {len(candles)} total candles in DB")
			
			# Filter and sort recent 1m candles (handle both data formats)
			btc_1m_candles = []
			for c in candles:
				# Check if it's BTCUSDT and has interval (new format) or is assumed 1m (old format)
				if c.get('symbol') == 'BTCUSDT':
					# New format has explicit interval
					if c.get('interval') == '1m':
						btc_1m_candles.append(c)
					# Old format without interval - assume it's 1m if timestamp looks right
					elif not c.get('interval') and c.get('timestamp'):
						btc_1m_candles.append(c)
			
			if not btc_1m_candles:
				logger.warning("No BTCUSDT 1m candles found in DB")
				return
			
			# Sort by timestamp (most recent last)
			btc_1m_candles.sort(key=lambda x: int(x.get('timestamp', 0)))
			
			# Take last 800 candles for enterprise LSTM (target: 800+)
			recent_candles = btc_1m_candles[-800:] if len(btc_1m_candles) > 800 else btc_1m_candles
			
			if recent_candles:
				# Initialize cache
				if '1m' not in self.candle_history:
					self.candle_history['1m'] = deque(maxlen=self.max_history)
				
				# Convert DB format to cache format (handle both formats)
				loaded_count = 0
				for db_candle in recent_candles:
					try:
						# Handle both data formats
						if 'open' in db_candle:
							# New format: open, high, low, close
							open_price = float(db_candle.get("open", 0))
							high_price = float(db_candle.get("high", 0))
							low_price = float(db_candle.get("low", 0))
							close_price = float(db_candle.get("close", 0))
						else:
							# Old format: open_price, high_price, low_price, close_price
							open_price = float(db_candle.get("open_price", 0))
							high_price = float(db_candle.get("high_price", 0))
							low_price = float(db_candle.get("low_price", 0))
							close_price = float(db_candle.get("close_price", 0))
						
						cache_candle = {
							"symbol": db_candle.get("symbol", "BTCUSDT"),
							"interval": "1m", 
							"open": open_price,
							"high": high_price,
							"low": low_price,
							"close": close_price,
							"volume": float(db_candle.get("volume", 0)),
							"is_closed": True,
							"timestamp": db_candle.get("timestamp", "")
						}
						self.candle_history['1m'].append(cache_candle)
						loaded_count += 1
					except Exception as e:
						logger.warning(f"Skipped malformed candle: {e}")
						continue
				
				logger.info(f"✅ Cache populated: {loaded_count} candles from DB (target: 800+)")
				if loaded_count >= 800:
					logger.info("🎯 TARGET ACHIEVED: 800+ candles loaded for LSTM models!")
				else:
					logger.warning(f"⚠️ Only {loaded_count} candles loaded, target was 800+")
			else:
				logger.warning("No recent 1m candles found in DB")
				
		except Exception as e:
			logger.error(f"Failed to populate cache from DB: {e}")
			# Continue without cache - will populate from live stream
	
	async def _backfill_candles_if_needed(self, symbol: str = "BTCUSDT", interval: str = "1m", target: int = 800):
		"""Backfill candles if we have less than target amount"""
		try:
			from app.backend.core.database import DynamoDBClient
			from app.backend.core.config import get_settings
			from app.backend.utils.dynamodb_key_normalizer import safe_put_item
			import requests
			
			settings = get_settings()
			table_name = 'live_candles' if settings.is_development else f'tradepulse-live_candles-{settings.ENVIRONMENT}'
			
			# Count existing candles
			db_client = DynamoDBClient(local_development=settings.is_development)
			candles = db_client.scan_table(table_name)
			
			# Filter for our symbol and interval
			existing_count = len([c for c in candles if c.get('symbol') == symbol and c.get('interval') == interval])
			
			if existing_count >= target:
				logger.info(f"📊 PIPELINE DEBUG: Sufficient candles: {existing_count}/{target}")
				return
			
			need = target - existing_count
			logger.info(f"📊 PIPELINE DEBUG: Need to backfill {need} candles ({existing_count}/{target})")
			
			# Get historical data from Binance REST API
			url = "https://api.binance.com/api/v3/klines"
			params = {
				'symbol': symbol,
				'interval': interval,
				'limit': min(need, 1000)  # Binance limit
			}
			
			logger.info(f"🔄 PIPELINE DEBUG: Fetching {params['limit']} historical candles from Binance...")
			response = requests.get(url, params=params, timeout=10)
			
			if response.status_code == 200:
				klines = response.json()
				
				# Save to database
				table = db_client.get_table(table_name)
				saved_count = 0
				
				for kline in klines:
					try:
						timestamp = int(kline[0])
						
						# Match existing table schema: symbol (S) + timestamp (S)
						candle_data = {
							'symbol': str(symbol),  # String key
							'timestamp': str(timestamp),  # String key to match schema
							'interval': str(interval),
							'open': str(kline[1]),
							'high': str(kline[2]),
							'low': str(kline[3]),
							'close': str(kline[4]),
							'volume': str(kline[5])
						}
						
						# Only save if not already exists - use safe wrapper
						try:
							success = safe_put_item(
								table, 
								candle_data, 
								table_name,
								ConditionExpression='attribute_not_exists(symbol) AND attribute_not_exists(#ts)',
								ExpressionAttributeNames={'#ts': 'timestamp'}
							)
							if success:
								saved_count += 1
						except:
							# Item already exists or other error, skip
							pass
							
					except Exception as e:
						logger.debug(f"Failed to save candle {kline[0]}: {e}")
				
				logger.info(f"✅ PIPELINE DEBUG: Backfilled {saved_count} new candles")
			else:
				logger.warning(f"⚠️ PIPELINE DEBUG: Backfill failed - HTTP {response.status_code}")
				
		except Exception as e:
			logger.warning(f"⚠️ PIPELINE DEBUG: Candles backfill failed: {e}")
			# Continue without backfill - system can operate with available data
	
	async def _ensure_single_subscription(self, stream_name: str) -> bool:
		"""Ensure we only have one subscription per stream"""
		async with self._subscription_lock:
			if stream_name in self._subscriptions:
				logger.debug(f"🔄 PIPELINE DEBUG: Already subscribed to {stream_name}, skipping duplicate")
				return False
			self._subscriptions.add(stream_name)
			logger.info(f"📊 PIPELINE DEBUG: Added subscription for {stream_name}")
			return True
		
	async def initialize(self):
		"""Initialize method - alias for start() for compatibility"""
		logger.info("🔄 PIPELINE DEBUG: Market Data Service - initialize() called (alias for start())")
		return await self.start()
	
	async def start(self):
		"""Start all live data connections"""
		if self.is_running:
			logger.info("🔄 PIPELINE DEBUG: Market Data Service already running, skipping...")
			return
			
		logger.info("🚀 Starting live market data service...")
		logger.info("📊 PIPELINE DEBUG: Market Data Service - Starting initialization sequence")
		logger.info(f"🎯 PIPELINE DEBUG: Market Data Service - Component: Live Market Data Service v1.0.0")
		logger.info(f"🎯 PIPELINE DEBUG: Market Data Service - Purpose: Real-time market data streaming")
		
		self.is_running = True
		
		try:
			# Pre-populate cache with recent DB data for LSTM
			logger.info("🗄️ PIPELINE DEBUG: Market Data Service - Pre-populating cache from database...")
			await self._populate_cache_from_db()
			logger.info("✅ PIPELINE DEBUG: Market Data Service - Cache populated from database")
			
			# Check if we need to backfill more candles
			logger.info("📊 PIPELINE DEBUG: Market Data Service - Checking candles backfill need...")
			await self._backfill_candles_if_needed()
			logger.info("✅ PIPELINE DEBUG: Market Data Service - Backfill check completed")
			
			# Start ticker stream
			logger.info("📈 PIPELINE DEBUG: Market Data Service - Starting ticker stream...")
			ticker_task = asyncio.create_task(self._ticker_stream())
			self.tasks.append(ticker_task)
			logger.info("✅ PIPELINE DEBUG: Market Data Service - Ticker stream started")
			
			# Start 1m candle stream
			candle_task = asyncio.create_task(self._candle_stream("1m"))
			self.tasks.append(candle_task)
			
			logger.info("✅ Live market data service started")
			
		except Exception as e:
			logger.error(f"Failed to start live market data service: {e}")
			await self.stop()
			raise
	
	async def stop(self):
		"""Stop all live data connections"""
		if not self.is_running:
			return
			
		logger.info("🛑 Stopping live market data service...")
		self.is_running = False
		
		# Cancel all tasks
		for task in self.tasks:
			if not task.done():
				task.cancel()
				
		# Wait for tasks to complete
		if self.tasks:
			await asyncio.gather(*self.tasks, return_exceptions=True)
			
		self.tasks.clear()
		self.connections.clear()
		
		logger.info("✅ Live market data service stopped")
	
	async def _ticker_stream(self):
		"""WebSocket stream for 24hr ticker updates with deduplication"""
		canonical_symbol = get_canonical_symbol()
		streams = get_binance_streams()
		stream_name = streams["ticker"]
		stream_key = f"ticker_{canonical_symbol}"
		
		# Check if already subscribed
		if self.subscription_manager.is_subscribed(stream_key):
			logger.info(f"🔄 Already subscribed to {stream_key}, skipping duplicate")
			return
			
		url = f"{self.ws_base_url}/{stream_name}"
		reconnect_count = 0
		max_reconnects = 10
		
		while self.is_running and reconnect_count < max_reconnects:
			websocket = None
			try:
				logger.info(f"📡 Connecting to ticker stream: {stream_name} (attempt {reconnect_count + 1})")
				
				# Create WebSocket with proper session management
				websocket = await websockets.connect(
					url,
					ping_interval=20,
					ping_timeout=10,
					close_timeout=10
				)
				self.connections["ticker"] = websocket
				
				# Register subscription
				current_task = asyncio.current_task()
				self.subscription_manager.add_subscription(stream_key, current_task, canonical_symbol, "ticker")
				
				logger.info("✅ Ticker stream connected")
				reconnect_count = 0  # Reset on successful connection
				
				async for message in websocket:
					if not self.is_running:
						break
					try:
						data = json.loads(message)
						
						# Process with deduplication
						def process_ticker_data(ticker_data):
							# Normalize symbol from WebSocket data
							normalized_symbol = normalize_symbol(ticker_data["s"])
							
							# Update current ticker
							self.current_ticker = {
								"symbol": normalized_symbol,
								"price": float(ticker_data["c"]),
								"price_change": float(ticker_data["P"]),
								"price_change_percent": float(ticker_data["P"]),
								"high": float(ticker_data["h"]),
								"low": float(ticker_data["l"]),
								"volume": float(ticker_data["v"]),
								"timestamp": time.time()  # Use numeric timestamp for compatibility
							}
							
							# Notify callbacks
							for callback in self.ticker_callbacks:
								try:
									asyncio.create_task(callback(self.current_ticker))
								except Exception as e:
									logger.error(f"Ticker callback error: {e}")
						
						# Use deduplication
						if process_ticker_message(data, process_ticker_data):
							logger.debug(f"📊 Processed ticker update: ${data.get('c', 'N/A')}")
						
					except json.JSONDecodeError as e:
						logger.error(f"Failed to parse ticker message: {e}")
						
			except websockets.exceptions.ConnectionClosed as e:
				logger.warning(f"🔗 WebSocket connection closed: {e}")
				reconnect_count += 1
			except websockets.exceptions.WebSocketException as e:
				logger.error(f"❌ WebSocket error: {e}")
				reconnect_count += 1
			except Exception as e:
				logger.error(f"❌ Ticker stream error: {e}")
				reconnect_count += 1
			finally:
				# Proper cleanup
				if websocket:
					try:
						if hasattr(websocket, 'closed') and not websocket.closed:
							await websocket.close()
						elif hasattr(websocket, 'close'):
							await websocket.close()
					except:
						pass
				if "ticker" in self.connections:
					del self.connections["ticker"]
				
				# Remove subscription
				self.subscription_manager.remove_subscription(stream_key)
			
			# Exponential backoff reconnection
			if self.is_running and reconnect_count < max_reconnects:
				delay = min(5 * (2 ** min(reconnect_count, 3)), 30)
				logger.info(f"🔄 Reconnecting ticker stream in {delay:.1f}s...")
				await asyncio.sleep(delay)
		
		if reconnect_count >= max_reconnects:
			logger.error(f"❌ Ticker stream failed after {max_reconnects} attempts")
		logger.info("🛑 Ticker stream ended")
	
	async def _candle_stream(self, interval: str = "1m"):
		"""WebSocket stream for candlestick updates with symbol normalization"""
		streams = get_binance_streams()
		stream_name = streams[f"kline_{interval}"] if f"kline_{interval}" in streams else f"{streams['stream_symbol']}@kline_{interval}"
		
		# Check for duplicate subscription
		if not await self._ensure_single_subscription(f"kline_{interval}"):
			logger.info(f"📊 PIPELINE DEBUG: Skipping duplicate kline subscription for {interval}")
			return
		
		url = f"{self.ws_base_url}/{stream_name}"
		
		reconnect_count = 0
		max_reconnects = 10
		
		while self.is_running and reconnect_count < max_reconnects:
			websocket = None
			try:
				logger.info(f"📡 Connecting to candle stream: {stream_name} (attempt {reconnect_count + 1})")
				
				# Create WebSocket with proper session management
				websocket = await websockets.connect(
					url,
					ping_interval=20,
					ping_timeout=10,
					close_timeout=10
				)
				self.connections[f"kline_{interval}"] = websocket
				logger.info(f"✅ Candle stream connected ({interval})")
				reconnect_count = 0  # Reset on successful connection
				
				async for message in websocket:
					if not self.is_running:
						break
						
					try:
						data = json.loads(message)
						kline = data["k"]
						
						# Normalize symbol and update current candles
						normalized_symbol = normalize_symbol(kline["s"])
						candle_data = {
							"symbol": normalized_symbol,
							"interval": kline["i"],
							"open_time": int(kline["t"]),
							"close_time": int(kline["T"]),
							"open": float(kline["o"]),
							"high": float(kline["h"]),
							"low": float(kline["l"]),
							"close": float(kline["c"]),
							"volume": float(kline["v"]),
							"trades": int(kline["n"]),
							"is_closed": kline["x"],
							"timestamp": time.time()  # Use numeric timestamp for compatibility
						}
						
						self.current_candles[interval] = candle_data
						# Append closed candle to history
						if candle_data.get("is_closed"):
							if interval not in self.candle_history:
								self.candle_history[interval] = deque(maxlen=self.max_history)
							self.candle_history[interval].append(candle_data)
						
						# Notify callbacks
						for callback in self.candle_callbacks:
							try:
								await callback(candle_data)
							except Exception as e:
								logger.error(f"Candle callback error: {e}")
							
					except json.JSONDecodeError as e:
						logger.error(f"Failed to parse candle message: {e}")
							
			except websockets.exceptions.ConnectionClosed as e:
				logger.warning(f"🔗 Candle WebSocket connection closed: {e}")
				reconnect_count += 1
			except websockets.exceptions.WebSocketException as e:
				logger.error(f"❌ Candle WebSocket error: {e}")
				reconnect_count += 1
			except Exception as e:
				logger.error(f"❌ Candle stream error: {e}")
				reconnect_count += 1
			finally:
				# Proper cleanup
				if websocket:
					try:
						if hasattr(websocket, 'closed') and not websocket.closed:
							await websocket.close()
						elif hasattr(websocket, 'close'):
							await websocket.close()
					except:
						pass
				if f"kline_{interval}" in self.connections:
					del self.connections[f"kline_{interval}"]
			
			# Exponential backoff reconnection
			if self.is_running and reconnect_count < max_reconnects:
				delay = min(5 * (2 ** min(reconnect_count, 3)), 30)
				logger.info(f"🔄 Reconnecting candle stream ({interval}) in {delay:.1f}s...")
				await asyncio.sleep(delay)
		
		if reconnect_count >= max_reconnects:
			logger.error(f"❌ Candle stream failed after {max_reconnects} attempts")
		logger.info(f"🛑 Candle stream ended ({interval})")
	
	def subscribe_to_ticker(self, callback: Callable):
		"""Subscribe to ticker updates"""
		self.ticker_callbacks.append(callback)
	
	def subscribe_to_candles(self, callback: Callable):
		"""Subscribe to candle updates"""
		self.candle_callbacks.append(callback)
	
	def add_ticker_callback(self, callback: Callable):
		"""Add ticker callback - alias for subscribe_to_ticker for compatibility"""
		self.subscribe_to_ticker(callback)
	
	def add_candle_callback(self, callback: Callable):
		"""Add candle callback - alias for subscribe_to_candles for compatibility"""
		self.subscribe_to_candles(callback)
	
	def get_current_ticker(self) -> Optional[Dict]:
		"""Get current ticker data"""
		return self.current_ticker

	async def get_current_price(self, symbol: str) -> Optional[float]:
		"""Get current price for symbol - REQUIRED BY TRADING ROUTES"""
		try:
			# Get current ticker data
			ticker = self.get_current_ticker()
			if ticker and ticker.get('symbol') == symbol:
				# Return the last price from ticker
				return float(ticker.get('last_price', 0))

			# Fallback: try to get price from current candle (ensure symbol match)
			candle = self.get_current_candle()
			if candle:
				candle_symbol = normalize_symbol(candle.get("symbol", ""))
				canonical_symbol = get_canonical_symbol()
				
				if candle_symbol == canonical_symbol:
					close_price = float(candle.get('close', 0))
					logger.debug(f"💰 Using candle close price ({candle_symbol}): ${close_price:,.2f}")
					return close_price
				else:
					logger.warning(f"⚠️ Candle symbol mismatch: got {candle_symbol}, expected {canonical_symbol}")

			# Last resort: fetch directly from Binance API (avoid circular import)
			if symbol == "BTCUSDT":
				logger.warning("No ticker/candle data - fetching directly from Binance API")
				try:
					from app.backend.services.binance_hybrid_client import get_hybrid_client
					client = await get_hybrid_client()
					result = await client.get_data_hybrid("ticker", "BTCUSDT")
					price = result["data"]["price"]
					logger.info(f"💰 Direct Binance API price: ${price:,.2f}")
					return float(price)
				except Exception as api_error:
					logger.error(f"Failed to fetch price from Binance API: {api_error}")
					return 0.0

			logger.warning(f"Could not get current price for {symbol}")
			return None

		except Exception as e:
			logger.error(f"Error getting current price for {symbol}: {e}")
			return None
	
	def get_current_candle(self, interval: str = "1m") -> Optional[Dict]:
		"""Get current candle data"""
		return self.current_candles.get(interval)
	
	def get_recent_candles(self, interval: str = "1m", limit: int = 100) -> List[Dict]:
		"""Return recent closed candles from in-memory history."""
		hist = self.candle_history.get(interval)
		if not hist:
			return []
		arr = list(hist)
		return arr[-limit:]
	
	def get_market_summary(self) -> Dict:
		"""Get market data summary"""
		return {
			"is_running": self.is_running,
			"connections": {
				name: ws is not None for name, ws in self.connections.items()
			},
			"current_ticker": self.current_ticker is not None,
			"current_candles": list(self.current_candles.keys()),
			"timestamp": datetime.now(timezone.utc).isoformat()
		}

# Global service instance
_live_market_service: Optional[LiveMarketDataService] = None

async def get_live_market_data_service() -> LiveMarketDataService:
	"""Get or create global live market data service"""
	global _live_market_service
	if _live_market_service is None:
		_live_market_service = LiveMarketDataService()
		# Auto-start the service
		if not _live_market_service.is_running:
			await _live_market_service.start()
	return _live_market_service

# BTC Price cache with TTL for API throttling
_btc_price_cache: Optional[Tuple[float, datetime]] = None
_btc_price_cache_ttl = 3  # Cache for 3 seconds

async def get_live_bitcoin_price() -> float:
	"""Get current live Bitcoin price with intelligent caching"""
	global _btc_price_cache
	
	current_time = datetime.now(timezone.utc)
	
	# Check if we have a cached price that's still fresh
	if _btc_price_cache is not None:
		cached_price, cached_time = _btc_price_cache
		age_seconds = (current_time - cached_time).total_seconds()
		
		if age_seconds < _btc_price_cache_ttl:
			logger.debug(f"💰 Using cached BTC price: ${cached_price:,.2f} (age: {age_seconds:.1f}s)")
			return cached_price
	
	try:
		# Try WebSocket data first (ensure it's for BTCUSDT)
		service = await get_live_market_data_service()
		if service.current_ticker:
			# Verify the ticker symbol matches our canonical symbol
			ticker_symbol = normalize_symbol(service.current_ticker.get("symbol", ""))
			canonical_symbol = get_canonical_symbol()
			
			if ticker_symbol == canonical_symbol:
				price = service.current_ticker["price"]
				_btc_price_cache = (price, current_time)
				logger.debug(f"💰 Fresh BTC price from WebSocket ({ticker_symbol}): ${price:,.2f}")
				return price
			else:
				logger.warning(f"⚠️ WebSocket ticker symbol mismatch: got {ticker_symbol}, expected {canonical_symbol}")
		
		settings = get_settings()
		cfg = await runtime_config_store.get()
		if settings.STRICT_LIVE_STREAM or cfg.strict_live_stream:
			raise RuntimeError("STRICT_LIVE_STREAM enabled and no WebSocket ticker available")
		
		# Fallback to REST API (only if STRICT_LIVE_STREAM is false)
		client = await get_hybrid_client()
		result = await client.get_data_hybrid("ticker", "BTCUSDT")
		price = result["data"]["price"]
		
		# Cache the fresh price
		_btc_price_cache = (price, current_time)
		logger.debug(f"💰 Fresh BTC price from REST API: ${price:,.2f}")
		return price
			
	except Exception as e:
		logger.error(f"Failed to get live Bitcoin price: {e}")
		raise RuntimeError(f"Real Bitcoin price unavailable: {e}")

async def get_live_market_data() -> Dict:
	"""Get comprehensive live market data"""
	try:
		service = await get_live_market_data_service()
		settings = get_settings()
		cfg = await runtime_config_store.get()
		
		# Get current price and ticker
		if service.current_ticker:
			ticker_data = service.current_ticker
		else:
			if settings.STRICT_LIVE_STREAM or cfg.strict_live_stream:
				raise RuntimeError("STRICT_LIVE_STREAM enabled and no WebSocket ticker available")
			# Fallback to REST API
			client = await get_hybrid_client()
			result = await client.get_data_hybrid("ticker", "BTCUSDT")
			ticker_data = result["data"]
		
		return {
			"symbol": "BTCUSDT",
			"current_price": ticker_data["price"],
			"price_change_24h": ticker_data["price_change"],
			"price_change_percent_24h": ticker_data["price_change_percent"],
			"high_24h": ticker_data["high"],
			"low_24h": ticker_data["low"],
			"volume_24h": ticker_data["volume"],
			"last_updated": datetime.now(timezone.utc).isoformat(),
			"source": "websocket" if service.current_ticker else "rest_api"
		}
		
	except Exception as e:
		logger.error(f"Failed to get live market data: {e}")
		raise

async def get_live_candlestick_data(timeframe: str = "1m", limit: int = 100) -> List[Dict]:
	"""Get live candlestick data"""
	try:
		settings = get_settings()
		cfg = await runtime_config_store.get()
		if settings.STRICT_LIVE_STREAM or cfg.strict_live_stream:
			raise RuntimeError("STRICT_LIVE_STREAM enabled: candlesticks must come from WS cache")
		client = await get_hybrid_client()
		result = await client.get_data_hybrid("candles", "BTCUSDT", interval=timeframe, limit=limit)
		return result["data"]
			
	except Exception as e:
		logger.error(f"Failed to get live candlestick data: {e}")
		raise

async def get_live_orderbook_data() -> Dict:
	"""Get live order book data"""
	try:
		settings = get_settings()
		cfg = await runtime_config_store.get()
		if settings.STRICT_LIVE_STREAM or cfg.strict_live_stream:
			raise RuntimeError("STRICT_LIVE_STREAM enabled: orderbook must come from WS stream")
		client = await get_hybrid_client()
		result = await client.get_data_hybrid("depth", "BTCUSDT", limit=20)
		return result["data"]
			
	except Exception as e:
		logger.error(f"Failed to get live orderbook data: {e}")
		raise
