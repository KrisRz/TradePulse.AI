"""
Boot Once Guard - Prevents duplicate initialization
Implements singleton pattern for service initialization
"""

import logging
import asyncio
from typing import Set, Callable, Any, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class BootOnce:
    """
    Boot Once Guard - prevents duplicate service initialization
    Ensures each service starts only once regardless of how many times it's called
    """
    
    _started: Set[str] = set()
    _instances: Dict[str, Any] = {}
    _lock = asyncio.Lock()
    
    @classmethod
    async def start_async(cls, name: str, fn: Callable, *args, **kwargs) -> bool:
        """Start async function once"""
        async with cls._lock:
            if name in cls._started:
                logger.debug(f"🔒 {name} already started, skipping")
                return False
            
            try:
                logger.info(f"🚀 Starting {name} (first time)")
                result = await fn(*args, **kwargs)
                cls._started.add(name)
                if result is not None:
                    cls._instances[name] = result
                logger.info(f"✅ {name} started successfully")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to start {name}: {e}")
                raise
    
    @classmethod
    def start_sync(cls, name: str, fn: Callable, *args, **kwargs) -> bool:
        """Start sync function once"""
        if name in cls._started:
            logger.debug(f"🔒 {name} already started, skipping")
            return False
        
        try:
            logger.info(f"🚀 Starting {name} (first time)")
            result = fn(*args, **kwargs)
            cls._started.add(name)
            if result is not None:
                cls._instances[name] = result
            logger.info(f"✅ {name} started successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start {name}: {e}")
            raise
    
    @classmethod
    def get_instance(cls, name: str) -> Any:
        """Get started instance"""
        return cls._instances.get(name)
    
    @classmethod
    def is_started(cls, name: str) -> bool:
        """Check if service is already started"""
        return name in cls._started
    
    @classmethod
    def reset(cls) -> None:
        """Reset all started services (for testing)"""
        cls._started.clear()
        cls._instances.clear()
        logger.info("🔄 BootOnce reset - all services can start again")


def normalize_ticker_price(ticker_data: Dict[str, Any]) -> float:
    """
    Normalize price from different ticker schemas (WS vs REST)
    Handles different field names across Binance APIs and nested data structures
    """
    try:
        # Handle nested structure: {'data': {...}, 'source': '...'}
        if 'data' in ticker_data and isinstance(ticker_data['data'], dict):
            actual_ticker = ticker_data['data']
        else:
            actual_ticker = ticker_data
        
        # Try common price field names
        for field in ("price", "lastPrice", "last", "close", "c", "p"):
            value = actual_ticker.get(field)
            if value is not None:
                return float(value)
        
        # Log available keys for debugging
        available_keys = list(actual_ticker.keys())
        logger.error(f"❌ Price normalization failed - no price field found in data. Available keys: {available_keys}")
        raise KeyError(f"No price field found in ticker data. Available: {available_keys}")
        
    except Exception as e:
        logger.error(f"❌ Ticker price normalization error: {e}")
        raise


def normalize_ticker_change_percent(ticker_data: Dict[str, Any]) -> float:
    """
    Normalize price change percent from different ticker schemas
    """
    try:
        # Handle nested structure: {'data': {...}, 'source': '...'}
        if 'data' in ticker_data and isinstance(ticker_data['data'], dict):
            actual_ticker = ticker_data['data']
        else:
            actual_ticker = ticker_data
        
        # Try common price change percent field names
        for field in ("price_change_percent", "priceChangePercent", "change_percent", "changePercent"):
            value = actual_ticker.get(field)
            if value is not None:
                return float(value)
        
        # Fallback to 0 if not available
        return 0.0
        
    except Exception as e:
        logger.warning(f"⚠️ Price change percent normalization failed: {e}")
        return 0.0
