"""Фикстуры и общая конфигурация для тестов эндпоинтов."""
import os
import pytest
import requests
from typing import Generator, Dict, Any

from .utils import clean_all_indices, elastic_health_check

# Конфигурация из переменных окружения
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8080")
API_KEY = os.getenv("API_KEY", "change-me")
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "user")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "password")


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
    Используется для тестов GET-эндпоинтов.
    """
    resp = requests.post(
        f"{BACKEND_URL}/auth/login",
        json=auth_credentials,
        timeout=5
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"]
    }


@pytest.fixture
def bearer_headers(logged_in_tokens: Dict[str, Any]) -> Dict[str, str]:
    """Заголовки с Bearer-токеном для авторизованных запросов."""
    return {
        "Authorization": f"Bearer {logged_in_tokens['access_token']}",
        "Content-Type": "application/json"
    }