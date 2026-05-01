"""Интеграционные тесты для эндпоинта POST /auth/logout."""
import time
import jwt
import secrets
from typing import Dict, Any, Optional

from .conftest import (
    BACKEND_URL,
    SECRET_KEY,
    JWT_ALGORITHM,
    REFRESH_TTL_SECONDS,
)
from .utils import auth_login, auth_logout, assert_api_error, get_recent_audit_log


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

    def test_logout_no_auth_required(self):
        """Успешный логаут без каких-либо токенов - просто очищает cookie."""
        resp = auth_logout(BACKEND_URL, payload=None, timeout=5)
        
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_logout_response_format(self):
        """Проверка формата ответа при успешном логауте."""
        resp = auth_logout(BACKEND_URL, payload=None, timeout=5)
        
        data = resp.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert data["status"] == "ok"
        # Убедиться, что нет лишних полей в ответе
        assert set(data.keys()) == {"status"}
    
    def test_logout_with_access_token_ignored(self, logged_in_tokens: Dict[str, Any]):
        """Логаут игнорирует переданный access_token в заголовке."""
        headers = {"Authorization": f"Bearer {logged_in_tokens['access_token']}"}
        resp = auth_logout(
            BACKEND_URL,
            payload=None,
            headers=headers,
            timeout=5,
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_logout_with_refresh_cookie_ignored(self, logged_in_tokens: Dict[str, Any]):
        """Логаут игнорирует refresh_token в cookie - всё равно возвращает ok."""
        resp = auth_logout(
            BACKEND_URL,
            payload=None,
            cookies={"refresh_token": logged_in_tokens["refresh_token"]},
            timeout=5,
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

class TestLogoutAudit:
    """Тесты проверки записи аудита в ElasticSearch."""

    def test_audit_on_success(self):
        """При успешном логауте в индекс 'safety' пишется запись с severity=info."""
        resp = auth_logout(BACKEND_URL, payload=None, timeout=5)
        assert resp.status_code == 200
        
        # Проверяем аудит
        audit_entry = get_recent_audit_log(
            expected_substring="action=auth_logout status=success",
            severity="info",
            index_name="safety"
        )
        
        assert audit_entry is not None, "Audit log not found in ElasticSearch"
        assert audit_entry["service"] == "infopanel"
        assert "action=auth_logout" in audit_entry["message"]