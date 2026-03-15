"""Тесты для POST-эндпоинтов /log/* (требуют API Key)."""
import pytest
import requests
from datetime import datetime
from typing import List, Dict, Any

from .conftest import BACKEND_URL


def get_timestamp_ms() -> int:
    """Возвращает текущее время в миллисекундах (как в приложении)."""
    return int(datetime.now().timestamp() * 1000)


class TestLogEvent:
    """Тесты POST /log/event."""

    def test_event_success(self, api_headers: Dict[str, str]):
        """Успешная отправка обычного события."""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "event_type": "event",
            "service": "GCS",
            "service_id": 1,
            "severity": "info",
            "message": "Mission started"
        }]
        resp = requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        assert resp.status_code == 200
        assert resp.json()["accepted"] == 1

    def test_safety_event_success(self, api_headers: Dict[str, str]):
        """Успешная отправка safety_event (должен попасть в индекс 'safety')."""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "event_type": "safety_event",
            "service": "dronePort",
            "service_id": 2,
            "severity": "warning",
            "message": "High wind detected"
        }]
        resp = requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        assert resp.status_code == 200
        assert resp.json()["accepted"] == 1

    def test_event_invalid_service(self, api_headers: Dict[str, str]):
        """Невалидное значение service (не из Literal)."""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "service": "unknown_service",
            "service_id": 1,
            "message": "Test"
        }]
        resp = requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=5)
        assert resp.status_code == 400  # Validation error

    def test_event_batch_mixed_types(self, api_headers: Dict[str, str]):
        """Пакет с обычными и safety событиями одновременно."""
        payload = [
            {
                "apiVersion": "1.0.0",
                "timestamp": get_timestamp_ms(),
                "event_type": "event",
                "service": "aggregator",
                "service_id": 3,
                "message": "Regular event"
            },
            {
                "apiVersion": "1.0.0",
                "timestamp": get_timestamp_ms(),
                "event_type": "safety_event",
                "service": "regulator",
                "service_id": 4,
                "severity": "error",
                "message": "Safety event"
            }
        ]
        resp = requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert data["accepted"] == 2
        assert data["rejected"] == 0