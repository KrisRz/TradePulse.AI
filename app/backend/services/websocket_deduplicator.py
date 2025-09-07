"""
WebSocket Message Deduplicator for TradePulse.AI
Prevents duplicate processing of WebSocket messages and manages subscription state
"""

import asyncio
import time
import logging
from typing import Dict, Set, Optional, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass
import threading

logger = logging.getLogger(__name__)


@dataclass
class MessageDeduplicator:
    """Deduplicate WebSocket messages based on event ID and timestamp"""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minute TTL
        self.seen_messages: Dict[str, float] = {}
        self.ttl_seconds = ttl_seconds
        self.lock = threading.Lock()
        self.cleanup_task: Optional[asyncio.Task] = None
        
    def is_duplicate(self, event_type: str, event_time: int, extra_id: str = "") -> bool:
        """
        Check if message is duplicate based on event type and timestamp
        
        Args:
            event_type: Type of event (e.g., '24hrTicker', 'kline')
            event_time: Event timestamp from Binance (E field)
            extra_id: Additional identifier for uniqueness (e.g., symbol, interval)
            
        Returns:
            bool: True if duplicate, False if new message
        """
        # Create unique event ID
        event_id = f"{event_type}:{event_time}:{extra_id}"
        current_time = time.time()
        
        with self.lock:
            # Clean old entries first
            self._cleanup_old_entries(current_time)
            
            # Check if we've seen this message
            if event_id in self.seen_messages:
                logger.debug(f"🔄 Duplicate WebSocket message: {event_id}")
                return True
                
            # Mark as seen
            self.seen_messages[event_id] = current_time
            return False
    
    def _cleanup_old_entries(self, current_time: float):
        """Remove expired entries from seen_messages"""
        cutoff_time = current_time - self.ttl_seconds
        expired_keys = [
            key for key, timestamp in self.seen_messages.items() 
            if timestamp < cutoff_time
        ]
        
        for key in expired_keys:
            del self.seen_messages[key]
            
        if expired_keys:
            logger.debug(f"🧹 Cleaned {len(expired_keys)} expired WebSocket message IDs")
    
    async def start_cleanup_task(self):
        """Start background cleanup task"""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("🧹 Started WebSocket deduplicator cleanup task")
    
    async def stop_cleanup_task(self):
        """Stop background cleanup task"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
            logger.info("🛑 Stopped WebSocket deduplicator cleanup task")
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired entries"""
        while True:
            try:
                await asyncio.sleep(60)  # Clean every minute
                with self.lock:
                    self._cleanup_old_entries(time.time())
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket deduplicator cleanup: {e}")


class SubscriptionManager:
    """Manage WebSocket subscriptions to prevent duplicate connections"""
    
    def __init__(self):
        self.active_subscriptions: Dict[str, Dict[str, Any]] = {}
        self.subscription_lock = threading.Lock()
        
    def is_subscribed(self, stream_key: str) -> bool:
        """Check if already subscribed to a stream"""
        with self.subscription_lock:
            subscription = self.active_subscriptions.get(stream_key)
            if subscription:
                # Check if subscription is still active
                if subscription.get('status') == 'active':
                    logger.debug(f"🔄 Already subscribed to {stream_key}")
                    return True
                else:
                    # Clean up inactive subscription
                    del self.active_subscriptions[stream_key]
                    
        return False
    
    def add_subscription(self, stream_key: str, websocket_task: asyncio.Task, 
                        symbol: str, stream_type: str):
        """Add active subscription"""
        with self.subscription_lock:
            self.active_subscriptions[stream_key] = {
                'status': 'active',
                'task': websocket_task,
                'symbol': symbol,
                'stream_type': stream_type,
                'created_at': time.time()
            }
            logger.info(f"➕ Added WebSocket subscription: {stream_key}")
    
    def remove_subscription(self, stream_key: str):
        """Remove subscription"""
        with self.subscription_lock:
            if stream_key in self.active_subscriptions:
                del self.active_subscriptions[stream_key]
                logger.info(f"➖ Removed WebSocket subscription: {stream_key}")
    
    def get_active_subscriptions(self) -> Dict[str, Dict[str, Any]]:
        """Get all active subscriptions"""
        with self.subscription_lock:
            return dict(self.active_subscriptions)
    
    def cleanup_failed_subscriptions(self):
        """Clean up failed/cancelled subscription tasks"""
        with self.subscription_lock:
            failed_keys = []
            for stream_key, subscription in self.active_subscriptions.items():
                task = subscription.get('task')
                if task and (task.done() or task.cancelled()):
                    failed_keys.append(stream_key)
            
            for key in failed_keys:
                logger.warning(f"🧹 Cleaning up failed subscription: {key}")
                del self.active_subscriptions[key]
            
            return len(failed_keys)


# Global instances for application-wide deduplication
_message_deduplicator: Optional[MessageDeduplicator] = None
_subscription_manager: Optional[SubscriptionManager] = None


def get_message_deduplicator() -> MessageDeduplicator:
    """Get global message deduplicator instance"""
    global _message_deduplicator
    if _message_deduplicator is None:
        _message_deduplicator = MessageDeduplicator()
    return _message_deduplicator


def get_subscription_manager() -> SubscriptionManager:
    """Get global subscription manager instance"""
    global _subscription_manager
    if _subscription_manager is None:
        _subscription_manager = SubscriptionManager()
    return _subscription_manager


async def init_websocket_deduplication():
    """Initialize WebSocket deduplication system"""
    deduplicator = get_message_deduplicator()
    await deduplicator.start_cleanup_task()
    logger.info("✅ WebSocket deduplication system initialized")


async def shutdown_websocket_deduplication():
    """Shutdown WebSocket deduplication system"""
    if _message_deduplicator:
        await _message_deduplicator.stop_cleanup_task()
    logger.info("🛑 WebSocket deduplication system shutdown")


def process_websocket_message(event_type: str, data: Dict[str, Any], 
                             processor_func, extra_id: str = "") -> bool:
    """
    Process WebSocket message with deduplication
    
    Args:
        event_type: Type of event ('24hrTicker', 'kline', etc.)
        data: Message data from WebSocket
        processor_func: Function to process the message
        extra_id: Additional identifier for uniqueness
        
    Returns:
        bool: True if processed, False if duplicate
    """
    deduplicator = get_message_deduplicator()
    
    # Extract event time from message
    event_time = data.get('E', 0)  # Binance event time
    if not event_time:
        # Fallback for messages without event time
        event_time = int(time.time() * 1000)
    
    # Check for duplicates
    if deduplicator.is_duplicate(event_type, event_time, extra_id):
        return False
    
    # Process the message
    try:
        processor_func(data)
        return True
    except Exception as e:
        logger.error(f"Error processing WebSocket message {event_type}: {e}")
        return False


# Utility functions for common WebSocket message types
def process_ticker_message(data: Dict[str, Any], processor_func) -> bool:
    """Process 24hr ticker message with deduplication"""
    symbol = data.get('s', 'UNKNOWN')
    return process_websocket_message('24hrTicker', data, processor_func, symbol)


def process_kline_message(data: Dict[str, Any], processor_func) -> bool:
    """Process kline message with deduplication"""
    if 'k' in data:
        kline = data['k']
        symbol = kline.get('s', 'UNKNOWN')
        interval = kline.get('i', 'UNKNOWN')
        kline_start_time = kline.get('t', 0)  # Kline start time for uniqueness
        extra_id = f"{symbol}:{interval}:{kline_start_time}"
    else:
        extra_id = "UNKNOWN"
    
    return process_websocket_message('kline', data, processor_func, extra_id)


def process_depth_message(data: Dict[str, Any], processor_func) -> bool:
    """Process orderbook depth message with deduplication"""
    symbol = data.get('s', 'UNKNOWN')
    last_update_id = data.get('u', 0)  # Last update ID for uniqueness
    extra_id = f"{symbol}:{last_update_id}"
    
    return process_websocket_message('depth', data, processor_func, extra_id)
