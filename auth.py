"""
Authentification utilisateur — bcrypt + JWT (cookie httpOnly).
"""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24
COOKIE_NAME = "access_token"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> str | None:
    """Decode JWT and return user_id, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def _get_user_id_from_request(request: Request) -> str | None:
    """Extract user_id from the access_token cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return decode_token(token)


async def get_current_user(request: Request):
    """Dependency: returns the current user dict or redirects to /login.
    For API calls (Accept: application/json), returns 401 instead of redirect."""
    from database import get_user_by_id

    user_id = _get_user_id_from_request(request)
    if not user_id:
        if "application/json" in request.headers.get("accept", ""):
            raise HTTPException(status_code=401, detail="Non authentifié.")
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(user_id)
    if not user:
        if "application/json" in request.headers.get("accept", ""):
            raise HTTPException(status_code=401, detail="Non authentifié.")
        return RedirectResponse(url="/login", status_code=303)

    return user


async def get_optional_user(request: Request):
    """Dependency: returns the current user dict or None (for public pages)."""
    from database import get_user_by_id

    user_id = _get_user_id_from_request(request)
    if not user_id:
        return None
    return get_user_by_id(user_id)
