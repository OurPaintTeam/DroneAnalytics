from __future__ import annotations

from fastapi import APIRouter, Body, Request, Response

from app.audit import audit_safety
from app.config import COOKIE_SAMESITE, COOKIE_SECURE, REFRESH_TTL_SECONDS
from app.models import LoginRequest, RefreshTokenRequest, TokenPairResponse
from app.security import (
    auth_error,
    consume_refresh_token,
    issue_access_token,
    issue_refresh_token,
    verify_user,
)

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


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key="refresh_token", path="/")


@router.post("/login", response_model=TokenPairResponse)
def auth_login(payload: LoginRequest, request: Request, response: Response):
    if not verify_user(payload.username, payload.password):
        raise auth_error("Invalid credentials")

    access_token, expires_in = issue_access_token(payload.username)
    refresh_token = issue_refresh_token(payload.username)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="Lax",
        path="/",
    )

    return TokenPairResponse(
        access_token=access_token,
        refresh_token="",
        token_type="Bearer",
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=TokenPairResponse)
def auth_refresh(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise auth_error("Missing refresh token")

    subject = consume_refresh_token(refresh_token)

    access_token, expires_in = issue_access_token(subject)
    new_refresh_token = issue_refresh_token(subject)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="Lax",
        path="/",
    )

    return TokenPairResponse(
        access_token=access_token,
        refresh_token="",
        token_type="Bearer",
        expires_in=expires_in,
    )

@router.post("/logout")
def auth_logout(response: Response):
    response.delete_cookie("refresh_token", path="/")
    return {"status": "ok"}