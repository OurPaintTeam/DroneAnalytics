import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Добавляем backend в PYTHONPATH, чтобы импортировать app
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from main import app


@pytest.fixture(scope="module")
def client():
    """TestClient для запросов к приложению без запуска сервера"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def valid_api_key():
    """API-ключ из config.py для тестов /log/*"""
    from app.config import API_KEY
    return API_KEY


@pytest.fixture(scope="module")
def valid_credentials():
    """Логин/пароль из config.py для тестов авторизации"""
    from app.config import AUTH_USERNAME, AUTH_PASSWORD
    return {"username": AUTH_USERNAME, "password": AUTH_PASSWORD}

@pytest.fixture(scope="module")
def valid_expires_in():
    """Время на expires_in"""
    from app.config import ACCESS_TTL_SECONDS
    return ACCESS_TTL_SECONDS

@pytest.fixture(scope="module")
def valid_ref_in():
    """Время на refresh token"""
    from app.config import REFRESH_TTL_SECONDS
    return REFRESH_TTL_SECONDS

@pytest.fixture(scope="module")
def valid_secret_key():
    """Ключ подписи"""
    from app.config import SECRET_KEY
    return SECRET_KEY

@pytest.fixture(scope="module")
def valid_jwt_algoritm():
    """Алгоритм для jwt"""
    from app.security import JWT_ALGORITHM
    return JWT_ALGORITHM