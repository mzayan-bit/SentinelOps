"""
SentinelOps — Redis Caching Service
======================================
Provides a graceful Redis connection and caching decorators for async functions.
If Redis is unavailable, the decorators will no-op and execute the original
functions, ensuring the application remains available.
"""

import asyncio
import functools
import hashlib
import json
import logging
from typing import Any, Callable, TypeVar, cast

from pydantic import BaseModel
import redis.asyncio as redis

from config.settings import settings

logger = logging.getLogger("sentinelops.cache_service")

# Global Redis client
_redis_client: redis.Redis | None = None
_redis_available: bool = True

def get_redis_client() -> redis.Redis:
    """Initialize or return the global Redis connection pool."""
    global _redis_client
    if _redis_client is None:
        logger.info(f"Connecting to Redis at {settings.redis_url}")
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
        )
    return _redis_client

async def ping_redis() -> bool:
    """Test the Redis connection."""
    global _redis_available
    try:
        client = get_redis_client()
        await client.ping()
        _redis_available = True
        return True
    except Exception as e:
        logger.warning(f"Redis is unavailable: {e}")
        _redis_available = False
        return False

# Type variables for decorator
F = TypeVar('F', bound=Callable[..., Any])

def _generate_cache_key(prefix: str, func_name: str, *args, **kwargs) -> str:
    """Generate a stable string cache key from function arguments."""
    # Convert args/kwargs to a stable string representation
    key_dict = {"args": args, "kwargs": kwargs}
    try:
        key_str = json.dumps(key_dict, sort_keys=True, default=str)
    except Exception:
        # Fallback if args aren't JSON serializable
        key_str = str(args) + str(kwargs)
    
    hash_str = hashlib.md5(key_str.encode()).hexdigest()
    return f"{prefix}{func_name}:{hash_str}"

def cached(prefix: str, ttl_seconds: int = 60) -> Callable[[F], F]:
    """
    Decorator to cache the result of an asynchronous function in Redis.
    
    Args:
        prefix: A string prefix for the cache key (e.g., 'analytics:').
        ttl_seconds: Expiration time in seconds.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            global _redis_available
            
            # If Redis was previously determined to be down, we skip cache overhead.
            # (In a production system, a background task might occasionally re-ping Redis).
            if not _redis_available:
                return await func(*args, **kwargs)
                
            client = get_redis_client()
            cache_key = _generate_cache_key(prefix, func.__name__, *args, **kwargs)
            
            try:
                cached_val = await client.get(cache_key)
                if cached_val:
                    # Deserialize JSON
                    data = json.loads(cached_val)
                    logger.debug(f"Cache HIT for {cache_key}")
                    
                    # We don't magically know the Pydantic model to return,
                    # so we rely on FastAPI to re-parse the raw dict.
                    # Alternatively, if the original function returns a Pydantic model,
                    # we should inspect the return annotation, but returning a dict 
                    # is perfectly fine for FastAPI response models.
                    return data
            except Exception as e:
                logger.warning(f"Redis GET failed for {cache_key}: {e}")
                _redis_available = False
            
            # Cache miss or Redis error
            logger.debug(f"Cache MISS for {cache_key}")
            result = await func(*args, **kwargs)
            
            # Serialize
            try:
                if isinstance(result, BaseModel):
                    # Pydantic v2
                    if hasattr(result, "model_dump"):
                        serialized = result.model_dump(mode="json")
                    else:
                        serialized = result.dict()
                elif isinstance(result, dict):
                    serialized = result
                elif isinstance(result, list) and len(result) > 0 and isinstance(result[0], BaseModel):
                    if hasattr(result[0], "model_dump"):
                        serialized = [item.model_dump(mode="json") for item in result]
                    else:
                        serialized = [item.dict() for item in result]
                else:
                    serialized = result

                cache_data = json.dumps(serialized, default=str)
                await client.set(cache_key, cache_data, ex=ttl_seconds)
            except Exception as e:
                logger.warning(f"Redis SET failed for {cache_key}: {e}")
                
            return result
        return cast(F, wrapper)
    return decorator

async def invalidate_prefix(prefix: str) -> None:
    """Invalidate all keys matching a given prefix."""
    global _redis_available
    if not _redis_available:
        return
        
    client = get_redis_client()
    try:
        # Use SCAN to find keys matching the prefix
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor, match=f"{prefix}*", count=100)
            if keys:
                await client.delete(*keys)
            if cursor == 0:
                break
        logger.debug(f"Invalidated cache prefix: {prefix}")
    except Exception as e:
        logger.warning(f"Redis invalidate failed for prefix {prefix}: {e}")
        _redis_available = False
