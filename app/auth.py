"""
SentinelOps — Role-Based Access Control (RBAC) Core
===================================================
Provides API key authentication and role-based authorization for FastAPI.

Roles form a hierarchy: Admin (3) > Supervisor (2) > Viewer (1).
Users and API keys are loaded from ``config/users.json``.

Usage::

    from fastapi import Depends
    from app.auth import require_role, Role

    @router.post("/sensitive-action")
    def action(user: User = Depends(require_role(Role.SUPERVISOR))):
        pass
"""

from __future__ import annotations

import json
import logging
from enum import IntEnum
from pathlib import Path
from typing import Any, Callable

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger("sentinelops.auth")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
USERS_FILE = Path("config/users.json")
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Global switch used by the test suite to disable auth entirely.
_AUTH_ENABLED = True


def set_auth_enabled(enabled: bool) -> None:
    """Enable or disable global API authentication. Used by tests."""
    global _AUTH_ENABLED
    _AUTH_ENABLED = enabled
    logger.info("API Authentication enabled: %s", _AUTH_ENABLED)


# ---------------------------------------------------------------------------
# Models & Roles
# ---------------------------------------------------------------------------
class Role(IntEnum):
    """Role hierarchy. Higher numbers have more permissions."""
    VIEWER = 1
    SUPERVISOR = 2
    ADMIN = 3


class User(BaseModel):
    """Authenticated user entity."""
    username: str
    role: Role
    api_key: str

    model_config = ConfigDict(use_enum_values=False)


# Dummy user used when auth is disabled.
_DUMMY_ADMIN = User(username="test_admin", role=Role.ADMIN, api_key="dummy_key")


# ---------------------------------------------------------------------------
# User Store
# ---------------------------------------------------------------------------
class UserStore:
    """Manages user persistence and retrieval from JSON file."""

    def __init__(self, path: Path = USERS_FILE) -> None:
        self._path = path
        self._users: dict[str, User] = {}
        self._load()

    def _load(self) -> None:
        """Load users from the configuration file."""
        if not self._path.exists():
            logger.warning("Users file missing at %s. Creating empty config.", self._path)
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text('{"users": []}')
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._users.clear()
            for u in data.get("users", []):
                role_str = str(u.get("role", "viewer")).upper()
                try:
                    role = Role[role_str]
                except KeyError:
                    logger.warning("Invalid role '%s' for user '%s', defaulting to VIEWER", role_str, u.get("username"))
                    role = Role.VIEWER

                user = User(
                    username=u["username"],
                    role=role,
                    api_key=u["api_key"],
                )
                self._users[user.api_key] = user

            logger.info("Loaded %d users for RBAC", len(self._users))
        except Exception as e:
            logger.error("Failed to load users config: %s", e)

    def _save(self) -> None:
        """Save users back to the configuration file."""
        data = {
            "users": [
                {
                    "username": u.username,
                    "role": u.role.name.lower(),
                    "api_key": u.api_key,
                }
                for u in self._users.values()
            ]
        }
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def authenticate(self, api_key: str) -> User | None:
        """Find a user by their API key."""
        return self._users.get(api_key)

    def list_users(self) -> list[User]:
        return list(self._users.values())

    def create_user(self, user: User) -> None:
        self._users[user.api_key] = user
        self._save()

    def delete_user(self, username: str) -> bool:
        to_delete = None
        for key, u in self._users.items():
            if u.username == username:
                to_delete = key
                break
        if to_delete:
            del self._users[to_delete]
            self._save()
            return True
        return False


# Global singleton
_user_store = UserStore()


# ---------------------------------------------------------------------------
# FastAPI Dependencies
# ---------------------------------------------------------------------------
def require_role(min_role: Role) -> Callable:
    """Dependency generator that enforces a minimum role requirement."""

    def role_dependency(api_key: str | None = Security(API_KEY_HEADER)) -> User:
        if not _AUTH_ENABLED:
            return _DUMMY_ADMIN

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-API-Key header missing",
            )

        user = _user_store.authenticate(api_key)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key",
            )

        if user.role < min_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Requires {min_role.name} role.",
            )

        return user

    return role_dependency


def get_current_user(api_key: str | None = Security(API_KEY_HEADER)) -> User:
    """Dependency to fetch the current user without role checking."""
    return require_role(Role.VIEWER)(api_key)
