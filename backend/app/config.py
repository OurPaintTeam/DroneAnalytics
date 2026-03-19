# backend/app/config.py
from __future__ import annotations

import hashlib
import os
import secrets as py_secrets
from pathlib import Path
from typing import Any

import yaml


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_backend_secrets(path: str = "/run/secrets/backend.yaml") -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


_backend_secrets = _load_backend_secrets()

SECRET_KEY = (
    _backend_secrets.get("secret_key")
    or os.getenv("DRONE_SECRET_KEY")
    or py_secrets.token_urlsafe(48)
).encode("utf-8")

JWT_ALGORITHM = os.getenv("DRONE_JWT_ALGORITHM", "HS256")
API_KEY = str(_backend_secrets.get("api_key") or os.getenv("DRONE_API_KEY", "change-me-api-key"))

# Backward-compatible single-user env fallback.
AUTH_USERNAME = os.getenv("DRONE_AUTH_USERNAME", "user")
AUTH_PASSWORD = os.getenv("DRONE_AUTH_PASSWORD", "password")
AUTH_PASSWORD_HASH = os.getenv("DRONE_AUTH_PASSWORD_HASH", "")

ACCESS_TTL_SECONDS = int(os.getenv("DRONE_ACCESS_TTL_SECONDS", "900"))
REFRESH_TTL_SECONDS = int(os.getenv("DRONE_REFRESH_TTL_SECONDS", "604800"))
COOKIE_SECURE = _bool_env("DRONE_COOKIE_SECURE", False)
COOKIE_SAMESITE = os.getenv("DRONE_COOKIE_SAMESITE", "Lax")
CORS_ORIGINS = [x.strip() for x in os.getenv("DRONE_CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elastic:9200")


def _looks_like_bcrypt_hash(value: str) -> bool:
    return value.startswith("$2") and len(value) >= 50


def _normalize_users(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, str] = {}
    for username, value in raw.items():
        if not isinstance(username, str):
            continue
        if isinstance(value, str):
            if _looks_like_bcrypt_hash(value):
                normalized[username] = value
            continue
        if isinstance(value, dict):
            password_hash = value.get("password_hash") or value.get("hash")
            if isinstance(password_hash, str) and _looks_like_bcrypt_hash(password_hash):
                normalized[username] = password_hash
    return normalized


AUTH_USERS = _normalize_users(_backend_secrets.get("users", {}))

# Keep compatibility with old structure but prefer a single API key source.
AUTH_API_KEYS = []
raw_api_keys = _backend_secrets.get("api_keys", [])
if isinstance(raw_api_keys, list):
    AUTH_API_KEYS = [str(x) for x in raw_api_keys if str(x)]
elif isinstance(raw_api_keys, str) and raw_api_keys:
    AUTH_API_KEYS = [raw_api_keys]
