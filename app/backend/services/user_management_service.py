"""
TradePulse.AI User Management Service
====================================

Professional user management service for enterprise trading system.
Manages user accounts and authentication using real data only.

Author: TradePulse.AI Development Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import hashlib
import uuid

from app.backend.core.database import get_database_client
from app.backend.core.config import get_settings
from app.backend.core.lazy import LazyProxy

logger = logging.getLogger(__name__)
settings = get_settings()

@dataclass
class User:
    """User data structure"""
    user_id: str
    email: str
    username: str
    created_at: int
    last_active: int
    is_active: bool = True

class UserManagementService:
    """
    Professional user management service for TradePulse.AI
    Manages user accounts with real data only
    """
    
    def __init__(self):
        self.db_client = get_database_client()
        self.users_cache: Dict[str, User] = {}
        logger.info("🔧 UserManagementService initialized")
    
    async def create_user(self, email: str, username: str) -> str:
        """Create a new user account"""
        try:
            user_id = str(uuid.uuid4())
            
            user = User(
                user_id=user_id,
                email=email,
                username=username,
                created_at=int(datetime.now(timezone.utc).timestamp()),
                last_active=int(datetime.now(timezone.utc).timestamp())
            )
            
            await self._store_user(user)
            self.users_cache[user_id] = user
            
            logger.info(f"👤 Created user: {user_id} ({email})")
            return user_id
            
        except Exception as e:
            logger.error(f"❌ Error creating user: {e}")
            raise
    
    async def _store_user(self, user: User) -> None:
        """Store user in database"""
        try:
            item = {
                'id': user.user_id,
                'email': user.email,
                'username': user.username,
                'created_at': user.created_at,
                'last_active': user.last_active,
                'is_active': user.is_active,
                'date': datetime.fromtimestamp(user.created_at, tz=timezone.utc).strftime('%Y-%m-%d')
            }
            
            table = self.db_client.get_table('tradepulse-users')
            table.put_item(Item=item)
            
        except Exception as e:
            logger.error(f"❌ Error storing user: {e}")
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        if user_id in self.users_cache:
            return self.users_cache[user_id]
        
        try:
            table = self.db_client.get_table('tradepulse-users')
            response = table.get_item(Key={'id': user_id})
            
            if 'Item' in response:
                item = response['Item']
                user = User(
                    user_id=item['id'],
                    email=item['email'],
                    username=item['username'],
                    created_at=int(item['created_at']),
                    last_active=int(item['last_active']),
                    is_active=item.get('is_active', True)
                )
                self.users_cache[user_id] = user
                return user
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user: {e}")
            return None
    
    def get_cached_users(self) -> List[User]:
        """Get all cached users"""
        return list(self.users_cache.values())

# Global instance
_user_management_service = None

def get_user_management_service():
    """Get global user management service instance"""
    global _user_management_service
    if _user_management_service is None:
        _user_management_service = UserManagementService()
    return _user_management_service

# Export for backward compatibility
user_management_service = LazyProxy(get_user_management_service)