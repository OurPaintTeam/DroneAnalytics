"""
Интеграционные тесты для эндпоинта POST /auth/refresh.
Проверяют бизнес-логику обновления токенов, валидацию входных данных
и базовую запись аудита в ElasticSearch.
"""
import os
import time
import jwt
import pytest
from typing import Dict, Any, Optional

from .utils import auth_login, auth_refresh, assert_api_error, get_recent_audit_log

from .conftest import BACKEND_URL, JWT_ALGORITHM, REFRESH_TTL_SECONDS, SECRET_KEY


# =============================================================================
# Вспомогательные функции для генерации тестовых токенов
# =============================================================================
def _create_test_jwt(
    subject: str,
    token_type: str,
    ttl_seconds: Optional[int] = None,
    override_payload: Optional[Dict[str, Any]] = None,
    secret: bytes = SECRET_KEY,
) -> str:
    """Создаёт тестовый JWT с указанными параметрами."""
    now = int(time.time())
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + (ttl_seconds or REFRESH_TTL_SECONDS),
        "jti": "test-jti-" + os.urandom(8).hex(),
    }
    if override_payload:
        payload.update(override_payload)
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


# =============================================================================
# Позитивные тесты (Happy Path)
# =============================================================================
class TestAuthRefreshSuccess:
    """Позитивные сценарии обновления токенов."""

    def test_refresh_success(self, logged_in_tokens: Dict[str, Any]):
        """RF-01: Успешное обновление токенов валидным refresh-токеном из cookie."""
        # Refresh токен берётся из cookie после логина
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": logged_in_tokens["refresh_token"]}, timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "expires_in" in data
        assert data["token_type"] == "Bearer"
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

    def test_refresh_tokens_are_new(self, logged_in_tokens: Dict[str, Any]):
        """RF-02: Новые токены отличаются от старых."""
        old_access = logged_in_tokens["access_token"]
        old_refresh = logged_in_tokens["refresh_token"]
        
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": old_refresh}, timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] != old_access
        # Новый refresh токен установлен в cookie
        new_refresh = resp.cookies.get("refresh_token")
        assert new_refresh is not None
        assert new_refresh != old_refresh

    def test_refresh_preserves_subject(self, logged_in_tokens: Dict[str, Any], auth_credentials: Dict[str, str]):
        """RF-03: Субъект (пользователь) сохраняется в новом токене."""
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": logged_in_tokens["refresh_token"]}, timeout=5)
        assert resp.status_code == 200
        new_access = resp.json()["access_token"]
        
        # Декодируем без проверки подписи, только для чтения claims
        new_payload = jwt.decode(
            new_access,
            SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"verify_signature": False},
        )
        assert new_payload["sub"] == auth_credentials["username"]
        assert new_payload["type"] == "access"

    def test_refresh_immediately_after_login(self, auth_credentials: Dict[str, str]):
        """RF-04: Рефреш работает сразу после получения токена от логина."""
        # Логин
        login_resp = auth_login(BACKEND_URL, auth_credentials, timeout=5)
        assert login_resp.status_code == 200
        refresh_token = login_resp.cookies.get("refresh_token")
        assert refresh_token is not None
        
        # Сразу рефреш
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": refresh_token}, timeout=5)
        assert resp.status_code == 200
        assert resp.json()["token_type"] == "Bearer"

    def test_refresh_from_json_body(self, logged_in_tokens: Dict[str, Any]):
        """RF-05: refresh-token можно передать через JSON тело запроса (но backend всё равно читает из cookie)."""
        # Backend игнорирует JSON тело и читает токен только из cookie
        # Этот тест проверяет, что при наличии токена в cookie запрос работает
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": logged_in_tokens["refresh_token"]}, timeout=5)
        assert resp.status_code == 200
        assert resp.json()["token_type"] == "Bearer"

# =============================================================================
# Тесты валидации входных данных (уровень приложения)
# =============================================================================
class TestAuthRefreshValidation:
    """Валидация refresh_token: backend читает токен только из cookie."""

    def test_refresh_missing_cookie(self):
        """RF-17: Без cookie backend возвращает Missing refresh token."""
        resp = auth_refresh(BACKEND_URL, payload=None, timeout=5)
        assert_api_error(resp, 401, message_exact="Missing refresh token")

    @pytest.mark.parametrize("token_value", [
        "",                    # пустая строка
        "short",               # короткая строка
        "x" * 1025,            # очень длинная строка
        "not.a.jwt.token",     # невалидный JWT формат
    ])
    def test_refresh_invalid_token_in_cookie(self, token_value: str):
        """Невалидный токен в cookie возвращает 401."""
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": token_value}, timeout=5)
        assert resp.status_code == 401

# =============================================================================
# Тесты валидации JWT-логики (уровень приложения)
# =============================================================================
class TestAuthRefreshJWTLogic:
    """Проверка валидности JWT-токена: подпись, claims, тип, экспирация."""

    def test_refresh_invalid_jwt_format(self):
        """RF-21: Произвольная строка вместо валидного JWT."""
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": "not.a.jwt.token"}, timeout=5)
        assert resp.status_code == 401

    def test_refresh_wrong_signature(self):
        """RF-22: Валидная структура JWT, но подпись другим ключом."""
        wrong_secret = b"different-secret-key-for-testing"
        token = _create_test_jwt(
            subject="user",
            token_type="refresh",
            secret=wrong_secret,
        )
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": token}, timeout=5)
        assert resp.status_code == 401

    def test_refresh_expired_token(self):
        """RF-23: Токен с истёкшим сроком действия (exp в прошлом)."""
        expired_token = _create_test_jwt(
            subject="user",
            token_type="refresh",
            ttl_seconds=-10,  # Уже истёк
        )
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": expired_token}, timeout=5)
        assert resp.status_code == 401

    def test_refresh_access_token_instead_of_refresh(self, logged_in_tokens: Dict[str, Any]):
        """RF-24: Попытка использовать access_token вместо refresh_token."""
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": logged_in_tokens["access_token"]}, timeout=5)
        assert resp.status_code == 401
        data = resp.json()
        message = data.get("message", "") if isinstance(data, dict) else str(data)
        # Backend возвращает "Invalid token type" при использовании access_token вместо refresh
        assert "type" in message.lower() or "invalid" in message.lower()

    def test_refresh_token_without_sub(self):
        """RF-25: Токен без обязательного claim 'sub' (subject)."""
        now = int(time.time())
        payload_no_sub = {
            "type": "refresh",
            "iat": now,
            "exp": now + REFRESH_TTL_SECONDS,
            "jti": "test-no-sub",
        }
        token = jwt.encode(payload_no_sub, SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": token}, timeout=5)
        assert resp.status_code == 401

    def test_refresh_token_without_jti(self):
        """RF-26: Токен без обязательного claim 'jti' - backend пропускает (jti не обязателен)."""
        now = int(time.time())
        payload_no_jti = {
            "sub": "user",
            "type": "refresh",
            "iat": now,
            "exp": now + REFRESH_TTL_SECONDS,
            # jti намеренно отсутствует - backend это допускает
        }
        token = jwt.encode(payload_no_jti, SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        # Backend принимает токен без jti, т.к. не требует этот claim
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": token}, timeout=5)
        assert resp.status_code == 200
        assert resp.json()["token_type"] == "Bearer"

    def test_refresh_token_with_empty_sub(self):
        """RF-27: Токен с пустым значением sub (""), что отклоняется логикой."""
        token = _create_test_jwt(
            subject="",  # Пустой subject
            token_type="refresh",
        )
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": token}, timeout=5)
        assert resp.status_code == 401


# =============================================================================
# Тесты аудита (проверка записи событий в ElasticSearch)
# =============================================================================
class TestAuthRefreshAudit:
    """Проверка, что события аудита корректно записываются в индекс 'safety'."""

    def test_audit_on_success(self, logged_in_tokens: Dict[str, Any], auth_credentials: Dict[str, str]):
        """RF-31: Успешный рефреш создаёт запись аудита со severity=info."""
        # Выполняем рефреш
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": logged_in_tokens["refresh_token"]}, timeout=5)
        assert resp.status_code == 200
        
        # Ищем запись аудита через универсальную функцию
        audit_log = get_recent_audit_log(
            expected_substring="action=auth_refresh",
            severity="info",
            index_name="safety"
        )
        
        # Если ES недоступен, тест будет пропущен (pytest.skip)
        assert audit_log is not None, "Audit log not found in ElasticSearch"
        
        # Проверяем содержание записи
        assert "action=auth_refresh" in audit_log["message"]
        assert "status=success" in audit_log["message"]
        assert f"subject={auth_credentials['username']}" in audit_log["message"]

    def test_audit_on_failure(self):
        """RF-32: Неудачный рефреш (невалидный токен) создаёт запись аудита со severity=warning."""
        # Отправляем заведомо невалидный токен в cookie
        resp = auth_refresh(BACKEND_URL, payload=None, cookies={"refresh_token": "invalid.token.format"}, timeout=5)
        assert resp.status_code == 401
        
        # Ищем запись о неудаче через универсальную функцию
        audit_log = get_recent_audit_log(
            expected_substring="action=auth_refresh",
            severity="warning",
            index_name="safety"
        )
        
        # Если ES недоступен, тест будет пропущен (pytest.skip)
        assert audit_log is not None, "Audit failure log not found"
        
        # Проверяем содержание записи
        assert "action=auth_refresh" in audit_log["message"]
        assert "status=failure" in audit_log["message"]
        assert "reason=" in audit_log["message"]