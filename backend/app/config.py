import os
from typing import Any

import yaml


def _load_backend_secrets(path: str = "/run/secrets/backend.yaml") -> dict[str, Any]:
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


def _normalize_api_keys(raw: Any) -> list[str]:
    if isinstance(raw, str):
        return [raw] if raw else []
    if not isinstance(raw, list):
        return []
    return [str(key) for key in raw if str(key)]

_backend_secrets = _load_backend_secrets()

_secret_key = _backend_secrets.get("secret_key")
if not isinstance(_secret_key, str) or not _secret_key:
    raise RuntimeError("secret_key is required in backend.yaml")

SECRET_KEY = _secret_key.encode("utf-8")
JWT_ALGORITHM = "HS256"
ACCESS_TTL_SECONDS = int(os.getenv("DRONE_ACCESS_TTL_SECONDS", "900"))
REFRESH_TTL_SECONDS = int(os.getenv("DRONE_REFRESH_TTL_SECONDS", "604800"))
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elastic:9200")
CORS_ORIGINS = [
    x.strip()
    for x in os.getenv("DRONE_CORS_ORIGINS", "http://localhost:5173").split(",")
    if x.strip()
]
COOKIE_SECURE = True
COOKIE_SAMESITE = "Lax"
API_KEYS = _normalize_api_keys(_backend_secrets.get("api_keys", []))
AUTH_USERS = _normalize_users(_backend_secrets.get("users", {}))
