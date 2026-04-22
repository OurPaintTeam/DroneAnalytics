"""Security scenario: Threat 1 — подмена телеметрии через API-ключ."""
from __future__ import annotations

import pytest
import time
from typing import Any

from security_scenario.utils import proxy_request, wait_for_elastic_sync


pytestmark = pytest.mark.filterwarnings(
    "ignore::urllib3.exceptions.InsecureRequestWarning"
)


def _telemetry_payload(
    *,
    drone_id: int,
    timestamp_ms: int,
    latitude: float,
    longitude: float,
) -> list[dict[str, Any]]:
    return [
        {
            "apiVersion": "1.0.0",
            "timestamp": timestamp_ms,
            "drone": "delivery",
            "drone_id": drone_id,
            "battery": 80,
            "pitch": 0.0,
            "roll": 0.0,
            "course": 120.0,
            "latitude": latitude,
            "longitude": longitude,
            "height": 0.0,
        }
    ]


def _fetch_telemetry_for_drone(
    *,
    proxy_base_url: str,
    bearer_headers: dict[str, str],
    drone_id: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    response = proxy_request(
        "GET",
        f"{proxy_base_url}/log/telemetry",
        params={"drone_id": drone_id, "limit": limit, "page": 1},
        headers=bearer_headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, list), f"Expected telemetry list, got: {type(payload).__name__}"
    return payload


class TestThreat1ApiKeySpoofing:
    """Пошаговая проверка угрозы №1 (шаги 1-4)."""

    # В маппинге Elastic поле telemetry.drone_id имеет тип short (до 32767).

    def test_step_1_valid_api_key_allows_telemetry(
        self,
        proxy_base_url: str,
        api_headers: dict[str, str],
        bearer_headers: dict[str, str],
    ) -> None:
        drone_id = 901
        payload = _telemetry_payload(
            drone_id=drone_id,
            timestamp_ms=int(time.time() * 1000),
            latitude=55.7558,
            longitude=37.6176,
        )

        response = proxy_request(
            "POST",
            f"{proxy_base_url}/log/telemetry",
            json=payload,
            headers=api_headers,
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["accepted"] == 1
        assert data["rejected"] == 0

        wait_for_elastic_sync()
        telemetry_docs = _fetch_telemetry_for_drone(
            proxy_base_url=proxy_base_url,
            bearer_headers=bearer_headers,
            drone_id=drone_id,
        )
        assert len(telemetry_docs) == 1

    def test_step_2_missing_api_key_is_rejected(
        self,
        proxy_base_url: str,
        bearer_headers: dict[str, str],
    ) -> None:
        drone_id = 902
        payload = _telemetry_payload(
            drone_id=drone_id,
            timestamp_ms=int(time.time() * 1000),
            latitude=55.7560,
            longitude=37.6180,
        )

        response = proxy_request(
            "POST",
            f"{proxy_base_url}/log/telemetry",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 401, response.text

        wait_for_elastic_sync()
        telemetry_docs = _fetch_telemetry_for_drone(
            proxy_base_url=proxy_base_url,
            bearer_headers=bearer_headers,
            drone_id=drone_id,
        )
        assert len(telemetry_docs) == 0

    def test_step_3_invalid_api_key_is_rejected(
        self,
        proxy_base_url: str,
        bearer_headers: dict[str, str],
    ) -> None:
        drone_id = 903
        payload = _telemetry_payload(
            drone_id=drone_id,
            timestamp_ms=int(time.time() * 1000),
            latitude=55.7570,
            longitude=37.6190,
        )

        response = proxy_request(
            "POST",
            f"{proxy_base_url}/log/telemetry",
            json=payload,
            headers={"X-API-Key": "invalid-key", "Content-Type": "application/json"},
        )

        assert response.status_code == 401, response.text

        wait_for_elastic_sync()
        telemetry_docs = _fetch_telemetry_for_drone(
            proxy_base_url=proxy_base_url,
            bearer_headers=bearer_headers,
            drone_id=drone_id,
        )
        assert len(telemetry_docs) == 0

    def test_step_4_compromised_valid_api_key_allows_spoofing(
        self,
        proxy_base_url: str,
        api_headers: dict[str, str],
        bearer_headers: dict[str, str],
    ) -> None:
        drone_id = 904
        base_ts = int(time.time() * 1000)

        legitimate_payloads = [
            _telemetry_payload(
                drone_id=drone_id,
                timestamp_ms=base_ts,
                latitude=55.7558,
                longitude=37.6176,
            ),
            _telemetry_payload(
                drone_id=drone_id,
                timestamp_ms=base_ts + 1000,
                latitude=55.7562,
                longitude=37.6181,
            ),
        ]

        for payload in legitimate_payloads:
            response = proxy_request(
                "POST",
                f"{proxy_base_url}/log/telemetry",
                json=payload,
                headers=api_headers,
            )
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["accepted"] == 1
            assert data["rejected"] == 0

        attacker_headers = {
            "X-API-Key": api_headers["X-API-Key"],
            "Content-Type": "application/json",
        }
        spoofed_payload = _telemetry_payload(
            drone_id=drone_id,
            timestamp_ms=base_ts + 2000,
            latitude=-33.8688,
            longitude=151.2093,
        )

        attacker_response = proxy_request(
            "POST",
            f"{proxy_base_url}/log/telemetry",
            json=spoofed_payload,
            headers=attacker_headers,
        )

        assert attacker_response.status_code == 200, attacker_response.text
        attacker_data = attacker_response.json()
        assert attacker_data["accepted"] == 1
        assert attacker_data["rejected"] == 0

        wait_for_elastic_sync()
        telemetry_docs = _fetch_telemetry_for_drone(
            proxy_base_url=proxy_base_url,
            bearer_headers=bearer_headers,
            drone_id=drone_id,
            limit=10,
        )
        assert len(telemetry_docs) == 3
        assert any(
            item.get("timestamp") == base_ts + 2000
            and item.get("latitude") == -33.8688
            and item.get("longitude") == 151.2093
            for item in telemetry_docs
        )
