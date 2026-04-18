"""Security scenario: Threat 4 — XSS-атака на инфопанель.

Важно: этот набор проверок работает только через HTTP-запросы к системе
(без доступа к исходному коду приложения и без браузерной автоматизации).
"""
from __future__ import annotations

import time

import pytest

from security_scenario.utils import elastic_health_check, proxy_request, wait_for_elastic_sync


@pytest.fixture(scope="session", autouse=True)
def wait_for_services() -> None:
    """Переопределяем глобальный skip, чтобы тесты могли сами решать skip по доступности стека."""
    return None


pytestmark = pytest.mark.filterwarnings(
    "ignore::urllib3.exceptions.InsecureRequestWarning"
)


def _require_runtime_stack(proxy_base_url: str) -> None:
    """Проверяет доступность runtime-стека; при недоступности пропускает API-тесты."""
    if not elastic_health_check(timeout=3):
        pytest.skip("ElasticSearch is not available in current environment")

    try:
        resp = proxy_request("GET", f"{proxy_base_url}/auth/login", timeout=3)
    except Exception as exc:  # pragma: no cover - инфраструктурный guard
        pytest.skip(f"Proxy is not available in current environment: {exc}")

    if resp.status_code >= 500:
        pytest.skip(f"Proxy is not healthy in current environment: status={resp.status_code}")

def _require_proxy(proxy_base_url: str) -> None:
    """Проверяет только доступность proxy для header-check тестов."""
    try:
        resp = proxy_request("GET", f"{proxy_base_url}/auth/login", timeout=3)
    except Exception as exc:  # pragma: no cover - инфраструктурный guard
        pytest.skip(f"Proxy is not available in current environment: {exc}")

    if resp.status_code >= 500:
        pytest.skip(f"Proxy is not healthy in current environment: status={resp.status_code}")



class TestThreat4XssInfopanel:
    """API-level проверки снижения риска stored-XSS для поля message."""

    def _post_basic_message(self, proxy_base_url: str, api_headers: dict[str, str], message: str) -> None:
        payload = [{"timestamp": int(time.time() * 1000), "message": message}]
        post_resp = proxy_request(
            "POST",
            f"{proxy_base_url}/log/basic",
            json=payload,
            headers=api_headers,
        )
        assert post_resp.status_code == 200, post_resp.text

    def _login_bearer_headers(self, proxy_base_url: str) -> dict[str, str]:
        login_resp = proxy_request(
            "POST",
            f"{proxy_base_url}/auth/login",
            json={"username": "user", "password": "password"},
        )
        if login_resp.status_code != 200:
            pytest.skip(f"Cannot obtain access token in current environment: {login_resp.status_code}")

        token = login_resp.json().get("access_token")
        if not token:
            pytest.skip("Login response has no access_token")

        return {"Authorization": f"Bearer {token}"}

    def _fetch_basic_logs(self, proxy_base_url: str, bearer_headers: dict[str, str]) -> tuple[list[dict], str]:
        get_resp = proxy_request(
            "GET",
            f"{proxy_base_url}/log/basic",
            params={"limit": 100, "page": 1},
            headers=bearer_headers,
        )
        assert get_resp.status_code == 200, get_resp.text
        content_type = get_resp.headers.get("content-type", "")
        data = get_resp.json()
        assert isinstance(data, list), data
        return data, content_type

    def test_step_1_script_payload_roundtrip_via_api(
        self,
        proxy_base_url: str,
        api_headers: dict[str, str],
    ) -> None:
        """Проверка roundtrip для payload с <script>."""
        _require_runtime_stack(proxy_base_url)
        bearer_headers = self._login_bearer_headers(proxy_base_url)

        marker = f"TH4_SCRIPT_{int(time.time() * 1000)}"
        payload = f"<script>window.__xss_test__='{marker}'</script>"

        self._post_basic_message(proxy_base_url, api_headers, payload)
        wait_for_elastic_sync()

        logs, _ = self._fetch_basic_logs(proxy_base_url, bearer_headers)
        messages = [str(item.get("message", "")) for item in logs if isinstance(item, dict)]
        assert payload in messages, "Script payload not found in API read response"

    def test_step_2_event_handler_payload_roundtrip_via_api(
        self,
        proxy_base_url: str,
        api_headers: dict[str, str],
    ) -> None:
        """Проверка roundtrip для payload с onerror-обработчиком."""
        _require_runtime_stack(proxy_base_url)
        bearer_headers = self._login_bearer_headers(proxy_base_url)

        marker = f"TH4_ONERR_{int(time.time() * 1000)}"
        payload = f"<img src=x onerror=\"window.__xss_test__='{marker}'\">"

        self._post_basic_message(proxy_base_url, api_headers, payload)
        wait_for_elastic_sync()

        logs, _ = self._fetch_basic_logs(proxy_base_url, bearer_headers)
        messages = [str(item.get("message", "")) for item in logs if isinstance(item, dict)]
        assert payload in messages, "onerror payload not found in API read response"

    def test_step_3_js_uri_payload_roundtrip_via_api(
        self,
        proxy_base_url: str,
        api_headers: dict[str, str],
    ) -> None:
        """Проверка roundtrip для payload с javascript: URI."""
        _require_runtime_stack(proxy_base_url)
        bearer_headers = self._login_bearer_headers(proxy_base_url)

        marker = f"TH4_JSURI_{int(time.time() * 1000)}"
        payload = f"<a href=\"javascript:window.__xss_test__='{marker}'\">click</a>"

        self._post_basic_message(proxy_base_url, api_headers, payload)
        wait_for_elastic_sync()

        logs, _ = self._fetch_basic_logs(proxy_base_url, bearer_headers)
        messages = [str(item.get("message", "")) for item in logs if isinstance(item, dict)]
        assert payload in messages, "javascript: payload not found in API read response"

    def test_step_4_logs_endpoint_returns_json_not_html(self, proxy_base_url: str) -> None:
        """GET /log/basic должен возвращать JSON (не HTML), чтобы снизить риск инъекций на транспортном уровне."""
        _require_runtime_stack(proxy_base_url)
        bearer_headers = self._login_bearer_headers(proxy_base_url)

        _, content_type = self._fetch_basic_logs(proxy_base_url, bearer_headers)
        assert "application/json" in content_type.lower(), f"Unexpected content-type: {content_type}"

    def test_step_5_proxy_security_headers_present(self, proxy_base_url: str) -> None:
        """Проверка базовых security headers на proxy (без skip по CSP)."""
        _require_proxy(proxy_base_url)

        resp = proxy_request("GET", f"{proxy_base_url}/auth/login")
        assert resp.status_code in {400, 401, 405}, resp.text

        xcto = resp.headers.get("X-Content-Type-Options")
        xfo = resp.headers.get("X-Frame-Options")
        assert xcto is not None and xcto.lower() == "nosniff"
        assert xfo is not None and xfo.upper() == "DENY"