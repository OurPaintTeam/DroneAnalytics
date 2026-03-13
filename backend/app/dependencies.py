import hmac
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.audit import audit_safety
from app.config import API_KEY
from app.security import auth_error, decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Depends(api_key_scheme)) -> str:
    if not api_key or not hmac.compare_digest(api_key, API_KEY):
        audit_safety("warning", "action=api_key_auth status=failure reason=invalid_api_key")
        raise auth_error("Invalid API key")
    return api_key


def require_bearer_payload(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        audit_safety("warning", "action=bearer_auth status=failure reason=missing_bearer_token")
        raise auth_error("Missing bearer token")
    try:
        payload = decode_access_token(credentials.credentials)
    except HTTPException:
        audit_safety("warning", "action=bearer_auth status=failure reason=invalid_or_expired_token")
        raise
    subject = str(payload.get("sub", ""))
    if not subject:
        audit_safety("warning", "action=bearer_auth status=failure reason=empty_subject")
        raise auth_error("Invalid access token")
    return payload
