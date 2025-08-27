"""
Live Market Data Service for TradePulse.AI
Real-time market data processing with WebSocket and REST fallback
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
import websockets
from collections import deque
from .binance_client import get_binance_client
from app.backend.core.config import get_settings
from app.backend.core.runtime_config import runtime_config_store

logger = logging.getLogger(__name__)

class LiveMarketDataService:
	"""Professional live market data service with WebSocket streams"""
	
	def __init__(self):
		self.is_running = False
		self.connections = {}
		self.tasks = []
		
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
		
	async def start(self):
		"""Start all live data connections"""
		if self.is_running:
			return
			
		logger.info("🚀 Starting live market data service...")
		self.is_running = True
		
		try:
			# Pre-populate cache with recent DB data for LSTM
			await self._populate_cache_from_db()
			
			# Start ticker stream
			ticker_task = asyncio.create_task(self._ticker_stream())
			self.tasks.append(ticker_task)
			
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
		"""WebSocket stream for 24hr ticker updates"""
		stream_name = "btcusdt@ticker"
		url = f"{self.ws_base_url}/{stream_name}"
		
		while self.is_running:
			try:
				logger.info(f"📡 Connecting to ticker stream: {stream_name}")
				async with websockets.connect(url) as websocket:
					self.connections["ticker"] = websocket
					logger.info("✅ Ticker stream connected")
					async for message in websocket:
						if not self.is_running:
							break
						try:
							data = json.loads(message)
							# Update current ticker
							self.current_ticker = {
								"symbol": data["s"],
								"price": float(data["c"]),
								"price_change": float(data["P"]),
								"price_change_percent": float(data["P"]),
								"high": float(data["h"]),
								"low": float(data["l"]),
								"volume": float(data["v"]),
								"timestamp": datetime.now(timezone.utc)
							}
							# Notify callbacks
							for callback in self.ticker_callbacks:
								try:
									await callback(self.current_ticker)
								except Exception as e:
									logger.error(f"Ticker callback error: {e}")
						except json.JSONDecodeError as e:
							logger.error(f"Failed to parse ticker message: {e}")
			except Exception as e:
				logger.error(f"Ticker stream error: {e}")
				if "ticker" in self.connections:
					del self.connections["ticker"]
				if self.is_running:
					logger.info("Reconnecting ticker stream in 5 seconds...")
					await asyncio.sleep(5)
	
	async def _candle_stream(self, interval: str = "1m"):
		"""WebSocket stream for candlestick updates"""
		stream_name = f"btcusdt@kline_{interval}"
		url = f"{self.ws_base_url}/{stream_name}"
		
		while self.is_running:
			try:
				logger.info(f"📡 Connecting to candle stream: {stream_name}")
				
				async with websockets.connect(url) as websocket:
					self.connections[f"kline_{interval}"] = websocket
					logger.info(f"✅ Candle stream connected ({interval})")
					
					async for message in websocket:
						if not self.is_running:
							break
							
						try:
							data = json.loads(message)
							kline = data["k"]
							
							# Update current candles
							candle_data = {
								"symbol": kline["s"],
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
								"timestamp": datetime.now(timezone.utc)
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
							
			except Exception as e:
				logger.error(f"Candle stream error: {e}")
				if f"kline_{interval}" in self.connections:
					del self.connections[f"kline_{interval}"]
					
				if self.is_running:
					logger.info(f"Reconnecting candle stream ({interval}) in 5 seconds...")
					await asyncio.sleep(5)
	
	def subscribe_to_ticker(self, callback: Callable):
		"""Subscribe to ticker updates"""
		self.ticker_callbacks.append(callback)
	
	def subscribe_to_candles(self, callback: Callable):
		"""Subscribe to candle updates"""
		self.candle_callbacks.append(callback)
	
	def get_current_ticker(self) -> Optional[Dict]:
		"""Get current ticker data"""
		return self.current_ticker
	
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

async def get_live_bitcoin_price() -> float:
	"""Get current live Bitcoin price"""
	try:
		# Try WebSocket data first
		service = await get_live_market_data_service()
		if service.current_ticker:
			return service.current_ticker["price"]
		
		settings = get_settings()
		cfg = await runtime_config_store.get()
		if settings.STRICT_LIVE_STREAM or cfg.strict_live_stream:
			raise RuntimeError("STRICT_LIVE_STREAM enabled and no WebSocket ticker available")
		# Fallback to REST API (only if STRICT_LIVE_STREAM is false)
		client = await get_binance_client()
		async with client:
			return await client.get_current_price("BTCUSDT")
			
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
			client = await get_binance_client()
			async with client:
				ticker_data = await client.get_24hr_ticker("BTCUSDT")
		
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
		client = await get_binance_client()
		async with client:
			return await client.get_klines("BTCUSDT", timeframe, limit)
			
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
		client = await get_binance_client()
		async with client:
			return await client.get_order_book("BTCUSDT", 20)
			
	except Exception as e:
		logger.error(f"Failed to get live orderbook data: {e}")
		raise
