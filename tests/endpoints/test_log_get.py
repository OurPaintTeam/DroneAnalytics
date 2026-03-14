"""Тесты для GET-эндпоинтов /log/* (требуют Bearer Token)."""
import pytest
import requests
import time
from typing import Dict, Any, List

from .conftest import BACKEND_URL


def wait_for_elastic_sync(seconds: int = 2) -> None:
    """Ждёт применения изменений в ElasticSearch (eventual consistency)."""
    time.sleep(seconds)


class TestGetBasicLogs:
    """Тесты GET /log/basic."""

    def test_get_basic_empty(self, bearer_headers: Dict[str, str]):
        """Получение логов из пустого индекса."""
        wait_for_elastic_sync()
        resp = requests.get(f"{BACKEND_URL}/log/basic", headers=bearer_headers, timeout=5)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_basic_after_insert(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Получение логов после записи."""
        # Сначала записываем
        timestamp = int(time.time() * 1000)
        payload = [{"timestamp": timestamp, "message": "Test message"}]
        post_resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=api_headers, timeout=10)
        assert post_resp.status_code == 200
        
        wait_for_elastic_sync()
        
        # Читаем
        resp = requests.get(f"{BACKEND_URL}/log/basic", headers=bearer_headers, timeout=5)
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 1
        assert logs[0]["message"] == "Test message"
        assert logs[0]["timestamp"] == timestamp

    def test_get_basic_pagination(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Проверка пагинации."""
        # Записываем 5 записей
        timestamp = int(time.time() * 1000)
        payload = [{"timestamp": timestamp + i, "message": f"Msg {i}"} for i in range(5)]
        requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=api_headers, timeout=10)
        wait_for_elastic_sync()
        
        # Запрашиваем по 2 записи
        resp = requests.get(f"{BACKEND_URL}/log/basic", params={"limit": 2, "page": 1}, headers=bearer_headers, timeout=5)
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        
        resp = requests.get(f"{BACKEND_URL}/log/basic", params={"limit": 2, "page": 2}, headers=bearer_headers, timeout=5)
        assert len(resp.json()) == 2
        
        resp = requests.get(f"{BACKEND_URL}/log/basic", params={"limit": 2, "page": 3}, headers=bearer_headers, timeout=5)
        assert len(resp.json()) == 1

    def test_get_basic_unauthorized(self):
        """Запрос без Bearer-токена."""
        resp = requests.get(f"{BACKEND_URL}/log/basic", timeout=5)
        assert resp.status_code == 401


class TestGetTelemetryLogs:
    """Тесты GET /log/telemetry."""

    def test_get_telemetry_after_insert(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Получение телеметрии после записи."""
        timestamp = int(time.time() * 1000)
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": timestamp,
            "drone": "agriculture",
            "drone_id": 42,
            "latitude": 45.0,
            "longitude": 75.0
        }]
        requests.post(f"{BACKEND_URL}/log/telemetry", json=payload, headers=api_headers, timeout=10)
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/telemetry", headers=bearer_headers, timeout=5)
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 1
        assert logs[0]["drone"] == "agriculture"
        assert logs[0]["drone_id"] == 42


class TestGetEventLogs:
    """Тесты GET /log/event и /log/safety."""

    def test_get_event_excludes_audit(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """GET /log/event не возвращает внутренние аудит-логи сервиса."""
        # Записываем событие от сервиса "infopanel" (это AUDIT_SERVICE в бэкенде)
        timestamp = int(time.time() * 1000)
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": timestamp,
            "service": "infopanel",  # Этот сервис исключается при чтении
            "service_id": 1,
            "message": "Internal audit message"
        }]
        requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        
        # Записываем событие от другого сервиса
        payload2 = [{
            "apiVersion": "1.0.0",
            "timestamp": timestamp + 1,
            "service": "GCS",
            "service_id": 1,
            "message": "User event message"
        }]
        requests.post(f"{BACKEND_URL}/log/event", json=payload2, headers=api_headers, timeout=10)
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/event", headers=bearer_headers, timeout=5)
        assert resp.status_code == 200
        logs = resp.json()
        # Должно быть только одно событие (от GCS), аудит-лог от infopanel исключён
        assert len(logs) == 1
        assert logs[0]["service"] == "GCS"

    def test_get_safety_events(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Получение только safety-событий."""
        timestamp = int(time.time() * 1000)
        # Отправляем mixed пакет
        payload = [
            {
                "apiVersion": "1.0.0",
                "timestamp": timestamp,
                "event_type": "event",
                "service": "operator",
                "service_id": 1,
                "message": "Regular event"
            },
            {
                "apiVersion": "1.0.0",
                "timestamp": timestamp + 1,
                "event_type": "safety_event",
                "service": "insurance",
                "service_id": 2,
                "severity": "critical",
                "message": "Safety critical"
            }
        ]
        requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        wait_for_elastic_sync()
        
        # GET /log/event не должен содержать safety
        resp_event = requests.get(f"{BACKEND_URL}/log/event", headers=bearer_headers, timeout=5)
        assert all(log.get("service") != "insurance" for log in resp_event.json())
        
        # GET /log/safety должен содержать только safety
        resp_safety = requests.get(f"{BACKEND_URL}/log/safety", headers=bearer_headers, timeout=5)
        safety_logs = resp_safety.json()
        assert len(safety_logs) == 1
        assert safety_logs[0]["service"] == "insurance"
        assert safety_logs[0]["severity"] == "critical"


class TestLogsSorting:
    """Тесты сортировки логов по времени."""

    def test_logs_sorted_desc(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Логи возвращаются в порядке убывания времени (новые первыми)."""
        base_ts = int(time.time() * 1000)
        # Записываем в обратном порядке
        for i in [3, 1, 2]:
            payload = [{"timestamp": base_ts + i, "message": f"Msg {i}"}]
            requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=api_headers, timeout=10)
        
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/basic", params={"limit": 10}, headers=bearer_headers, timeout=5)
        timestamps = [log["timestamp"] for log in resp.json()]
        assert timestamps == sorted(timestamps, reverse=True)