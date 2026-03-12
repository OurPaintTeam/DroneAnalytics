import hmac
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.audit import audit_safety
from app.config import AUTH_USERNAME
from app.dependencies import require_bearer_payload
from app.models import LoginRequest, RefreshTokenRequest, TokenPairResponse
from app.security import (
    AUTH_PASSWORD_HASH,
    auth_error,
    consume_refresh_token,
    decode_refresh_token,
    issue_access_token,
    issue_refresh_token,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPairResponse)
def auth_login(payload: LoginRequest, request: Request) -> TokenPairResponse:
    client_ip = request.client.host if request.client else "unknown"
    username_ok = hmac.compare_digest(payload.username, AUTH_USERNAME)
    password_ok = verify_password(payload.password, AUTH_PASSWORD_HASH)
    if not (username_ok and password_ok):
        audit_safety(
            "warning",
            f"action=login status=failure subject={payload.username} client_ip={client_ip} reason=invalid_credentials",
        )
        raise auth_error("Invalid credentials")
    access_token, expires_in = issue_access_token(payload.username)
    refresh_token = issue_refresh_token(payload.username)
    audit_safety(
        "info",
        f"action=login status=success subject={payload.username} client_ip={client_ip}",
    )
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=TokenPairResponse)
def auth_refresh(payload: RefreshTokenRequest, request: Request) -> TokenPairResponse:
    client_ip = request.client.host if request.client else "unknown"
    try:
        subject = consume_refresh_token(payload.refresh_token)
    except HTTPException:
        audit_safety(
            "warning",
            f"action=token_refresh status=failure client_ip={client_ip} reason=invalid_token",
        )
        raise
    access_token, expires_in = issue_access_token(subject)
    refresh_token = issue_refresh_token(subject)
    audit_safety(
        "info",
        f"action=token_refresh status=success subject={subject} client_ip={client_ip}",
    )
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=expires_in,
    )


@router.post("/logout")
def auth_logout(
    payload: RefreshTokenRequest,
    request: Request,
    access_payload: dict[str, Any] = Depends(require_bearer_payload),
) -> dict[str, str]:
    client_ip = request.client.host if request.client else "unknown"
    subject = str(access_payload["sub"])
    try:
        refresh_payload = decode_refresh_token(payload.refresh_token)
    except HTTPException:
        audit_safety(
            "warning",
            f"action=logout status=failure subject={subject} client_ip={client_ip} reason=invalid_refresh_token",
        )
        raise
    refresh_subject = str(refresh_payload.get("sub", ""))
    if refresh_subject != subject:
        audit_safety(
            "warning",
            f"action=logout status=failure subject={subject} client_ip={client_ip} reason=token_subject_mismatch",
        )
        raise auth_error("Refresh token does not belong to current user")
    audit_safety(
        "info",
        f"action=logout status=success subject={subject} client_ip={client_ip}",
    )
    return {"status": "ok"}
