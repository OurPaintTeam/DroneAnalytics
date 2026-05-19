import logging
import os
from pathlib import Path
import shlex
from typing import Any

import yaml

_logger = logging.getLogger(__name__)


def _fail(message: str) -> None:
    # Log a generic error to avoid leaking sensitive configuration details
    _logger.critical("Backend configuration error")
    raise RuntimeError(message)


def _load_backend_secrets(path: str = "/run/secrets/backend.yaml") -> dict[str, Any]:
    secret_path = Path(path)
    if not secret_path.is_file():
        _fail(f"Backend secrets file is missing: {path}")

    try:
        with secret_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as exc:
        _fail(f"Failed to load backend secrets from {path}: {exc}")

    if not isinstance(data, dict):
        _fail(f"Backend secrets file must contain a mapping: {path}")

    return data


def _load_secret_text(path: str) -> str:
    secret_path = Path(path)
    if not secret_path.is_file():
        _fail(f"Secret file is missing: {path}")

    try:
        return secret_path.read_text(encoding="utf-8")
    except Exception as exc:
        _fail(f"Failed to read secret file {path}: {exc}")


def _read_redis_credentials(path: str = "/run/secrets/redis-sec.acl", username: str = "app") -> tuple[str, str]:
    for raw_line in _load_secret_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        try:
            tokens = shlex.split(line)
        except ValueError as exc:
            _fail(f"Failed to parse Redis ACL secret {path}: {exc}")

        if len(tokens) < 2 or tokens[0] != "user" or tokens[1] != username:
            continue

        password_token = next((token for token in tokens[2:] if token.startswith(">") and len(token) > 1), None)
        if password_token is None:
            _fail(f"Redis ACL entry for user {username} does not contain a password")

        return username, password_token[1:]

    _fail(f"Redis ACL entry for user {username} is missing in {path}")


def _looks_like_password_hash(value: str) -> bool:
    return value.startswith("pbkdf2_sha256$") or (value.startswith("$2") and len(value) >= 50)


def _normalize_users(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict) or not raw:
        _fail("users is required in secrets/backend.yaml")

    normalized: dict[str, str] = {}
    for username, value in raw.items():
        if not isinstance(username, str) or not username.strip():
            _fail("users contains an invalid username in secrets/backend.yaml")

        if isinstance(value, str):
            if not _looks_like_password_hash(value):
                _fail(f"users[{username}] must contain a valid password hash")
            normalized[username] = value
            continue

        if isinstance(value, dict):
            password_hash = value.get("password_hash") or value.get("hash")
            if not isinstance(password_hash, str) or not _looks_like_password_hash(password_hash):
                _fail(f"users[{username}] must contain a valid password hash")
            normalized[username] = password_hash
            continue

        _fail(f"users[{username}] must be a password hash string or mapping")

    return normalized


def _normalize_api_keys(raw: Any) -> list[str]:
    if not isinstance(raw, list) or not raw:
        _fail("api_keys is required in secrets/backend.yaml")

    keys: list[str] = []
    for index, key in enumerate(raw):
        if not isinstance(key, str) or not key.strip():
            _fail(f"api_keys[{index}] must be a non-empty string")
        keys.append(key.strip())
    return keys


_backend_secrets = _load_backend_secrets()

_secret_key = _backend_secrets.get("secret_key")
if not isinstance(_secret_key, str) or not _secret_key.strip():
    _fail("secret_key is required in secrets/backend.yaml")

_users = _normalize_users(_backend_secrets.get("users"))
_api_keys = _normalize_api_keys(_backend_secrets.get("api_keys"))

SECRET_KEY = _secret_key.encode("utf-8")
JWT_ALGORITHM = "HS256"
ACCESS_TTL_SECONDS = int(os.getenv("DRONE_ACCESS_TTL_SECONDS", "900"))
REFRESH_TTL_SECONDS = int(os.getenv("DRONE_REFRESH_TTL_SECONDS", "604800"))
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elastic:9200")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_USER, REDIS_PASSWORD = _read_redis_credentials(
    username=os.getenv("REDIS_USER", "app"),
)
CORS_ORIGINS = [
    x.strip()
    for x in os.getenv("DRONE_CORS_ORIGINS", "*").split(",")
    if x.strip()
]
COOKIE_SECURE = True
COOKIE_SAMESITE = "Strict"
AUTH_USERS = _users
API_KEYS = _api_keys
