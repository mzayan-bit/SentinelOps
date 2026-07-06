from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_context import get_request_id

logger = logging.getLogger("sentinelops.api.errors")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorResponse(BaseModel):
    detail: Any
    error: ErrorDetail
    request_id: str | None = Field(default=None)


class AppError(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "internal_error"
    message = "Internal server error"

    def __init__(self, message: str | None = None, details: Any = None) -> None:
        self.message = message or self.message
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    message = "Resource not found"


class ValidationAppError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"
    message = "Validation failed"


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_error"
    message = "Authentication failed"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "permission_denied"
    message = "Permission denied"


class DatabaseError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "database_error"
    message = "Database operation failed"


class AIInferenceError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "ai_inference_error"
    message = "AI inference failed"


def _error_payload(*, detail: Any, code: str, message: str, details: Any = None) -> dict[str, Any]:
    return ErrorResponse(
        detail=detail,
        error=ErrorDetail(code=code, message=message, details=details),
        request_id=get_request_id(),
    ).model_dump(mode="json")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                detail=exc.message,
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_payload(
                detail=exc.errors(),
                code="validation_error",
                message="Request validation failed",
                details=exc.errors(),
            ),
        )

    @app.exception_handler(HTTPException)
    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
        status_code = exc.status_code
        code = {
            400: "bad_request",
            401: "authentication_error",
            403: "permission_denied",
            404: "not_found",
            409: "conflict",
            422: "validation_error",
            429: "rate_limited",
        }.get(status_code, "http_error")
        return JSONResponse(
            status_code=status_code,
            headers=getattr(exc, "headers", None),
            content=_error_payload(
                detail=exc.detail,
                code=code,
                message=str(exc.detail),
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload(
                detail="Internal server error",
                code="internal_server_error",
                message="Internal server error",
            ),
        )
