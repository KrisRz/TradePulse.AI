"""
Professional Brain State Store with Race Condition Prevention
Single source of truth for brain state with proper barriers
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

from app.backend.core.database import DynamoDBClient

logger = logging.getLogger(__name__)


@dataclass
class BrainState:
    """Brain state data structure"""
    enabled: bool
    start_time: str
    last_updated: str
    
    @classmethod
    def from_db_item(cls, item: Optional[Dict[str, Any]]) -> 'BrainState':
        """Create BrainState from DynamoDB item, handling both resource and low-level formats"""
        if not item:
            return cls(enabled=False, start_time="", last_updated="")
        
        # Handle both AttributeValue format and resource format
        def extract_value(field_data):
            if isinstance(field_data, dict):
                # Low-level client format: {"S": "value"} or {"BOOL": True}
                if "S" in field_data:
                    return field_data["S"]
                elif "BOOL" in field_data:
                    return field_data["BOOL"]
                elif "N" in field_data:
                    return field_data["N"]
            # Resource format: direct value
            return field_data
        
        return cls(
            enabled=bool(extract_value(item.get("enabled", False))),
            start_time=str(extract_value(item.get("start_time", ""))),
            last_updated=str(extract_value(item.get("last_updated", "")))
        )


class BrainStateStore:
    """
    Professional Brain State Store with Race Condition Prevention
    
    Ensures single source of truth for brain state across all services
    with proper barriers to prevent race conditions during startup.
    """
    
    def __init__(self, table_name: str = "brain_portfolio_state"):
        self.table_name = table_name
        self._cache: Optional[BrainState] = None
        self._ready = asyncio.Event()
        self._loading = False
        self._load_lock = asyncio.Lock()
        
    async def load_once(self) -> BrainState:
        """Load brain state exactly once with proper locking"""
        if self._cache is not None:
            return self._cache
            
        async with self._load_lock:
            # Double-check after acquiring lock
            if self._cache is not None:
                return self._cache
                
            if self._loading:
                # Another task is loading, wait for it
                await self._ready.wait()
                return self._cache
                
            self._loading = True
            
            try:
                logger.info("🔄 Loading brain state from DynamoDB (single source of truth)")
                
                # Use DynamoDB client with consistent read
                from app.backend.core.config import get_settings
                client = DynamoDBClient(local_development=get_settings().is_development)
                
                response = client.get_item(
                    table_name=self.table_name,
                    key={'id': 'brain_state_global'},
                    consistent_read=True  # CRITICAL: Avoid eventual consistency races in DynamoDB Local
                )
                
                raw_item = response.get('Item') if response else None
                
                if raw_item:
                    logger.info("✅ Brain state found in DB")
                    logger.debug(f"Raw brain state item: {raw_item}")
                else:
                    logger.info("📄 No brain state in DB, using default: DISABLED")
                
                # Create state from DB item (handles both formats)
                self._cache = BrainState.from_db_item(raw_item)
                
                logger.info(f"📥 Brain state loaded: {'ENABLED' if self._cache.enabled else 'DISABLED'}")
                
                # Set the barrier - all waiters can now proceed
                self._ready.set()
                
                return self._cache
                
            except Exception as e:
                logger.error(f"❌ Failed to load brain state: {e}")
                # Set default state and still set the barrier
                self._cache = BrainState(enabled=False, start_time="", last_updated="")
                self._ready.set()
                return self._cache
            finally:
                self._loading = False
    
    async def wait_ready(self) -> BrainState:
        """Wait for brain state to be loaded and return it"""
        await self._ready.wait()
        if self._cache is None:
            # This shouldn't happen, but handle gracefully
            logger.warning("⚠️ Brain state cache is None after ready event")
            return BrainState(enabled=False, start_time="", last_updated="")
        return self._cache
    
    async def update_state(self, enabled: bool, start_time: Optional[str] = None) -> None:
        """Update brain state in both cache and database"""
        try:
            if start_time is None:
                start_time = datetime.utcnow().isoformat()
            
            # Update cache first
            if self._cache:
                self._cache.enabled = enabled
                self._cache.start_time = start_time
                self._cache.last_updated = datetime.utcnow().isoformat()
            else:
                self._cache = BrainState(
                    enabled=enabled,
                    start_time=start_time,
                    last_updated=datetime.utcnow().isoformat()
                )
            
            # Update database
            client = DynamoDBClient(local_development=True)
            
            item = {
                'id': 'brain_state_global',
                'enabled': enabled,
                'start_time': start_time,
                'last_updated': self._cache.last_updated
            }
            
            client.put_item(self.table_name, item)
            
            logger.info(f"✅ Brain state updated: {'ENABLED' if enabled else 'DISABLED'}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update brain state: {e}")
            raise
    
    def is_ready(self) -> bool:
        """Check if brain state has been loaded"""
        return self._ready.is_set()
    
    def get_cached_state(self) -> Optional[BrainState]:
        """Get cached state without waiting (returns None if not loaded)"""
        return self._cache


# Global instance
_brain_state_store: Optional[BrainStateStore] = None


def get_brain_state_store() -> BrainStateStore:
    """Get global brain state store instance"""
    global _brain_state_store
    if _brain_state_store is None:
        _brain_state_store = BrainStateStore()
    return _brain_state_store


def ensure_services_ready(container) -> None:
    """Ensure all services are registered before brain operations"""
    if not hasattr(container, '_initialized') or not container._initialized:
        raise RuntimeError("Services not ready - DI container not initialized")
    
    # Check critical services
    try:
        brain_controller = container.get("brain_controller")
        if brain_controller is None:
            raise RuntimeError("Brain controller not registered")
    except ValueError:
        raise RuntimeError("Brain controller not registered in DI container")
