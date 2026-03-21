import os
from typing import Any

import yaml


def _load_backend_secrets(path="/run/secrets/backend.yaml") -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _looks_like_bcrypt_hash(value: str) -> bool:
    return value.startswith("$2") and len(value) >= 50


def _normalize_users(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}

    normalized: dict[str, str] = {}
    for username, value in raw.items():
        if not isinstance(username, str):
            continue

        if isinstance(value, str) and _looks_like_bcrypt_hash(value):
            normalized[username] = value
            continue

        if isinstance(value, dict):
            password_hash = value.get("password_hash") or value.get("hash")
            if isinstance(password_hash, str) and _looks_like_bcrypt_hash(password_hash):
                normalized[username] = password_hash

    return normalized


_backend_secrets = _load_backend_secrets()

secret_key = _backend_secrets.get("secret_key")
if not isinstance(secret_key, str) or not secret_key:
    raise RuntimeError("secret_key is required in backend.yaml")

SECRET_KEY = secret_key.encode("utf-8")

JWT_ALGORITHM = "HS256"

API_KEYS = _backend_secrets.get("api_keys", [])
if isinstance(API_KEYS, str):
    API_KEYS = [API_KEYS]
elif not isinstance(API_KEYS, list):
    API_KEYS = []

AUTH_USERS = _normalize_users(_backend_secrets.get("users", {}))

COOKIE_SECURE = True
COOKIE_SAMESITE = "Lax"