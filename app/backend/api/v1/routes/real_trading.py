from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import logging
from decimal import Decimal

from app.backend.services import (
    get_live_market_data_service, 
    get_live_bitcoin_price,
    get_live_market_data,
    get_live_candlestick_data,
    get_live_orderbook_data
)
from app.backend.utils.dependencies import require_admin_role, get_current_user, User

logger = logging.getLogger(__name__)

# DEBUG: Print when module is imported
print("🔥 DEBUG: real_trading.py module is being imported!")
logger.info("🔥 DEBUG: real_trading.py module is being imported!")

router = APIRouter()

# =============================================================================
# LIVE MARKET DATA ENDPOINTS
# =============================================================================

@router.get("/test-simple")
async def test_simple():
    """
    🧪 SIMPLE TEST ENDPOINT - No Dependencies
    Test endpoint to verify router is working
    """
    return {
        "status": "success", 
        "message": "Real trading router is working!",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/health-check")
async def health_check():
    """
    🏥 HEALTH CHECK - Minimal endpoint
    """
    return {"status": "ok", "router": "real_trading"}

@router.get("/live/bitcoin-price")
async def get_bitcoin_price(admin_user: User = Depends(require_admin_role)):
    """
    🔴 GET LIVE BITCOIN PRICE - Real Binance Data (Cached)
    Returns current live Bitcoin price from cache or WebSocket stream
    """
    try:
        from app.backend.services.btc_price_cache import get_cached_btc_price
        price_data = await get_cached_btc_price("BTCUSDT")

        if price_data and "price" in price_data:
            return {
                "status": "success",
                "data": {
                    "symbol": "BTCUSDT",
                    "price": price_data["price"],
                    "timestamp": price_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "source": price_data.get("source", "cache")
                }
            }

        # Fallback to direct API call
        logger.warning("💰 Cache miss - falling back to direct API call")
        price = await get_live_bitcoin_price()
        return {
            "status": "success",
            "data": {
                "symbol": "BTCUSDT",
                "price": price,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "binance_websocket_fallback"
            }
        }

    except Exception as e:
        logger.error(f"Failed to get live Bitcoin price: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get live price: {str(e)}")

@router.get("/live/market-data")
async def get_market_data(admin_user: User = Depends(require_admin_role)):
    """
    🔴 GET LIVE MARKET DATA - Real Binance Data
    Returns comprehensive live market statistics
    """
    try:
        market_data = await get_live_market_data()
        return {
            "status": "success",
            "data": market_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get live market data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get market data: {str(e)}")

@router.get("/live/candlestick/{timeframe}")
async def get_candlestick_data(
    timeframe: str,
    limit: int = 50,
    admin_user: User = Depends(require_admin_role)
):
    """
    🔴 GET LIVE CANDLESTICK DATA - Real Binance Data
    Returns live candlestick data for specified timeframe
    """
    try:
        # Validate timeframe
        valid_timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid timeframe. Must be one of: {valid_timeframes}"
            )
        
        candlestick_data = await get_live_candlestick_data(timeframe, limit)
        return {
            "status": "success",
            "data": {
                "timeframe": timeframe,
                "candles": candlestick_data,
                "count": len(candlestick_data)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get candlestick data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get candlestick data: {str(e)}")

@router.get("/live/orderbook")
async def get_orderbook(admin_user: User = Depends(require_admin_role)):
    """
    🔴 GET LIVE ORDER BOOK - Real Binance Data
    Returns live order book depth data
    """
    try:
        orderbook_data = await get_live_orderbook_data()
        return {
            "status": "success",
            "data": orderbook_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get orderbook data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get orderbook data: {str(e)}")

# =============================================================================
# WEBSOCKET STREAMING ENDPOINTS
# =============================================================================

@router.get("/live/stream/price")
async def stream_bitcoin_price(admin_user: User = Depends(require_admin_role)):
    """
    🔴 STREAM LIVE BITCOIN PRICE - Real-time WebSocket to SSE
    Server-Sent Events stream of live Bitcoin price updates
    """
    async def generate_price_stream():
        """Generate real-time price updates"""
        try:
            service = await get_live_market_data_service()
            
            # Subscribe to live ticker updates
            price_queue = asyncio.Queue()
            
            async def price_callback(ticker):
                await price_queue.put({
                    "type": "price_update",
                    "data": {
                        "price": ticker.price,
                        "change": ticker.price_change,
                        "change_percent": ticker.price_change_percent,
                        "timestamp": ticker.timestamp.isoformat()
                    }
                })
            
            service.subscribe_to_ticker(price_callback)
            
            # Send initial data
            initial_data = service.get_current_ticker()
            if initial_data:
                yield f"data: {json.dumps(initial_data)}\n\n"
            
            # Stream live updates
            while True:
                try:
                    # Wait for new price update
                    update = await asyncio.wait_for(price_queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(update)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': datetime.now().isoformat()})}\n\n"
                    
        except Exception as e:
            logger.error(f"Price stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_price_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )

# =============================================================================
# REAL TRADING WALLET ENDPOINTS
# =============================================================================

@router.get("/wallet/balances")
async def get_wallet_balances(admin_user: User = Depends(require_admin_role)):
    """
    🔴 GET LIVE WALLET BALANCES - Real Exchange Data
    Returns live wallet balances from connected exchange
    """
    try:
        # In development mode, return realistic zero balances
        # In production, this would connect to actual exchange API
        
        balances = [
            {
                "currency": "USD",
                "symbol": "$",
                "balance": 0.0,
                "available": 0.0,
                "locked": 0.0,
                "usd_value": 0.0,
                "change_24h": 0.0
            },
            {
                "currency": "BTC",
                "symbol": "₿",
                "balance": 0.0,
                "available": 0.0,
                "locked": 0.0,
                "usd_value": 0.0,
                "change_24h": 0.0
            },
            {
                "currency": "ETH",
                "symbol": "Ξ",
                "balance": 0.0,
                "available": 0.0,
                "locked": 0.0,
                "usd_value": 0.0,
                "change_24h": 0.0
            },
            {
                "currency": "USDT",
                "symbol": "₮",
                "balance": 0.0,
                "available": 0.0,
                "locked": 0.0,
                "usd_value": 0.0,
                "change_24h": 0.0
            }
        ]
        
        return {
            "status": "success",
            "data": {
                "balances": balances,
                "total_usd_value": 0.0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "exchange_status": "development_mode"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get wallet balances: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get wallet balances: {str(e)}")

@router.get("/wallet/transactions")
async def get_wallet_transactions(
    limit: int = 50,
    transaction_type: Optional[str] = None,
    admin_user: User = Depends(require_admin_role)
):
    """
    🔴 GET LIVE WALLET TRANSACTIONS - Real Exchange Data
    Returns live transaction history from connected exchange
    """
    try:
        # In development mode, return empty transactions
        # In production, this would fetch from actual exchange API
        
        transactions = []
        
        return {
            "status": "success",
            "data": {
                "transactions": transactions,
                "total_count": 0,
                "has_more": False,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "exchange_status": "development_mode"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get wallet transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get wallet transactions: {str(e)}")

# =============================================================================
# REAL TRADING POSITIONS ENDPOINTS
# =============================================================================

@router.get("/positions/open")
async def get_open_positions(admin_user: User = Depends(require_admin_role)):
    """
    🔴 GET LIVE OPEN POSITIONS - Real Exchange Data
    Returns live open positions from connected exchange
    """
    try:
        # In development mode, return empty positions
        # In production, this would fetch from actual exchange API
        
        live_price = await get_live_bitcoin_price()
        
        positions = []
        
        summary = {
            "total_positions": 0,
            "total_unrealized_pnl": 0.0,
            "total_margin_used": 0.0,
            "avg_ai_confidence": 0.0,
            "long_positions": 0,
            "short_positions": 0,
            "profitable_positions": 0
        }
        
        return {
            "status": "success",
            "data": {
                "positions": positions,
                "summary": summary,
                "current_btc_price": live_price,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "exchange_status": "development_mode"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get open positions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get open positions: {str(e)}")

@router.get("/positions/closed")
async def get_closed_positions(
    limit: int = 50,
    admin_user: User = Depends(require_admin_role)
):
    """
    🔴 GET LIVE CLOSED POSITIONS - Real Exchange Data
    Returns closed positions history from connected exchange
    """
    try:
        # In development mode, return empty positions
        # In production, this would fetch from actual exchange API
        
        closed_positions = []
        
        analytics = {
            "total_trades": 0,
            "profitable_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "avg_hold_time": "0h 0m",
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "profit_factor": 0.0,
            "avg_pnl_per_trade": 0.0,
            "total_commissions": 0.0,
            "sharpe_ratio": 0.0
        }
        
        return {
            "status": "success",
            "data": {
                "closed_positions": closed_positions,
                "analytics": analytics,
                "total_count": 0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "exchange_status": "development_mode"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get closed positions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get closed positions: {str(e)}")

# =============================================================================
# REAL TRADING ORDERS ENDPOINTS
# =============================================================================

@router.get("/orders/active")
async def get_active_orders(admin_user: User = Depends(require_admin_role)):
    """
    🔴 GET LIVE ACTIVE ORDERS - Real Exchange Data
    Returns live active orders from connected exchange
    """
    try:
        # In development mode, return empty orders
        # In production, this would fetch from actual exchange API
        
        active_orders = []
        
        return {
            "status": "success",
            "data": {
                "active_orders": active_orders,
                "total_count": 0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "exchange_status": "development_mode"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get active orders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active orders: {str(e)}")

@router.post("/orders/place")
async def place_order(
    order_data: Dict[str, Any],
    admin_user: User = Depends(require_admin_role)
):
    """
    🔴 PLACE LIVE ORDER - Real Exchange Integration
    Places a live order on the connected exchange
    """
    try:
        # In development mode, simulate order placement
        # In production, this would place actual orders via exchange API
        
        logger.warning("🚨 ORDER PLACEMENT DISABLED - DEVELOPMENT MODE")
        
        return {
            "status": "error",
            "message": "Order placement disabled in development mode",
            "data": {
                "order_id": None,
                "exchange_status": "development_mode",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Failed to place order: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to place order: {str(e)}")

# =============================================================================
# SYSTEM STATUS ENDPOINTS
# =============================================================================

@router.get("/status/connections")
async def get_connection_status(admin_user: User = Depends(require_admin_role)):
    """
    🔴 GET LIVE CONNECTION STATUS
    Returns status of all live data connections
    """
    try:
        service = await get_live_market_data_service()
        market_summary = service.get_market_summary()
        
        status = {
            "market_data": {
                "status": "connected" if service.is_running else "disconnected",
                "connections": market_summary.get("connections", {}),
                "last_update": market_summary.get("timestamp")
            },
            "exchange_api": {
                "status": "development_mode",
                "authenticated": False,
                "rate_limits": {
                    "remaining": "N/A",
                    "reset_time": "N/A"
                }
            },
            "websockets": {
                "ticker": market_summary.get("connections", {}).get("ticker", False),
                "klines": market_summary.get("connections", {}).get("klines", False),
                "orderbook": market_summary.get("connections", {}).get("orderbook", False)
            },
            "overall_status": "live_data_active" if service.is_running else "disconnected"
        }
        
        return {
            "status": "success",
            "data": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get connection status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get connection status: {str(e)}")

@router.post("/control/start-live-data")
async def start_live_data(
    background_tasks: BackgroundTasks,
    admin_user: User = Depends(require_admin_role)
):
    """
    🔴 START LIVE DATA CONNECTIONS
    Manually start all live data connections
    """
    try:
        service = await get_live_market_data_service()
        if not service.is_running:
            background_tasks.add_task(service.start)
            logger.info("🚀 Live data connections started")
        
        return {
            "status": "success",
            "message": "Live data connections started",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to start live data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start live data: {str(e)}")

@router.post("/control/stop-live-data")
async def stop_live_data(
    background_tasks: BackgroundTasks,
    admin_user: User = Depends(require_admin_role)
):
    """
    🔴 STOP LIVE DATA CONNECTIONS
    Manually stop all live data connections
    """
    try:
        service = await get_live_market_data_service()
        if service.is_running:
            background_tasks.add_task(service.stop)
            logger.info("🛑 Live data connections stopped")
        
        return {
            "status": "success",
            "message": "Live data connections stopped",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to stop live data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop live data: {str(e)}")

# =============================================================================
# DEVELOPMENT UTILITIES
# =============================================================================

@router.get("/debug/market-data")
async def debug_market_data(admin_user: User = Depends(require_admin_role)):
    """
    🔧 DEBUG LIVE MARKET DATA
    Returns detailed debug information about live market data service
    """
    try:
        service = await get_live_market_data_service()
        
        debug_info = {
            "service_status": "running" if service.is_running else "stopped",
            "connections": {
                "active": list(service.connections.keys()),
                "count": len(service.connections)
            },
            "callbacks": {
                "ticker": len(service.ticker_callbacks),
                "candles": len(service.candle_callbacks),
                "orderbook": len(service.orderbook_callbacks)
            },
            "data_status": {
                "current_ticker": service.current_ticker is not None,
                "candle_timeframes": list(service.current_candles.keys()),
                "current_orderbook": service.current_orderbook is not None
            },
            "tasks": {
                "total": len(service.tasks),
                "running": sum(1 for task in service.tasks if not task.done())
            }
        }
        
        return {
            "status": "success",
            "data": debug_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get debug info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get debug info: {str(e)}") 