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
from app.backend.utils.dynamodb_key_normalizer import safe_put_item, normalize_dynamodb_item
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
            
            # Extract OHLCV values for validation
            open_price = float(candle["open"])
            high_price = float(candle["high"])
            low_price = float(candle["low"])
            close_price = float(candle["close"])
            volume = float(candle["volume"])
            trades = int(candle.get("trades", 0))
            
            # Professional validation guardrails
            if not _is_valid_candle(open_price, high_price, low_price, close_price, volume, trades):
                print(f"⚠️ Invalid candle data for {candle['symbol']}: O={open_price} H={high_price} L={low_price} C={close_price}")
                return
            
            # Professional schema with composite PK for idempotency
            symbol = candle["symbol"]
            interval = candle["interval"]
            timestamp_ms = int(candle["close_time"])
            
            item: Dict[str, Any] = {
                "pk": f"{symbol}#{interval}",  # Composite partition key
                "ts": timestamp_ms,            # Sort key (timestamp)
                "symbol": symbol,
                "interval": interval,
                "timestamp": timestamp_ms,     # Keep for backward compatibility
                # DynamoDB requires Decimal for non-integer numeric values
                "open": Decimal(str(open_price)),
                "high": Decimal(str(high_price)),
                "low": Decimal(str(low_price)),
                "close": Decimal(str(close_price)),
                "volume": Decimal(str(volume)),
                "trades": trades,
                "date_hour": datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d-%H"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            
            # Idempotent write - only insert if timestamp doesn't exist
            try:
                client.put_item_conditional(
                    table_name, 
                    item, 
                    condition_expression="attribute_not_exists(#ts)",
                    expression_attribute_names={"#ts": "ts"}
                )
            except Exception as e:
                if "ConditionalCheckFailedException" in str(e):
                    # Duplicate candle - safe to ignore
                    pass
                else:
                    print(f"❌ Failed to save candle for {symbol}: {e}")
                    
        except Exception as e:
            # Log but don't break the callback loop
            print(f"❌ Candle persistence error: {e}")


    # Register callback
    live_service.subscribe_to_candles(_save_closed_candle)  # type: ignore[arg-type]

    # Keep task alive
    while True:
        await asyncio.sleep(60)


def _is_valid_candle(open_price: float, high_price: float, low_price: float, 
                    close_price: float, volume: float, trades: int) -> bool:
    """Professional OHLCV validation guardrails"""
    try:
        # Basic range validation
        if any(price <= 0 for price in [open_price, high_price, low_price, close_price]):
            return False
        
        if volume < 0 or trades < 0:
            return False
        
        # OHLC consistency validation
        min_price = min(open_price, close_price)
        max_price = max(open_price, close_price)
        
        # Low must be <= all other prices, High must be >= all other prices
        if low_price > min_price or high_price < max_price:
            return False
            
        # Additional sanity checks
        if low_price > high_price:
            return False
            
        # Extreme price movement check (> 50% in one minute is suspicious)
        price_range = high_price - low_price
        avg_price = (high_price + low_price) / 2
        if price_range / avg_price > 0.5:  # 50% range
            return False
            
        return True
        
    except Exception:
        return False


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


async def write_decisions(entry_decision, exit_decision, risk_assessment, signal) -> bool:
    """
    PHASE 1A: Write trading decisions for audit trail
    
    Returns:
        bool: True if successfully written, False otherwise
    """
    try:
        settings = get_settings()
        client = DynamoDBClient(local_development=settings.is_development)
        
        # Add day partition key for proper DynamoDB structure
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        # Ensure proper key types for DynamoDB
        timestamp_now = datetime.now(timezone.utc)
        
        decision_item = {
            "day": str(today),  # Ensure string type
            "timestamp": timestamp_now.isoformat(),  # Keep as string to match schema
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
        
        # Normalize keys before write to prevent type mismatch
        normalized_item = normalize_dynamodb_item("trading_decisions", decision_item)
        
        # Try to write to decisions table with safe wrapper
        table = client.get_table("trading_decisions")
        success = safe_put_item(table, normalized_item, "trading_decisions")
        
        if success:
            return True
        else:
            print(f"Decision audit write failed: safe_put_item returned False")
            return False
            
    except Exception as e:
        print(f"Decision audit logging failed: {e}")
        return False


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


