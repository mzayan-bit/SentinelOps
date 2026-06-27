"""
SentinelOps — Cache Service Tests
====================================
Tests the generic `@cached` decorator and graceful degradation logic.
"""

import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from pydantic import BaseModel
from app.services.cache_service import cached, invalidate_prefix

class DummyModel(BaseModel):
    id: int
    name: str

@pytest_asyncio.fixture(autouse=True)
def reset_cache_state():
    """Reset the global state in cache_service before each test."""
    from app.services import cache_service
    cache_service._redis_available = True
    cache_service._redis_client = None

@pytest.mark.asyncio
@patch("app.services.cache_service.get_redis_client")
async def test_cached_decorator_hit(mock_get_client):
    """Test that a cache hit returns the cached data and skips the function."""
    mock_redis = AsyncMock()
    # Return JSON string simulating a previous SET
    mock_redis.get.return_value = '{"id": 1, "name": "test"}'
    mock_get_client.return_value = mock_redis

    call_count = 0

    @cached(prefix="test:", ttl_seconds=10)
    async def dummy_func():
        nonlocal call_count
        call_count += 1
        return {"id": 1, "name": "test"}

    result = await dummy_func()

    assert result == {"id": 1, "name": "test"}
    assert call_count == 0  # Function was NOT executed
    mock_redis.get.assert_called_once()
    mock_redis.setex.assert_not_called()

@pytest.mark.asyncio
@patch("app.services.cache_service.get_redis_client")
async def test_cached_decorator_miss_and_set(mock_get_client):
    """Test that a cache miss executes the function and stores the result."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Cache miss
    mock_get_client.return_value = mock_redis

    call_count = 0

    @cached(prefix="test:", ttl_seconds=10)
    async def dummy_func():
        nonlocal call_count
        call_count += 1
        return DummyModel(id=2, name="miss")

    result = await dummy_func()

    assert result.id == 2
    assert call_count == 1  # Function WAS executed
    mock_redis.get.assert_called_once()
    mock_redis.set.assert_called_once()
    
    # Check what was stored
    args, kwargs = mock_redis.set.call_args
    key = args[0]
    value = args[1]
    ttl = kwargs.get("ex")
    assert key.startswith("test:dummy_func:")
    assert ttl == 10
    
    data = json.loads(value)
    assert data["id"] == 2
    assert data["name"] == "miss"

@pytest.mark.asyncio
@patch("app.services.cache_service.get_redis_client")
async def test_graceful_degradation_on_get_error(mock_get_client):
    """Test that if Redis GET fails, the function executes normally."""
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("Connection refused")
    mock_get_client.return_value = mock_redis

    @cached(prefix="test:", ttl_seconds=10)
    async def dummy_func():
        return {"fallback": True}

    # Should not raise exception
    result = await dummy_func()
    assert result == {"fallback": True}
    
    # Global state should mark Redis as unavailable
    from app.services import cache_service
    assert cache_service._redis_available is False

@pytest.mark.asyncio
@patch("app.services.cache_service.get_redis_client")
async def test_fast_fail_when_unavailable(mock_get_client):
    """Test that subsequent calls bypass Redis entirely if it's marked down."""
    from app.services import cache_service
    cache_service._redis_available = False
    
    mock_redis = AsyncMock()
    mock_get_client.return_value = mock_redis

    call_count = 0

    @cached(prefix="test:", ttl_seconds=10)
    async def dummy_func():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await dummy_func()
    
    assert result == "ok"
    assert call_count == 1
    # Redis client should not have been touched
    mock_get_client.assert_not_called()

@pytest.mark.asyncio
@patch("app.services.cache_service.get_redis_client")
async def test_invalidate_prefix(mock_get_client):
    """Test that invalidate_prefix correctly SCANs and DELETEs."""
    mock_redis = AsyncMock()
    # Return cursor 0 (done) and two keys
    mock_redis.scan.return_value = (0, ["cameras:1", "cameras:2"])
    mock_get_client.return_value = mock_redis

    await invalidate_prefix("cameras:")
    
    mock_redis.scan.assert_called_once_with(0, match="cameras:*", count=100)
    mock_redis.delete.assert_called_once_with("cameras:1", "cameras:2")
