"""Тесты для GET /log/download/safety — скачивание safety логов в формате CSV."""
from typing import Dict

import requests

from .conftest import BACKEND_URL
from .utils import (
    wait_for_elastic_sync,
    get_csv_headers,
    get_timestamp_ms,
    parse_csv_from_response,
    filter_rows_by_match,
    insert_safety_log,
)


class TestDownloadSafetyEmpty:
    """Тесты для пустого индекса safety (без учёта аудит-логов авторизации)."""

    def test_no_test_data_returns_header_only(self, bearer_headers: Dict[str, str]):
        """
        Если мы не создавали тестовых данных, CSV не должен содержать наших записей.
        Аудит-логи авторизации могут присутствовать — это нормально.
        """
        wait_for_elastic_sync()
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        
        # Фильтруем по маркеру тестовых данных — их быть не должно
        test_rows = filter_rows_by_match(rows, "Test safety message")
        assert len(test_rows) == 0
        
        # Заголовок должен быть всегда
        header = get_csv_headers(resp)
        assert header == ["timestamp", "service", "service_id", "severity", "message"]


class TestDownloadSafetyBasic:
    """Базовые тесты скачивания safety логов."""

    def test_single_document_export(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Один документ должен корректно экспортироваться в CSV."""
        timestamp = get_timestamp_ms()
        test_message = "TEST_SINGLE_DOC_export_12345"
        insert_safety_log(BACKEND_URL, 
            api_headers=api_headers,
            timestamp=timestamp,
            service="GCS",
            service_id=1,
            severity="error",
            message=test_message,
        )
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        
        # Фильтруем только наши тестовые данные
        test_rows = filter_rows_by_match(rows, test_message)
        assert len(test_rows) == 1
        assert int(test_rows[0]["timestamp"]) == timestamp
        assert test_rows[0]["service"] == "GCS"
        assert test_rows[0]["service_id"] == "1"
        assert test_rows[0]["severity"] == "error"
        assert test_rows[0]["message"] == test_message

    def test_multiple_documents_sorted_desc(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Документы должны быть отсортированы по timestamp (убывание)."""
        base_ts = get_timestamp_ms()
        test_marker = "TEST_SORTED_"
        timestamps = [base_ts + i * 1000 for i in range(5)]  # 5 документов
        
        for ts in timestamps:
            insert_safety_log(BACKEND_URL, api_headers=api_headers, timestamp=ts, message=f"{test_marker}{ts}")
        
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        
        # Фильтруем только наши тестовые данные
        test_rows = filter_rows_by_match(rows, test_marker)
        assert len(test_rows) == 5
        
        # Проверка сортировки: timestamp должны идти по убыванию
        row_timestamps = [int(row["timestamp"]) for row in test_rows]
        assert row_timestamps == sorted(row_timestamps, reverse=True)

    def test_column_order_in_header(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Заголовок CSV должен иметь строго определённый порядок колонок."""
        insert_safety_log(BACKEND_URL, api_headers=api_headers, message="TEST_HEADER_marker")
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        header = get_csv_headers(resp)
        assert header == ["timestamp", "service", "service_id", "severity", "message"]

    def test_no_extra_columns(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """В CSV не должно быть лишних колонок (_id, _index, apiVersion и др.)."""
        insert_safety_log(BACKEND_URL, api_headers=api_headers, message="TEST_COLUMNS_marker")
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        header = get_csv_headers(resp)
        assert len(header) == 5
        assert "_id" not in header
        assert "_index" not in header
        assert "apiVersion" not in header


class TestDownloadSafetyTimeFilter:
    """Тесты фильтрации по временному диапазону."""

    def test_filter_from_ts_only(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Фильтр только по from_ts (gte — inclusive)."""
        base_ts = 1000000000000
        test_marker = "TEST_FROM_TS_"
        # Создаём документы с timestamp: base_ts, base_ts+1000, base_ts+2000
        for i in range(3):
            insert_safety_log(BACKEND_URL, api_headers=api_headers, timestamp=base_ts + i * 1000, message=f"{test_marker}{i}")
        
        wait_for_elastic_sync()
        
        # Запрашиваем от base_ts + 1000
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            params={"from_ts": base_ts + 1000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        
        # Фильтруем только наши тестовые данные
        test_rows = filter_rows_by_match(rows, test_marker)
        assert len(test_rows) == 2  # base_ts+1000 и base_ts+2000
        timestamps = [int(row["timestamp"]) for row in test_rows]
        assert all(ts >= base_ts + 1000 for ts in timestamps)

    def test_filter_to_ts_only(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Фильтр только по to_ts (lte — inclusive)."""
        base_ts = 1000000000000
        test_marker = "TEST_TO_TS_"
        for i in range(3):
            insert_safety_log(BACKEND_URL, api_headers=api_headers, timestamp=base_ts + i * 1000, message=f"{test_marker}{i}")
        
        wait_for_elastic_sync()
        
        # Запрашиваем до base_ts + 1000
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            params={"to_ts": base_ts + 1000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        
        # Фильтруем только наши тестовые данные
        test_rows = filter_rows_by_match(rows, test_marker)
        assert len(test_rows) == 2  # base_ts и base_ts+1000
        timestamps = [int(row["timestamp"]) for row in test_rows]
        assert all(ts <= base_ts + 1000 for ts in timestamps)

    def test_filter_from_and_to_ts(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Фильтр по обоим параметрам (from_ts <= timestamp <= to_ts)."""
        base_ts = 1000000000000
        test_marker = "TEST_RANGE_"
        for i in range(5):
            insert_safety_log(BACKEND_URL, api_headers=api_headers, timestamp=base_ts + i * 1000, message=f"{test_marker}{i}")
        
        wait_for_elastic_sync()
        
        # Запрашиваем диапазон [base_ts+1000, base_ts+3000]
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            params={"from_ts": base_ts + 1000, "to_ts": base_ts + 3000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        
        # Фильтруем только наши тестовые данные
        test_rows = filter_rows_by_match(rows, test_marker)
        assert len(test_rows) == 3  # base_ts+1000, base_ts+2000, base_ts+3000
        timestamps = [int(row["timestamp"]) for row in test_rows]
        assert all(base_ts + 1000 <= ts <= base_ts + 3000 for ts in timestamps)

    def test_filter_boundary_from_ts_inclusive(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Граница from_ts включительная (документ с точным timestamp входит)."""
        base_ts = 1000000000000
        test_message = "TEST_BOUNDARY_FROM_exact"
        insert_safety_log(BACKEND_URL, api_headers=api_headers, timestamp=base_ts, message=test_message)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            params={"from_ts": base_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        
        # Фильтруем только наши тестовые данные
        test_rows = filter_rows_by_match(rows, test_message)
        assert len(test_rows) == 1
        assert int(test_rows[0]["timestamp"]) == base_ts

    def test_filter_boundary_to_ts_inclusive(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Граница to_ts включительная (документ с точным timestamp входит)."""
        base_ts = 1000000000000
        test_message = "TEST_BOUNDARY_TO_exact"
        insert_safety_log(BACKEND_URL, api_headers=api_headers, timestamp=base_ts, message=test_message)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            params={"to_ts": base_ts},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        
        # Фильтруем только наши тестовые данные
        test_rows = filter_rows_by_match(rows, test_message)
        assert len(test_rows) == 1
        assert int(test_rows[0]["timestamp"]) == base_ts

    def test_filter_no_matches(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Диапазон без совпадений должен вернуть CSV без наших тестовых данных."""
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
        test_rows = filter_rows_by_match(rows, test_message)
        assert len(test_rows) == 0


class TestDownloadSafetySpecialCharacters:
    """Тесты специальных символов в CSV."""

    def test_comma_in_message(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Запятая в message должна быть корректно экранирована."""
        test_message = "TEST_COMMA_Error, critical failure"
        insert_safety_log(BACKEND_URL, api_headers=api_headers, message=test_message)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_match(rows, "TEST_COMMA_")
        assert len(test_rows) == 1
        assert test_rows[0]["message"] == test_message

    def test_quotes_in_message(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Кавычки в message должны быть корректно экранированы."""
        test_message = 'TEST_QUOTES_Failed with "error" code'
        insert_safety_log(BACKEND_URL, api_headers=api_headers, message=test_message)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_match(rows, "TEST_QUOTES_")
        assert len(test_rows) == 1
        assert test_rows[0]["message"] == test_message

    def test_newline_in_message(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Перенос строки в message не должен ломать CSV."""
        test_message = "TEST_NEWLINE_Line1\nLine2"
        insert_safety_log(BACKEND_URL, api_headers=api_headers, message=test_message)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_match(rows, "TEST_NEWLINE_")
        assert len(test_rows) == 1
        assert test_rows[0]["message"] == test_message

    def test_unicode_cyrillic_in_message(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Кириллица в message должна корректно кодироваться в UTF-8."""
        test_message = "TEST_CYRILLIC_Ошибка подключения к дрону"
        insert_safety_log(BACKEND_URL, api_headers=api_headers, message=test_message)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        # Проверка, что контент валидный UTF-8
        content = resp.content.decode("utf-8")
        assert "Ошибка" in content
        rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_match(rows, "TEST_CYRILLIC_")
        assert len(test_rows) == 1
        assert test_rows[0]["message"] == test_message

    def test_emoji_in_message(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Эмодзи в message должны корректно кодироваться."""
        test_message = "TEST_EMOJI_Warning ⚠️ Critical 🚨"
        insert_safety_log(BACKEND_URL, api_headers=api_headers, message=test_message)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_match(rows, "TEST_EMOJI_")
        assert len(test_rows) == 1
        assert test_rows[0]["message"] == test_message

    def test_long_message_1024_chars(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Длинное сообщение (1024 символа) должно экспортироваться целиком."""
        test_message = "TEST_LONG_" + "x" * 1014  # 1024 символа всего
        insert_safety_log(BACKEND_URL, api_headers=api_headers, message=test_message)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_match(rows, "TEST_LONG_")
        assert len(test_rows) == 1
        assert len(test_rows[0]["message"]) == 1024


class TestDownloadSafetyNullValues:
    """Тесты обработки null/None значений."""

    def test_null_severity_becomes_empty_string(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """None значение severity должно стать пустой строкой в CSV."""
        test_message = "TEST_NULL_SEVERITY_here"
        insert_safety_log(BACKEND_URL, api_headers=api_headers, severity=None, message=test_message)
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_match(rows, test_message)
        assert len(test_rows) == 1
        assert test_rows[0]["severity"] == ""


class TestDownloadSafetyHttpHeaders:
    """Тесты HTTP-заголовков ответа."""

    def test_content_type_header(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Content-Type должен быть application/octet-stream."""
        insert_safety_log(BACKEND_URL, api_headers=api_headers, message="TEST_CONTENT_TYPE_marker")
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert resp.headers["Content-Type"] == "application/octet-stream"

    def test_content_disposition_all_data(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Content-Disposition без фильтров: safety_logs_all_all.csv."""
        insert_safety_log(BACKEND_URL, api_headers=api_headers, message="TEST_DISP_ALL_marker")
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert 'attachment; filename="safety_logs_all.csv"' in resp.headers["Content-Disposition"]

    def test_content_disposition_with_from_ts(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Content-Disposition с from_ts: safety_logs_{from_ts}_all.csv."""
        insert_safety_log(BACKEND_URL, api_headers=api_headers, message="TEST_DISP_FROM_marker")
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            params={"from_ts": 1000000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert 'attachment; filename="safety_logs_1000000_all.csv"' in resp.headers["Content-Disposition"]

    def test_content_disposition_with_to_ts(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Content-Disposition с to_ts: safety_logs_all_{to_ts}.csv."""
        insert_safety_log(BACKEND_URL, api_headers=api_headers, message="TEST_DISP_TO_marker")
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            params={"to_ts": 2000000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert 'attachment; filename="safety_logs_all_2000000.csv"' in resp.headers["Content-Disposition"]

    def test_content_disposition_with_both_ts(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Content-Disposition с обоими фильтрами: safety_logs_{from}_{to}.csv."""
        insert_safety_log(BACKEND_URL, api_headers=api_headers, message="TEST_DISP_BOTH_marker")
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            params={"from_ts": 1000000, "to_ts": 2000000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert 'attachment; filename="safety_logs_1000000_2000000.csv"' in resp.headers["Content-Disposition"]


class TestDownloadSafetyScrollPagination:
    """Тесты работы Scroll API для больших объёмов данных."""

    def test_large_dataset_exceeds_batch_size(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """
        Экспорт более 1000 документов (batch_size=1000).
        Проверяет, что scroll API корректно итерирует все страницы.
        """
        base_ts = get_timestamp_ms()
        total_docs = 1500  # Больше batch_size
        test_marker = "TEST_SCROLL_"
        
        # Вставляем 1500 документов
        for i in range(total_docs):
            insert_safety_log(BACKEND_URL, api_headers=api_headers, timestamp=base_ts + i, message=f"{test_marker}{i}")
        
        wait_for_elastic_sync(seconds=5)  # Больше времени для индексации
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=60  # Больше времени на скачивание
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        
        # Фильтруем только наши тестовые данные
        test_rows = filter_rows_by_match(rows, test_marker)
        assert len(test_rows) == total_docs

    def test_different_service_values(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Разные значения service должны корректно экспортироваться."""
        services = ["GCS", "dronePort", "regulator", "insurance", "operator"]
        base_ts = get_timestamp_ms()
        test_marker = "TEST_SERVICE_"
        
        for i, service in enumerate(services):
            insert_safety_log(BACKEND_URL, api_headers=api_headers, timestamp=base_ts + i, service=service, message=f"{test_marker}{i}")
        
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_match(rows, test_marker)
        assert len(test_rows) == len(services)
        exported_services = [row["service"] for row in test_rows]
        assert set(exported_services) == set(services)

    def test_different_severity_values(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Разные значения severity должны корректно экспортироваться."""
        severities = ["debug", "info", "warning", "error", "critical", "alert", "emergency"]
        base_ts = get_timestamp_ms()
        test_marker = "TEST_SEVERITY_"
        
        for i, severity in enumerate(severities):
            insert_safety_log(BACKEND_URL, api_headers=api_headers, timestamp=base_ts + i, severity=severity, message=f"{test_marker}{i}")
        
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_match(rows, test_marker)
        assert len(test_rows) == len(severities)
        exported_severities = [row["severity"] for row in test_rows]
        assert set(exported_severities) == set(severities)

    def test_service_id_boundary_values(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """Граничные значения service_id (1, 32767) должны экспортироваться."""
        base_ts = get_timestamp_ms()
        service_ids = [1, 100, 32767]
        test_marker = "TEST_SERVICE_ID_"
        
        for i, sid in enumerate(service_ids):
            insert_safety_log(BACKEND_URL, api_headers=api_headers, timestamp=base_ts + i, service_id=sid, message=f"{test_marker}{i}")
        
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        test_rows = filter_rows_by_match(rows, test_marker)
        assert len(test_rows) == 3
        exported_ids = [int(row["service_id"]) for row in test_rows]
        assert set(exported_ids) == set(service_ids)


class TestDownloadSafetyAuditLogs:
    """Тесты внутренних аудит-логов сервиса."""

    def test_audit_service_logs_included_in_download(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """
        В отличие от GET /log/safety, download-эндпоинт НЕ фильтрует аудит-логи.
        Документы от service=infopanel должны присутствовать в CSV.
        """
        base_ts = get_timestamp_ms()
        test_message = "TEST_AUDIT_INCLUDE_internal"
        # Вставляем лог от infopanel (AUDIT_SERVICE в бэкенде)
        insert_safety_log(BACKEND_URL, 
            api_headers=api_headers,
            timestamp=base_ts,
            service="infopanel",
            service_id=1,
            message=test_message
        )
        wait_for_elastic_sync()
        
        resp = requests.get(
            f"{BACKEND_URL}/log/download/safety",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        # Фильтруем по нашему тестовому маркеру
        test_rows = filter_rows_by_match(rows, test_message)
        # Аудит-лог должен быть в download (в отличие от GET /log/safety)
        infopanel_logs = [r for r in test_rows if r["service"] == "infopanel"]
        assert len(infopanel_logs) == 1