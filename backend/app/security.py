import secrets
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException
from jwt import ExpiredSignatureError, InvalidTokenError

from app.config import ACCESS_TTL_SECONDS, AUTH_PASSWORD, AUTH_PASSWORD_HASH as AUTH_PASSWORD_HASH_ENV, REFRESH_TTL_SECONDS, SECRET_KEY
from app.storage import now_ts


JWT_ALGORITHM = "HS256"
JWT_REQUIRED_CLAIMS = ["exp", "iat", "sub", "type", "jti"]


def auth_error(message: str = "Unauthorized") -> HTTPException:
    return HTTPException(status_code=401, detail={"code": 401, "message": message})


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


AUTH_PASSWORD_HASH = AUTH_PASSWORD_HASH_ENV or hash_password(AUTH_PASSWORD)


def _issue_token(subject: str, token_type: str, ttl_seconds: int) -> str:
    now = now_ts()
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + ttl_seconds,
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def _decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": JWT_REQUIRED_CLAIMS},
        )
    except ExpiredSignatureError as exc:
        raise auth_error("Token expired") from exc
    except InvalidTokenError as exc:
        raise auth_error("Invalid token") from exc
    if payload.get("type") != expected_type:
        raise auth_error("Invalid token type")
    jti = str(payload.get("jti", ""))
    if not jti:
        raise auth_error("Invalid token")
    return dict(payload)


def issue_access_token(subject: str) -> tuple[str, int]:
    return _issue_token(subject, "access", ACCESS_TTL_SECONDS), ACCESS_TTL_SECONDS


def decode_access_token(token: str) -> dict[str, Any]:
    return _decode_token(token, "access")


def issue_refresh_token(subject: str) -> str:
    return _issue_token(subject, "refresh", REFRESH_TTL_SECONDS)


def consume_refresh_token(refresh_token: str) -> str:
    payload = decode_refresh_token(refresh_token)
    subject = str(payload.get("sub", ""))
    if not subject:
        raise auth_error("Invalid refresh token")
    return subject


def decode_refresh_token(token: str) -> dict[str, Any]:
    return _decode_token(token, "refresh")
