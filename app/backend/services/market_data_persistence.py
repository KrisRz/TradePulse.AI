"""
Market data persistence service.

Subscribes to the live candlestick WebSocket and persists CLOSED candles to DynamoDB.

Local (dev): writes to 'live_candles'
Production: writes to 'tradepulse-live_candles-<ENV>' (AWS-style naming)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

from app.backend.core.config import get_settings
from app.backend.core.database import DynamoDBClient
from app.backend.services.live_market_data import get_live_market_data_service


def _resolve_live_candles_table_name() -> str:
    settings = get_settings()
    if settings.is_development:
        return "live_candles"
    # Use AWS naming convention in non-dev
    env_suffix = settings.ENVIRONMENT
    return f"tradepulse-live_candles-{env_suffix}"


async def start_candle_persistence() -> None:
    """Start candle persistence loop by subscribing to closed candle events.

    This function attaches a callback to the live candle stream that writes
    closed candles into DynamoDB. It runs as a background coroutine.
    """
    settings = get_settings()
    client = DynamoDBClient(local_development=settings.is_development)
    table_name = _resolve_live_candles_table_name()

    live_service = await get_live_market_data_service()

    async def _save_closed_candle(candle: Dict[str, Any]) -> None:
        try:
            if not candle.get("is_closed"):
                return
            item: Dict[str, Any] = {
                "symbol": candle["symbol"],
                "timestamp": int(candle["close_time"]),
                "interval": candle["interval"],
                # DynamoDB requires Decimal for non-integer numeric values
                "open": Decimal(str(candle["open"])),
                "high": Decimal(str(candle["high"])),
                "low": Decimal(str(candle["low"])),
                "close": Decimal(str(candle["close"])),
                "volume": Decimal(str(candle["volume"])),
                "trades": int(candle.get("trades", 0)),
                "date_hour": datetime.fromtimestamp(candle["close_time"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d-%H"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            client.put_item(table_name, item)
        except Exception:
            # Swallow to avoid breaking callback loop
            pass

    # Register callback
    live_service.subscribe_to_candles(_save_closed_candle)  # type: ignore[arg-type]

    # Keep task alive
    while True:
        await asyncio.sleep(60)


async def load_recent(symbol: str = "BTCUSDT", horizon: str = '30m') -> list:
    """PHASE 1A: Load recent candles for engines after stream interruption"""
    try:
        table_name = _resolve_live_candles_table_name()
        settings = get_settings()
        client = DynamoDBClient(local_development=settings.is_development)
        
        # Calculate time range
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        if horizon == '30m':
            start_time = now - timedelta(minutes=30)
        elif horizon == '4h':
            start_time = now - timedelta(hours=4)
        elif horizon == '24h':
            start_time = now - timedelta(hours=24)
        else:
            start_time = now - timedelta(minutes=30)  # Default
        
        # Query by timestamp range (simplified - may need optimization)
        try:
            items = client.scan_table(table_name)
            # Filter by symbol and time range
            candles = []
            start_timestamp = int(start_time.timestamp() * 1000)
            for item in items:
                if (item.get('symbol') == symbol and 
                    item.get('timestamp', 0) >= start_timestamp):
                    candles.append(item)
                    
            # Sort by timestamp
            candles.sort(key=lambda x: x.get('timestamp', 0))
            return candles
            
        except Exception as e:
            print(f"Warning: Could not load recent candles: {e}")
            return []
            
    except Exception as e:
        print(f"Error in load_recent: {e}")
        return []


async def write_decisions(entry_decision, exit_decision, risk_assessment, signal):
    """PHASE 1A: Write trading decisions for audit trail"""
    try:
        settings = get_settings()
        client = DynamoDBClient(local_development=settings.is_development)
        
        # Add day partition key for proper DynamoDB structure
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        decision_item = {
            "day": today,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": "BTCUSDT",
            "signal_action": signal.action if signal else "none",
            "signal_confidence": Decimal(str(signal.confidence)) if signal else Decimal('0.0'),
            "entry_decision": entry_decision.get('should_enter', False) if entry_decision else False,
            "entry_reason": entry_decision.get('reasoning', 'none') if entry_decision else "none",
            "exit_decision": exit_decision.get('should_exit', False) if exit_decision else False,
            "exit_reason": exit_decision.get('reasoning', 'none') if exit_decision else "none",
            "risk_score": Decimal(str(getattr(risk_assessment, 'risk_score', 0.0))) if risk_assessment else Decimal('0.0'),
            "risk_block": getattr(risk_assessment, 'block_reason', None) if risk_assessment else None
        }
        
        # Try to write to decisions table (create if needed)
        try:
            client.put_item("trading_decisions", decision_item)
        except Exception:
            # Silently fail - not critical for trading operation
            pass
            
    except Exception as e:
        print(f"Decision audit logging failed: {e}")


async def write_orders(order_data: Dict):
    """PHASE 1A: Write order execution details"""
    try:
        settings = get_settings()
        client = DynamoDBClient(local_development=settings.is_development)
        
        order_item = {
            "timestamp": order_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "symbol": order_data.get("symbol", "BTCUSDT"),
            "action": order_data.get("action", "unknown"),
            "size": Decimal(str(order_data.get("size", 0))),
            "price": Decimal(str(order_data.get("price", 0))),
            "order_id": order_data.get("order_id", "virtual"),
            "slippage": Decimal(str(order_data.get("slippage", 0.0)))
        }
        
        # Try to write to orders table (create if needed)
        try:
            client.put_item("trading_orders", order_item)
        except Exception:
            # Silently fail - not critical for trading operation
            pass
            
    except Exception as e:
        print(f"Order audit logging failed: {e}")


