import pytest
from fastapi.testclient import TestClient

# Импорт тестовых данных
from .test_backend_config import (
    TEST_AUTH_USERNAME,
    TEST_AUTH_PASSWORD,
    TEST_API_KEY,
    TEST_SECRET_KEY,
    TEST_JWT_ALGORITHM,
    TEST_ACCESS_TTL_SECONDS,
    TEST_REFRESH_TTL_SECONDS,
    TEST_CORS_ORIGINS,
    TEST_PASSWORD_SALT,
)


@pytest.fixture(scope="function", autouse=True)
def override_env_vars(monkeypatch):
    """Переопределяет переменные окружения на тестовые"""
    
    # Авторизация
    monkeypatch.setenv("DRONE_AUTH_USERNAME", TEST_AUTH_USERNAME)
    monkeypatch.setenv("DRONE_AUTH_PASSWORD", TEST_AUTH_PASSWORD)
    monkeypatch.setenv("DRONE_API_KEY", TEST_API_KEY)
    
    # JWT и безопасность
    monkeypatch.setenv("DRONE_SECRET_KEY", TEST_SECRET_KEY.decode("utf-8"))
    monkeypatch.setenv("DRONE_PASSWORD_SALT", TEST_PASSWORD_SALT)
    monkeypatch.setenv("DRONE_ACCESS_TTL_SECONDS", str(TEST_ACCESS_TTL_SECONDS))
    monkeypatch.setenv("DRONE_REFRESH_TTL_SECONDS", str(TEST_REFRESH_TTL_SECONDS))
    
    # CORS
    monkeypatch.setenv("DRONE_CORS_ORIGINS", ",".join(TEST_CORS_ORIGINS))


@pytest.fixture(scope="function")
def client():
    """
    TestClient для запросов к приложению.
    """
    from main import app
    
    with TestClient(app) as test_client:
        yield test_client


# Фикстуры с тестовыми значениями, берем из test_backend_config.py для удобства
@pytest.fixture(scope="module")
def valid_api_key():
    return TEST_API_KEY


@pytest.fixture(scope="module")
def valid_credentials():
    return {"username": TEST_AUTH_USERNAME, "password": TEST_AUTH_PASSWORD}


@pytest.fixture(scope="module")
def valid_expires_in():
    return TEST_ACCESS_TTL_SECONDS


@pytest.fixture(scope="module")
def valid_ref_in():
    return TEST_REFRESH_TTL_SECONDS


@pytest.fixture(scope="module")
def valid_secret_key():
    return TEST_SECRET_KEY


@pytest.fixture(scope="module")
def valid_jwt_algorithm():
    return TEST_JWT_ALGORITHM