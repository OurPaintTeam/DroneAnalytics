import hmac
from typing import Any

from fastapi import Depends
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.config import API_KEY
from app.security import auth_error, decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Depends(api_key_scheme)) -> str:
    if not api_key or not hmac.compare_digest(api_key, API_KEY):
        raise auth_error("Invalid API key")
    return api_key


def require_bearer_payload(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise auth_error("Missing bearer token")
    payload = decode_access_token(credentials.credentials)
    subject = str(payload.get("sub", ""))
    if not subject:
        raise auth_error("Invalid access token")
    return payload
