import hashlib
import os
import secrets


def b64url_encode(value: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


SECRET_KEY = os.getenv("DRONE_SECRET_KEY", secrets.token_urlsafe(48)).encode("utf-8")
API_KEY = os.getenv("DRONE_API_KEY", "change-me-api-key")
AUTH_USERNAME = os.getenv("DRONE_AUTH_USERNAME", "user")
AUTH_PASSWORD = os.getenv("DRONE_AUTH_PASSWORD", "password")
AUTH_PASSWORD_HASH = os.getenv("DRONE_AUTH_PASSWORD_HASH", "")
PASSWORD_SALT = os.getenv("DRONE_PASSWORD_SALT", b64url_encode(hashlib.sha256(SECRET_KEY).digest()[:16]))
ACCESS_TTL_SECONDS = int(os.getenv("DRONE_ACCESS_TTL_SECONDS", "900"))
REFRESH_TTL_SECONDS = int(os.getenv("DRONE_REFRESH_TTL_SECONDS", "604800"))
CORS_ORIGINS = [x.strip() for x in os.getenv("DRONE_CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
