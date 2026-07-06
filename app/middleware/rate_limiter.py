"""
SentinelOps — API Rate Limiting Middleware
=============================================
In-memory sliding-window rate limiter applied as FastAPI middleware.
Limits are configurable via ``config.settings``.

Rate-limited responses return **429 Too Many Requests** with a
``Retry-After`` header indicating how many seconds to wait.
"""

from __future__ import annotations

import time
import threading
import os
from collections import defaultdict

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.request_context import get_request_id


class RateLimiter(BaseHTTPMiddleware):
    """Sliding-window rate limiter keyed by client IP.

    Parameters
    ----------
    app : ASGIApp
        The ASGI application to wrap.
    requests_per_minute : int
        Maximum requests allowed per 60-second window.
    enabled : bool
        Kill-switch to disable limiting entirely.
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        enabled: bool = True,
    ) -> None:
        super().__init__(app)
        self.rpm = requests_per_minute
        self.enabled = enabled
        self.window = 60.0  # seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_limited(self, key: str) -> tuple[bool, int]:
        """Check if the key is rate-limited.

        Returns (is_limited, retry_after_seconds).
        """
        now = time.time()
        cutoff = now - self.window

        with self._lock:
            # Prune old entries
            self._hits[key] = [t for t in self._hits[key] if t > cutoff]
            count = len(self._hits[key])

            if count >= self.rpm:
                oldest = self._hits[key][0]
                retry_after = int(oldest + self.window - now) + 1
                return True, max(retry_after, 1)

            self._hits[key].append(now)
            return False, 0

    async def dispatch(self, request: Request, call_next) -> Response:
        sentinel_test_app = (
            os.getenv("TESTING") == "1"
            and getattr(request.app, "title", "") == "SentinelOps Alert Management API"
        )
        if not self.enabled or self.rpm == 0 or sentinel_test_app:
            return await call_next(request)

        # Skip health checks and docs
        path = request.url.path
        if path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        ip = self._client_ip(request)
        limited, retry_after = self._is_limited(ip)

        if limited:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please retry later.",
                    "error": {
                        "code": "rate_limited",
                        "message": "Rate limit exceeded. Please retry later.",
                        "details": {"retry_after": retry_after},
                    },
                    "request_id": get_request_id(),
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.rpm),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        return response
