from __future__ import annotations

import os
from typing import Any

import requests
from hypothesis import HealthCheck, given, settings, strategies as st

from .conftest import BACKEND_URL

API_HEADERS = {
    "X-API-Key": os.getenv("DRONE_API_KEY", "change-me-api-key"),
    "Content-Type": "application/json",
}


json_scalar = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**31), max_value=2**31 - 1),
    st.floats(allow_nan=False, allow_infinity=False, width=32),
    st.text(min_size=0, max_size=128),
)

json_value = st.recursive(
    json_scalar,
    lambda children: st.one_of(
        st.lists(children, min_size=0, max_size=8),
        st.dictionaries(st.text(min_size=0, max_size=32), children, min_size=0, max_size=12),
    ),
    max_leaves=24,
)

telemetry_payload_fuzz = st.one_of(
    json_value,
    st.lists(json_value, min_size=0, max_size=8),
)


class TestTelemetryFuzz:
    """Fuzz tests for telemetry ingestion contract."""

    @settings(
        max_examples=120,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(payload=telemetry_payload_fuzz)
    def test_telemetry_endpoint_never_returns_5xx_for_fuzz_payload(
        self,
        payload: Any,
    ) -> None:
        """Server should reject bad input safely, not crash with 5xx."""
        response = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=API_HEADERS,
            timeout=10,
        )

        assert response.status_code < 500, (
            f"Unexpected 5xx for payload={payload!r}. "
            f"status={response.status_code}, body={response.text}"
        )

    @settings(max_examples=80, deadline=None)
    @given(
        latitude=st.floats(allow_nan=False, allow_infinity=False, width=32),
        longitude=st.floats(allow_nan=False, allow_infinity=False, width=32),
        drone_id=st.integers(min_value=-10_000, max_value=10_000),
        battery=st.one_of(st.none(), st.integers(min_value=-200, max_value=400)),
    )
    def test_telemetry_semantically_extreme_values_do_not_crash(
        self,
        latitude: float,
        longitude: float,
        drone_id: int,
        battery: int | None,
    ) -> None:
        """Extreme numeric values should be handled via validation, not 5xx."""
        record: dict[str, Any] = {
            "apiVersion": "1.0.0",
            "timestamp": 1716200000000,
            "drone": "delivery",
            "drone_id": drone_id,
            "latitude": latitude,
            "longitude": longitude,
        }
        if battery is not None:
            record["battery"] = battery

        response = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=[record],
            headers=API_HEADERS,
            timeout=10,
        )

        assert response.status_code < 500, response.text
        assert response.status_code in {200, 207, 400, 401, 422}, response.text

