from __future__ import annotations

import time
import uuid
from collections.abc import Callable
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.request_context import camera_id_ctx, request_id_ctx, user_id_ctx

logger = logging.getLogger("sentinelops.api.requests")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attaches request IDs and request-scoped logging metadata."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        user_token = user_id_ctx.set(request.headers.get("X-User-ID"))
        camera_token = camera_id_ctx.set(request.path_params.get("camera_id"))
        start = time.perf_counter()

        try:
            response = await call_next(request)
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "request completed",
                extra={
                    "request_id": request_id,
                    "endpoint": request.url.path,
                    "method": request.method,
                    "latency_ms": latency_ms,
                    "status_code": response.status_code,
                },
            )
        finally:
            request_id_ctx.reset(token)
            user_id_ctx.reset(user_token)
            camera_id_ctx.reset(camera_token)

        response.headers["X-Request-ID"] = request_id
        return response
