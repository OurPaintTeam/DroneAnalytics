"""Интеграционные тесты для GET /log/event."""
import requests
from typing import Dict

from .conftest import BACKEND_URL
from .utils import (
    wait_for_elastic_sync,
    get_timestamp_ms,
    create_event_payload,
    post_event_logs,
    get_paginated_logs,
)

# ============================================================================
# Тест-кейсы: базовая функциональность
# ============================================================================

class TestGetEventBasic:
    """Базовые тесты получения событий."""

    def test_empty_index_returns_empty_list(self, bearer_headers: Dict[str, str]):
        """TC_EVENT_001: Получение событий из пустого индекса."""
        wait_for_elastic_sync()
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_single_event_retrieval(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC_EVENT_002: Получение одного события."""
        ts = get_timestamp_ms()
        event = create_event_payload(ts, "GCS", 1, "Test message", "info")
        post_event_logs(BACKEND_URL, api_headers, [event])
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 1
        assert logs[0]["message"] == "Test message"
        assert logs[0]["service"] == "GCS"
        assert logs[0]["service_id"] == 1
        assert logs[0]["timestamp"] == ts
        assert logs[0]["severity"] == "info"

    def test_response_structure_required_fields(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC_EVENT_014: Структура ответа — все обязательные поля."""
        ts = get_timestamp_ms()
        event = create_event_payload(ts, "aggregator", 42, "Required fields test")
        post_event_logs(BACKEND_URL, api_headers, [event])
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers)
        assert resp.status_code == 200
        log = resp.json()[0]
        
        # Проверка обязательных полей
        assert "timestamp" in log
        assert "service" in log
        assert "service_id" in log
        assert "message" in log
        # severity опционально, но если есть — должно быть валидным
        if "severity" in log and log["severity"] is not None:
            assert log["severity"] in [
                "debug", "info", "notice", "warning", 
                "error", "critical", "alert", "emergency"
            ]

    def test_response_data_types(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC_EVENT_015: Типы данных в ответе."""
        ts = get_timestamp_ms()
        event = create_event_payload(ts, "dronePort", 100, "Type test", "warning")
        post_event_logs(BACKEND_URL, api_headers, [event])
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers)
        log = resp.json()[0]
        
        assert isinstance(log["timestamp"], int)
        assert isinstance(log["service_id"], int)
        assert isinstance(log["service"], str)
        assert isinstance(log["message"], str)
        assert log["severity"] == "warning"


# ============================================================================
# Тест-кейсы: сортировка
# ============================================================================

class TestGetEventSorting:
    """Тесты сортировки событий по времени."""

    def test_events_sorted_desc_by_timestamp(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC_EVENT_003: Сортировка по убыванию времени."""
        base_ts = get_timestamp_ms()
        # Создаём события в случайном порядке по времени
        events = [
            create_event_payload(base_ts + 3000, "GCS", 1, "Third"),
            create_event_payload(base_ts + 1000, "aggregator", 2, "First"),
            create_event_payload(base_ts + 2000, "dronePort", 3, "Second"),
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers, limit=10)
        logs = resp.json()
        timestamps = [log["timestamp"] for log in logs]
        
        assert timestamps == sorted(timestamps, reverse=True)
        assert logs[0]["message"] == "Third"
        assert logs[1]["message"] == "Second"
        assert logs[2]["message"] == "First"


# ============================================================================
# Тест-кейсы: пагинация
# ============================================================================

class TestGetEventPagination:
    """Тесты пагинации событий."""

    def test_pagination_first_page(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC_EVENT_004: Пагинация — первая страница."""
        base_ts = get_timestamp_ms()
        events = [
            create_event_payload(base_ts + i*1000, "GCS", i+1, f"Event {i+1}")
            for i in range(25)
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers, limit=10, page=1)
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 10
        # Первые 10 самых новых
        assert logs[0]["message"] == "Event 25"
        assert logs[9]["message"] == "Event 16"

    def test_pagination_second_page(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC_EVENT_005: Пагинация — вторая страница."""
        base_ts = get_timestamp_ms()
        events = [
            create_event_payload(base_ts + i*1000, "GCS", i+1, f"Event {i+1}")
            for i in range(25)
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers, limit=10, page=2)
        logs = resp.json()
        assert len(logs) == 10
        # События 11-20 по новизне
        assert logs[0]["message"] == "Event 15"
        assert logs[9]["message"] == "Event 6"

    def test_pagination_last_incomplete_page(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC_EVENT_006: Пагинация — последняя неполная страница."""
        base_ts = get_timestamp_ms()
        events = [
            create_event_payload(base_ts + i*1000, "GCS", i+1, f"Event {i+1}")
            for i in range(25)
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers, limit=10, page=3)
        logs = resp.json()
        assert len(logs) == 5
        assert logs[0]["message"] == "Event 5"
        assert logs[4]["message"] == "Event 1"

    def test_pagination_beyond_data(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC_EVENT_007: Пагинация — страница за пределами данных."""
        base_ts = get_timestamp_ms()
        events = [
            create_event_payload(base_ts + i*1000, "GCS", i+1, f"Event {i+1}")
            for i in range(5)
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers, limit=10, page=10)
        assert resp.status_code == 200
        assert resp.json() == []
# ============================================================================
# Тест-кейсы: фильтрация infopanel
# ============================================================================

class TestGetEventFiltering:
    """Тесты фильтрации событий."""

    def test_exclude_infopanel_service(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC_EVENT_008: Исключение логов аудита (infopanel)."""
        base_ts = get_timestamp_ms()
        events = [
            create_event_payload(base_ts + 3000, "infopanel", 1, "Audit log 1"),
            create_event_payload(base_ts + 2000, "GCS", 2, "User log 1"),
            create_event_payload(base_ts + 1000, "infopanel", 1, "Audit log 2"),
            create_event_payload(base_ts + 4000, "aggregator", 3, "User log 2"),
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers, limit=10)
        logs = resp.json()
        
        # Должны быть только 2 пользовательских лога
        assert len(logs) == 2
        services = [log["service"] for log in logs]
        assert "infopanel" not in services
        assert set(services) == {"GCS", "aggregator"}
        # Проверка сортировки
        assert logs[0]["message"] == "User log 2"  # самый новый
        assert logs[1]["message"] == "User log 1"

    def test_safety_events_not_in_event_endpoint(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC_EVENT_023: safety_event не попадают в /log/event."""
        base_ts = get_timestamp_ms()
        events = [
            create_event_payload(base_ts + 2000, "operator", 1, "Regular event", "info", "event"),
            create_event_payload(base_ts + 1000, "insurance", 2, "Safety event", "critical", "safety_event"),
            create_event_payload(base_ts + 3000, "regulator", 3, "Another regular", "warning", "event"),
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers, limit=10)
        logs = resp.json()
        
        # Должны быть только 2 обычных события
        assert len(logs) == 2
        messages = [log["message"] for log in logs]
        assert "Safety event" not in messages
        assert "Regular event" in messages
        assert "Another regular" in messages


# ============================================================================
# Тест-кейсы: валидация параметров
# ============================================================================

class TestGetEventValidation:
    """Тесты валидации входных параметров."""

    def test_limit_below_minimum(self, bearer_headers: Dict[str, str]):
        """TC_EVENT_011: Валидация limit — значение меньше минимума."""
        resp = requests.get(
            f"{BACKEND_URL}/log/event",
            params={"limit": 0},
            headers=bearer_headers,
            timeout=5
        )
        assert resp.status_code == 400
        assert "code" in resp.json()
        assert resp.json()["code"] == 400

    def test_limit_above_maximum(self, bearer_headers: Dict[str, str]):
        """TC_EVENT_012: Валидация limit — значение больше максимума."""
        resp = requests.get(
            f"{BACKEND_URL}/log/event",
            params={"limit": 101},
            headers=bearer_headers,
            timeout=5
        )
        assert resp.status_code == 400
        assert "code" in resp.json()

    def test_page_below_minimum(self, bearer_headers: Dict[str, str]):
        """TC_EVENT_013: Валидация page — некорректное значение."""
        resp = requests.get(
            f"{BACKEND_URL}/log/event",
            params={"page": 0},
            headers=bearer_headers,
            timeout=5
        )
        assert resp.status_code == 400
        assert "code" in resp.json()

    def test_limit_min_value_works(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC_EVENT_009: Фильтрация по limit — минимальное значение."""
        base_ts = get_timestamp_ms()
        events = [
            create_event_payload(base_ts + i*1000, "GCS", i+1, f"Event {i+1}")
            for i in range(5)
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers, limit=1, page=1)
        logs = resp.json()
        assert len(logs) == 1
        assert logs[0]["message"] == "Event 5"  # самый новый

    def test_limit_max_value_works(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC_EVENT_010: Фильтрация по limit — максимальное значение."""
        base_ts = get_timestamp_ms()
        events = [
            create_event_payload(base_ts + i*1000, "GCS", i+1, f"Event {i+1:03d}")
            for i in range(150)  # больше 100
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers, limit=100, page=1)
        logs = resp.json()
        assert len(logs) == 100  # не больше 100, даже если в базе больше
        assert logs[0]["message"] == "Event 150"


# ============================================================================
# Тест-кейсы: данные и граничные значения
# ============================================================================

class TestGetEventData:
    """Тесты работы с различными типами данных."""

    def test_different_severity_values(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC_EVENT_016: События с разными значениями severity."""
        base_ts = get_timestamp_ms()
        severities = ["debug", "info", "notice", "warning", "error", "critical", "alert", "emergency"]
        events = [
            create_event_payload(base_ts + i*1000, "GCS", i+1, f"Severity {sev}", sev)
            for i, sev in enumerate(severities)
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers, limit=20)
        logs = resp.json()
        
        returned_severities = [log.get("severity") for log in logs]
        for sev in severities:
            assert sev in returned_severities

    def test_filter_by_service_service_id_severity_and_message(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC_EVENT_017: Комбинированная фильтрация query-параметрами."""
        ts = get_timestamp_ms()
        events = [
            create_event_payload(ts + 1, "GCS", 10, "target payload", "warning"),
            create_event_payload(ts + 2, "GCS", 10, "non target", "info"),
            create_event_payload(ts + 3, "aggregator", 10, "target payload", "warning"),
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/event",
            headers=bearer_headers,
            params={
                "service": "GCS",
                "service_id": 10,
                "severity": "warning",
                "message": "target",
                "limit": 10,
                "page": 1,
            },
            timeout=5,
        )
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 1
        assert logs[0]["service"] == "GCS"
        assert logs[0]["service_id"] == 10
        assert logs[0]["severity"] == "warning"
        assert "target" in logs[0]["message"]

    def test_different_services_returned(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC_EVENT_017: События от разных сервисов."""
        base_ts = get_timestamp_ms()
        services = ["delivery", "queen", "inspector", "agriculture", "GCS", 
                   "aggregator", "insurance", "regulator", "dronePort"]
        events = [
            create_event_payload(base_ts + i*1000, svc, i+1, f"From {svc}")
            for i, svc in enumerate(services)
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers, limit=20)
        logs = resp.json()
        
        returned_services = {log["service"] for log in logs}
        assert returned_services == set(services)

    def test_long_message_preserved(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC_EVENT_018: Длинные сообщения в логах."""
        base_ts = get_timestamp_ms()
        long_message = "x" * 1000  # максимум по валидации
        event = create_event_payload(base_ts, "GCS", 1, long_message, "info")
        post_event_logs(BACKEND_URL, api_headers, [event])
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers)
        log = resp.json()[0]
        
        assert log["message"] == long_message
        assert len(log["message"]) == 1000

    def test_boundary_service_id_values(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC_EVENT_019: Граничные значения service_id."""
        base_ts = get_timestamp_ms()
        events = [
            create_event_payload(base_ts + 1000, "GCS", 1, "Min service_id"),
            create_event_payload(base_ts, "aggregator", 32766, "Max short service_id"),  # max signed short
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers, limit=10)
        logs = resp.json()
        
        service_ids = {log["service_id"] for log in logs}
        assert 1 in service_ids
        assert 32766 in service_ids

    def test_optional_severity_field_handling(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC_EVENT_021: Отсутствие поля severity в некоторых записях."""
        base_ts = get_timestamp_ms()
        events = [
            create_event_payload(base_ts + 2000, "GCS", 1, "With severity", "info"),
            create_event_payload(base_ts + 1000, "aggregator", 2, "Without severity", None),
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers, limit=10)
        logs = resp.json()
        
        assert len(logs) == 2
        # Одно с severity, одно без (None или поле отсутствует)
        severities = [log.get("severity") for log in logs]
        assert "info" in severities
        assert severities.count(None) >= 1  # хотя бы одно без severity

    def test_rapid_sequential_reads(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC_EVENT_022: Быстрое последовательное чтение."""
        base_ts = get_timestamp_ms()
        events = [
            create_event_payload(base_ts + i*1000, "GCS", i+1, f"Event {i+1}")
            for i in range(20)
        ]
        post_event_logs(BACKEND_URL, api_headers, events)
        wait_for_elastic_sync()
        
        responses = []
        for page in range(1, 6):
            resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers, limit=5, page=page)
            responses.append(resp)
        
        # Все запросы успешны
        assert all(r.status_code == 200 for r in responses)
        
        # Данные согласованы: всего 20 событий, разбитых на 4 страницы по 5
        all_logs = []
        for resp in responses:
            all_logs.extend(resp.json())
        assert len(all_logs) == 20
        
        # Нет дубликатов
        timestamps = [log["timestamp"] for log in all_logs]
        assert len(timestamps) == len(set(timestamps))


# ============================================================================
# Тест-кейсы: интеграция с другими индексами
# ============================================================================

class TestGetEventIntegration:
    """Интеграционные тесты с другими частями системы."""

    def test_event_endpoint_does_not_return_telemetry(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Убеждаемся, что /log/event не возвращает данные из индекса telemetry."""
        base_ts = get_timestamp_ms()
        
        # Записываем телеметрию
        telemetry = [{
            "apiVersion": "1.0.0",
            "timestamp": base_ts,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]
        requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=telemetry,
            headers=api_headers,
            timeout=10
        )
        
        # Записываем событие
        event = create_event_payload(base_ts + 1000, "GCS", 1, "Event message")
        post_event_logs(BACKEND_URL, api_headers, [event])
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers)
        logs = resp.json()
        
        # Должно быть только событие, без полей телеметрии
        assert len(logs) == 1
        assert "drone" not in logs[0]
        assert "latitude" not in logs[0]
        assert logs[0]["message"] == "Event message"

    def test_event_endpoint_does_not_return_basic_logs(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Убеждаемся, что /log/event не возвращает данные из индекса basic."""
        base_ts = get_timestamp_ms()
        
        # Записываем basic лог
        basic = [{"timestamp": base_ts, "message": "Basic log"}]
        requests.post(
            f"{BACKEND_URL}/log/basic",
            json=basic,
            headers=api_headers,
            timeout=10
        )
        
        # Записываем событие
        event = create_event_payload(base_ts + 1000, "GCS", 1, "Event message")
        post_event_logs(BACKEND_URL, api_headers, [event])
        wait_for_elastic_sync()
        
        resp = get_paginated_logs(BACKEND_URL, "/log/event", bearer_headers)
        logs = resp.json()
        
        assert len(logs) == 1
        assert logs[0]["service"] == "GCS"  # у basic логов нет поля service
        assert "Basic log" not in [log["message"] for log in logs]