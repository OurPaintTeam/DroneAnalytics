from fastapi import APIRouter, Request, Response

from app.config import COOKIE_SAMESITE, COOKIE_SECURE, REFRESH_TTL_SECONDS
from app.models import LoginRequest, TokenPairResponse
from app.security import auth_error, consume_refresh_token, issue_access_token, issue_refresh_token, verify_user

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
def auth_login(payload: LoginRequest, response: Response):
    if not verify_user(payload.username, payload.password):
        raise auth_error("Invalid credentials")

    access_token, expires_in = issue_access_token(payload.username)
    refresh_token = issue_refresh_token(payload.username)
    _set_refresh_cookie(response, refresh_token)

    return TokenPairResponse(
        access_token=access_token,
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
    _set_refresh_cookie(response, new_refresh_token)

    return TokenPairResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=expires_in,
    )


@router.post("/logout")
def auth_logout(response: Response):
    _clear_refresh_cookie(response)
    return {"status": "ok"}
