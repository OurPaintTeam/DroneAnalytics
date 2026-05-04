"""Фикстуры и общая конфигурация для тестов эндпоинтов."""
import os
import pytest
import requests
import secrets
from typing import Generator, Dict, Any


from .utils import clean_all_indices, elastic_health_check, auth_login


def _require_env(var_name: str) -> str:
    """Читает обязательную переменную окружения и валидирует, что она не пустая."""
    value = os.getenv(var_name)
    if value is None or not value.strip():
        raise RuntimeError(
            f"Required environment variable {var_name} is not set. "
            "Set it in pytest.ini or CI env to match backend secrets/backend.yaml."
        )
    return value

# Конфигурация из переменных окружения
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8080")
API_KEY = os.getenv("DRONE_API_KEY", "change-me-api-key")
AUTH_USERNAME = _require_env("AUTH_USERNAME")
AUTH_PASSWORD = _require_env("AUTH_PASSWORD")
# Тестовый секретный ключ для генерации JWT в тестах (должен совпадать с backend secrets)
SECRET_KEY = os.getenv("DRONE_SECRET_KEY", "replace-with-a-long-random-string").encode("utf-8")
REFRESH_TTL_SECONDS = int(os.getenv("DRONE_REFRESH_TTL_SECONDS", "604800"))
ACCESS_TTL_SECONDS = int(os.getenv("DRONE_ACCESS_TTL_SECONDS", "900"))
JWT_ALGORITHM = "HS256"
JWT_REQUIRED_CLAIMS = ["exp", "iat", "sub", "type", "jti"]


@pytest.fixture(scope="session", autouse=True)
def wait_for_services() -> None:
    """
    Фикстура сессии: ожидает готовности ElasticSearch.
    Запускается один раз перед всеми тестами.
    """
    if not elastic_health_check(timeout=60):
        pytest.fail("ElasticSearch is not available after 60 seconds")


@pytest.fixture(autouse=True)
def clean_elastic_after_test() -> Generator[None, None, None]:
    """
    Фикстура для каждого теста: очищает ElasticSearch ПОСЛЕ выполнения теста.
    Это гарантирует, что каждый тест начинает с чистого состояния.
    """
    yield  # Выполняем тест
    clean_all_indices()  # Очищаем после теста

@pytest.fixture(scope="session", autouse=True)
def verify_auth_seed_credentials() -> None:
    """
    Проверяет, что тестовые креды действительно соответствуют users в backend secrets.

    Зачем:
    - backend больше не читает логин/пароль из env;
    - тесты должны явно подтвердить, что AUTH_USERNAME/AUTH_PASSWORD синхронизированы
      с текущим secrets/backend.yaml backend-сервиса.
    """
    try:
        ok_resp = auth_login(
            BACKEND_URL,
            {"username": AUTH_USERNAME, "password": AUTH_PASSWORD},
            timeout=5,
        )
    except requests.RequestException as exc:
        pytest.skip(f"Cannot validate auth credentials in current environment: {exc}")

    if ok_resp.status_code in {403, 404, 502, 503, 504}:
        pytest.skip(
            "Cannot validate auth credentials in current environment "
            f"(BACKEND_URL={BACKEND_URL}, status={ok_resp.status_code})."
        )

    if ok_resp.status_code != 200:
        pytest.fail(
            "Configured AUTH_USERNAME/AUTH_PASSWORD are not accepted by backend. "
            f"Got {ok_resp.status_code}: {ok_resp.text}"
        )

    wrong_resp = auth_login(
        BACKEND_URL,
        {
            "username": f"{AUTH_USERNAME}_definitely_wrong",
            "password": f"{AUTH_PASSWORD}_definitely_wrong",
        },
        timeout=5,
    )
    if wrong_resp.status_code != 401:
        pytest.fail(
            "Backend unexpectedly accepted obviously invalid credentials. "
            f"Got {wrong_resp.status_code}: {wrong_resp.text}"
        )


@pytest.fixture
def api_headers() -> Dict[str, str]:
    """Заголовки для запросов с API Key (для POST /log/*)."""
    return {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }


@pytest.fixture
def auth_credentials() -> Dict[str, str]:
    """Учетные данные для логина."""
    return {"username": AUTH_USERNAME, "password": AUTH_PASSWORD}


@pytest.fixture
def logged_in_tokens(auth_credentials: Dict[str, str]) -> Dict[str, Any]:
    """
    Фикстура: выполняет логин и возвращает пару токенов.
    Refresh токен берётся из cookie, access_token из JSON ответа.
    Используется для тестов GET-эндпоинтов.
    """
    resp = requests.post(
        f"{BACKEND_URL}/auth/login",
        json=auth_credentials,
        timeout=5
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    refresh_token = resp.cookies.get("refresh_token")
    assert refresh_token is not None, "refresh_token not found in cookies"
    return {
        "access_token": data["access_token"],
        "refresh_token": refresh_token
    }


@pytest.fixture
def bearer_headers(logged_in_tokens: Dict[str, Any]) -> Dict[str, str]:
    """Заголовки с Bearer-токеном для авторизованных запросов."""
    return {
        "Authorization": f"Bearer {logged_in_tokens['access_token']}",
        "Content-Type": "application/json"
    }