import time
from typing import Any

import pytest
import requests

from endpoints.utils import wait_for_elastic_sync

pytestmark = pytest.mark.filterwarnings(
    "ignore::urllib3.exceptions.InsecureRequestWarning"
)


def _proxy_request(method: str, url: str, **kwargs: Any) -> requests.Response:
    """HTTP-запрос без использования системных proxy-переменных."""
    with requests.Session() as session:
        session.trust_env = False
        return session.request(method, url, verify=False, timeout=10, **kwargs)


def test_proxy_forwards_auth_login(proxy_base_url: str, proxy_auth_credentials: dict[str, str]):
    """Проверяет, что POST /api/auth/login проходит через proxy до backend."""
    response = _proxy_request(
        "POST",
        f"{proxy_base_url}/auth/login",
        json=proxy_auth_credentials,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data.get("token_type") == "Bearer"
    assert isinstance(data.get("expires_in"), int)
    assert data["expires_in"] > 0
    assert isinstance(response.cookies.get("refresh_token"), str)


def test_proxy_forwards_log_basic(proxy_base_url: str, proxy_api_headers: dict[str, str]):
    """Проверяет, что POST /api/log/basic проходит через proxy до backend."""
    payload = [
        {
            "timestamp": int(time.time() * 1000),
            "message": "Proxy smoke log",
        }
    ]

    response = _proxy_request(
        "POST",
        f"{proxy_base_url}/log/basic",
        json=payload,
        headers=proxy_api_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("total") == 1
    assert body.get("accepted") == 1
    assert body.get("rejected") == 0
    assert body.get("errors") == []


def test_proxy_forwards_log_basic_get(
    proxy_base_url: str,
    proxy_api_headers: dict[str, str],
    proxy_bearer_headers: dict[str, str],
):
    """Проверяет, что GET /api/log/basic возвращает данные, записанные через proxy."""
    message = f"Proxy GET smoke {int(time.time() * 1000)}"
    payload = [{"timestamp": int(time.time() * 1000), "message": message}]

    post_response = _proxy_request(
        "POST",
        f"{proxy_base_url}/log/basic",
        json=payload,
        headers=proxy_api_headers,
    )
    assert post_response.status_code == 200, post_response.text

    wait_for_elastic_sync()

    get_response = _proxy_request(
        "GET",
        f"{proxy_base_url}/log/basic",
        params={"limit": 10, "page": 1},
        headers=proxy_bearer_headers,
    )

    assert get_response.status_code == 200, get_response.text
    logs = get_response.json()
    assert isinstance(logs, list)
    assert any(log.get("message") == message for log in logs)

