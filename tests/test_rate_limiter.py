"""
SentinelOps — Rate Limiter Tests
===================================
Verifies 429 responses, Retry-After headers, health bypass, and
the enable/disable kill-switch.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.rate_limiter import RateLimiter


def _make_app(rpm: int = 5, enabled: bool = True) -> FastAPI:
    """Build a minimal FastAPI app with the rate limiter attached."""
    app = FastAPI()
    app.add_middleware(RateLimiter, requests_per_minute=rpm, enabled=enabled)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/test")
    async def test_endpoint():
        return {"result": "ok"}

    @app.post("/api/predict")
    async def predict():
        return {"prediction": "safe"}

    return app


# ------------------------------------------------------------------
# Core behaviour
# ------------------------------------------------------------------

class TestRateLimiting:
    def test_allows_under_limit(self):
        client = TestClient(_make_app(rpm=5))
        for _ in range(5):
            r = client.get("/api/test")
            assert r.status_code == 200
            assert "X-RateLimit-Limit" in r.headers

    def test_blocks_over_limit(self):
        client = TestClient(_make_app(rpm=3))
        # Exhaust the limit
        for _ in range(3):
            assert client.get("/api/test").status_code == 200

        # 4th request should be blocked
        r = client.get("/api/test")
        assert r.status_code == 429
        assert r.json()["detail"] == "Rate limit exceeded. Please retry later."
        assert "Retry-After" in r.headers
        assert int(r.headers["Retry-After"]) > 0

    def test_429_on_post_endpoint(self):
        client = TestClient(_make_app(rpm=2))
        assert client.post("/api/predict").status_code == 200
        assert client.post("/api/predict").status_code == 200
        assert client.post("/api/predict").status_code == 429

    def test_rate_limit_header_present(self):
        client = TestClient(_make_app(rpm=10))
        r = client.get("/api/test")
        assert r.headers["X-RateLimit-Limit"] == "10"


# ------------------------------------------------------------------
# Bypass & kill-switch
# ------------------------------------------------------------------

class TestBypass:
    def test_health_bypasses_limit(self):
        client = TestClient(_make_app(rpm=1))
        # Use up the limit on a normal endpoint
        assert client.get("/api/test").status_code == 200
        assert client.get("/api/test").status_code == 429

        # Health should still work
        for _ in range(5):
            assert client.get("/health").status_code == 200

    def test_disabled_allows_all(self):
        client = TestClient(_make_app(rpm=1, enabled=False))
        for _ in range(20):
            r = client.get("/api/test")
            assert r.status_code == 200
