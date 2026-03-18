# backend/app/config.py
import hashlib
import os
import secrets
from pathlib import Path
import yaml

def b64url_encode(value: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

SECRET_KEY = os.getenv("DRONE_SECRET_KEY", secrets.token_urlsafe(48)).encode("utf-8")
API_KEY = os.getenv("DRONE_API_KEY", "change-me-api-key")

# backward-compatible single-user envs
AUTH_USERNAME = os.getenv("DRONE_AUTH_USERNAME", "user")
AUTH_PASSWORD = os.getenv("DRONE_AUTH_PASSWORD", "password")
AUTH_PASSWORD_HASH = os.getenv("DRONE_AUTH_PASSWORD_HASH", "")

PASSWORD_SALT = os.getenv("DRONE_PASSWORD_SALT", b64url_encode(hashlib.sha256(SECRET_KEY).digest()[:16]))
ACCESS_TTL_SECONDS = int(os.getenv("DRONE_ACCESS_TTL_SECONDS", "900"))
REFRESH_TTL_SECONDS = int(os.getenv("DRONE_REFRESH_TTL_SECONDS", "604800"))
CORS_ORIGINS = [x.strip() for x in os.getenv("DRONE_CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elastic:9200")

# ---- load docker secret file if exists ----
def _load_backend_secrets(path: str = "/run/secrets/backend.yaml") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return yaml.safe_load(p.read_text()) or {}
    except Exception:
        return {}

__backend_secrets = _load_backend_secrets()
# expected structure: { "users": { "alice": "<bcrypt-hash>", ... }, "api_keys": [...] }
AUTH_USERS: dict = __backend_secrets.get("users", {}) or {}
AUTH_API_KEYS: list = __backend_secrets.get("api_keys", []) or []