import logging
import os
from pathlib import Path
from typing import Any

import yaml

from app.passwords import hash_password


_logger = logging.getLogger(__name__)


def _load_backend_secrets(path: str = "/run/secrets/backend.yaml") -> dict[str, Any]:
    secret_path = Path(path)
    if not secret_path.is_file():
        return {}

    try:
        with secret_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        message = f"Failed to load backend secrets from {path}: {exc}"
        _logger.critical(message)
        raise RuntimeError(message) from exc


def _looks_like_password_hash(value: str) -> bool:
    return value.startswith("pbkdf2_sha256$") or (value.startswith("$2") and len(value) >= 50)


def _normalize_users(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}

    normalized: dict[str, str] = {}
    for username, value in raw.items():
        if not isinstance(username, str):
            continue

        if isinstance(value, str) and _looks_like_password_hash(value):
            normalized[username] = value
            continue

        if isinstance(value, dict):
            password_hash = value.get("password_hash") or value.get("hash")
            if isinstance(password_hash, str) and _looks_like_password_hash(password_hash):
                normalized[username] = password_hash

    return normalized


def _normalize_api_keys(raw: Any) -> list[str]:
    if isinstance(raw, str):
        return [raw] if raw else []
    if not isinstance(raw, list):
        return []
    return [str(key) for key in raw if str(key)]


def _env(value_name: str) -> str | None:
    value = os.getenv(value_name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _env_api_keys() -> list[str]:
    keys: list[str] = []
    single_key = _env("DRONE_API_KEY")
    if single_key:
        keys.append(single_key)

    multi_key_raw = _env("DRONE_API_KEYS")
    if multi_key_raw:
        keys.extend([part.strip() for part in multi_key_raw.split(",") if part.strip()])

    return keys


def _build_env_user() -> dict[str, str]:
    username = _env("DRONE_AUTH_USERNAME")
    password = _env("DRONE_AUTH_PASSWORD")
    if username is None and password is None:
        return {}
    if not username or not password:
        message = "Both DRONE_AUTH_USERNAME and DRONE_AUTH_PASSWORD are required when using env-based auth"
        _logger.critical(message)
        raise RuntimeError(message)
    password_hash = hash_password(password)
    return {username: password_hash}


def _fail(message: str) -> None:
    _logger.critical(message)
    raise RuntimeError(message)


_backend_secrets = _load_backend_secrets()

_secret_key = _env("DRONE_SECRET_KEY") or _backend_secrets.get("secret_key")
if not isinstance(_secret_key, str) or not _secret_key:
    _fail("secret_key is required (set DRONE_SECRET_KEY or secrets/backend.yaml)")

_users = _normalize_users(_backend_secrets.get("users", {}))
_users.update(_build_env_user())
if not _users:
    _fail("At least one user/password pair is required (set DRONE_AUTH_USERNAME/DRONE_AUTH_PASSWORD or secrets/backend.yaml)")

_api_keys = _normalize_api_keys(_backend_secrets.get("api_keys", []))
_api_keys.extend(_env_api_keys())
# preserve order while removing duplicates
API_KEYS = list(dict.fromkeys(key for key in _api_keys if key))
if not API_KEYS:
    _fail("At least one API key is required (set DRONE_API_KEY / DRONE_API_KEYS or secrets/backend.yaml)")

SECRET_KEY = _secret_key.encode("utf-8")
JWT_ALGORITHM = "HS256"
ACCESS_TTL_SECONDS = int(os.getenv("DRONE_ACCESS_TTL_SECONDS", "900"))
REFRESH_TTL_SECONDS = int(os.getenv("DRONE_REFRESH_TTL_SECONDS", "604800"))
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elastic:9200")
CORS_ORIGINS = [
    x.strip()
    for x in os.getenv("DRONE_CORS_ORIGINS", "*").split(",")
    if x.strip()
]
COOKIE_SECURE = True
COOKIE_SAMESITE = "Strict"
AUTH_USERS = _users
