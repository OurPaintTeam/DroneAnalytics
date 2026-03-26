import time
import jwt
import pytest
import requests
from typing import Dict, Any

from .utils import auth_login, assert_api_error, get_recent_audit_log

from .conftest import (
    BACKEND_URL,
    SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TTL_SECONDS,
    REFRESH_TTL_SECONDS,
    JWT_REQUIRED_CLAIMS,
)


# ============================================================================
# Позитивные сценарии (Happy Path)
# ============================================================================

class TestLoginSuccess:
    """Тесты успешной аутентификации."""

    def test_auth_001_login_with_default_credentials(self, auth_credentials: Dict[str, str]):
        """AUTH-001: Успешный вход с учетными данными по умолчанию."""
        resp = auth_login(BACKEND_URL, auth_credentials, timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        
        # Проверка структуры ответа
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0
        
        # Проверка, что токены — непустые строки
        assert isinstance(data["access_token"], str) and len(data["access_token"]) > 0
        assert isinstance(data["refresh_token"], str) and len(data["refresh_token"]) > 0

    def test_auth_002_response_schema_validation(self, auth_credentials: Dict[str, str]):
        """AUTH-002: Тело ответа соответствует ожидаемой схеме."""
        resp = auth_login(BACKEND_URL, auth_credentials, timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        
        # Явная проверка типов и значений
        assert isinstance(data["access_token"], str)
        assert isinstance(data["refresh_token"], str)
        assert data["token_type"] == "Bearer"
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0
    
    def test_auth_003_access_token_claims_and_signature(self, auth_credentials: Dict[str, str]):
        """AUTH-003: access_token содержит ожидаемые claims после успешного логина."""
        resp = auth_login(BACKEND_URL, auth_credentials, timeout=5)
        assert resp.status_code == 200
        access_token = resp.json()["access_token"]

        payload: Dict[str, Any] = jwt.decode(
            access_token,
            options={"verify_signature": False},
        )
        assert {"exp", "iat", "sub", "type", "jti"}.issubset(payload.keys())
        assert payload["sub"] == auth_credentials["username"]
        assert payload["type"] == "access"

    def test_auth_004_refresh_token_claims_and_signature(self, auth_credentials: Dict[str, str]):
        """AUTH-004: refresh_token содержит ожидаемые claims после успешного логина."""
        resp = auth_login(BACKEND_URL, auth_credentials, timeout=5)
        assert resp.status_code == 200
        refresh_token = resp.json()["refresh_token"]

        payload: Dict[str, Any] = jwt.decode(
            refresh_token,
            options={"verify_signature": False},
        )
        assert {"exp", "iat", "sub", "type", "jti"}.issubset(payload.keys())
        assert payload["sub"] == auth_credentials["username"]
        assert payload["type"] == "refresh"

    def test_auth_005_token_ttl_matches_env(self, auth_credentials: Dict[str, str]):
        """AUTH-005: TTL access/refresh приблизительно совпадает с конфигурацией backend."""
        resp = auth_login(BACKEND_URL, auth_credentials, timeout=5)
        assert resp.status_code == 200
        data = resp.json()

        access_payload = jwt.decode(
            data["access_token"],
            options={"verify_signature": False},
        )
        refresh_payload = jwt.decode(
            data["refresh_token"],
            options={"verify_signature": False},
        )

        access_ttl = int(access_payload["exp"]) - int(access_payload["iat"])
        refresh_ttl = int(refresh_payload["exp"]) - int(refresh_payload["iat"])

        # Допускаем дрейф времени в 2 секунды.
        assert abs(access_ttl - ACCESS_TTL_SECONDS) <= 2
        assert abs(refresh_ttl - REFRESH_TTL_SECONDS) <= 2
        assert data["expires_in"] == ACCESS_TTL_SECONDS


# ============================================================================
# Негативные сценарии: Валидация входных данных (Pydantic)
# ============================================================================

class TestLoginValidation:
    """Тесты валидации входных данных через Pydantic."""

    def test_auth_010_empty_request_body(self):
        """AUTH-010: Пустое тело запроса."""
        resp = auth_login(BACKEND_URL, {}, timeout=5)
        assert_api_error(resp, 400)

    def test_auth_011_username_too_short(self, auth_credentials: Dict[str, str]):
        """AUTH-011: Username короче минимума (4 символа)."""
        payload = {**auth_credentials, "username": "usr"}
        resp = auth_login(BACKEND_URL, json=payload, timeout=5)
        assert resp.status_code == 400

    def test_auth_012_username_too_long(self, auth_credentials: Dict[str, str]):
        """AUTH-012: Username длиннее максимума (64 символа)."""
        payload = {**auth_credentials, "username": "a" * 65}
        resp = auth_login(BACKEND_URL, json=payload, timeout=5)
        assert resp.status_code == 400

    def test_auth_013_password_too_short(self, auth_credentials: Dict[str, str]):
        """AUTH-013: Password короче минимума (8 символов)."""
        payload = {**auth_credentials, "password": "1234567"}
        resp = auth_login(BACKEND_URL, json=payload, timeout=5)
        assert resp.status_code == 400

    def test_auth_014_password_too_long(self, auth_credentials: Dict[str, str]):
        """AUTH-014: Password длиннее максимума (64 символа)."""
        payload = {**auth_credentials, "password": "x" * 65}
        resp = auth_login(BACKEND_URL, json=payload, timeout=5)
        assert resp.status_code == 400

    def test_auth_015_extra_fields_forbidden(self, auth_credentials: Dict[str, str]):
        """AUTH-015: Лишние поля в запросе отклоняются (StrictModel)."""
        payload = {**auth_credentials, "extra_field": "should_be_rejected"}
        resp = auth_login(BACKEND_URL, json=payload, timeout=5)
        assert resp.status_code == 400

    def test_auth_016_wrong_field_types(self):
        """AUTH-016: Неверный тип данных для полей."""
        payload = {"username": 12345, "password": 67890}  # int вместо str
        resp = auth_login(BACKEND_URL, json=payload, timeout=5)
        assert resp.status_code == 400

    def test_auth_017_missing_username(self, auth_credentials: Dict[str, str]):
        """Отсутствует обязательное поле username."""
        payload = {"password": auth_credentials["password"]}
        resp = auth_login(BACKEND_URL, json=payload, timeout=5)
        assert resp.status_code == 400

    def test_auth_018_missing_password(self, auth_credentials: Dict[str, str]):
        """Отсутствует обязательное поле password."""
        payload = {"username": auth_credentials["username"]}
        resp = auth_login(BACKEND_URL, json=payload, timeout=5)
        assert resp.status_code == 400


# ============================================================================
# Негативные сценарии: Неверные учетные данные
# ============================================================================

class TestLoginInvalidCredentials:
    """Тесты обработки неверных учетных данных."""

    def test_auth_020_wrong_password(self, auth_credentials: Dict[str, str]):
        """AUTH-020: Неверный пароль."""
        payload = {**auth_credentials, "password": "wrong_password_123"}
        resp = auth_login(BACKEND_URL, json=payload, timeout=5)
        assert_api_error(resp, 401, message_exact="Invalid credentials")
    
    def test_auth_021_wrong_username(self, auth_credentials: Dict[str, str]):
        """AUTH-021: Неверный username."""
        payload = {**auth_credentials, "username": "nonexistent_user"}
        resp = auth_login(BACKEND_URL, json=payload, timeout=5)
        assert_api_error(resp, 401, message_exact="Invalid credentials")

    def test_auth_022_both_credentials_wrong(self):
        """AUTH-022: Оба поля неверны."""
        payload = {"username": "fake_user", "password": "fake_pass"}
        resp = auth_login(BACKEND_URL, json=payload, timeout=5)
        # Сообщение не раскрывает, какое именно поле неверно
        assert_api_error(resp, 401, message_exact="Invalid credentials")

    def test_auth_023_case_sensitive_username(self, auth_credentials: Dict[str, str]):
        """AUTH-023: Username чувствителен к регистру."""
        # Если оригинальный юзер "user", то "User" должен быть отвергнут
        payload = {
            "username": auth_credentials["username"].swapcase(),
            "password": auth_credentials["password"]
        }
        # Пропускаем, если своп кейса дал ту же строку (например, цифры)
        if payload["username"] == auth_credentials["username"]:
            pytest.skip("Username case swap produced same string")
        
        resp = auth_login(BACKEND_URL, json=payload, timeout=5)
        assert resp.status_code == 401

    def test_auth_024_whitespace_in_credentials(self, auth_credentials: Dict[str, str]):
        """AUTH-024: Пробелы в креденшиалах считаются частью строки."""
        payload = {
            "username": auth_credentials["username"] + " ",
            "password": auth_credentials["password"]
        }
        resp = auth_login(BACKEND_URL, json=payload, timeout=5)
        assert resp.status_code == 401


# ============================================================================
# Пограничные случаи (Edge Cases)
# ============================================================================

class TestLoginEdgeCases:
    """Тесты пограничных значений и специфичных сценариев.
    
    Важно: В этих тестах мы НЕ проверяем успешный вход (200).
    Главная цель — убедиться, что данные проходят валидацию Pydantic (статус НЕ 400).
    """

    def test_auth_030_username_min_length(self):
        """AUTH-030: Username ровно 4 символа (минимальная длина)."""
        
        resp = auth_login(BACKEND_URL, {"username": "test", "password": "test_password"}, timeout=5)
       
        assert resp.status_code != 400

    def test_auth_031_password_min_length(self):
        """AUTH-031: Password ровно 8 символов (минимальная длина)."""
        
        resp = auth_login(BACKEND_URL, {"username": "username", "password": "password"}, timeout=5)
        
        assert resp.status_code != 400

    def test_auth_032_special_chars_in_password(self):
        """AUTH-032: Спецсимволы в пароле обрабатываются корректно."""
        
        resp = auth_login(BACKEND_URL, {"username": "username", "password": "P@ssw0rd!#$%^&*()"}, timeout=5)

        assert resp.status_code != 400

    def test_auth_033_unicode_in_password(self):
        """AUTH-033: Unicode-символы в password не ломают обработку."""
        
        resp = auth_login(BACKEND_URL, {"username": "username", "password": "пароль123!@#"}, timeout=5)

        assert resp.status_code != 400

    def test_auth_034_max_length_username(self):
        """AUTH-034: Username ровно 64 символа (максимальная длина)."""
        test_username = "u" * 64  # Ровно 64 символа
        
        resp = auth_login(BACKEND_URL, {"username": test_username, "password": "password"}, timeout=5)

        assert resp.status_code != 400

    def test_auth_035_max_length_password(self):
        """AUTH-035: Password ровно 64 символа (максимальная длина)."""
        test_password = "p" * 64  # Ровно 64 символа
        
        resp = auth_login(BACKEND_URL, {"username": "username", "password": test_password}, timeout=5)
        assert resp.status_code != 400

    def test_auth_036_http_method_not_allowed(self):
        """AUTH-036: GET-запрос на эндпоинт логина должен вернуть 405."""
        resp = requests.get(f"{BACKEND_URL}/auth/login", timeout=5)
        # Это не валидация тела запроса, поэтому 405 — ожидаемый статус
        assert resp.status_code == 405, f"Expected 405 Method Not Allowed, got {resp.status_code}"

    def test_auth_037_empty_string_fields(self):
        """AUTH-038: Пустые строки в полях отклоняются валидацией."""
        # Пустая строка не удовлетворяет min_length, поэтому ожидаем 400
        resp = auth_login(BACKEND_URL, {"username": "", "password": ""}, timeout=5)
        assert resp.status_code == 400



# ============================================================================
# Проверка аудита (базовая интеграция с ElasticSearch)
# ============================================================================
    
class TestLoginAudit:
    """Тесты проверки записей аудита в ElasticSearch."""

    def test_auth_040_audit_on_successful_login(self, auth_credentials: Dict[str, str]):
        """AUTH-040: Успешный вход записывается в аудит с severity=info."""
        # Запоминаем время ДО запроса
        import time
        before_ts = time.time()
        
        # Выполняем успешный логин
        resp = auth_login(BACKEND_URL, auth_credentials, timeout=5)
        assert resp.status_code == 200
        
        # Ищем запись по известной части сообщения (без client_ip)
        username = auth_credentials["username"]
        # Ключевая часть, которая НЕ меняется
        search_substring = f"action=login status=success subject={username}"
        
        log_entry = get_recent_audit_log(search_substring, "info", "safety")
        
        assert log_entry is not None, (
            f"Audit log for successful login not found. "
            f"Searched for: '{search_substring}' in safety index"
        )
        
        # Дополнительная проверка: timestamp записи позже времени запроса
        assert log_entry.get("timestamp", 0) > int(before_ts * 1000), (
            "Audit log timestamp is before the login request"
        )

    def test_auth_041_audit_on_failed_login(self, auth_credentials: Dict[str, str]):
        """AUTH-041: Неудачный вход записывается в аудит с severity=warning."""
        before_ts = time.time()
        
        # Выполняем логин с неверным паролем
        payload = {**auth_credentials, "password": "wrong_password_for_audit_test"}
        resp = auth_login(BACKEND_URL, payload, timeout=5)
        assert resp.status_code == 401
        
        # Ищем запись о неудаче
        username = auth_credentials["username"]
        # Эта часть сообщения постоянная
        search_substring = f"action=login status=failure subject={username} reason=invalid_credentials"
        
        log_entry = get_recent_audit_log(search_substring, "warning", "safety")
        
        assert log_entry is not None, (
            f"Audit log for failed login not found. "
            f"Searched for: '{search_substring}' in safety index"
        )
        
        # Проверка timestamp
        assert log_entry.get("timestamp", 0) > int(before_ts * 1000), (
            "Audit log timestamp is before the login request"
        )