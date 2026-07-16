"""
TradePulse.AI User Analytics Service
===================================

Professional user analytics service for enterprise trading system.
Tracks user behavior and analytics using real data only.

Author: TradePulse.AI Development Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json

from app.backend.core.database import get_database_client
from app.backend.core.config import get_settings
from app.backend.core.lazy import LazyProxy

logger = logging.getLogger(__name__)
settings = get_settings()

@dataclass
class UserActivity:
    """User activity data"""
    user_id: str
    activity_type: str
    timestamp: int
    metadata: Dict[str, Any]

class UserAnalyticsService:
    """
    Professional user analytics service for TradePulse.AI
    Tracks user behavior with real data only
    """
    
    def __init__(self):
        self.db_client = get_database_client()
        self.activity_buffer: List[UserActivity] = []
        logger.info("🔧 UserAnalyticsService initialized")
    
    async def track_activity(self, user_id: str, activity_type: str, metadata: Dict[str, Any] = None) -> None:
        """Track user activity"""
        try:
            activity = UserActivity(
                user_id=user_id,
                activity_type=activity_type,
                timestamp=int(datetime.now(timezone.utc).timestamp()),
                metadata=metadata or {}
            )
            
            self.activity_buffer.append(activity)
            await self._store_activity(activity)
            
            # Keep buffer size manageable
            if len(self.activity_buffer) > 1000:
                self.activity_buffer = self.activity_buffer[-500:]
            
        except Exception as e:
            logger.error(f"❌ Error tracking activity: {e}")
    
    async def _store_activity(self, activity: UserActivity) -> None:
        """Store activity in database"""
        try:
            item = {
                'PK': f'USER_ACTIVITY#{activity.user_id}',
                'SK': f'{activity.timestamp}#{activity.activity_type}',
                'user_id': activity.user_id,
                'activity_type': activity.activity_type,
                'timestamp': activity.timestamp,
                'metadata': json.dumps(activity.metadata),
                'date': datetime.fromtimestamp(activity.timestamp, tz=timezone.utc).strftime('%Y-%m-%d'),
                'TTL': activity.timestamp + (90 * 24 * 60 * 60)  # 90 days retention
            }
            
            table = self.db_client.get_table('user_activity_logs')
            table.put_item(Item=item)
            
        except Exception as e:
            logger.error(f"❌ Error storing activity: {e}")
    
    def get_recent_activities(self, limit: int = 100) -> List[UserActivity]:
        """Get recent user activities"""
        return self.activity_buffer[-limit:]

# Global instance
_user_analytics_service = None

def get_user_analytics_service():
    """Get global user analytics service instance"""
    global _user_analytics_service
    if _user_analytics_service is None:
        _user_analytics_service = UserAnalyticsService()
    return _user_analytics_service

# Export for backward compatibility
user_analytics_service = LazyProxy(get_user_analytics_service)