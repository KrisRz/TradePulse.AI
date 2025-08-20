"""
Real Binance API Client for TradePulse.AI
Professional-grade market data and trading operations
"""

import asyncio
import aiohttp
import hashlib
import hmac
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import random

logger = logging.getLogger(__name__)

class BinanceClient:
    """Professional Binance API client with real market data"""
    
    def __init__(self, api_key: str = None, secret_key: str = None, production: bool = True):
        self.api_key = api_key
        self.secret_key = secret_key
        self.production = production
        
        if production:
            self.base_url = "https://api.binance.com/api/v3"
        else:
            self.base_url = "https://testnet.binance.vision/api/v3"
            
        self.session = None
        self.max_retries = 4
        self.request_timeout_seconds = 3.0
        self.backoff_base_seconds = 0.25
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.request_timeout_seconds)
        connector = aiohttp.TCPConnector(limit=50, ttl_dns_cache=300)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC SHA256 signature for authenticated requests"""
        if not self.secret_key:
            return ""
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _make_request(self, endpoint: str, params: Dict = None, signed: bool = False) -> Dict:
        """Make authenticated request to Binance API with retries and tight timeouts."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.request_timeout_seconds)
            connector = aiohttp.TCPConnector(limit=50, ttl_dns_cache=300)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)

        url = f"{self.base_url}{endpoint}"
        headers: Dict[str, str] = {}
        req_params: Dict[str, Any] = {} if params is None else dict(params)

        if signed:
            req_params['timestamp'] = int(time.time() * 1000)
            query_string = '&'.join([f"{key}={value}" for key, value in req_params.items()])
            signature = self._generate_signature(query_string)
            req_params['signature'] = signature

        if self.api_key:
            headers['X-MBX-APIKEY'] = self.api_key

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with self.session.get(url, params=req_params, headers=headers) as response:
                    data = await response.json()

                    if response.status == 200:
                        return data

                    # Handle rate limits and transient errors with backoff
                    status = response.status
                    msg = data.get('msg', 'Unknown error') if isinstance(data, dict) else str(data)
                    logger.warning(f"Binance API non-200 status {status}: {msg} (attempt {attempt}/{self.max_retries})")

                    if status in (418, 429) or 500 <= status < 600:
                        # Exponential backoff with jitter
                        backoff = self.backoff_base_seconds * (2 ** (attempt - 1))
                        jitter = random.uniform(0, backoff * 0.2)
                        await asyncio.sleep(backoff + jitter)
                        continue

                    # Non-retriable
                    raise Exception(f"Binance API error: {msg}")

            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(f"Binance request timeout to {endpoint} (attempt {attempt}/{self.max_retries})")
                backoff = self.backoff_base_seconds * (2 ** (attempt - 1))
                jitter = random.uniform(0, backoff * 0.2)
                await asyncio.sleep(backoff + jitter)
                continue
            except Exception as e:
                last_error = e
                logger.warning(f"Binance request error to {endpoint}: {e} (attempt {attempt}/{self.max_retries})")
                backoff = self.backoff_base_seconds * (2 ** (attempt - 1))
                jitter = random.uniform(0, backoff * 0.2)
                await asyncio.sleep(backoff + jitter)
                continue

        logger.error(f"Failed all retries to Binance endpoint {endpoint}: {last_error}")
        raise RuntimeError(f"Binance request failed after retries: {endpoint}: {last_error}")
    
    async def get_current_price(self, symbol: str = "BTCUSDT") -> float:
        """Get current price for symbol"""
        try:
            data = await self._make_request("/ticker/price", {"symbol": symbol})
            return float(data["price"])
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            raise
    
    async def get_24hr_ticker(self, symbol: str = "BTCUSDT") -> Dict:
        """Get 24hr ticker statistics"""
        try:
            data = await self._make_request("/ticker/24hr", {"symbol": symbol})
            return {
                "symbol": data["symbol"],
                "price": float(data["lastPrice"]),
                "price_change": float(data["priceChange"]),
                "price_change_percent": float(data["priceChangePercent"]),
                "high": float(data["highPrice"]),
                "low": float(data["lowPrice"]),
                "volume": float(data["volume"]),
                "volume_usdt": float(data["quoteVolume"]),
                "open": float(data["openPrice"]),
                "timestamp": int(data["closeTime"])
            }
        except Exception as e:
            logger.error(f"Failed to get 24hr ticker for {symbol}: {e}")
            raise
    
    async def get_klines(self, symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 100, start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[Dict]:
        """Get candlestick data.

        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            interval: Binance interval string (e.g., 1m, 5m, 1h)
            limit: Max rows per request (<= 1000 per Binance API)
            start_time: Optional start time in ms since epoch
            end_time: Optional end time in ms since epoch

        Returns:
            List of candle dicts with numeric types.
        """
        try:
            req: Dict[str, Any] = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
            }
            if start_time is not None:
                req["startTime"] = int(start_time)
            if end_time is not None:
                req["endTime"] = int(end_time)

            data = await self._make_request("/klines", req)
            
            candles = []
            for kline in data:
                candles.append({
                    "open_time": int(kline[0]),
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5]),
                    "close_time": int(kline[6]),
                    "quote_volume": float(kline[7]),
                    "trades": int(kline[8])
                })
            return candles
        except Exception as e:
            logger.error(f"Failed to get klines for {symbol}: {e}")
            raise
    
    async def get_order_book(self, symbol: str = "BTCUSDT", limit: int = 100) -> Dict:
        """Get order book depth"""
        try:
            data = await self._make_request("/depth", {
                "symbol": symbol,
                "limit": limit
            })
            
            return {
                "symbol": symbol,
                "bids": [[float(price), float(qty)] for price, qty in data["bids"]],
                "asks": [[float(price), float(qty)] for price, qty in data["asks"]],
                "timestamp": datetime.now(timezone.utc).timestamp()
            }
        except Exception as e:
            logger.error(f"Failed to get order book for {symbol}: {e}")
            raise
    
    async def get_account_info(self) -> Dict:
        """Get account information (requires API key)"""
        if not self.api_key or not self.secret_key:
            raise Exception("API credentials required for account info")
            
        try:
            data = await self._make_request("/account", signed=True)
            return {
                "maker_commission": data["makerCommission"],
                "taker_commission": data["takerCommission"],
                "buyer_commission": data["buyerCommission"],
                "seller_commission": data["sellerCommission"],
                "can_trade": data["canTrade"],
                "can_withdraw": data["canWithdraw"],
                "can_deposit": data["canDeposit"],
                "balances": [
                    {
                        "asset": balance["asset"],
                        "free": float(balance["free"]),
                        "locked": float(balance["locked"])
                    }
                    for balance in data["balances"]
                    if float(balance["free"]) > 0 or float(balance["locked"]) > 0
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            raise

# Global client instance
_binance_client: Optional[BinanceClient] = None

async def get_binance_client() -> BinanceClient:
    """Get or create global Binance client for PRODUCTION"""
    global _binance_client
    if _binance_client is None:
        from app.backend.core.config import get_settings
        settings = get_settings()
        _binance_client = BinanceClient(
            api_key=settings.BINANCE_API_KEY,
            secret_key=settings.BINANCE_SECRET_KEY,
            production=not settings.BINANCE_TESTNET
        )
    return _binance_client
 

