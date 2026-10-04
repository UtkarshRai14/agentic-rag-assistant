"""Session-cookie authentication for the API.

The cookie holds a random session token (see ``rag_agent.users``). Every protected
route depends on ``current_user``, and everything a request reads or writes is
scoped to that user.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, Response, status

from rag_agent.config import settings
from rag_agent.users import SESSION_TTL_SECONDS, User, user_for_session

AUTH_COOKIE = "rag_session"


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        AUTH_COOKIE,
        token,
        max_age=SESSION_TTL_SECONDS,
        path="/",
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        AUTH_COOKIE,
        path="/",
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )


def current_user(request: Request) -> User:
    """FastAPI dependency: the logged-in user, or 401.

    It is a plain function, so FastAPI runs it in a worker thread and the SQLite
    lookup does not block the event loop.
    """
    user = user_for_session(request.cookies.get(AUTH_COOKIE))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    return user
