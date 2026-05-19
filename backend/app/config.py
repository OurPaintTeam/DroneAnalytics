import logging
import os
from pathlib import Path
from typing import Any, get_args

import yaml
from app.models import AccountIdType, LogServiceType

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


def _normalize_redis(raw: Any) -> tuple[str, str]:
    if not isinstance(raw, dict):
        _fail("redis section is required in secrets/backend.yaml")

    username = raw.get("username")
    password = raw.get("password")

    if not isinstance(username, str) or not username.strip():
        _fail("redis.username is required in secrets/backend.yaml")
    if not isinstance(password, str) or not password.strip():
        _fail("redis.password is required in secrets/backend.yaml")

    return username.strip(), password.strip()


def _normalize_account_services(raw: Any, account_id: str) -> list[str]:
    allowed_services = set(get_args(LogServiceType))

    if raw is None:
        return []
    if not isinstance(raw, list):
        _fail(f"accounts[{account_id}].services must be a list")

    services: list[str] = []
    seen: set[str] = set()
    for index, service in enumerate(raw):
        if not isinstance(service, str) or not service.strip():
            _fail(f"accounts[{account_id}].services[{index}] must be a non-empty string")
        normalized = service.strip()
        if normalized not in allowed_services:
            _fail(f"accounts[{account_id}].services[{index}] has unsupported service: {normalized}")
        if normalized in seen:
            continue
        seen.add(normalized)
        services.append(normalized)
    return services


def _normalize_accounts(raw: Any) -> list[dict[str, Any]]:
    allowed_account_ids = set(get_args(AccountIdType))

    if not isinstance(raw, list) or not raw:
        _fail("accounts is required in secrets/backend.yaml")

    accounts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            _fail(f"accounts[{index}] must be a mapping")

        account_id = item.get("account_id")
        name = item.get("name")
        balance = item.get("balance")
        reserved = item.get("reserved")

        if not isinstance(account_id, str) or account_id not in allowed_account_ids:
            _fail(f"accounts[{index}].account_id must be one of {sorted(allowed_account_ids)}")
        if account_id in seen_ids:
            _fail(f"accounts contains duplicate account_id: {account_id}")
        if not isinstance(name, str) or not name.strip():
            _fail(f"accounts[{account_id}].name must be a non-empty string")
        if not isinstance(balance, int) or balance < 0:
            _fail(f"accounts[{account_id}].balance must be a non-negative integer")
        if not isinstance(reserved, int) or reserved < 0:
            _fail(f"accounts[{account_id}].reserved must be a non-negative integer")

        seen_ids.add(account_id)
        accounts.append(
            {
                "account_id": account_id,
                "name": name.strip(),
                "services": _normalize_account_services(item.get("services"), account_id),
                "balance": balance,
                "reserved": reserved,
            }
        )

    return accounts


_backend_secrets = _load_backend_secrets()

_secret_key = _backend_secrets.get("secret_key")
if not isinstance(_secret_key, str) or not _secret_key.strip():
    _fail("secret_key is required in secrets/backend.yaml")

_users = _normalize_users(_backend_secrets.get("users"))
_api_keys = _normalize_api_keys(_backend_secrets.get("api_keys"))
_redis_user, _redis_password = _normalize_redis(_backend_secrets.get("redis"))
_accounts = _normalize_accounts(_backend_secrets.get("accounts"))

SECRET_KEY = _secret_key.encode("utf-8")
JWT_ALGORITHM = "HS256"
ACCESS_TTL_SECONDS = int(os.getenv("DRONE_ACCESS_TTL_SECONDS", "900"))
REFRESH_TTL_SECONDS = int(os.getenv("DRONE_REFRESH_TTL_SECONDS", "604800"))
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elastic:9200")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_USER = _redis_user
REDIS_PASSWORD = _redis_password
CORS_ORIGINS = [
    x.strip()
    for x in os.getenv("DRONE_CORS_ORIGINS", "*").split(",")
    if x.strip()
]
COOKIE_SECURE = True
COOKIE_SAMESITE = "Strict"
AUTH_USERS = _users
API_KEYS = _api_keys
ACCOUNT_SEEDS = _accounts
