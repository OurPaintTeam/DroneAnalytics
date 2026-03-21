
import hmac
import time
import uuid
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException, status

from app.config import (
    ACCESS_TTL_SECONDS,
    AUTH_PASSWORD,
    AUTH_PASSWORD_HASH,
    AUTH_USERNAME,
    AUTH_USERS,
    JWT_ALGORITHM,
    REFRESH_TTL_SECONDS,
    SECRET_KEY,
)


def auth_error(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": 401, "message": message})


def _utc_ts() -> int:
    return int(time.time())


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")



def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except Exception:
        return False


def verify_user(username: str, password: str) -> bool:
    stored_hash = AUTH_USERS.get(username)
    if not stored_hash:
        return False

    return verify_password(password, stored_hash)


def _encode_token(subject: str, token_type: str, ttl_seconds: int) -> str:
    now = _utc_ts()
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
        raise auth_error("Invalid access token") from exc

    if payload.get("type") != "access":
        raise auth_error("Invalid access token")
    if not payload.get("sub"):
        raise auth_error("Invalid access token")
    return payload


def consume_refresh_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise auth_error("Refresh token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise auth_error("Invalid refresh token") from exc

    if payload.get("type") != "refresh":
        raise auth_error("Invalid refresh token")

    subject = str(payload.get("sub", "")).strip()
    if not subject:
        raise auth_error("Invalid refresh token")
    return subject
