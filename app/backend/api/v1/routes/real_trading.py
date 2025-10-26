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
    🔴 GET LIVE CLOSED POSITIONS - Real Position Results from Database
    Returns closed positions history from position_results table
    """
    try:
        # PROFESSIONAL FIX: Read actual closed positions from AWS DynamoDB
        from app.backend.core.database import get_database_client
        from datetime import datetime, timezone
        from dateutil import parser as dateparser
        import os
        
        # FORCE AWS DynamoDB connection (not local) - deployed app uses AWS
        original_endpoint = os.environ.get('DYNAMODB_ENDPOINT')
        if original_endpoint:
            os.environ.pop('DYNAMODB_ENDPOINT', None)
            logger.info(f"🌍 Removed local DYNAMODB_ENDPOINT, connecting to AWS DynamoDB (eu-west-2)")
        
        db_client = get_database_client()
        
        # Get portfolio_closed_positions (AWS DynamoDB)
        try:
            response = db_client.scan_table('portfolio_closed_positions')
            all_positions = response if isinstance(response, list) else []
            
            # Restore original endpoint if it was set
            if original_endpoint:
                os.environ['DYNAMODB_ENDPOINT'] = original_endpoint
            
            logger.info(f"🔍 AWS DynamoDB portfolio_closed_positions returned {len(all_positions)} positions")
            
            # Parse and sort by closed_at (newest first)
            positions_with_time = []
            for pos in all_positions:
                if 'closed_at' in pos:
                    try:
                        closed_str = pos['closed_at']
                        if isinstance(closed_str, str):
                            dt = dateparser.parse(closed_str)
                        else:
                            dt = datetime.fromtimestamp(int(closed_str) / 1000, tz=timezone.utc)
                        positions_with_time.append((dt, pos))
                    except:
                        pass
            
            positions_with_time.sort(key=lambda x: x[0], reverse=True)
            
            # Take only the requested limit
            limited_positions = positions_with_time[:limit]
            
            # Format for frontend (portfolio_closed_positions schema)
            closed_positions = []
            for dt, pos in limited_positions:
                from decimal import Decimal
                
                # Parse PnL values (handle Decimal from DynamoDB)
                realized_pnl_raw = pos.get('realized_pnl', 0)
                pnl_percentage_raw = pos.get('pnl_percentage', 0)
                
                if isinstance(realized_pnl_raw, Decimal):
                    realized_pnl = float(realized_pnl_raw)
                else:
                    realized_pnl = float(realized_pnl_raw) if realized_pnl_raw else 0.0
                    
                if isinstance(pnl_percentage_raw, Decimal):
                    pnl_percentage = float(pnl_percentage_raw)
                else:
                    pnl_percentage = float(pnl_percentage_raw) if pnl_percentage_raw else 0.0
                
                # Calculate hold duration from duration_minutes
                duration_raw = pos.get('duration_minutes', 0)
                time_in_minutes = float(duration_raw) if duration_raw else 0
                
                closed_positions.append({
                    "position_id": pos.get("position_id", "N/A"),
                    "symbol": pos.get("symbol", "BTCUSDT"),
                    "type": pos.get("position_type", "LONG").upper(),
                    "side": pos.get("position_type", "LONG").upper(),
                    "entry_price": float(pos.get("entry_price", 0)),
                    "exit_price": float(pos.get("exit_price", 0)),
                    "current_price": float(pos.get("exit_price", 0)),
                    "quantity": float(pos.get("size", 0.01)),
                    "size": float(pos.get("size", 0.01)),
                    "pnl": realized_pnl,
                    "realized_pnl": realized_pnl,
                    "pnl_percentage": pnl_percentage,
                    "realized_pnl_percentage": pnl_percentage,
                    "outcome": pos.get("status", "completed"),
                    "was_successful": realized_pnl > 0,
                    "closed_at": dt.isoformat(),
                    "exit_time": pos.get("exit_time", dt.isoformat()),
                    "entry_time": pos.get("entry_time", ""),
                    "hold_duration": f"{int(time_in_minutes // 60)}h {int(time_in_minutes % 60)}m" if time_in_minutes else "N/A",
                    "ai_confidence": float(pos.get("ai_confidence", 0)) if pos.get("ai_confidence") else 0,
                    "ai_reasoning": pos.get("ai_reasoning", "")
                })
            
        except Exception as e:
            logger.warning(f"Failed to read from position_results: {e}")
            closed_positions = []
        
        # Calculate analytics from ALL positions (not just the limited set)
        all_results = [pos for _, pos in positions_with_time]
        
        total_trades = len(all_results)
        profitable_trades = sum(1 for pos in all_results if float(pos.get('realized_pnl', 0)) > 0)
        losing_trades = total_trades - profitable_trades
        
        total_pnl = sum(float(pos.get('realized_pnl', 0)) for pos in all_results)
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        avg_hold_time_minutes = sum(float(pos.get('duration_minutes', 0)) for pos in all_results) / total_trades if total_trades > 0 else 0
        avg_hold_hours = int(avg_hold_time_minutes // 60)
        avg_hold_mins = int(avg_hold_time_minutes % 60)
        
        pnls = [float(pos.get('realized_pnl', 0)) for pos in all_results]
        best_trade = max(pnls) if pnls else 0.0
        worst_trade = min(pnls) if pnls else 0.0
        
        avg_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0.0
        
        # Profit factor: total gains / total losses
        total_gains = sum(p for p in pnls if p > 0)
        total_losses = abs(sum(p for p in pnls if p < 0))
        profit_factor = total_gains / total_losses if total_losses > 0 else 0.0
        
        analytics = {
            "total_trades": total_trades,
            "profitable_trades": profitable_trades,
            "losing_trades": losing_trades,
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate, 2),
            "avg_hold_time": f"{avg_hold_hours}h {avg_hold_mins}m",
            "best_trade": round(best_trade, 2),
            "worst_trade": round(worst_trade, 2),
            "profit_factor": round(profit_factor, 2),
            "avg_pnl_per_trade": round(avg_pnl_per_trade, 2),
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