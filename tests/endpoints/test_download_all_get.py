"""Тесты для GET /log/download/all — экспорт всех логов в CSV."""
from typing import List, Dict, Any, Optional

import pytest
import requests

from .conftest import BACKEND_URL
from .utils import (
    wait_for_elastic_sync,
    get_csv_headers,
    get_timestamp_ms,
    parse_csv_from_response,
    insert_safety_log,
)

# =============================================================================
# Константы
# =============================================================================

AUDIT_SERVICE = "infopanel"  # AUDIT_SERVICE из backend/app/audit.py

EXPECTED_HEADERS = [
    "index", "timestamp", "message", "drone", "drone_id", "battery", "pitch", "roll", 
    "course", "latitude", "longitude", "service", "service_id", "severity"
]


# =============================================================================
# Вспомогательные функции для тестов
# =============================================================================


def filter_out_audit_logs(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Фильтрует аудит-логи из результатов.
    Аудит-логи имеют service="infopanel" и index="event" или index="safety".
    """
    return [
        row for row in rows 
        if not (row.get("service") == AUDIT_SERVICE and row.get("index") in ("event", "safety"))
    ]


def insert_basic_log(api_headers: Dict[str, str], message: str, timestamp: Optional[int] = None) -> Dict[str, Any]:
    """Вставляет запись в индекс basic."""
    if timestamp is None:
        timestamp = get_timestamp_ms()
    payload = [{"timestamp": timestamp, "message": message}]
    resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=api_headers, timeout=10)
    assert resp.status_code == 200
    return {"index": "basic", "timestamp": timestamp, "message": message}


def insert_telemetry_log(api_headers: Dict[str, str], drone: str = "delivery", drone_id: int = 1, 
                         timestamp: Optional[int] = None) -> Dict[str, Any]:
    """Вставляет запись в индекс telemetry."""
    if timestamp is None:
        timestamp = get_timestamp_ms()
    payload = [{
        "apiVersion": "1.0.0",
        "timestamp": timestamp,
        "drone": drone,
        "drone_id": drone_id,
        "latitude": 55.0,
        "longitude": 37.0
    }]
    resp = requests.post(f"{BACKEND_URL}/log/telemetry", json=payload, headers=api_headers, timeout=10)
    assert resp.status_code == 200
    return {"index": "telemetry", "timestamp": timestamp, "drone": drone, "drone_id": drone_id}


def insert_event_log(api_headers: Dict[str, str], service: str = "GCS", severity: str = "info",
                     message: str = "Test event", timestamp: Optional[int] = None) -> Dict[str, Any]:
    """Вставляет запись в индекс event."""
    if timestamp is None:
        timestamp = get_timestamp_ms()
    payload = [{
        "apiVersion": "1.0.0",
        "timestamp": timestamp,
        "event_type": "event",
        "service": service,
        "service_id": 1,
        "severity": severity,
        "message": message
    }]
    resp = requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
    assert resp.status_code == 200
    return {"index": "event", "timestamp": timestamp, "service": service, "severity": severity, "message": message}


# =============================================================================
# Базовые сценарии
# =============================================================================

class TestDownloadAllBasic:
    """Базовые тесты для /log/download/all."""

    def test_empty_database(self, bearer_headers: Dict[str, str]):
        """Тест #1: Пустая база данных."""
        wait_for_elastic_sync()
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10, stream=True)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/octet-stream"
        
        rows = parse_csv_from_response(resp)
        # Могут быть аудит-логи от предыдущих запросов, фильтруем их
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 0
        
        headers = get_csv_headers(resp)
        assert headers == EXPECTED_HEADERS

    def test_only_basic_logs(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #2: Только basic логи."""
        insert_basic_log(api_headers, "Basic message 1")
        insert_basic_log(api_headers, "Basic message 2")
        insert_basic_log(api_headers, "Basic message 3")
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 3
        for row in filtered_rows:
            assert row["index"] == "basic"
            assert row["message"].startswith("Basic message")
            assert row["drone"] == ""
            assert row["service"] == ""

    def test_only_telemetry_logs(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #3: Только telemetry логи."""
        insert_telemetry_log(api_headers, drone="delivery", drone_id=1)
        insert_telemetry_log(api_headers, drone="inspector", drone_id=2)
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 2
        for row in filtered_rows:
            assert row["index"] == "telemetry"
            assert row["drone"] in ["delivery", "inspector"]
            assert row["message"] == ""

    def test_only_event_logs(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #4: Только event логи."""
        insert_event_log(api_headers, service="GCS", severity="info")
        insert_event_log(api_headers, service="aggregator", severity="warning")
        insert_event_log(api_headers, service="operator", severity="error")
        insert_event_log(api_headers, service="registry", severity="debug")
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 4
        for row in filtered_rows:
            assert row["index"] == "event"
            assert row["service"] in ["GCS", "aggregator", "operator", "registry"]

    def test_only_safety_logs(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #5: Только safety логи."""
        insert_safety_log(BACKEND_URL, api_headers, service="dronePort", severity="warning")
        insert_safety_log(BACKEND_URL, api_headers, service="insurance", severity="critical")
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 2
        for row in filtered_rows:
            assert row["index"] == "safety"
            assert row["service"] in ["dronePort", "insurance"]

    def test_mixed_all_indices(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #6: Смешанные данные из всех индексов."""
        insert_basic_log(api_headers, "Basic 1")
        insert_basic_log(api_headers, "Basic 2")
        insert_telemetry_log(api_headers, drone="delivery", drone_id=1)
        insert_telemetry_log(api_headers, drone="agriculture", drone_id=3)
        insert_event_log(api_headers, service="GCS", severity="info")
        insert_event_log(api_headers, service="operator", severity="error")
        insert_safety_log(BACKEND_URL, api_headers, service="dronePort", severity="warning")
        insert_safety_log(BACKEND_URL, api_headers, service="regulator", severity="alert")
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 8
        
        indices = {row["index"] for row in filtered_rows}
        assert indices == {"basic", "telemetry", "event", "safety"}


# =============================================================================
# Фильтрация по времени
# =============================================================================

class TestDownloadAllTimeFilter:
    """Тесты фильтрации по timestamp."""

    def test_filter_from_ts_only(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #7: Фильтр from_ts только."""
        base_ts = get_timestamp_ms()
        # Создаём записи с разными timestamp
        for i in range(10):
            insert_basic_log(api_headers, f"Msg {i}", timestamp=base_ts + i * 1000)
        wait_for_elastic_sync()
        
        from_ts = base_ts + 5 * 1000  # Середина диапазона
        resp = requests.get(
            f"{BACKEND_URL}/log/download/all",
            params={"from_ts": from_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 5  # Записи с 5 до 9
        for row in filtered_rows:
            assert int(row["timestamp"]) >= from_ts

    def test_filter_to_ts_only(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #8: Фильтр to_ts только."""
        base_ts = get_timestamp_ms()
        for i in range(10):
            insert_basic_log(api_headers, f"Msg {i}", timestamp=base_ts + i * 1000)
        wait_for_elastic_sync()
        
        to_ts = base_ts + 5 * 1000
        resp = requests.get(
            f"{BACKEND_URL}/log/download/all",
            params={"to_ts": to_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 6  # Записи с 0 до 5 (inclusive)
        for row in filtered_rows:
            assert int(row["timestamp"]) <= to_ts

    def test_filter_from_and_to_ts(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #9: Фильтр from_ts + to_ts."""
        base_ts = get_timestamp_ms()
        for i in range(10):
            insert_basic_log(api_headers, f"Msg {i}", timestamp=base_ts + i * 1000)
        wait_for_elastic_sync()
        
        from_ts = base_ts + 2 * 1000
        to_ts = base_ts + 6 * 1000
        resp = requests.get(
            f"{BACKEND_URL}/log/download/all",
            params={"from_ts": from_ts, "to_ts": to_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 5  # Записи 2,3,4,5,6
        for row in filtered_rows:
            ts = int(row["timestamp"])
            assert from_ts <= ts <= to_ts

    def test_filter_boundary_from_ts_inclusive(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #10: Граница from_ts inclusive."""
        base_ts = get_timestamp_ms()
        insert_basic_log(api_headers, "At boundary", timestamp=base_ts)
        insert_basic_log(api_headers, "After boundary", timestamp=base_ts + 1000)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/all",
            params={"from_ts": base_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 2
        messages = {row["message"] for row in filtered_rows}
        assert "At boundary" in messages

    def test_filter_boundary_to_ts_inclusive(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #11: Граница to_ts inclusive."""
        base_ts = get_timestamp_ms()
        insert_basic_log(api_headers, "Before boundary", timestamp=base_ts - 1000)
        insert_basic_log(api_headers, "At boundary", timestamp=base_ts)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/all",
            params={"to_ts": base_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 2
        messages = {row["message"] for row in filtered_rows}
        assert "At boundary" in messages

    def test_filter_range_no_data(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #12: Диапазон без данных."""
        base_ts = 1000000000000
        test_message = "TEST_NO_MATCHES_here"
        insert_safety_log(BACKEND_URL, api_headers=api_headers, timestamp=base_ts, message=test_message)
        wait_for_elastic_sync()
        
        # Запрашиваем диапазон, где нет документов
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            params={"from_ts": base_ts + 10000, "to_ts": base_ts + 20000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        
        # Фильтруем только наши тестовые данные — их быть не должно в этом диапазоне
        test_rows = filter_out_audit_logs(rows)
        assert len(test_rows) == 0


# =============================================================================
# Формат CSV
# =============================================================================

class TestDownloadAllCSVFormat:
    """Тесты формата CSV."""

    def test_csv_headers_correct(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #13: Заголовки колонок."""
        insert_basic_log(api_headers, "Test")
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        assert resp.status_code == 200
        
        headers = get_csv_headers(resp)
        assert headers == EXPECTED_HEADERS
        assert len(headers) == 14

    def test_utf8_encoding_cyrillic(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #14: Кодировка UTF-8 (кириллица)."""
        insert_basic_log(api_headers, "Тест сообщение с кириллицей")
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        assert resp.status_code == 200
        
        content = resp.content.decode('utf-8')
        assert "Тест сообщение с кириллицей" in content

    def test_special_characters_escaping(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #15: Специальные символы в message."""
        special_msg = 'Message with "quotes", commas, and\nnewlines'
        insert_basic_log(api_headers, special_msg)
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 1
        assert filtered_rows[0]["message"] == special_msg

    def test_null_values_as_empty_strings(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #16: NULL значения полей."""
        insert_telemetry_log(api_headers, drone="delivery", drone_id=1)
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 1
        # Поля, которые не заполняются для telemetry
        assert filtered_rows[0]["service"] == ""
        assert filtered_rows[0]["severity"] == ""
        assert filtered_rows[0]["message"] == ""

    def test_numeric_values_preserved(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #17: Числовые значения."""
        ts = get_timestamp_ms()
        insert_telemetry_log(api_headers, drone="agriculture", drone_id=42, timestamp=ts)
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 1
        assert filtered_rows[0]["drone_id"] == "42"
        assert filtered_rows[0]["timestamp"] == str(ts)


# =============================================================================
# Имя файла (Content-Disposition)
# =============================================================================

class TestDownloadAllFilename:
    """Тесты имени файла в Content-Disposition."""

    def test_filename_no_filters(self, bearer_headers: Dict[str, str]):
        """Тест #18: Имя без фильтров."""
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        assert resp.status_code == 200
        
        content_disp = resp.headers.get("Content-Disposition", "")
        assert 'filename="all_logs_all.csv"' in content_disp

    def test_filename_with_from_ts(self, bearer_headers: Dict[str, str]):
        """Тест #19: Имя с from_ts."""
        from_ts = 1700000000000
        resp = requests.get(
            f"{BACKEND_URL}/log/download/all",
            params={"from_ts": from_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        content_disp = resp.headers.get("Content-Disposition", "")
        assert f'filename="all_logs_{from_ts}_all.csv"' in content_disp

    def test_filename_with_to_ts(self, bearer_headers: Dict[str, str]):
        """Тест #20: Имя с to_ts."""
        to_ts = 1700000500000
        resp = requests.get(
            f"{BACKEND_URL}/log/download/all",
            params={"to_ts": to_ts},
            headers=bearer_headers,
            timeout=10,
            stream=True
        )
        assert resp.status_code == 200
        
        content_disp = resp.headers.get("Content-Disposition", "")
        assert f'filename="all_logs_all_{to_ts}.csv"' in content_disp

    def test_filename_with_both_filters(self, bearer_headers: Dict[str, str]):
        """Тест #21: Имя с обоими фильтрами."""
        from_ts = 1700000000000
        to_ts = 1700000500000
        resp = requests.get(
            f"{BACKEND_URL}/log/download/all",
            params={"from_ts": from_ts, "to_ts": to_ts},
            headers=bearer_headers,
            timeout=10,
            stream=True
        )
        assert resp.status_code == 200
        
        content_disp = resp.headers.get("Content-Disposition", "")
        assert f'filename="all_logs_{from_ts}_{to_ts}.csv"' in content_disp


# =============================================================================
# Сортировка
# =============================================================================

class TestDownloadAllSorting:
    """Тесты сортировки результатов."""

    def test_sorting_timestamp_desc(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #22: Сортировка timestamp desc."""
        base_ts = 1000000000000
        # Вставляем в случайном порядке
        for ts_offset in [3000, 1000, 5000, 2000, 4000]:
            insert_basic_log(api_headers, f"Msg {ts_offset}", timestamp=base_ts + ts_offset)
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        timestamps = [int(row["timestamp"]) for row in filtered_rows]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_global_sorting_across_indices(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #23: Сортировка между индексами."""
        base_ts = 1000000000000
        # Создаём записи в разных индексах с пересекающимися timestamp
        insert_basic_log(api_headers, "Basic", timestamp=base_ts + 3000)
        insert_telemetry_log(api_headers, drone="delivery", timestamp=base_ts + 1000)
        insert_event_log(api_headers, service="GCS", timestamp=base_ts + 5000)
        insert_safety_log(BACKEND_URL, api_headers, service="dronePort", timestamp=base_ts + 2000)
        insert_basic_log(api_headers, "Basic2", timestamp=base_ts + 4000)
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        timestamps = [int(row["timestamp"]) for row in filtered_rows]
        assert timestamps == sorted(timestamps, reverse=True)
        assert len(filtered_rows) == 5


# =============================================================================
# Пагинация (Scroll)
# =============================================================================

class TestDownloadAllScroll:
    """Тесты scroll API для больших объёмов данных."""

    def test_large_dataset_over_1000(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #24: Большой объём данных (>1000 записей)."""
        # Вставляем 1500 записей
        for i in range(1500):
            insert_basic_log(api_headers, f"Msg {i}", timestamp=get_timestamp_ms() + i)
        wait_for_elastic_sync(3)  # Дольше ждём для большого объёма
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=60)
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 1500

    def test_exactly_batch_size(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #25: Ровно batch_size записей (1000)."""
        for i in range(1000):
            insert_basic_log(api_headers, f"Msg {i}", timestamp=get_timestamp_ms() + i)
        wait_for_elastic_sync(3)
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=60)
        assert resp.status_code == 200
        
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 1000


# =============================================================================
# Валидация данных из разных индексов
# =============================================================================

class TestDownloadAllIndexValidation:
    """Тесты корректности данных для каждого типа индекса."""

    def test_basic_index_fields(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #26: Поле index для basic."""
        ts = get_timestamp_ms()
        insert_basic_log(api_headers, "Unique basic message", timestamp=ts)
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        
        basic_rows = [r for r in filtered_rows if r["index"] == "basic" and r["message"] == "Unique basic message"]
        assert len(basic_rows) == 1
        assert basic_rows[0]["timestamp"] == str(ts)
        assert basic_rows[0]["drone"] == ""
        assert basic_rows[0]["service"] == ""

    def test_telemetry_index_fields(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #27: Поле index для telemetry."""
        ts = get_timestamp_ms()
        insert_telemetry_log(api_headers, drone="delivery", drone_id=1, timestamp=ts)
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        
        telemetry_rows = [r for r in filtered_rows if r["index"] == "telemetry" and r["drone"] == "delivery"]
        assert len(telemetry_rows) == 1
        assert telemetry_rows[0]["drone_id"] == "1"
        assert telemetry_rows[0]["service"] == ""

    def test_event_index_fields(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #28: Поле index для event."""
        ts = get_timestamp_ms()
        insert_event_log(api_headers, service="GCS", severity="info", timestamp=ts)
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        
        event_rows = [r for r in filtered_rows if r["index"] == "event" and r["service"] == "GCS"]
        assert len(event_rows) == 1
        assert event_rows[0]["severity"] == "info"

    def test_safety_index_fields(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #29: Поле index для safety."""
        ts = get_timestamp_ms()
        insert_safety_log(BACKEND_URL, api_headers, service="dronePort", severity="warning", timestamp=ts)
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        
        safety_rows = [r for r in filtered_rows if r["index"] == "safety" and r["service"] == "dronePort"]
        assert len(safety_rows) == 1
        assert safety_rows[0]["severity"] == "warning"

    def test_mixed_mapping_validation(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """Тест #30: Смешанные данные — проверка mapping."""
        ts = get_timestamp_ms()
        insert_basic_log(api_headers, "Basic", timestamp=ts)
        insert_telemetry_log(api_headers, drone="delivery", drone_id=1, timestamp=ts + 1)
        insert_event_log(api_headers, service="GCS", severity="info", timestamp=ts + 2)
        insert_safety_log(BACKEND_URL, api_headers, service="dronePort", severity="warning", timestamp=ts + 3)
        wait_for_elastic_sync()
        
        resp = requests.get(f"{BACKEND_URL}/log/download/all", headers=bearer_headers, timeout=10)
        rows = parse_csv_from_response(resp)
        filtered_rows = filter_out_audit_logs(rows)
        assert len(filtered_rows) == 4
        
        # Проверяем каждую строку
        for row in filtered_rows:
            if row["index"] == "basic":
                assert row["message"] == "Basic"
                assert row["drone"] == ""
            elif row["index"] == "telemetry":
                assert row["drone"] == "delivery"
                assert row["drone_id"] == "1"
                assert row["message"] == ""
            elif row["index"] == "event":
                assert row["service"] == "GCS"
                assert row["severity"] == "info"
            elif row["index"] == "safety":
                assert row["service"] == "dronePort"
                assert row["severity"] == "warning"