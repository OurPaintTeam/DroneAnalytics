from typing import Any
import uuid

import jwt

from app.config import ACCESS_TTL_SECONDS, AUTH_USERS, JWT_ALGORITHM, REFRESH_TTL_SECONDS, SECRET_KEY
from app.errors import auth_error
from app.passwords import verify_password
from app.storage import now_ts


def verify_user(username: str, password: str) -> bool:
    stored_hash = AUTH_USERS.get(username)
    if not stored_hash:
        return False
    return verify_password(password, stored_hash)


def _encode_token(subject: str, token_type: str, ttl_seconds: int) -> str:
    now = now_ts()
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + ttl_seconds,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def issue_access_token(subject: str) -> tuple[str, int]:
    token = _encode_token(subject, "access", ACCESS_TTL_SECONDS)
    return token, ACCESS_TTL_SECONDS


def issue_refresh_token(subject: str) -> str:
    return _encode_token(subject, "refresh", REFRESH_TTL_SECONDS)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise auth_error("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise auth_error("Invalid token") from exc

    if payload.get("type") != "access":
        raise auth_error("Invalid token type")
    if not str(payload.get("sub", "")).strip():
        raise auth_error("Invalid access token")
    return payload


def consume_refresh_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise auth_error("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise auth_error("Invalid token") from exc

    if payload.get("type") != "refresh":
        raise auth_error("Invalid token type")

    subject = str(payload.get("sub", "")).strip()
    if not subject:
        raise auth_error("Invalid refresh token")
    return subject
