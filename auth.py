"""
Authentification utilisateur — bcrypt + JWT (cookie httpOnly).
"""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from jwt.exceptions import InvalidTokenError

from database import get_user_by_id

JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    raise RuntimeError(
        "Variable d'environnement JWT_SECRET obligatoire. "
        "Définissez-la avant de lancer l'API."
    )
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
    except InvalidTokenError:
        return None


def _get_user_id_from_request(request: Request) -> str | None:
    """Extract user_id from the access_token cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return decode_token(token)


async def get_current_user(request: Request) -> dict:
    """Dependency pour les endpoints API : lève HTTP 401 si non authentifié."""
    user_id = _get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Non authentifié.")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié.")

    return user


async def get_current_user_page(request: Request):
    """Dependency pour les pages HTML : redirige vers /login si non authentifié."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)


async def get_optional_user(request: Request):
    """Dependency: returns the current user dict or None (for public pages)."""
    user_id = _get_user_id_from_request(request)
    if not user_id:
        return None
    return get_user_by_id(user_id)
