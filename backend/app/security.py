# backend/app/security.py (фрагменты)

import bcrypt
import hmac
import jwt
from fastapi import HTTPException
from typing import Any
from app.config import (
    ACCESS_TTL_SECONDS,
    REFRESH_TTL_SECONDS,
    SECRET_KEY,
    AUTH_USERS,
    AUTH_USERNAME,
    AUTH_PASSWORD,
    AUTH_PASSWORD_HASH,
    PASSWORD_SALT,
)

# helper: соль + bcrypt
def _password_bytes(password: str) -> bytes:
    # объединяем с солью перед хешированием/проверкой, чтобы усилить
    return (password + PASSWORD_SALT).encode("utf-8")

def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(_password_bytes(plain_password), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_password_bytes(plain_password), stored_hash.encode("utf-8"))
    except Exception:
        return False

def verify_user(username: str, password: str) -> bool:
    # 1) try load from AUTH_USERS (secrets)
    if AUTH_USERS:
        stored = AUTH_USERS.get(username)
        if stored:
            return verify_password(password, stored)
        # user not found in secret users
        return False
    # 2) fallback на старую одиночную пару (env)
    username_ok = hmac.compare_digest(username, AUTH_USERNAME)
    # AUTH_PASSWORD_HASH: если задан — используем его, иначе генерируем хеш от AUTH_PASSWORD
    env_hash = AUTH_PASSWORD_HASH or hash_password(AUTH_PASSWORD)
    password_ok = verify_password(password, env_hash)
    return username_ok and password_ok