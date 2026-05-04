import os
from typing import Any, Dict, Generator

import pytest
import requests

from endpoints.utils import clean_all_indices, elastic_health_check

PROXY_URL = os.getenv("PROXY_URL", "https://proxy")
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "user")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "password")
API_KEY = os.getenv("DRONE_API_KEY", "change-me-api-key")


@pytest.fixture(scope="session", autouse=True)
def wait_for_services() -> None:
    """Ожидает готовности ElasticSearch до запуска proxy-тестов."""
    if not elastic_health_check(timeout=60):
        pytest.fail("ElasticSearch is not available after 60 seconds")


@pytest.fixture(autouse=True)
def clean_elastic_after_test() -> Generator[None, None, None]:
    """Очищает тестовые индексы после каждого proxy-теста."""
    yield
    clean_all_indices()


@pytest.fixture
def proxy_base_url() -> str:
    """Базовый URL прокси с API-префиксом."""
    return f"{PROXY_URL.rstrip('/')}/api"


@pytest.fixture
def proxy_auth_credentials() -> Dict[str, str]:
    """Учетные данные пользователя для логина через прокси."""
    return {"username": AUTH_USERNAME, "password": AUTH_PASSWORD}


@pytest.fixture
def proxy_api_headers() -> Dict[str, str]:
    """Заголовки для API Key запросов через прокси."""
    return {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    }


@pytest.fixture
def proxy_logged_in_tokens(proxy_base_url: str, proxy_auth_credentials: Dict[str, str]) -> Dict[str, Any]:
    """Логин через proxy и возврат access-токена + refresh-токена из cookie."""
    with requests.Session() as session:
        session.trust_env = False
        response = session.post(
            f"{proxy_base_url}/auth/login",
            json=proxy_auth_credentials,
            verify=False,
            timeout=10,
        )
    assert response.status_code == 200, response.text
    data = response.json()
    refresh_cookie = response.cookies.get("refresh_token")
    assert isinstance(refresh_cookie, str) and len(refresh_cookie) > 0
    return {
        "access_token": data["access_token"],
        "refresh_token": refresh_cookie,
    }


@pytest.fixture
def proxy_bearer_headers(proxy_logged_in_tokens: Dict[str, Any]) -> Dict[str, str]:
    """Authorization-заголовки для GET-запросов через proxy."""
    return {
        "Authorization": f"Bearer {proxy_logged_in_tokens['access_token']}",
        "Content-Type": "application/json",
    }