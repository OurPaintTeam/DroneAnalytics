import hmac
from typing import Any

from fastapi import APIRouter, Depends

from app.config import AUTH_USERNAME
from app.dependencies import require_bearer_payload
from app.models import LoginRequest, RefreshTokenRequest, TokenPairResponse
from app.security import AUTH_PASSWORD_HASH, auth_error, consume_refresh_token, decode_refresh_token, issue_access_token, issue_refresh_token, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPairResponse)
def auth_login(payload: LoginRequest) -> TokenPairResponse:
    username_ok = hmac.compare_digest(payload.username, AUTH_USERNAME)
    password_ok = verify_password(payload.password, AUTH_PASSWORD_HASH)
    if not (username_ok and password_ok):
        raise auth_error("Invalid credentials")
    access_token, expires_in = issue_access_token(payload.username)
    refresh_token = issue_refresh_token(payload.username)
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=TokenPairResponse)
def auth_refresh(payload: RefreshTokenRequest) -> TokenPairResponse:
    subject = consume_refresh_token(payload.refresh_token)
    access_token, expires_in = issue_access_token(subject)
    refresh_token = issue_refresh_token(subject)
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=expires_in,
    )


@router.post("/logout")
def auth_logout(
    payload: RefreshTokenRequest,
    access_payload: dict[str, Any] = Depends(require_bearer_payload),
) -> dict[str, str]:
    subject = str(access_payload["sub"])
    refresh_payload = decode_refresh_token(payload.refresh_token)
    refresh_subject = str(refresh_payload.get("sub", ""))
    if refresh_subject != subject:
        raise auth_error("Refresh token does not belong to current user")
    return {"status": "ok"}
