"""Интеграционные тесты для эндпоинта POST /auth/logout."""
import time
import jwt
import secrets
import pytest
import requests
from typing import Dict, Any, Optional

from .conftest import (
    BACKEND_URL,
    SECRET_KEY,
    JWT_ALGORITHM,
    REFRESH_TTL_SECONDS,
)
from .utils import get_recent_audit_log


def _create_custom_jwt(
    subject: str,
    token_type: str,
    ttl_seconds: int,
    extra_claims: Optional[Dict[str, Any]] = None,
    omit_claims: Optional[list[str]] = None,
) -> str:
    """
    Создаёт кастомный JWT для негативных тестов.
    
    Args:
        subject: Значение claim 'sub'
        token_type: 'access' или 'refresh'
        ttl_seconds: Время жизни токена в секундах
        extra_claims: Дополнительные claim'ы
        omit_claims: Список обязательных claim'ов, которые нужно исключить
        
    Returns:
        Подписанный JWT-токен
    """
    now = int(time.time())
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + ttl_seconds,
        "jti": secrets.token_hex(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    if omit_claims:
        for key in omit_claims:
            payload.pop(key, None)
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


class TestLogoutSuccess:
    """Позитивные тесты успешного логаута."""

    def test_logout_valid_tokens(self, logged_in_tokens: Dict[str, Any]):
        """Успешный логаут с валидной парой токенов."""
        headers = {"Authorization": f"Bearer {logged_in_tokens['access_token']}"}
        payload = {"refresh_token": logged_in_tokens["refresh_token"]}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_logout_response_format(self, logged_in_tokens: Dict[str, Any]):
        """Проверка формата ответа при успешном логауте."""
        headers = {"Authorization": f"Bearer {logged_in_tokens['access_token']}"}
        payload = {"refresh_token": logged_in_tokens["refresh_token"]}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        
        data = resp.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert data["status"] == "ok"
        # Убедиться, что нет лишних полей в ответе
        assert set(data.keys()) == {"status"}


class TestLogoutValidation:
    """Тесты валидации входных данных."""

    def test_missing_refresh_token_field(self, logged_in_tokens: Dict[str, Any]):
        """Отсутствует поле refresh_token в теле запроса."""
        headers = {"Authorization": f"Bearer {logged_in_tokens['access_token']}"}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json={},  # Пустое тело
            headers=headers,
            timeout=5
        )
        
        assert resp.status_code == 400
        assert "code" in resp.json()
        assert resp.json()["code"] == 400

    def test_empty_refresh_token(self, logged_in_tokens: Dict[str, Any]):
        """Пустая строка в поле refresh_token."""
        headers = {"Authorization": f"Bearer {logged_in_tokens['access_token']}"}
        payload = {"refresh_token": ""}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        
        assert resp.status_code == 400  # Validation error: min_length=16

    def test_short_refresh_token(self, logged_in_tokens: Dict[str, Any]):
        """refresh_token короче минимальной длины (16 символов)."""
        headers = {"Authorization": f"Bearer {logged_in_tokens['access_token']}"}
        payload = {"refresh_token": "short"}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        
        assert resp.status_code == 400


class TestLogoutAuthErrors:
    """Тесты ошибок аутентификации (Bearer-токен)."""

    def test_no_bearer_header(self, logged_in_tokens: Dict[str, Any]):
        """Запрос без заголовка Authorization."""
        payload = {"refresh_token": logged_in_tokens["refresh_token"]}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            timeout=5
        )
        
        assert resp.status_code == 401
        assert resp.json()["code"] == 401
        assert "Missing bearer token" in resp.json()["message"]

    def test_expired_access_token(self, auth_credentials: Dict[str, str]):
        """Использование просроченного access_token."""
        # Создаём токен с истёкшим сроком
        expired_token = _create_custom_jwt(
            subject=auth_credentials["username"],
            token_type="access",
            ttl_seconds=-10,  # Уже истёк 10 секунд назад
        )
        
        # Нужен валидный refresh для прохождения валидации тела
        login_resp = requests.post(
            f"{BACKEND_URL}/auth/login",
            json=auth_credentials,
            timeout=5
        )
        refresh_token = login_resp.json()["refresh_token"]
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        payload = {"refresh_token": refresh_token}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        
        assert resp.status_code == 401

    def test_wrong_token_type_in_bearer(self, logged_in_tokens: Dict[str, Any]):
        """В заголовке Authorization передан refresh_token вместо access_token."""
        # refresh_token имеет type="refresh", эндпоинт ожидает type="access"
        headers = {"Authorization": f"Bearer {logged_in_tokens['refresh_token']}"}
        payload = {"refresh_token": logged_in_tokens["refresh_token"]}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        
        assert resp.status_code == 401
        assert "Invalid token type" in resp.json()["message"]

    def test_invalid_jwt_signature(self, logged_in_tokens: Dict[str, Any]):
        """JWT с неверной подписью в заголовке Authorization."""
        # Создаём токен с другим ключом (подпись не совпадёт)
        fake_token = jwt.encode(
            {
                "sub": "user",
                "type": "access",
                "iat": int(time.time()),
                "exp": int(time.time()) + 300,
                "jti": "fake",
            },
            b"wrong-secret-key",
            algorithm=JWT_ALGORITHM
        )
        
        headers = {"Authorization": f"Bearer {fake_token}"}
        payload = {"refresh_token": logged_in_tokens["refresh_token"]}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        
        assert resp.status_code == 401
        assert "Invalid token" in resp.json()["message"]


class TestLogoutLogicErrors:
    """Тесты бизнес-логики: валидация refresh-токена."""

    def test_invalid_refresh_signature(self, logged_in_tokens: Dict[str, Any]):
        """refresh_token с неверной подписью."""
        headers = {"Authorization": f"Bearer {logged_in_tokens['access_token']}"}
        
        # Создаём поддельный refresh с неправильной подписью
        fake_refresh = jwt.encode(
            {
                "sub": "user",
                "type": "refresh",
                "iat": int(time.time()),
                "exp": int(time.time()) + REFRESH_TTL_SECONDS,
                "jti": "fake-jti",
            },
            b"another-wrong-key",
            algorithm=JWT_ALGORITHM
        )
        
        payload = {"refresh_token": fake_refresh}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        
        assert resp.status_code == 401
        assert "Invalid token" in resp.json()["message"]

    def test_expired_refresh_token(self, logged_in_tokens: Dict[str, Any]):
        """Использование просроченного refresh_token."""
        headers = {"Authorization": f"Bearer {logged_in_tokens['access_token']}"}
        
        # Создаём refresh с истёкшим сроком
        expired_refresh = _create_custom_jwt(
            subject="user",
            token_type="refresh",
            ttl_seconds=-60,  # Истёк минуту назад
        )
        
        payload = {"refresh_token": expired_refresh}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        
        assert resp.status_code == 401

    def test_access_token_as_refresh(self, logged_in_tokens: Dict[str, Any]):
        """Попытка использовать access_token в качестве refresh_token."""
        headers = {"Authorization": f"Bearer {logged_in_tokens['access_token']}"}
        # Передаём access туда, где ждут refresh
        payload = {"refresh_token": logged_in_tokens["access_token"]}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        
        assert resp.status_code == 401
        # Ошибка: ожидался тип "refresh", получен "access"
        assert "Invalid token type" in resp.json()["message"]

    def test_missing_required_claim_in_refresh(self, logged_in_tokens: Dict[str, Any]):
        """refresh_token без обязательного claim 'jti'."""
        headers = {"Authorization": f"Bearer {logged_in_tokens['access_token']}"}
        
        # Создаём токен без jti
        malformed_refresh = _create_custom_jwt(
            subject="user",
            token_type="refresh",
            ttl_seconds=REFRESH_TTL_SECONDS,
            omit_claims=["jti"],
        )
        
        payload = {"refresh_token": malformed_refresh}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        
        assert resp.status_code == 401
        assert "Invalid token" in resp.json()["message"]


class TestLogoutAudit:
    """Тесты проверки записи аудита в ElasticSearch."""

    def test_audit_on_success(self, logged_in_tokens: Dict[str, Any]):
        """При успешном логауте в индекс 'safety' пишется запись с severity=info."""
        headers = {"Authorization": f"Bearer {logged_in_tokens['access_token']}"}
        payload = {"refresh_token": logged_in_tokens["refresh_token"]}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        assert resp.status_code == 200
        
        # Проверяем аудит
        audit_entry = get_recent_audit_log(
            expected_substring="action=logout status=success",
            severity="info"
        )
        
        assert audit_entry is not None, "Audit log not found in ElasticSearch"
        assert audit_entry["service"] == "infopanel"
        assert "subject=" in audit_entry["message"]
        assert "client_ip=" in audit_entry["message"]

    def test_audit_on_invalid_refresh(self, logged_in_tokens: Dict[str, Any]):
        """При невалидном refresh пишется аудит с severity=warning."""
        headers = {"Authorization": f"Bearer {logged_in_tokens['access_token']}"}
        payload = {"refresh_token": "invalid.token.signature"}
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json=payload,
            headers=headers,
            timeout=5
        )
        assert resp.status_code == 401
        
        audit_entry = get_recent_audit_log(
            expected_substring="action=logout status=failure reason=invalid_refresh_token",
            severity="warning"
        )
        
        assert audit_entry is not None, "Warning audit log not found"
        assert audit_entry["severity"] == "warning"