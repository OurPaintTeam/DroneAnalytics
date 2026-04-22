"""Security scenario: Threat 2 — компрометация JWT-секрета."""
from __future__ import annotations

import os
from typing import Any

import pytest

from security_scenario.utils import forge_access_token, proxy_request


AUTH_USERNAME = os.getenv("AUTH_USERNAME", "user")


pytestmark = pytest.mark.filterwarnings(
    "ignore::urllib3.exceptions.InsecureRequestWarning"
)

def _assert_successful_basic_access(response: Any) -> list[dict[str, Any]]:
    assert response.status_code == 200, response.text
    assert "application/json" in response.headers.get("Content-Type", "")
    data = response.json()
    assert isinstance(data, list), f"Expected list response from /log/basic, got: {type(data).__name__}"
    return data

class TestThreat2JwtSecretCompromise:
    """Шаговые тесты сценария угрозы №2."""

    def test_step_1_valid_access_token_allows_access(self, proxy_base_url: str, valid_access_token: str) -> None:
        response = proxy_request(
            "GET",
            f"{proxy_base_url}/log/basic",
            params={"limit": 10, "page": 1},
            headers={"Authorization": f"Bearer {valid_access_token}"},
        )
        assert response.status_code == 200, response.text

    def test_step_2_tampered_token_is_rejected(self, proxy_base_url: str, valid_access_token: str) -> None:
        tampered = valid_access_token[:-1] + ("a" if valid_access_token[-1] != "a" else "b")
        response = proxy_request(
            "GET",
            f"{proxy_base_url}/log/basic",
            params={"limit": 10, "page": 1},
            headers={"Authorization": f"Bearer {tampered}"},
        )
                
        assert response.status_code == 401, response.text

    def test_step_3_expired_forged_token_is_rejected(self, proxy_base_url: str, compromised_secret_key: str) -> None:
        expired_token = forge_access_token(compromised_secret_key, subject=AUTH_USERNAME, exp_delta_sec=-60)
        response = proxy_request(
            "GET",
            f"{proxy_base_url}/log/basic",
            params={"limit": 10, "page": 1},
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401, response.text

    def test_step_4_forged_token_with_compromised_secret_allows_access(
        self,
        proxy_base_url: str,
        compromised_secret_key: str,
    ) -> None:
        forged_token = forge_access_token(compromised_secret_key, subject=AUTH_USERNAME)
        response = proxy_request(
            "GET",
            f"{proxy_base_url}/log/basic",
            params={"limit": 10, "page": 1},
            headers={"Authorization": f"Bearer {forged_token}"},
        )

        # Ожидаем 200 в текущей модели: при утечке SECRET_KEY можно выпустить валидный токен.
        _assert_successful_basic_access(response)

    def test_step_5_forged_token_without_login_still_allows_access(
        self,
        proxy_base_url: str,
        compromised_secret_key: str,
    ) -> None:
        forged_token = forge_access_token(compromised_secret_key, subject="operator")
        response = proxy_request(
            "GET",
            f"{proxy_base_url}/log/basic",
            params={"limit": 10, "page": 1},
            headers={"Authorization": f"Bearer {forged_token}"},
        )

        # Проверяем именно отсутствие зависимости от /auth/login сессии.
        _assert_successful_basic_access(response)