"""
DynamoDB Tables Cache
Centralized table verification to prevent ListTables storms
"""

from typing import Set, Optional
import logging

logger = logging.getLogger(__name__)


class DynamoTables:
    """Centralized DynamoDB table cache to prevent repeated ListTables calls"""
    
    _cache: Optional[Set[str]] = None
    _initialized: bool = False
    
    @classmethod
    async def list_once(cls, client) -> Set[str]:
        """List tables once and cache the result"""
        if cls._cache is None:
            logger.info("🔍 Fetching DynamoDB tables (one-time cache)")
            try:
                response = await client.list_tables()
                cls._cache = set(response["TableNames"])
                cls._initialized = True
                logger.info(f"✅ Cached {len(cls._cache)} DynamoDB tables")
            except Exception as e:
                logger.error(f"❌ Failed to cache DynamoDB tables: {e}")
                cls._cache = set()
        return cls._cache
    
    @classmethod
    async def has_table(cls, client, table_name: str) -> bool:
        """Check if table exists (cached)"""
        tables = await cls.list_once(client)
        return table_name in tables
    
    @classmethod
    def reset_cache(cls):
        """Reset cache (for testing)"""
        cls._cache = None
        cls._initialized = False
        logger.info("🔄 DynamoDB tables cache reset")
    
    @classmethod
    def is_initialized(cls) -> bool:
        """Check if cache is initialized"""
        return cls._initialized
