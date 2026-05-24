"""Интеграционные тесты для эндпоинта GET /auth/check."""

import jwt
from typing import Any, Dict

import requests

from .conftest import BACKEND_URL, SECRET_KEY, JWT_ALGORITHM
from .utils import auth_check


class TestAuthCheck:
    def test_auth_check_requires_bearer_token(self):
        """GET /auth/check без Bearer-токена возвращает 401."""
        resp = auth_check(BACKEND_URL, timeout=5)

        assert resp.status_code == 401

    def test_auth_check_rejects_invalid_bearer_token(self):
        """GET /auth/check с невалидным Bearer-токеном возвращает 401."""
        resp = auth_check(
            BACKEND_URL,
            headers={"Authorization": "Bearer invalid.token.value"},
            timeout=5,
        )

        assert resp.status_code == 401

    def test_auth_check_returns_subject_and_expires_in(self, logged_in_tokens: Dict[str, Any], auth_credentials: Dict[str, str]):
        """GET /auth/check возвращает subject и корректный expires_in для access-токена."""
        headers = {"Authorization": f"Bearer {logged_in_tokens['access_token']}"}

        # Делаем 2 последовательных вызова, чтобы избежать флаки по времени
        first = auth_check(BACKEND_URL, headers=headers, timeout=5)
        second = auth_check(BACKEND_URL, headers=headers, timeout=5)

        assert first.status_code == 200
        assert second.status_code == 200

        first_data = first.json()
        second_data = second.json()

        assert first_data["subject"] == auth_credentials["username"]
        assert second_data["subject"] == auth_credentials["username"]
        assert first_data["token_type"] == "access"
        assert second_data["token_type"] == "access"

        assert isinstance(first_data["expires_in"], int)
        assert isinstance(second_data["expires_in"], int)
        assert first_data["expires_in"] >= 0
        assert second_data["expires_in"] >= 0
        assert second_data["expires_in"] <= first_data["expires_in"]

    def test_auth_check_expires_in_matches_access_token_exp(self, logged_in_tokens: Dict[str, Any]):
        """expires_in из /auth/check не превышает exp из access JWT."""
        token = logged_in_tokens["access_token"]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])

        resp = auth_check(
            BACKEND_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["token_type"] == "access"

        max_expected = max(0, int(payload["exp"]) - int(payload["iat"]))
        assert 0 <= data["expires_in"] <= max_expected

    def test_auth_check_method_not_allowed_for_post(self, logged_in_tokens: Dict[str, Any]):
        """POST /auth/check недопустим и должен возвращать 405."""
        resp = requests.post(
            f"{BACKEND_URL}/auth/check",
            headers={"Authorization": f"Bearer {logged_in_tokens['access_token']}"},
            timeout=5,
        )

        assert resp.status_code == 405