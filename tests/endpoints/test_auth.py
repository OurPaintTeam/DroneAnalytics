"""Тесты для эндпоинтов /auth/*."""
import pytest
import requests
import time
from typing import Dict, Any

from .conftest import BACKEND_URL


class TestAuthLogin:
    """Тесты POST /auth/login."""

    def test_login_success(self, auth_credentials: Dict[str, str]):
        """Успешный вход с валидными учетными данными."""
        resp = requests.post(
            f"{BACKEND_URL}/auth/login",
            json=auth_credentials,
            timeout=5
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

    def test_login_wrong_password(self, auth_credentials: Dict[str, str]):
        """Вход с неверным паролем."""
        payload = {**auth_credentials, "password": "wrong_password"}
        resp = requests.post(f"{BACKEND_URL}/auth/login", json=payload, timeout=5)
        assert resp.status_code == 401
        data = resp.json()
        assert data["code"] == 401
        assert "message" in data

    def test_login_wrong_username(self, auth_credentials: Dict[str, str]):
        """Вход с неверным именем пользователя."""
        payload = {**auth_credentials, "username": "nonexistent"}
        resp = requests.post(f"{BACKEND_URL}/auth/login", json=payload, timeout=5)
        assert resp.status_code == 401

    def test_login_missing_fields(self):
        """Попытка входа без обязательных полей."""
        resp = requests.post(f"{BACKEND_URL}/auth/login", json={}, timeout=5)
        assert resp.status_code == 400  # Validation error

    def test_login_password_too_short(self, auth_credentials: Dict[str, str]):
        """Пароль короче минимальной длины (8 символов)."""
        payload = {**auth_credentials, "password": "short"}
        resp = requests.post(f"{BACKEND_URL}/auth/login", json=payload, timeout=5)
        assert resp.status_code == 400  # Validation error


class TestAuthRefresh:
    """Тесты POST /auth/refresh."""

    def test_refresh_success(self, logged_in_tokens: Dict[str, Any]):
        """Успешное обновление токенов."""
        payload = {"refresh_token": logged_in_tokens["refresh_token"]}
        resp = requests.post(f"{BACKEND_URL}/auth/refresh", json=payload, timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] != logged_in_tokens["access_token"]
        assert data["refresh_token"] != logged_in_tokens["refresh_token"]
        assert data["token_type"] == "Bearer"

    def test_refresh_invalid_token(self):
        """Попытка обновления с невалидным токеном."""
        payload = {"refresh_token": "invalid.token.here"}
        resp = requests.post(f"{BACKEND_URL}/auth/refresh", json=payload, timeout=5)
        assert resp.status_code == 401

    def test_refresh_empty_token(self):
        """Пустой токен обновления."""
        resp = requests.post(f"{BACKEND_URL}/auth/refresh", json={"refresh_token": ""}, timeout=5)
        assert resp.status_code == 400  # Validation error


class TestAuthLogout:
    """Тесты POST /auth/logout."""

    def test_logout_success(self, logged_in_tokens: Dict[str, Any]):
        """Успешный выход."""
        headers = {"Authorization": f"Bearer {logged_in_tokens['access_token']}"}
        payload = {"refresh_token": logged_in_tokens["refresh_token"]}
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_logout_missing_bearer(self, logged_in_tokens: Dict[str, Any]):
        """Выход без Bearer-токена."""
        payload = {"refresh_token": logged_in_tokens["refresh_token"]}
        resp = requests.post(f"{BACKEND_URL}/auth/logout", json=payload, timeout=5)
        assert resp.status_code == 401

    def test_logout_token_mismatch(self, logged_in_tokens: Dict[str, Any], auth_credentials: Dict[str, str]):
        """Refresh-токен не принадлежит текущему пользователю."""
        # Логинимся вторым "пользователем" (на самом деле тем же, но получаем новые токены)
        resp1 = requests.post(f"{BACKEND_URL}/auth/login", json=auth_credentials, timeout=5)
        tokens1 = resp1.json()
        
        resp2 = requests.post(f"{BACKEND_URL}/auth/login", json=auth_credentials, timeout=5)
        tokens2 = resp2.json()
        
        # Пытаемся выйти с access от первого и refresh от второго
        headers = {"Authorization": f"Bearer {tokens1['access_token']}"}
        payload = {"refresh_token": tokens2["refresh_token"]}
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        assert resp.status_code == 401