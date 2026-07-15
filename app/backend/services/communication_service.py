"""
TradePulse.AI Communication Service
==================================

Professional communication service for enterprise trading system.
Handles notifications and messaging using real data only.

Author: TradePulse.AI Development Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json

from app.backend.core.database import get_database_client
from app.backend.core.config import get_settings
from app.backend.core.lazy import LazyProxy

logger = logging.getLogger(__name__)
settings = get_settings()

class MessageType(Enum):
    """Message type classification"""
    ALERT = "alert"
    NOTIFICATION = "notification"
    TRADE_UPDATE = "trade_update"
    SYSTEM_MESSAGE = "system_message"

@dataclass
class Message:
    """Message data structure"""
    message_id: str
    recipient_id: str
    message_type: MessageType
    title: str
    content: str
    timestamp: int
    is_read: bool = False
    metadata: Dict[str, Any] = None

class CommunicationService:
    """
    Professional communication service for TradePulse.AI
    Handles messaging and notifications with real data only
    """
    
    def __init__(self):
        self.db_client = get_database_client()
        self.message_queue: List[Message] = []
        logger.info("🔧 CommunicationService initialized")
    
    async def send_message(self, recipient_id: str, message_type: MessageType, 
                          title: str, content: str, metadata: Dict[str, Any] = None) -> str:
        """Send a message to a user"""
        try:
            message = Message(
                message_id=f"msg_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                recipient_id=recipient_id,
                message_type=message_type,
                title=title,
                content=content,
                timestamp=int(datetime.now(timezone.utc).timestamp()),
                metadata=metadata or {}
            )
            
            self.message_queue.append(message)
            await self._store_message(message)
            
            logger.info(f"📧 Message sent: {message_type.value} to {recipient_id}")
            return message.message_id
            
        except Exception as e:
            logger.error(f"❌ Error sending message: {e}")
            raise
    
    async def _store_message(self, message: Message) -> None:
        """Store message in database"""
        try:
            item = {
                'PK': f'MESSAGES#{message.recipient_id}',
                'SK': f'{message.timestamp}#{message.message_id}',
                'message_id': message.message_id,
                'recipient_id': message.recipient_id,
                'message_type': message.message_type.value,
                'title': message.title,
                'content': message.content,
                'timestamp': message.timestamp,
                'is_read': message.is_read,
                'metadata': json.dumps(message.metadata) if message.metadata else '{}',
                'date': datetime.fromtimestamp(message.timestamp, tz=timezone.utc).strftime('%Y-%m-%d'),
                'TTL': message.timestamp + (30 * 24 * 60 * 60)  # 30 days retention
            }
            
            table = self.db_client.get_table('messages')
            table.put_item(Item=item)
            
        except Exception as e:
            logger.error(f"❌ Error storing message: {e}")
    
    async def send_trade_alert(self, recipient_id: str, trade_data: Dict[str, Any]) -> None:
        """Send a trade alert notification"""
        title = f"Trade Alert: {trade_data.get('action', 'Unknown').upper()}"
        content = f"Signal: {trade_data.get('action')} {trade_data.get('symbol')} with {trade_data.get('confidence', 0):.1%} confidence"
        
        await self.send_message(
            recipient_id=recipient_id,
            message_type=MessageType.TRADE_UPDATE,
            title=title,
            content=content,
            metadata=trade_data
        )
    
    def get_recent_messages(self, limit: int = 50) -> List[Message]:
        """Get recent messages from queue"""
        return self.message_queue[-limit:]

# Global instance
_communication_service = None

def get_communication_service():
    """Get global communication service instance"""
    global _communication_service
    if _communication_service is None:
        _communication_service = CommunicationService()
    return _communication_service

# Export for backward compatibility
communication_service = LazyProxy(get_communication_service)