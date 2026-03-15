"""
Интеграционные тесты для эндпоинта POST /auth/refresh.
Проверяют бизнес-логику обновления токенов, валидацию входных данных
и базовую запись аудита в ElasticSearch.
"""
import os
import time
import jwt
import pytest
import requests
from typing import Dict, Any, Optional

from .utils import get_recent_audit_log

from .conftest import BACKEND_URL, ELASTIC_URL, JWT_ALGORITHM, REFRESH_TTL_SECONDS, SECRET_KEY


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
        """RF-01: Успешное обновление токенов валидным refresh-токеном."""
        payload = {"refresh_token": logged_in_tokens["refresh_token"]}
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json=payload,
            timeout=5,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

    def test_refresh_tokens_are_new(self, logged_in_tokens: Dict[str, Any]):
        """RF-02: Новые токены отличаются от старых."""
        old_access = logged_in_tokens["access_token"]
        old_refresh = logged_in_tokens["refresh_token"]
        
        payload = {"refresh_token": old_refresh}
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json=payload,
            timeout=5,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] != old_access
        assert data["refresh_token"] != old_refresh

    def test_refresh_preserves_subject(self, logged_in_tokens: Dict[str, Any], auth_credentials: Dict[str, str]):
        """RF-03: Субъект (пользователь) сохраняется в новом токене."""
        payload = {"refresh_token": logged_in_tokens["refresh_token"]}
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json=payload,
            timeout=5,
        )
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
        login_resp = requests.post(
            f"{BACKEND_URL}/auth/login",
            json=auth_credentials,
            timeout=5,
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]
        
        # Сразу рефреш
        payload = {"refresh_token": refresh_token}
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json=payload,
            timeout=5,
        )
        assert resp.status_code == 200
        assert resp.json()["token_type"] == "Bearer"

    def test_refresh_near_expiration(self, auth_credentials: Dict[str, str]):
        """RF-05: Рефреш токена, который скоро истечёт (проверка логики exp)."""
        # Создаём токен с малым TTL (5 секунд)
        short_ttl = 5
        custom_refresh = _create_test_jwt(
            subject=auth_credentials["username"],
            token_type="refresh",
            ttl_seconds=short_ttl,
        )
        
        # Ждём почти до экспирации
        time.sleep(short_ttl - 2)
        
        payload = {"refresh_token": custom_refresh}
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json=payload,
            timeout=5,
        )
        # Должен успеть пройти, так как ещё не истёк
        assert resp.status_code == 200


# =============================================================================
# Тесты валидации входных данных (Pydantic модели)
# =============================================================================
class TestAuthRefreshValidation:
    """Валидация поля refresh_token через Pydantic (модель RefreshTokenRequest)."""

    @pytest.mark.parametrize("token_value,expected_status", [
        ("", 400),                    # RF-11: пустая строка (min_length=16)
        ("short", 400),               # RF-12: короче 16 символов
        ("x" * 1025, 400),            # RF-13: длиннее 1024 символов
    ])
    def test_refresh_token_length_validation(self, token_value: str, expected_status: int):
        """RF-11, RF-12, RF-13: Проверка ограничений длины токена."""
        payload = {"refresh_token": token_value}
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json=payload,
            timeout=5,
        )
        assert resp.status_code == expected_status

    def test_refresh_missing_field(self):
        """RF-14: Отсутствует обязательное поле refresh_token."""
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json={},
            timeout=5,
        )
        assert resp.status_code == 400

    def test_refresh_wrong_type(self):
        """RF-15: Неверный тип данных (число вместо строки)."""
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json={"refresh_token": 12345},
            timeout=5,
        )
        assert resp.status_code == 400

    def test_refresh_not_json(self):
        """RF-16: Тело запроса не в формате JSON."""
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            data="not-json-string",
            headers={"Content-Type": "text/plain"},
            timeout=5,
        )
        # FastAPI вернёт 400 при невозможности распарсить тело
        assert resp.status_code == 400


# =============================================================================
# Тесты валидации JWT-логики (уровень приложения)
# =============================================================================
class TestAuthRefreshJWTLogic:
    """Проверка валидности JWT-токена: подпись, claims, тип, экспирация."""

    def test_refresh_invalid_jwt_format(self):
        """RF-21: Произвольная строка вместо валидного JWT."""
        payload = {"refresh_token": "not.a.jwt.token"}
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json=payload,
            timeout=5,
        )
        assert resp.status_code == 401
        assert resp.json()["code"] == 401

    def test_refresh_wrong_signature(self):
        """RF-22: Валидная структура JWT, но подпись другим ключом."""
        wrong_secret = b"different-secret-key-for-testing"
        token = _create_test_jwt(
            subject="user",
            token_type="refresh",
            secret=wrong_secret,
        )
        payload = {"refresh_token": token}
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json=payload,
            timeout=5,
        )
        assert resp.status_code == 401

    def test_refresh_expired_token(self):
        """RF-23: Токен с истёкшим сроком действия (exp в прошлом)."""
        expired_token = _create_test_jwt(
            subject="user",
            token_type="refresh",
            ttl_seconds=-10,  # Уже истёк
        )
        payload = {"refresh_token": expired_token}
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json=payload,
            timeout=5,
        )
        assert resp.status_code == 401
        assert "expired" in resp.json()["message"].lower()

    def test_refresh_access_token_instead_of_refresh(self, logged_in_tokens: Dict[str, Any]):
        """RF-24: Попытка использовать access_token вместо refresh_token."""
        payload = {"refresh_token": logged_in_tokens["access_token"]}
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json=payload,
            timeout=5,
        )
        assert resp.status_code == 401
        assert "type" in resp.json()["message"].lower()

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
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json={"refresh_token": token},
            timeout=5,
        )
        assert resp.status_code == 401

    def test_refresh_token_without_jti(self):
        """RF-26: Токен без обязательного claim 'jti'."""
        now = int(time.time())
        payload_no_jti = {
            "sub": "user",
            "type": "refresh",
            "iat": now,
            "exp": now + REFRESH_TTL_SECONDS,
            # jti намеренно отсутствует
        }
        token = jwt.encode(payload_no_jti, SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json={"refresh_token": token},
            timeout=5,
        )
        assert resp.status_code == 401

    def test_refresh_token_with_empty_sub(self):
        """RF-27: Токен с пустым значением sub (""), что отклоняется логикой."""
        token = _create_test_jwt(
            subject="",  # Пустой subject
            token_type="refresh",
        )
        payload = {"refresh_token": token}
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json=payload,
            timeout=5,
        )
        assert resp.status_code == 401


# =============================================================================
# Тесты аудита (проверка записи событий в ElasticSearch)
# =============================================================================
class TestAuthRefreshAudit:
    """Проверка, что события аудита корректно записываются в индекс 'safety'."""

    def test_audit_on_success(self, logged_in_tokens: Dict[str, Any], auth_credentials: Dict[str, str]):
        """RF-31: Успешный рефреш создаёт запись аудита со severity=info."""
        # Выполняем рефреш
        payload = {"refresh_token": logged_in_tokens["refresh_token"]}
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json=payload,
            timeout=5,
        )
        assert resp.status_code == 200
        
        # Ищем запись аудита через универсальную функцию
        audit_log = get_recent_audit_log(
            expected_substring="action=token_refresh",
            severity="info"
        )
        
        # Если ES недоступен, тест будет пропущен (pytest.skip)
        assert audit_log is not None, "Audit log not found in ElasticSearch"
        
        # Проверяем содержание записи
        assert "action=token_refresh" in audit_log["message"]
        assert "status=success" in audit_log["message"]
        assert f"subject={auth_credentials['username']}" in audit_log["message"]

    def test_audit_on_failure(self, logged_in_tokens: Dict[str, Any]):
        """RF-32: Неудачный рефреш (невалидный токен) создаёт запись аудита со severity=warning."""
        # Отправляем заведомо невалидный токен
        payload = {"refresh_token": "invalid.token.format"}
        resp = requests.post(
            f"{BACKEND_URL}/auth/refresh",
            json=payload,
            timeout=5,
        )
        assert resp.status_code == 401
        
        # Ищем запись о неудаче через универсальную функцию
        audit_log = get_recent_audit_log(
            expected_substring="action=token_refresh",
            severity="warning"
        )
        
        # Если ES недоступен, тест будет пропущен (pytest.skip)
        assert audit_log is not None, "Audit failure log not found"
        
        # Проверяем содержание записи
        assert "action=token_refresh" in audit_log["message"]
        assert "status=failure" in audit_log["message"]
        assert "reason=" in audit_log["message"]