from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response

from app.audit import audit_safety
from app.config import COOKIE_SAMESITE, COOKIE_SECURE, REFRESH_TTL_SECONDS
from app.dependencies import require_bearer_payload
from app.errors import auth_error
from app.models import LoginRequest, RefreshTokenRequest, TokenPairResponse
from app.security import consume_refresh_token, issue_access_token, issue_refresh_token, verify_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
        max_age=REFRESH_TTL_SECONDS,
    )



@router.get("/check", response_model=AccessTokenStatusResponse)
def auth_check(bearer_payload: dict[str, Any] = Depends(require_bearer_payload)):
    subject = str(bearer_payload.get("sub", "")).strip()
    expires_at = int(bearer_payload.get("exp", 0) or 0)
    expires_in = max(0, expires_at - now_ts())

    audit_safety("info", f"action=auth_check status=success subject={subject} expires_in={expires_in}")

    return AccessTokenStatusResponse(
        subject=subject,
        token_type="access",
        expires_in=expires_in,
    )

def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key="refresh_token", path="/")


@router.post("/login", response_model=TokenPairResponse)
def auth_login(payload: LoginRequest, response: Response):
    if not verify_user(payload.username, payload.password):
        audit_safety(
            "warning",
            f"action=auth_login status=failure username={payload.username} reason=invalid_credentials",
        )
        raise auth_error("Invalid credentials")

    access_token, expires_in = issue_access_token(payload.username)
    refresh_token = issue_refresh_token(payload.username)
    _set_refresh_cookie(response, refresh_token)
    audit_safety("info", f"action=auth_login status=success username={payload.username}")

    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=TokenPairResponse)
def auth_refresh(
    request: Request,
    response: Response,
    payload: RefreshTokenRequest | None = Body(default=None),
):
    refresh_token = payload.refresh_token if payload is not None else request.cookies.get("refresh_token")
    if not refresh_token:
        audit_safety("warning", "action=auth_refresh status=failure reason=missing_refresh_token")
        raise auth_error("Missing refresh token")

    try:
        subject = consume_refresh_token(refresh_token)
    except HTTPException as exc:
        detail = exc.detail
        reason = str(detail.get("message", detail)) if isinstance(detail, dict) else str(detail)
        audit_safety("warning", f"action=auth_refresh status=failure reason={reason}")
        raise

    access_token, expires_in = issue_access_token(subject)
    new_refresh_token = issue_refresh_token(subject)
    _set_refresh_cookie(response, new_refresh_token)
    audit_safety("info", f"action=auth_refresh status=success subject={subject}")

    return TokenPairResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="Bearer",
        expires_in=expires_in,
    )


@router.post("/logout")
def auth_logout(
    request: Request,
    response: Response,
    payload: RefreshTokenRequest | None = Body(default=None),
    bearer_payload: dict[str, Any] = Depends(require_bearer_payload),
):
    refresh_token = payload.refresh_token if payload is not None else request.cookies.get("refresh_token")
    if not refresh_token:
        audit_safety("warning", "action=auth_logout status=failure reason=missing_refresh_token")
        raise auth_error("Missing refresh token")

    refresh_subject = consume_refresh_token(refresh_token)
    access_subject = str(bearer_payload.get("sub", "")).strip()

    if refresh_subject != access_subject:
        audit_safety(
            "warning",
            "action=auth_logout status=failure reason=subject_mismatch "
            f"access_subject={access_subject} refresh_subject={refresh_subject}",
        )
        raise auth_error("Refresh token does not belong to current user")

    _clear_refresh_cookie(response)
    audit_safety("info", f"action=auth_logout status=success subject={access_subject}")
    return {"status": "ok"}
