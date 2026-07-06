from __future__ import annotations

from contextvars import ContextVar

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)
camera_id_ctx: ContextVar[str | None] = ContextVar("camera_id", default=None)


def get_request_id() -> str | None:
    return request_id_ctx.get()


def get_user_id() -> str | None:
    return user_id_ctx.get()


def get_camera_id() -> str | None:
    return camera_id_ctx.get()
