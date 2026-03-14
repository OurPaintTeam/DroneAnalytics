"""Тесты для POST-эндпоинтов /log/* (требуют API Key)."""
import pytest
import requests
from datetime import datetime
from typing import List, Dict, Any

from .conftest import BACKEND_URL


def get_timestamp_ms() -> int:
    """Возвращает текущее время в миллисекундах (как в приложении)."""
    return int(datetime.now().timestamp() * 1000)


class TestLogTelemetry:
    """Тесты POST /log/telemetry."""

    def test_telemetry_success(self, api_headers: Dict[str, str]):
        """Успешная отправка валидной телеметрии."""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "drone": "delivery",
            "drone_id": 1,
            "battery": 85,
            "pitch": 5.5,
            "roll": -2.1,
            "course": 180.0,
            "latitude": 55.7558,
            "longitude": 37.6176
        }]
        resp = requests.post(f"{BACKEND_URL}/log/telemetry", json=payload, headers=api_headers, timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert data["accepted"] == 1
        assert data["rejected"] == 0
        assert data["errors"] == []

    def test_telemetry_partial_success(self, api_headers: Dict[str, str]):
        """Частичный успех: один валидный, один невалидный документ."""
        payload = [
            {
                "apiVersion": "1.0.0",
                "timestamp": get_timestamp_ms(),
                "drone": "inspector",
                "drone_id": 2,
                "latitude": 59.9343,
                "longitude": 30.3351
                # Остальные поля опциональны
            },
            {
                "apiVersion": "1.0.0",
                "timestamp": get_timestamp_ms(),
                "drone": "invalid_type",  # Не из Literal
                "drone_id": 999,
                "latitude": 0,
                "longitude": 0
            }
        ]
        resp = requests.post(f"{BACKEND_URL}/log/telemetry", json=payload, headers=api_headers, timeout=10)
        assert resp.status_code == 207  # Multi-Status
        data = resp.json()
        assert data["accepted"] == 1
        assert data["rejected"] == 1
        assert len(data["errors"]) == 1

    def test_telemetry_missing_api_key(self):
        """Запрос без API-ключа должен быть отклонён."""
        resp = requests.post(f"{BACKEND_URL}/log/telemetry", json=[], timeout=5)
        assert resp.status_code == 401

    def test_telemetry_invalid_api_key(self):
        """Запрос с неверным API-ключом."""
        headers = {"X-API-Key": "wrong-key", "Content-Type": "application/json"}
        resp = requests.post(f"{BACKEND_URL}/log/telemetry", json=[], headers=headers, timeout=5)
        assert resp.status_code == 401

    def test_telemetry_empty_array(self, api_headers: Dict[str, str]):
        """Пустой массив должен вызвать ошибку валидации (min_length=1)."""
        resp = requests.post(f"{BACKEND_URL}/log/telemetry", json=[], headers=api_headers, timeout=5)
        assert resp.status_code == 400


class TestLogBasic:
    """Тесты POST /log/basic."""

    def test_basic_success(self, api_headers: Dict[str, str]):
        """Успешная отправка базовых логов."""
        payload = [{
            "timestamp": get_timestamp_ms(),
            "message": "Test basic log message"
        }]
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=api_headers, timeout=10)
        assert resp.status_code == 200
        assert resp.json()["accepted"] == 1

    def test_basic_message_too_long(self, api_headers: Dict[str, str]):
        """Сообщение длиннее 1024 символов."""
        payload = [{
            "timestamp": get_timestamp_ms(),
            "message": "x" * 1025
        }]
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=api_headers, timeout=5)
        assert resp.status_code == 400  # Validation error


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