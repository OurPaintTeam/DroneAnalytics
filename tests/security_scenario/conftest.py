"""Общие фикстуры для security_scenario тестов."""
from __future__ import annotations

import os
from typing import Generator

import pytest

from security_scenario.utils import clean_all_indices, elastic_health_check, proxy_request


PROXY_URL = os.getenv("PROXY_URL", "https://proxy")
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "user")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "password")
API_KEY = os.getenv("DRONE_API_KEY", "change-me-api-key")


@pytest.fixture(scope="session", autouse=True)
def wait_for_services() -> None:
    """Ожидает доступность ElasticSearch перед запуском security_scenario тестов."""
    if not elastic_health_check(timeout=60):
        pytest.skip("ElasticSearch is not available after 60 seconds in current environment")


@pytest.fixture(autouse=True)
def clean_elastic_after_test() -> Generator[None, None, None]:
    """Очищает индексы после каждого теста."""
    yield
    clean_all_indices()


@pytest.fixture
def proxy_base_url() -> str:
    """Базовый URL proxy с API-префиксом."""
    return f"{PROXY_URL.rstrip('/')}/api"


@pytest.fixture
def api_headers() -> dict[str, str]:
    """Заголовки для API-key защищённых запросов."""
    return {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    }


@pytest.fixture
def bearer_headers(proxy_base_url: str) -> dict[str, str]:
    """Bearer-заголовки после логина через proxy."""
    login_resp = proxy_request(
        "POST",
        f"{proxy_base_url}/auth/login",
        json={"username": AUTH_USERNAME, "password": AUTH_PASSWORD},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def valid_access_token(proxy_base_url: str) -> str:
    """Валидный access token, выданный backend через login."""
    login_resp = proxy_request(
        "POST",
        f"{proxy_base_url}/auth/login",
        json={"username": AUTH_USERNAME, "password": AUTH_PASSWORD},
    )
    assert login_resp.status_code == 200, login_resp.text
    return login_resp.json()["access_token"]


@pytest.fixture
def compromised_secret_key() -> str:
    """Скомпрометированный секрет для сценариев Threat 2 (если задан)."""
    key = os.getenv("DRONE_SECRET_KEY", "replace-with-a-long-random-string")
    return key

