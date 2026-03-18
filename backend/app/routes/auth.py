# backend/app/routes/auth.py (фрагмы замены функции auth_login и auth_refresh)
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from app.models import LoginRequest, RefreshTokenRequest, TokenPairResponse
from app.security import issue_access_token, issue_refresh_token, consume_refresh_token, verify_user

router = APIRouter()

@router.post("/login", response_model=TokenPairResponse)
def auth_login(payload: LoginRequest, request: Request, response: Response) -> TokenPairResponse:
    client_ip = request.client.host if request.client else "unknown"
    if not verify_user(payload.username, payload.password):
        audit_safety("warning", f"action=login status=failure subject={payload.username} client_ip={client_ip} reason=invalid_credentials")
        raise auth_error("Invalid credentials")

    access_token, expires_in = issue_access_token(payload.username)
    refresh_token = issue_refresh_token(payload.username)

    # Set refresh token in HttpOnly cookie (secure should be True in prod)
    secure_flag = request.url.scheme == "https"  # или ставить по ENV
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure_flag,
        samesite="Lax",  # или "Strict" по желанию
        path="/",        # путь cookie — возможно /api или /
        max_age=None,    # можно установить REFRESH_TTL_SECONDS
    )

    audit_safety("info", f"action=login status=success subject={payload.username} client_ip={client_ip}")
    # возвращаем access_token в теле; не возвращаем refresh_token (cookie уже установлена)
    return TokenPairResponse(access_token=access_token, refresh_token="", token_type="Bearer")

@router.post("/refresh", response_model=TokenPairResponse)
def auth_refresh(request: Request, response: Response) -> TokenPairResponse:
    # 1) try to read cookie
    refresh_token = request.cookies.get("refresh_token")
    # 2) fallback: if client still passes it in body
    if not refresh_token:
        try:
            body = await request.json()  # если использует pydantic model — альтернативно принимать RefreshTokenRequest
            refresh_token = body.get("refresh_token")
        except Exception:
            refresh_token = None

    if not refresh_token:
        raise auth_error("Missing refresh token")

    subject = consume_refresh_token(refresh_token)
    # issue new access and refresh tokens
    access_token, expires_in = issue_access_token(subject)
    new_refresh_token = issue_refresh_token(subject)

    # rotate cookie
    secure_flag = request.url.scheme == "https"
    response.set_cookie("refresh_token", new_refresh_token, httponly=True, secure=secure_flag, samesite="Lax", path="/")

    audit_safety("info", f"action=token_refresh status=success subject={subject}")
    return TokenPairResponse(access_token=access_token, refresh_token="", token_type="Bearer")