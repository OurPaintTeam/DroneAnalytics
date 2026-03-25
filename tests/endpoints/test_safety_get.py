"""
Интеграционные тесты для эндпоинта GET /log/safety.

Проверяют получение safety-событий из ElasticSearch:
- фильтрацию (только safety_event, исключение infopanel)
- сортировку по времени (desc)
- пагинацию
- целостность данных
"""
import requests
from typing import Dict

from .conftest import BACKEND_URL
from .utils import (
    get_timestamp_ms,
    wait_for_elastic_sync,
    create_event_payload,
    post_event_logs,
    get_paginated_logs,
)


# ============================================================================
# Тестовый класс
# ============================================================================

class TestGetSafetyLogs:
    """Интеграционные тесты для GET /log/safety."""

    # -------------------------------------------------------------------------
    # Базовые сценарии: пустой индекс, одно событие
    # -------------------------------------------------------------------------

    def test_get_safety_empty_index(self, bearer_headers: Dict[str, str]):
        """TC-SAFETY-001: Получение логов из пустого индекса."""
        wait_for_elastic_sync()
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers)
        
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_safety_single_event(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-002: Получение одного записанного safety-события."""
        timestamp = get_timestamp_ms()
        event = create_event_payload(event_type="safety_event", 
            service="insurance",
            service_id=42,
            severity="critical",
            message="Critical safety issue",
            timestamp=timestamp
        )
        
        # Записываем событие
        post_resp = post_event_logs(BACKEND_URL, api_headers, [event])
        assert post_resp.status_code == 200
        wait_for_elastic_sync()
        
        # Читаем
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 1
        assert logs[0]["timestamp"] == timestamp
        assert logs[0]["service"] == "insurance"
        assert logs[0]["service_id"] == 42
        assert logs[0]["severity"] == "critical"
        assert logs[0]["message"] == "Critical safety issue"
        # Убедимся, что служебные поля записи отсутствуют в ответе
        assert "apiVersion" not in logs[0]
        assert "event_type" not in logs[0]

    # -------------------------------------------------------------------------
    # Фильтрация: только safety_event, исключение AUDIT_SERVICE
    # -------------------------------------------------------------------------

    def test_get_safety_excludes_regular_events(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-003: Возвращаются только события с event_type='safety_event'."""
        timestamp = get_timestamp_ms()
        
        # Отправляем смешанный пакет: обычное событие + safety
        payload = [
            create_event_payload(event_type="event", 
                service="GCS",
                message="Regular event - should NOT appear",
                timestamp=timestamp
            ),
            create_event_payload(event_type="safety_event", 
                service="regulator",
                message="Safety event - SHOULD appear",
                timestamp=timestamp + 1
            )
        ]
        
        post_resp = post_event_logs(BACKEND_URL, api_headers, payload)
        assert post_resp.status_code == 200
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        
        # Должно быть только одно событие, и это safety
        assert len(logs) == 1
        assert logs[0]["service"] == "regulator"
        assert logs[0]["message"] == "Safety event - SHOULD appear"

    def test_get_safety_excludes_audit_service(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-004: Исключение логов сервиса infopanel (AUDIT_SERVICE)."""
        timestamp = get_timestamp_ms()
        
        # Отправляем safety-события: одно от infopanel (аудит), одно от другого сервиса
        payload = [
            create_event_payload(event_type="safety_event", 
                service="infopanel",  # AUDIT_SERVICE - должен быть исключён
                service_id=1,
                message="Internal audit safety log - should NOT appear",
                timestamp=timestamp
            ),
            create_event_payload(event_type="safety_event", 
                service="dronePort",  # Обычный сервис - должен быть в ответе
                service_id=2,
                severity="warning",
                message="External safety log - SHOULD appear",
                timestamp=timestamp + 1
            )
        ]
        
        post_resp = post_event_logs(BACKEND_URL, api_headers, payload)
        assert post_resp.status_code == 200
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        
        # Только событие от dronePort должно быть в ответе
        assert len(logs) == 1
        assert logs[0]["service"] == "dronePort"
        assert logs[0]["message"] == "External safety log - SHOULD appear"
        # Убеждаемся, что аудит-лог действительно отфильтрован
        assert not any(log["service"] == "infopanel" for log in logs)

    # -------------------------------------------------------------------------
    # Сортировка по времени (desc)
    # -------------------------------------------------------------------------

    def test_get_safety_sorted_by_timestamp_desc(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-005: Сортировка по убыванию timestamp (новые первыми)."""
        base_ts = get_timestamp_ms()
        
        # Записываем события в "перемешанном" порядке по времени
        payload = [
            create_event_payload(event_type="safety_event", message="Old event", timestamp=base_ts),
            create_event_payload(event_type="safety_event", message="Newest event", timestamp=base_ts + 2000),
            create_event_payload(event_type="safety_event", message="Middle event", timestamp=base_ts + 1000),
        ]
        
        post_resp = post_event_logs(BACKEND_URL, api_headers, payload)
        assert post_resp.status_code == 200
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers, limit=10)
        assert resp.status_code == 200
        logs = resp.json()
        
        # Проверяем порядок: сначала самый новый
        assert len(logs) == 3
        assert logs[0]["message"] == "Newest event"
        assert logs[1]["message"] == "Middle event"
        assert logs[2]["message"] == "Old event"
        
        # Дополнительная проверка: значения timestamp действительно идут по убыванию
        timestamps = [log["timestamp"] for log in logs]
        assert timestamps == sorted(timestamps, reverse=True)

    # -------------------------------------------------------------------------
    # Пагинация
    # -------------------------------------------------------------------------

    def test_get_safety_pagination_first_page(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-006: Пагинация: limit=2, page=1."""
        base_ts = get_timestamp_ms()
        
        # Записываем 5 событий
        payload = [
            create_event_payload(event_type="safety_event", message=f"Event {i}", timestamp=base_ts + i * 100)
            for i in range(5)
        ]
        post_event_logs(BACKEND_URL, api_headers, payload)
        wait_for_elastic_sync()
        
        # Запрашиваем первую страницу: 2 самых новых
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers, limit=2, page=1)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 2
        # Самые новые: Event 4 и Event 3 (т.к. сортировка desc)
        assert logs[0]["message"] == "Event 4"
        assert logs[1]["message"] == "Event 3"

    def test_get_safety_pagination_second_page(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-007: Пагинация: limit=2, page=2."""
        base_ts = get_timestamp_ms()
        
        payload = [
            create_event_payload(event_type="safety_event", message=f"Event {i}", timestamp=base_ts + i * 100)
            for i in range(5)
        ]
        post_event_logs(BACKEND_URL, api_headers, payload)
        wait_for_elastic_sync()
        
        # Вторая страница: следующие 2 события
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers, limit=2, page=2)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 2
        assert logs[0]["message"] == "Event 2"
        assert logs[1]["message"] == "Event 1"

    def test_get_safety_pagination_last_partial_page(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-008: Пагинация: последняя страница с неполным набором."""
        base_ts = get_timestamp_ms()
        
        payload = [
            create_event_payload(event_type="safety_event", message=f"Event {i}", timestamp=base_ts + i * 100)
            for i in range(5)
        ]
        post_event_logs(BACKEND_URL, api_headers, payload)
        wait_for_elastic_sync()
        
        # Третья страница: останется 1 событие
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers, limit=2, page=3)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 1
        assert logs[0]["message"] == "Event 0"  # Самое старое

    def test_get_safety_pagination_empty_page(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-018: Запрос за пределами доступных данных (page=999)."""
        base_ts = get_timestamp_ms()
        
        # Записываем 3 события
        payload = [create_event_payload(event_type="safety_event", timestamp=base_ts + i) for i in range(3)]
        post_event_logs(BACKEND_URL, api_headers, payload)
        wait_for_elastic_sync()
        
        # Запрашиваем несуществующую страницу
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers, limit=10, page=999)
        assert resp.status_code == 200
        assert resp.json() == []

    # -------------------------------------------------------------------------
    # Граничные значения параметров
    # -------------------------------------------------------------------------

    def test_get_safety_limit_min(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-009: Граничное значение limit=1."""
        base_ts = get_timestamp_ms()
        
        payload = [
            create_event_payload(event_type="safety_event", message="First", timestamp=base_ts),
            create_event_payload(event_type="safety_event", message="Second", timestamp=base_ts + 100)
        ]
        post_event_logs(BACKEND_URL, api_headers, payload)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers, limit=1)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 1
        assert logs[0]["message"] == "Second"  # Самый новый

    def test_get_safety_limit_max(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-010: Граничное значение limit=100."""
        base_ts = get_timestamp_ms()
        
        # Записываем 105 событий
        payload = [
            create_event_payload(event_type="safety_event", timestamp=base_ts + i)
            for i in range(105)
        ]
        post_event_logs(BACKEND_URL, api_headers, payload)
        wait_for_elastic_sync()
        
        # Запрашиваем максимум (100)
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers, limit=100)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 100
        # Проверяем, что вернулись самые новые (104..5)
        assert logs[0]["timestamp"] == base_ts + 104
        assert logs[-1]["timestamp"] == base_ts + 5

    def test_get_safety_default_limit(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-011: Значение limit по умолчанию."""
        base_ts = get_timestamp_ms()
        
        # Записываем 15 событий
        payload = [create_event_payload(event_type="safety_event", timestamp=base_ts + i) for i in range(15)]
        post_event_logs(BACKEND_URL, api_headers, payload)
        wait_for_elastic_sync()
        
        # Запрос без параметров
        resp = requests.get(
            f"{BACKEND_URL}/log/safety",
            headers=bearer_headers,
            timeout=5
        )
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) !=0

    def test_get_safety_default_page(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-012: Первая страница по умолчанию (page=1)."""
        base_ts = get_timestamp_ms()
        
        payload = [create_event_payload(event_type="safety_event", timestamp=base_ts + i) for i in range(25)]
        post_event_logs(BACKEND_URL, api_headers, payload)
        wait_for_elastic_sync()
        
        # Запрос с limit, но без page: должен применить page=1
        resp = requests.get(
            f"{BACKEND_URL}/log/safety?limit=10",
            headers=bearer_headers,
            timeout=5
        )
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 10
        assert logs[0]["timestamp"] == base_ts + 24  # Самый новый
        assert logs[-1]["timestamp"] == base_ts + 15

    # -------------------------------------------------------------------------
    # Целостность данных и валидация схемы
    # -------------------------------------------------------------------------

    def test_get_safety_response_schema_integrity(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-013: Проверка целостности полей ответа."""
        timestamp = get_timestamp_ms()
        
        event = create_event_payload(event_type="safety_event", 
            service="agriculture",
            service_id=99,
            severity="error",
            message="Test message with all fields",
            timestamp=timestamp
        )
        
        post_event_logs(BACKEND_URL, api_headers, [event])
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 1
        log = logs[0]
        
        # Проверка обязательных полей
        assert "timestamp" in log and isinstance(log["timestamp"], int)
        assert "service" in log and isinstance(log["service"], str)
        assert "service_id" in log and isinstance(log["service_id"], int)
        assert "message" in log and isinstance(log["message"], str)
        
        # Проверка опционального поля
        assert "severity" in log  # Может быть null или строка
        
        # Проверка отсутствия служебных полей записи
        assert "apiVersion" not in log
        assert "event_type" not in log
        
        # Проверка значений
        assert log["service"] == "agriculture"
        assert log["service_id"] == 99
        assert log["severity"] == "error"
        assert log["message"] == "Test message with all fields"
        assert log["timestamp"] == timestamp

    def test_get_safety_with_null_severity(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-015: Обработка событий с null в опциональных полях."""
        timestamp = get_timestamp_ms()
        
        # Создаём событие с null severity (разрешено схемой)
        event = {
            "apiVersion": "1.0.0",
            "timestamp": timestamp,
            "event_type": "safety_event",
            "service": "operator",
            "service_id": 7,
            "severity": None,  # Явный null
            "message": "Event without severity"
        }
        
        post_event_logs(BACKEND_URL, api_headers, [event])
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 1
        assert logs[0]["severity"] is None
        assert logs[0]["message"] == "Event without severity"

    def test_get_safety_boundary_values(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-020: Валидация с граничными значениями полей."""
        timestamp = get_timestamp_ms()
        
        # Сообщение максимальной длины (1024 символа) и минимальный service_id
        event = create_event_payload(event_type="safety_event", 
            service="registry",
            service_id=1,  # Минимальное значение по схеме
            severity="emergency",  # Максимальный уровень
            message="x" * 1024,  # Максимальная длина
            timestamp=timestamp
        )
        
        post_event_logs(BACKEND_URL, api_headers, [event])
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 1
        assert logs[0]["service_id"] == 1
        assert logs[0]["severity"] == "emergency"
        assert len(logs[0]["message"]) == 1024
        assert logs[0]["message"] == "x" * 1024

    # -------------------------------------------------------------------------
    # Дополнительные сценарии
    # -------------------------------------------------------------------------

    def test_get_safety_all_severity_levels(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-014: Фильтрация по severity не применяется — все уровни возвращаются."""
        base_ts = get_timestamp_ms()
        
        severities = ["debug", "info", "notice", "warning", "error", "critical", "alert", "emergency"]
        payload = [
            create_event_payload(event_type="safety_event", severity=sev, message=f"Level: {sev}", timestamp=base_ts + idx)
            for idx, sev in enumerate(severities)
        ]
        
        post_event_logs(BACKEND_URL, api_headers, payload)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers, limit=20)
        assert resp.status_code == 200
        logs = resp.json()
        
        # Должны вернуться все 8 событий
        assert len(logs) == 8
        
        # Проверка, что все уровни присутствуют
        returned_severities = [log["severity"] for log in logs]
        for sev in severities:
            assert sev in returned_severities

    def test_get_safety_multiple_same_service_id(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-016: Множественные события от одного service_id."""
        base_ts = get_timestamp_ms()
        
        # Три события от одного сервиса с одинаковым service_id
        payload = [
            create_event_payload(event_type="safety_event", service="regulator", service_id=5, message=f"Msg {i}", timestamp=base_ts + i)
            for i in range(3)
        ]
        
        post_event_logs(BACKEND_URL, api_headers, payload)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 3
        # Все события должны быть от regulator с service_id=5
        assert all(log["service"] == "regulator" and log["service_id"] == 5 for log in logs)
        # И сообщения должны совпадать
        messages = {log["message"] for log in logs}
        assert messages == {"Msg 0", "Msg 1", "Msg 2"}

    def test_get_safety_same_timestamp_multiple_events(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-017: События с одинаковым timestamp."""
        timestamp = get_timestamp_ms()
        
        # Два события с идентичным timestamp
        payload = [
            create_event_payload(event_type="safety_event", service="GCS", message="First same-ts", timestamp=timestamp),
            create_event_payload(event_type="safety_event", service="aggregator", message="Second same-ts", timestamp=timestamp)
        ]
        
        post_event_logs(BACKEND_URL, api_headers, payload)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        
        # Оба события должны быть в ответе
        assert len(logs) == 2
        
        # Оба имеют одинаковый timestamp
        assert logs[0]["timestamp"] == logs[1]["timestamp"] == timestamp
        
        # Оба сообщения присутствуют (порядок не гарантирован при одинаковом timestamp)
        messages = {log["message"] for log in logs}
        assert messages == {"First same-ts", "Second same-ts"}

    def test_get_safety_timestamp_format_preserved(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-SAFETY-019: Проверка формата timestamp в ответе."""
        # Используем конкретное известное значение в миллисекундах
        fixed_timestamp = 1700000000123  # Пример epoch ms
        
        event = create_event_payload(event_type="safety_event", timestamp=fixed_timestamp)
        post_event_logs(BACKEND_URL, api_headers, [event])
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/safety", bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 1
        # Timestamp должен быть целым числом и точно совпадать
        assert isinstance(logs[0]["timestamp"], int)
        assert logs[0]["timestamp"] == fixed_timestamp