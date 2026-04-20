"""Тесты для GET /log/download/basic — экспорт логов в CSV."""
from typing import Dict

from .conftest import BACKEND_URL
from .utils import (
    wait_for_elastic_sync,
    parse_csv_from_response,
    get_csv_headers,
    post_basic_logs,
)
import requests


# --- Тест-кейсы ---

class TestDownloadBasicEmpty:
    """Тесты для пустого индекса."""

    def test_empty_index_headers_only(self, bearer_headers: Dict[str, str]):
        """TC-BASIC-01: Пустой индекс — только заголовки."""
        wait_for_elastic_sync()
        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 0
        headers = get_csv_headers(resp)
        assert headers == ["timestamp", "message"]


class TestDownloadBasicContent:
    """Тесты содержимого CSV."""

    def test_single_document(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-02: Один документ — корректная строка."""
        timestamp = 1700000000000
        logs = [{"timestamp": timestamp, "message": "Test"}]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 1
        assert rows[0]["timestamp"] == str(timestamp)
        assert rows[0]["message"] == "Test"

    def test_multiple_documents(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-03: Множество записей — полный экспорт."""
        base_ts = 1700000000000
        logs = [{"timestamp": base_ts + i * 1000, "message": f"Msg {i}"} for i in range(5)]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 5

    def test_sorting_timestamp_desc(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-08: Сортировка: timestamp desc."""
        timestamps = [1000, 3000, 2000]
        logs = [{"timestamp": ts, "message": f"Msg {ts}"} for ts in timestamps]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        returned_ts = [int(row["timestamp"]) for row in rows]
        assert returned_ts == sorted(returned_ts, reverse=True)


class TestDownloadBasicFiltering:
    """Тесты фильтрации по времени."""

    def test_filter_from_ts_inclusive(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-04: Фильтр from_ts — включительно."""
        logs = [{"timestamp": ts, "message": f"Msg {ts}"} for ts in [1000, 2000, 3000]]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            params={"from_ts": 2000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 2
        timestamps = [int(row["timestamp"]) for row in rows]
        assert all(ts >= 2000 for ts in timestamps)

    def test_filter_to_ts_inclusive(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-05: Фильтр to_ts — включительно."""
        logs = [{"timestamp": ts, "message": f"Msg {ts}"} for ts in [1000, 2000, 3000]]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            params={"to_ts": 2000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 2
        timestamps = [int(row["timestamp"]) for row in rows]
        assert all(ts <= 2000 for ts in timestamps)

    def test_filter_range_both(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-06: Фильтр диапазона [from, to]."""
        logs = [{"timestamp": ts, "message": f"Msg {ts}"} for ts in [1000, 2000, 3000, 4000]]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            params={"from_ts": 2000, "to_ts": 3000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 2
        timestamps = [int(row["timestamp"]) for row in rows]
        assert 2000 in timestamps
        assert 3000 in timestamps

    def test_filter_no_matches(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-07: Диапазон без совпадений."""
        logs = [{"timestamp": ts, "message": f"Msg {ts}"} for ts in [1000, 2000, 3000]]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            params={"from_ts": 5000, "to_ts": 6000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 0

    def test_filter_boundary_equal(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-21: Граничное значение: from_ts = to_ts."""
        target_ts = 1700000000000
        logs = [
            {"timestamp": target_ts - 1000, "message": "Before"},
            {"timestamp": target_ts, "message": "Exact"},
            {"timestamp": target_ts + 1000, "message": "After"},
        ]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            params={"from_ts": target_ts, "to_ts": target_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 1
        assert rows[0]["message"] == "Exact"

    def test_filter_future_range(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-24: Фильтр с несуществующим future-диапазоном."""
        logs = [{"timestamp": 1700000000000, "message": "Old data"}]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            params={"from_ts": 9999999999999, "to_ts": None},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 0

    def test_filter_by_message_substring(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-25: Фильтрация по `message` в download/basic."""
        logs = [
            {"timestamp": 1000, "message": "download-target"},
            {"timestamp": 2000, "message": "download-other"},
        ]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            params={"message": "target"},
            headers=bearer_headers,
            timeout=10,
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 1
        assert rows[0]["message"] == "download-target"


class TestDownloadBasicCSVEscaping:
    """Тесты экранирования специальных символов в CSV."""

    def test_comma_in_message(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-09: Экранирование запятой в сообщении."""
        logs = [{"timestamp": 1000, "message": "Error, code 404"}]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 1
        assert rows[0]["message"] == "Error, code 404"

    def test_quotes_in_message(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-10: Экранирование кавычек в сообщении."""
        logs = [{"timestamp": 1000, "message": 'He said "Hello"'}]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 1
        assert rows[0]["message"] == 'He said "Hello"'

    def test_newline_in_message(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-11: Перенос строки в сообщении."""
        logs = [{"timestamp": 1000, "message": "Line1\nLine2"}]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 1
        assert rows[0]["message"] == "Line1\nLine2"

    def test_unicode_cyrillic(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-12: Unicode и кириллица."""
        logs = [{"timestamp": 1000, "message": "Ошибка: данные не получены"}]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        content = resp.content.decode('utf-8')
        assert "Ошибка" in content
        rows = parse_csv_from_response(resp)
        assert rows[0]["message"] == "Ошибка: данные не получены"

    def test_min_message(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-13: Минимальная длина сообщения (1 символ)."""
        # Примечание: Pydantic не пропустит null или пустую строку (min_length=1)
        logs = [{"timestamp": 123, "message": "x"}]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 1
        assert rows[0]["message"] == "x"

    def test_long_message(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-23: Очень длинное сообщение (1024 символа)."""
        long_msg = "x" * 1024
        logs = [{"timestamp": 1000, "message": long_msg}]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 1
        assert len(rows[0]["message"]) == 1024


class TestDownloadBasicScroll:
    """Тесты scroll-итерации для больших объёмов данных."""

    def test_large_dataset_over_1000(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-15: Большое количество записей (>1000)."""
        base_ts = 1700000000000
        logs = [{"timestamp": base_ts + i, "message": f"Msg {i}"} for i in range(1500)]
        
        # Отправляем пачками по 100 (максимум в API)
        for i in range(0, 1500, 100):
            batch = logs[i:i+100]
            resp = post_basic_logs(BACKEND_URL, api_headers, batch)
            assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        
        wait_for_elastic_sync(5.0)  # Ждём дольше для большого объёма

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            headers=bearer_headers,
            timeout=60  # Увеличиваем таймаут для большого экспорта
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 1500


class TestDownloadBasicHeaders:
    """Тесты HTTP-заголовков ответа."""

    def test_content_type(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-20: Content-Type ответа."""
        logs = [{"timestamp": 1000, "message": "Test"}]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert resp.headers["Content-Type"] == "application/octet-stream"

    def test_filename_no_filters(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-16: Имя файла: без фильтров."""
        logs = [{"timestamp": 1000, "message": "Test"}]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        disposition = resp.headers.get("Content-Disposition", "")
        assert 'filename="basic_logs_all.csv"' in disposition

    def test_filename_only_from_ts(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-17: Имя файла: только from_ts."""
        logs = [{"timestamp": 1000, "message": "Test"}]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            params={"from_ts": 1700000000000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        disposition = resp.headers.get("Content-Disposition", "")
        assert 'filename="basic_logs_1700000000000_all.csv"' in disposition

    def test_filename_only_to_ts(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-18: Имя файла: только to_ts."""
        logs = [{"timestamp": 1000, "message": "Test"}]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            params={"to_ts": 1700000000000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        disposition = resp.headers.get("Content-Disposition", "")
        assert 'filename="basic_logs_all_1700000000000.csv"' in disposition

    def test_filename_both_filters(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-BASIC-19: Имя файла: оба фильтра."""
        logs = [{"timestamp": 1000, "message": "Test"}]
        resp = post_basic_logs(BACKEND_URL, api_headers, logs)
        assert resp.status_code in (200, 207), f"Failed to insert logs: {resp.text}"
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/basic",
            params={"from_ts": 1000, "to_ts": 2000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        disposition = resp.headers.get("Content-Disposition", "")
        assert 'filename="basic_logs_1000_2000.csv"' in disposition