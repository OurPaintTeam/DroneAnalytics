"""Тесты для GET /log/download/event эндпоинта (CSV выгрузка).

ВАЖНО: При каждом POST /log/event бэкенд вызывает audit_event(),
который пишет служебную запись в индекс 'event'. Поэтому количество
записей в выгрузке = N тестовых + M аудит-логов.

Для надёжности тесты используют уникальные префиксы сообщений и
проверяют наличие конкретных данных, а не точное общее количество.
"""
import uuid
from typing import Dict, Any, List, Optional

import pytest
import requests

from .conftest import BACKEND_URL
from .utils import wait_for_elastic_sync, get_timestamp_ms, get_csv_headers, parse_csv_from_response

def filter_rows_by_prefix(rows: List[Dict[str, str]], prefix: str, field: str = "message") -> List[Dict[str, str]]:
    """Фильтрует строки CSV по префиксу в указанном поле."""
    return [row for row in rows if row.get(field, "").startswith(prefix)]


def generate_test_prefix() -> str:
    """Генерирует уникальный префикс для тестовых данных."""
    return f"TEST_{uuid.uuid4().hex[:8]}"


class TestDownloadEventBasic:
    """Базовые тесты для GET /log/download/event."""

    def test_download_event_empty_index(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-01: Выгрузка индекса без тестовых данных.
        
        Примечание: аудит-логи могут присутствовать от других тестов,
        поэтому проверяем только заголовки, а не количество строк.
        """
        wait_for_elastic_sync()
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/octet-stream"
        assert 'filename="event_logs_all.csv"' in resp.headers["content-disposition"]
        
        # Проверяем заголовки
        headers = get_csv_headers(resp)
        assert headers == ["timestamp", "service", "service_id", "severity", "message"]

    def test_download_event_all_data(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-02: Выгрузка всех данных без фильтров."""
        test_prefix = generate_test_prefix()
        base_ts = get_timestamp_ms()
        
        # Записываем 3 события с уникальным префиксом
        payload = [
            {
                "apiVersion": "1.0.0",
                "timestamp": base_ts,
                "service": "GCS",
                "service_id": 1,
                "severity": "info",
                "message": f"{test_prefix} Event 1"
            },
            {
                "apiVersion": "1.0.0",
                "timestamp": base_ts + 1000,
                "service": "operator",
                "service_id": 2,
                "severity": "warning",
                "message": f"{test_prefix} Event 2"
            },
            {
                "apiVersion": "1.0.0",
                "timestamp": base_ts + 2000,
                "service": "aggregator",
                "service_id": 3,
                "severity": "error",
                "message": f"{test_prefix} Event 3"
            }
        ]
        post_resp = requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        assert post_resp.status_code == 200
        
        wait_for_elastic_sync()
        
        # Скачиваем CSV
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert 'filename="event_logs_all.csv"' in resp.headers["content-disposition"]
        
        all_rows = parse_csv_from_response(resp)
        
        # Фильтруем только наши тестовые записи (исключаем аудит-логи)
        test_rows = filter_rows_by_prefix(all_rows, test_prefix)
        
        # Проверяем, что все 3 тестовые записи на месте
        assert len(test_rows) == 3
        
        # Проверяем сортировку по timestamp desc (новые первыми)
        timestamps = [int(row["timestamp"]) for row in test_rows]
        assert timestamps == sorted(timestamps, reverse=True)
        
        # Проверяем данные
        assert test_rows[0]["service"] == "aggregator"  # Самый новый
        assert test_rows[1]["service"] == "operator"
        assert test_rows[2]["service"] == "GCS"  # Самый старый

    def test_download_event_filename_no_filters(self, bearer_headers: Dict[str, str]):
        """TC-15, TC-16: Проверка имени файла без фильтров."""
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert 'filename="event_logs_all.csv"' in resp.headers["content-disposition"]


class TestDownloadEventTimestampFilters:
    """Тесты фильтрации по времени для GET /log/download/event."""

    def test_download_event_filter_full_range(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-03: Фильтрация по полному диапазону (from_ts + to_ts)."""
        test_prefix = generate_test_prefix()
        base_ts = get_timestamp_ms()
        
        # Записываем события с известными timestamp
        test_timestamps = [base_ts + 100, base_ts + 200, base_ts + 300, base_ts + 400, base_ts + 500]
        payload = []
        for ts in test_timestamps:
            payload.append({
                "apiVersion": "1.0.0",
                "timestamp": ts,
                "service": "GCS",
                "service_id": 1,
                "severity": "info",
                "message": f"{test_prefix} Event {ts}"
            })
        
        post_resp = requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        assert post_resp.status_code == 200
        wait_for_elastic_sync()
        
        # Запрашиваем диапазон [base_ts + 200, base_ts + 400]
        from_ts = base_ts + 200
        to_ts = base_ts + 400
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            params={"from_ts": from_ts, "to_ts": to_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert f'filename="event_logs_{from_ts}_{to_ts}.csv"' in resp.headers["content-disposition"]
        
        all_rows = parse_csv_from_response(resp)
        # Фильтруем только наши тестовые записи
        test_rows = filter_rows_by_prefix(all_rows, test_prefix)
        
        # Должны быть события 200, 300, 400 (границы включительно)
        assert len(test_rows) == 3
        timestamps = [int(row["timestamp"]) for row in test_rows]
        assert all(from_ts <= ts <= to_ts for ts in timestamps)

    def test_download_event_filter_from_only(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-04: Фильтрация только по from_ts."""
        test_prefix = generate_test_prefix()
        base_ts = get_timestamp_ms()
        
        test_timestamps = [base_ts + 100, base_ts + 200, base_ts + 300]
        payload = []
        for ts in test_timestamps:
            payload.append({
                "apiVersion": "1.0.0",
                "timestamp": ts,
                "service": "GCS",
                "service_id": 1,
                "severity": "info",
                "message": f"{test_prefix} Event {ts}"
            })
        
        requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        wait_for_elastic_sync()
        
        from_ts = base_ts + 200
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            params={"from_ts": from_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert f'filename="event_logs_{from_ts}_all.csv"' in resp.headers["content-disposition"]
        
        all_rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_prefix(all_rows, test_prefix)
        
        # Должны быть события >= from_ts (200, 300)
        assert len(test_rows) == 2
        timestamps = [int(row["timestamp"]) for row in test_rows]
        assert all(ts >= from_ts for ts in timestamps)

    def test_download_event_filter_to_only(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-05: Фильтрация только по to_ts."""
        test_prefix = generate_test_prefix()
        base_ts = get_timestamp_ms()
        
        test_timestamps = [base_ts + 100, base_ts + 200, base_ts + 300]
        payload = []
        for ts in test_timestamps:
            payload.append({
                "apiVersion": "1.0.0",
                "timestamp": ts,
                "service": "GCS",
                "service_id": 1,
                "severity": "info",
                "message": f"{test_prefix} Event {ts}"
            })
        
        requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        wait_for_elastic_sync()
        
        to_ts = base_ts + 200
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            params={"to_ts": to_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert f'filename="event_logs_all_{to_ts}.csv"' in resp.headers["content-disposition"]
        
        all_rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_prefix(all_rows, test_prefix)
        
        # Должны быть события <= to_ts (100, 200)
        assert len(test_rows) == 2
        timestamps = [int(row["timestamp"]) for row in test_rows]
        assert all(ts <= to_ts for ts in timestamps)

    def test_download_event_filter_no_matches(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-06: Диапазон без совпадений."""
        test_prefix = generate_test_prefix()
        base_ts = get_timestamp_ms()
        
        # Записываем события с timestamp: 100, 500
        payload = [
            {
                "apiVersion": "1.0.0",
                "timestamp": base_ts + 100,
                "service": "GCS",
                "service_id": 1,
                "severity": "info",
                "message": f"{test_prefix} Event 100"
            },
            {
                "apiVersion": "1.0.0",
                "timestamp": base_ts + 500,
                "service": "GCS",
                "service_id": 1,
                "severity": "info",
                "message": f"{test_prefix} Event 500"
            }
        ]
        requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        wait_for_elastic_sync()
        
        # Запрашиваем диапазон [200, 300] - нет совпадений
        from_ts = base_ts + 200
        to_ts = base_ts + 300
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            params={"from_ts": from_ts, "to_ts": to_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert f'filename="event_logs_{from_ts}_{to_ts}.csv"' in resp.headers["content-disposition"]
        
        all_rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_prefix(all_rows, test_prefix)
        
        # Наши тестовые записи не должны попасть в диапазон
        assert len(test_rows) == 0


class TestDownloadEventCSVFormat:
    """Тесты формата CSV для GET /log/download/event."""

    def test_download_event_header_order(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-07: Проверка порядка колонок в заголовке."""
        test_prefix = generate_test_prefix()
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "service": "GCS",
            "service_id": 1,
            "severity": "info",
            "message": f"{test_prefix} Test"
        }]
        requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        headers = get_csv_headers(resp)
        assert headers == ["timestamp", "service", "service_id", "severity", "message"]

    def test_download_event_null_severity(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-08: Обработка null значений в поле severity."""
        test_prefix = generate_test_prefix()
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "service": "GCS",
            "service_id": 1,
            "severity": None,
            "message": f"{test_prefix} Test message"
        }]
        requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        all_rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_prefix(all_rows, test_prefix)
        
        assert len(test_rows) == 1
        assert test_rows[0]["severity"] == ""
        assert test_rows[0]["message"] == f"{test_prefix} Test message"

    def test_download_event_commas_in_message(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-09: Экранирование запятых в сообщении."""
        test_prefix = generate_test_prefix()
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "service": "GCS",
            "service_id": 1,
            "severity": "error",
            "message": f"{test_prefix} Error, code: 500, retry"
        }]
        requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        all_rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_prefix(all_rows, test_prefix)
        
        assert len(test_rows) == 1
        assert test_rows[0]["message"] == f"{test_prefix} Error, code: 500, retry"
        assert len(test_rows[0]) == 5  # Проверяем, что всего 5 колонок

    def test_download_event_quotes_in_message(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-10: Экранирование двойных кавычек в сообщении."""
        test_prefix = generate_test_prefix()
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "service": "GCS",
            "service_id": 1,
            "severity": "info",
            "message": f'{test_prefix} Say "Hello"'
        }]
        requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        all_rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_prefix(all_rows, test_prefix)
        
        assert len(test_rows) == 1
        assert test_rows[0]["message"] == f'{test_prefix} Say "Hello"'

    def test_download_event_newlines_in_message(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-11: Экранирование переносов строк в сообщении."""
        test_prefix = generate_test_prefix()
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "service": "GCS",
            "service_id": 1,
            "severity": "warning",
            "message": f"{test_prefix} Line 1\nLine 2\nLine 3"
        }]
        requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        all_rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_prefix(all_rows, test_prefix)
        
        assert len(test_rows) == 1
        assert test_rows[0]["message"] == f"{test_prefix} Line 1\nLine 2\nLine 3"

    def test_download_event_utf8_cyrillic(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-12: Кодировка UTF-8 (кириллица)."""
        test_prefix = generate_test_prefix()
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "service": "GCS",
            "service_id": 1,
            "severity": "error",
            "message": f"{test_prefix} Ошибка запуска системы"
        }]
        requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        content = resp.content.decode("utf-8")
        assert "Ошибка запуска системы" in content
        
        all_rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_prefix(all_rows, test_prefix)
        
        assert len(test_rows) == 1
        assert test_rows[0]["message"] == f"{test_prefix} Ошибка запуска системы"

    def test_download_event_utf8_emoji(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-12: Кодировка UTF-8 (эмодзи)."""
        test_prefix = generate_test_prefix()
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "service": "GCS",
            "service_id": 1,
            "severity": "info",
            "message": f"{test_prefix} Drone launched 🚀 successfully ✅"
        }]
        requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        content = resp.content.decode("utf-8")
        assert "🚀" in content
        assert "✅" in content
        
        all_rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_prefix(all_rows, test_prefix)
        
        assert len(test_rows) == 1
        assert test_rows[0]["message"] == f"{test_prefix} Drone launched 🚀 successfully ✅"


class TestDownloadEventScroll:
    """Тесты Scroll API для больших объёмов данных."""

    def test_download_event_large_dataset(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-13: Выгрузка большого объёма данных (>1000 записей)."""
        test_prefix = generate_test_prefix()
        base_ts = get_timestamp_ms()
        
        # Записываем 1500 событий (больше batch_size=1000)
        total_records = 1500
        for i in range(0, total_records, 1000):
            payload = []
            for j in range(i, min(i + 1000, total_records)):
                payload.append({
                    "apiVersion": "1.0.0",
                    "timestamp": base_ts + j,
                    "service": "GCS",
                    "service_id": 1,
                    "severity": "info",
                    "message": f"{test_prefix} Event {j}"
                })
            post_resp = requests.post(f"{BACKEND_URL}/log/event", json=payload, headers=api_headers, timeout=10)
            assert post_resp.status_code == 200
        
        wait_for_elastic_sync(seconds=3)
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            headers=bearer_headers,
            timeout=30
        )
        assert resp.status_code == 200
        
        all_rows = parse_csv_from_response(resp)
        # Фильтруем только наши тестовые записи
        test_rows = filter_rows_by_prefix(all_rows, test_prefix)
        
        # Проверяем, что все тестовые записи на месте
        assert len(test_rows) == total_records
        
        # Проверяем сортировку (desc)
        timestamps = [int(row["timestamp"]) for row in test_rows]
        assert timestamps == sorted(timestamps, reverse=True)
        
        # Проверяем отсутствие дубликатов
        assert len(set(timestamps)) == total_records


class TestDownloadEventAuditLogs:
    """Тесты на наличие/отсутствие аудит-логов в выгрузке."""

    def test_download_event_includes_audit_service(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-14: Проверка, попадают ли логи сервиса 'infopanel' в выгрузку."""
        test_prefix = generate_test_prefix()
        base_ts = get_timestamp_ms()
        
        # Записываем событие от infopanel (внутренний аудит-сервис)
        payload_audit = [{
            "apiVersion": "1.0.0",
            "timestamp": base_ts,
            "service": "infopanel",
            "service_id": 1,
            "severity": "info",
            "message": f"{test_prefix} Internal audit event"
        }]
        requests.post(f"{BACKEND_URL}/log/event", json=payload_audit, headers=api_headers, timeout=10)
        
        # Записываем событие от другого сервиса
        payload_user = [{
            "apiVersion": "1.0.0",
            "timestamp": base_ts + 1000,
            "service": "GCS",
            "service_id": 1,
            "severity": "info",
            "message": f"{test_prefix} User event"
        }]
        requests.post(f"{BACKEND_URL}/log/event", json=payload_user, headers=api_headers, timeout=10)
        
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        all_rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_prefix(all_rows, test_prefix)
        
        # В download_event_csv нет фильтра exclude_service
        services = [row["service"] for row in test_rows]
        assert "infopanel" in services
        assert "GCS" in services
        assert len(test_rows) == 2


class TestDownloadEventFilename:
    """Тесты именования файлов."""

    def test_download_event_filename_from_only(self, bearer_headers: Dict[str, str]):
        """TC-15: Имя файла только с from_ts."""
        from_ts = 1234567890
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            params={"from_ts": from_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert f'filename="event_logs_{from_ts}_all.csv"' in resp.headers["content-disposition"]

    def test_download_event_filename_to_only(self, bearer_headers: Dict[str, str]):
        """TC-16: Имя файла только с to_ts."""
        to_ts = 9876543210
        resp = requests.get(
            f"{BACKEND_URL}/log/download/event",
            params={"to_ts": to_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert f'filename="event_logs_all_{to_ts}.csv"' in resp.headers["content-disposition"]