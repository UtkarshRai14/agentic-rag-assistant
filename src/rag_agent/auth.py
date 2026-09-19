"""Small signed-cookie authentication for the single-user deployment."""

from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import HTTPException, Request, status

from rag_agent.config import settings

AUTH_COOKIE = "rag_session"
SESSION_TTL_SECONDS = 60 * 60 * 24


def _signature(timestamp: str) -> str:
    return hmac.new(
        settings.auth_secret.encode(), timestamp.encode(), hashlib.sha256
    ).hexdigest()


def create_session() -> str:
    timestamp = str(int(time.time()))
    return f"{timestamp}.{_signature(timestamp)}"


def valid_session(value: str | None) -> bool:
    if not settings.auth_secret or not value:
        return False
    try:
        timestamp, signature = value.split(".", 1)
        issued = int(timestamp)
    except (ValueError, AttributeError):
        return False
    if time.time() - issued > SESSION_TTL_SECONDS or issued > time.time() + 30:
        return False
    return hmac.compare_digest(signature, _signature(timestamp))


def require_auth(request: Request) -> None:
    if not settings.app_auth_password or not settings.auth_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        )
    if not valid_session(request.cookies.get(AUTH_COOKIE)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
