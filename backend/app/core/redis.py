"""
Redis configuration and connection management
"""

import json
import logging
from typing import Any, Optional, Union

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis connection
redis_client: Optional[Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection"""
    global redis_client
    
    try:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
        )
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection successful")
        
    except Exception as e:
        logger.error(f"Redis initialization failed: {e}")
        raise


async def close_redis() -> None:
    """Close Redis connection"""
    global redis_client
    
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")


async def get_redis() -> Redis:
    """Get Redis client instance"""
    if not redis_client:
        raise RuntimeError("Redis not initialized")
    return redis_client


class CacheManager:
    """Redis cache manager with JSON serialization"""
    
    @staticmethod
    async def set(
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set a value in cache with optional TTL"""
        try:
            client = await get_redis()
            
            # Serialize value to JSON
            serialized_value = json.dumps(value, default=str)
            
            # Set with TTL
            ttl = ttl or settings.CACHE_TTL_SECONDS
            result = await client.setex(key, ttl, serialized_value)
            
            return result
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    @staticmethod
    async def get(key: str) -> Optional[Any]:
        """Get a value from cache"""
        try:
            client = await get_redis()
            value = await client.get(key)
            
            if value is None:
                return None
            
            # Deserialize from JSON
            return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    @staticmethod
    async def delete(key: str) -> bool:
        """Delete a key from cache"""
        try:
            client = await get_redis()
            result = await client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    @staticmethod
    async def exists(key: str) -> bool:
        """Check if key exists in cache"""
        try:
            client = await get_redis()
            result = await client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    @staticmethod
    async def increment(key: str, amount: int = 1) -> Optional[int]:
        """Increment a numeric value in cache"""
        try:
            client = await get_redis()
            return await client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None
    
    @staticmethod
    async def set_with_expiry(
        key: str,
        value: Any,
        expire_at: int
    ) -> bool:
        """Set value with specific expiration timestamp"""
        try:
            client = await get_redis()
            serialized_value = json.dumps(value, default=str)
            result = await client.set(key, serialized_value, exat=expire_at)
            return result
        except Exception as e:
            logger.error(f"Cache set with expiry error for key {key}: {e}")
            return False


class SessionManager:
    """Redis session manager for user sessions"""
    
    @staticmethod
    def _session_key(user_id: int) -> str:
        """Generate session key for user"""
        return f"session:user:{user_id}"
    
    @staticmethod
    async def create_session(
        user_id: int,
        session_data: dict,
        ttl: Optional[int] = None
    ) -> bool:
        """Create user session"""
        key = SessionManager._session_key(user_id)
        ttl = ttl or settings.SESSION_TTL_SECONDS
        
        return await CacheManager.set(key, session_data, ttl)
    
    @staticmethod
    async def get_session(user_id: int) -> Optional[dict]:
        """Get user session data"""
        key = SessionManager._session_key(user_id)
        return await CacheManager.get(key)
    
    @staticmethod
    async def update_session(
        user_id: int,
        session_data: dict
    ) -> bool:
        """Update existing session"""
        key = SessionManager._session_key(user_id)
        
        # Get existing TTL
        try:
            client = await get_redis()
            ttl = await client.ttl(key)
            
            # If key doesn't exist or has no expiry, use default
            if ttl <= 0:
                ttl = settings.SESSION_TTL_SECONDS
                
            return await CacheManager.set(key, session_data, ttl)
        except Exception as e:
            logger.error(f"Session update error for user {user_id}: {e}")
            return False
    
    @staticmethod
    async def delete_session(user_id: int) -> bool:
        """Delete user session"""
        key = SessionManager._session_key(user_id)
        return await CacheManager.delete(key)
    
    @staticmethod
    async def session_exists(user_id: int) -> bool:
        """Check if user session exists"""
        key = SessionManager._session_key(user_id)
        return await CacheManager.exists(key)


# Export cache and session managers
cache = CacheManager()
session = SessionManager()