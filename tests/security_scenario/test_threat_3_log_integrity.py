"""Security scenario: Threat 3 — удаление/модификация журнала."""
from __future__ import annotations

import time

import pytest
import requests

from security_scenario.utils import (
    ELASTIC_URL,
    count_basic_docs_by_message,
    proxy_request,
    wait_for_elastic_sync,
)


pytestmark = pytest.mark.filterwarnings(
    "ignore::urllib3.exceptions.InsecureRequestWarning"
)


class TestThreat3LogIntegrity:
    """Шаговые проверки угрозы удаления/модификации журнала."""

    def test_step_1_baseline_log_persists(self, proxy_base_url: str, api_headers: dict[str, str], bearer_headers: dict[str, str]) -> None:
        marker = f"TH3_BASELINE_{int(time.time() * 1000)}"
        payload = [{"timestamp": int(time.time() * 1000), "message": marker}]

        post_resp = proxy_request(
            "POST",
            f"{proxy_base_url}/log/basic",
            json=payload,
            headers=api_headers,
        )
        assert post_resp.status_code == 200, post_resp.text

        wait_for_elastic_sync()

        get_resp = proxy_request(
            "GET",
            f"{proxy_base_url}/log/basic",
            params={"limit": 50, "page": 1},
            headers=bearer_headers,
        )
        assert get_resp.status_code == 200, get_resp.text
        logs = get_resp.json()
        assert any(item.get("message") == marker for item in logs)

    def test_step_2_delete_method_via_api_is_not_allowed(self, proxy_base_url: str, bearer_headers: dict[str, str]) -> None:
        resp = proxy_request(
            "DELETE",
            f"{proxy_base_url}/log/basic",
            headers=bearer_headers,
        )

        assert resp.status_code in {404, 405}, resp.text

    def test_step_3_conflicting_writes_do_not_erase_previous_entries(self, proxy_base_url: str, api_headers: dict[str, str]) -> None:
        ts = int(time.time() * 1000)
        marker_a = f"TH3_A_{ts}"
        marker_b = f"TH3_B_{ts}"

        payload_a = [{"timestamp": ts, "message": marker_a}]
        payload_b = [{"timestamp": ts, "message": marker_b}]

        resp_a = proxy_request("POST", f"{proxy_base_url}/log/basic", json=payload_a, headers=api_headers)
        resp_b = proxy_request("POST", f"{proxy_base_url}/log/basic", json=payload_b, headers=api_headers)

        assert resp_a.status_code == 200, resp_a.text
        assert resp_b.status_code == 200, resp_b.text

        wait_for_elastic_sync()

        assert count_basic_docs_by_message(marker_a) == 1
        assert count_basic_docs_by_message(marker_b) == 1

    def test_step_4_proxy_path_cannot_delete_in_elastic_style(self, proxy_base_url: str, api_headers: dict[str, str]) -> None:
        """
        Прикладной тест: имитируем попытку обратиться к ES-like endpoint через proxy.
        Ожидание: такой путь не должен позволять удалять данные из журнала.
        """
        marker = f"TH3_PROXY_ES_PATH_{int(time.time() * 1000)}"
        payload = [{"timestamp": int(time.time() * 1000), "message": marker}]

        create_resp = proxy_request("POST", f"{proxy_base_url}/log/basic", json=payload, headers=api_headers)
        assert create_resp.status_code == 200, create_resp.text
        wait_for_elastic_sync()

        before = count_basic_docs_by_message(marker)
        assert before == 1

        attack_resp = proxy_request(
            "POST",
            f"{proxy_base_url}/basic/_delete_by_query",
            json={"query": {"match_phrase": {"message": marker}}},
            headers=api_headers,
        )

        # Через proxy такой ES-admin путь не должен работать.
        assert attack_resp.status_code in {400, 401, 403, 404, 405, 422}, attack_resp.text

        wait_for_elastic_sync()
        after = count_basic_docs_by_message(marker)
        assert after == before
