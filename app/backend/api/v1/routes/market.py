"""
Market Data API Routes - TradePulse.AI
Live market data and symbol information endpoints
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from app.backend.core.config import get_settings
from app.backend.core.logging import get_logger
from app.backend.utils.dependencies import get_current_user, User
from app.backend.services.live_market_data import get_live_bitcoin_price
from app.backend.services.binance_hybrid_client import get_hybrid_client

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


class MarketSymbol(BaseModel):
    """Market symbol information"""
    symbol: str
    base_asset: str
    quote_asset: str
    status: str
    price_precision: int
    quantity_precision: int
    min_notional: float
    description: str


@router.get("/symbols")
async def get_market_symbols(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get available trading symbols
    
    Args:
        current_user: Authenticated user
        
    Returns:
        List of available trading symbols
    """
    try:
        # For now, return the main symbols we support
        symbols = [
            MarketSymbol(
                symbol="BTCUSDT",
                base_asset="BTC",
                quote_asset="USDT",
                status="TRADING",
                price_precision=2,
                quantity_precision=6,
                min_notional=10.0,
                description="Bitcoin / Tether USD"
            ),
            MarketSymbol(
                symbol="ETHUSDT", 
                base_asset="ETH",
                quote_asset="USDT",
                status="TRADING",
                price_precision=2,
                quantity_precision=5,
                min_notional=10.0,
                description="Ethereum / Tether USD"
            ),
            MarketSymbol(
                symbol="ADAUSDT",
                base_asset="ADA",
                quote_asset="USDT", 
                status="TRADING",
                price_precision=4,
                quantity_precision=1,
                min_notional=10.0,
                description="Cardano / Tether USD"
            ),
            MarketSymbol(
                symbol="SOLUSDT",
                base_asset="SOL",
                quote_asset="USDT",
                status="TRADING", 
                price_precision=2,
                quantity_precision=3,
                min_notional=10.0,
                description="Solana / Tether USD"
            )
        ]
        
        return {
            "symbols": [symbol.dict() for symbol in symbols],
            "total_count": len(symbols),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get market symbols: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get market symbols: {str(e)}"
        )


@router.get("/data/{symbol}")
async def get_market_data(
    symbol: str
) -> Dict[str, Any]:
    """
    Get current market data for a symbol
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        current_user: Authenticated user
        
    Returns:
        Current market data
    """
    try:
        if symbol.upper() == "BTCUSDT":
            # Use our live Bitcoin price service
            price_data = await get_live_bitcoin_price()
            # Skip market data for now to avoid function signature issues
            market_data = {}
            
            return {
                "symbol": symbol.upper(),
                "price": price_data.get("price", 0.0),
                "change_24h": market_data.get("price_change_24h", 0.0),
                "volume_24h": market_data.get("volume", 0.0),
                "high_24h": market_data.get("high", 0.0),
                "low_24h": market_data.get("low", 0.0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "live_binance_api"
            }
        else:
            # For other symbols, return basic data structure
            return {
                "symbol": symbol.upper(),
                "price": 0.0,
                "change_24h": 0.0,
                "volume_24h": 0.0,
                "high_24h": 0.0,
                "low_24h": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "placeholder",
                "note": f"Live data for {symbol} not yet implemented"
            }
        
    except Exception as e:
        logger.error(f"Failed to get market data for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get market data: {str(e)}"
        )


@router.get("/price/{symbol}")
async def get_symbol_price(
    symbol: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current price for a symbol
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        current_user: Authenticated user
        
    Returns:
        Current price data
    """
    try:
        if symbol.upper() == "BTCUSDT":
            price_data = await get_live_bitcoin_price()
            return {
                "symbol": symbol.upper(),
                "price": price_data.get("price", 0.0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "live_binance_api"
            }
        else:
            return {
                "symbol": symbol.upper(),
                "price": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "placeholder",
                "note": f"Live price for {symbol} not yet implemented"
            }
        
    except Exception as e:
        logger.error(f"Failed to get price for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get price: {str(e)}"
        )


@router.get("/klines")
async def get_market_klines(
    symbol: str = "BTCUSDT",
    interval: str = "5m",
    limit: int = 500
) -> Dict[str, Any]:
    """
    Get candlestick/klines data for charting
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d)
        limit: Number of klines to return (max 1000)
        
    Returns:
        Candlestick data for chart rendering
    """
    try:
        # Get hybrid client for reliable data fetching
        client = await get_hybrid_client()
        klines = await client.get_klines(symbol=symbol, interval=interval, limit=min(limit, 1000))
        
        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "klines": klines,
            "count": len(klines),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "binance_hybrid_client"
        }
        
    except Exception as e:
        logger.error(f"Failed to get klines for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get klines: {str(e)}"
        )
