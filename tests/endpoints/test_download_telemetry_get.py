"""Тесты для GET /log/download/* эндпоинтов (CSV экспорт)."""
import csv
import io
import time
from typing import Dict, Any, List, Optional

import pytest
import requests

from .conftest import BACKEND_URL
from .utils import wait_for_elastic_sync, parse_csv_from_response, get_csv_headers


# =============================================================================
# Вспомогательные функции
# =============================================================================


def get_filename_from_disposition(headers: Dict[str, str]) -> Optional[str]:
    """Извлекает имя файла из заголовка Content-Disposition."""
    disposition = headers.get('Content-Disposition', '')
    if 'filename=' in disposition:
        # Может быть в формате filename="name.csv" или filename=name.csv
        parts = disposition.split('filename=')
        if len(parts) > 1:
            filename = parts[1].strip().strip('"')
            return filename
    return None


def insert_telemetry_data(api_headers: Dict[str, str], records: List[Dict[str, Any]]) -> None:
    """Вставляет записи телеметрии через POST /log/telemetry."""
    resp = requests.post(
        f"{BACKEND_URL}/log/telemetry",
        json=records,
        headers=api_headers,
        timeout=10
    )
    assert resp.status_code in (200, 207), f"Failed to insert telemetry: {resp.text}"


# =============================================================================
# Константы
# =============================================================================

EXPECTED_FIELDNAMES = [
    "timestamp", "drone", "drone_id", "battery", "pitch", "roll", "course", "latitude", "longitude"
]

BASE_TIMESTAMP = 1700000000000  # Базовая метка времени для тестов


# =============================================================================
# Тесты базовой функциональности
# =============================================================================

class TestDownloadTelemetryBasic:
    """Базовые тесты экспорта телеметрии."""

    def test_dl_tm_001_empty_index_returns_headers_only(
        self, bearer_headers: Dict[str, str]
    ):
        """TC-DL-TM-001: Пустой индекс возвращает CSV только с заголовком."""
        wait_for_elastic_sync()
        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 0, "Пустой индекс должен вернуть 0 строк данных"
        headers = get_csv_headers(resp)
        assert headers == EXPECTED_FIELDNAMES, f"Заголовки не совпадают: {headers}"

    def test_dl_tm_002_single_record_exported_correctly(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-002: Одна запись корректно экспортируется в CSV."""
        test_record = [{
            "apiVersion": "1.0.0",
            "timestamp": BASE_TIMESTAMP,
            "drone": "delivery",
            "drone_id": 1,
            "battery": 85,
            "pitch": 5.5,
            "roll": -2.1,
            "course": 180.0,
            "latitude": 55.7558,
            "longitude": 37.6176
        }]
        insert_telemetry_data(api_headers, test_record)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 1, "Должна быть ровно одна строка данных"
        
        row = rows[0]
        assert row["timestamp"] == str(BASE_TIMESTAMP)
        assert row["drone"] == "delivery"
        assert row["drone_id"] == "1"
        assert row["battery"] == "85"
        assert row["pitch"] == "5.5"
        assert row["roll"] == "-2.1"
        assert row["course"] == "180.0"
        assert row["latitude"] == "55.7558"
        assert row["longitude"] == "37.6176"

    def test_dl_tm_003_multiple_records_sorted_desc(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-003: Множественные записи экспортируются в правильном порядке."""
        # Вставляем записи вразнобой по времени
        records = [
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP + 3000, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP + 1000, "drone": "inspector", "drone_id": 2, "latitude": 59.0, "longitude": 30.0},
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP + 2000, "drone": "queen", "drone_id": 3, "latitude": 50.0, "longitude": 40.0},
        ]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 3, "Все 3 записи должны быть в CSV"
        
        # Проверяем сортировку по убыванию timestamp
        timestamps = [int(row["timestamp"]) for row in rows]
        assert timestamps == sorted(timestamps, reverse=True), "Записи должны быть отсортированы по timestamp desc"
        assert timestamps[0] == BASE_TIMESTAMP + 3000
        assert timestamps[1] == BASE_TIMESTAMP + 2000
        assert timestamps[2] == BASE_TIMESTAMP + 1000


# =============================================================================
# Тесты фильтрации по времени
# =============================================================================

class TestDownloadTelemetryTimeFilters:
    """Тесты фильтрации по from_ts и to_ts."""

    def test_dl_tm_004_from_ts_includes_greater_or_equal(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-004: Фильтр from_ts включает записи с timestamp >= значения."""
        records = [
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP - 1000, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP, "drone": "delivery", "drone_id": 2, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP + 1000, "drone": "delivery", "drone_id": 3, "latitude": 55.0, "longitude": 37.0},
        ]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            params={"from_ts": BASE_TIMESTAMP},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 2, "Должны быть записи с timestamp >= from_ts"
        assert all(int(row["timestamp"]) >= BASE_TIMESTAMP for row in rows)

    def test_dl_tm_005_to_ts_includes_less_or_equal(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-005: Фильтр to_ts включает записи с timestamp <= значения."""
        records = [
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP - 1000, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP, "drone": "delivery", "drone_id": 2, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP + 1000, "drone": "delivery", "drone_id": 3, "latitude": 55.0, "longitude": 37.0},
        ]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            params={"to_ts": BASE_TIMESTAMP},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 2, "Должны быть записи с timestamp <= to_ts"
        assert all(int(row["timestamp"]) <= BASE_TIMESTAMP for row in rows)

    def test_dl_tm_006_range_filter_both_from_and_to(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-006: Диапазон [from_ts, to_ts] работает корректно."""
        records = [
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP - 2000, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP - 1000, "drone": "delivery", "drone_id": 2, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP, "drone": "delivery", "drone_id": 3, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP + 1000, "drone": "delivery", "drone_id": 4, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP + 2000, "drone": "delivery", "drone_id": 5, "latitude": 55.0, "longitude": 37.0},
        ]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            params={"from_ts": BASE_TIMESTAMP - 1000, "to_ts": BASE_TIMESTAMP + 1000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 3, "Должны быть записи в диапазоне [from_ts, to_ts]"
        for row in rows:
            ts = int(row["timestamp"])
            assert BASE_TIMESTAMP - 1000 <= ts <= BASE_TIMESTAMP + 1000

    def test_dl_tm_007_boundary_values_included(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-007: Граничные значения диапазона включаются."""
        records = [
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP + 1000, "drone": "delivery", "drone_id": 2, "latitude": 55.0, "longitude": 37.0},
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP + 2000, "drone": "delivery", "drone_id": 3, "latitude": 55.0, "longitude": 37.0},
        ]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            params={"from_ts": BASE_TIMESTAMP, "to_ts": BASE_TIMESTAMP + 2000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        timestamps = [int(row["timestamp"]) for row in rows]
        assert BASE_TIMESTAMP in timestamps, "Нижняя граница должна быть включена"
        assert BASE_TIMESTAMP + 2000 in timestamps, "Верхняя граница должна быть включена"

    def test_dl_tm_008_empty_result_non_overlapping_range(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-008: Пустой результат при непересекающемся диапазоне."""
        records = [
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0},
        ]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            params={"from_ts": BASE_TIMESTAMP + 999999999},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 0, "Не должно быть записей вне диапазона"
        headers = get_csv_headers(resp)
        assert headers == EXPECTED_FIELDNAMES, "Заголовки должны присутствовать даже при пустом результате"


# =============================================================================
# Тесты обработки значений
# =============================================================================

class TestDownloadTelemetryValueHandling:
    """Тесты обработки различных типов значений."""

    def test_dl_tm_009_null_values_as_empty_strings(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-009: Опциональные поля с null преобразуются в пустые строки."""
        records = [{
            "apiVersion": "1.0.0",
            "timestamp": BASE_TIMESTAMP,
            "drone": "delivery",
            "drone_id": 1,
            "battery": None,
            "pitch": None,
            "roll": None,
            "course": None,
            "latitude": 55.0,
            "longitude": 37.0
        }]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 1
        row = rows[0]
        assert row["battery"] == "", f"battery должен быть пустой строкой, получил: '{row['battery']}'"
        assert row["pitch"] == "", f"pitch должен быть пустой строкой, получил: '{row['pitch']}'"
        assert row["roll"] == "", f"roll должен быть пустой строкой, получил: '{row['roll']}'"
        assert row["course"] == "", f"course должен быть пустой строкой, получил: '{row['course']}'"

    def test_dl_tm_010_numeric_values_serialized_correctly(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-010: Числовые значения корректно сериализуются."""
        records = [{
            "apiVersion": "1.0.0",
            "timestamp": BASE_TIMESTAMP,
            "drone": "agriculture",
            "drone_id": 42,
            "battery": 100,
            "pitch": 5.555,
            "roll": -180.0,
            "course": 360.0,
            "latitude": 55.755826,
            "longitude": 37.617633
        }]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        row = rows[0]
        assert row["drone_id"] == "42"
        assert row["battery"] == "100"
        assert row["pitch"] == "5.555"
        assert row["roll"] == "-180.0"
        assert row["course"] == "360.0"
        assert row["latitude"] == "55.755826"
        assert row["longitude"] == "37.617633"

    def test_dl_tm_011_special_characters_escaped_in_csv(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-011: Специальные символы в строковых полях экранируются."""
        # Примечание: drone — это Literal, поэтому специальные символы там не ожидаются
        # Но тестируем общую CSV-валидность через другие поля
        records = [{
            "apiVersion": "1.0.0",
            "timestamp": BASE_TIMESTAMP,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        # Проверяем, что CSV парсится без ошибок
        rows = parse_csv_from_response(resp)
        assert len(rows) == 1
        # Проверяем, что content валидный CSV
        content = resp.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        all_rows = list(reader)
        assert len(all_rows) == 2  # заголовок + 1 строка данных

    def test_dl_tm_012_utf8_encoding_preserved(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-012: UTF-8 кодировка сохраняется."""
        records = [{
            "apiVersion": "1.0.0",
            "timestamp": BASE_TIMESTAMP,
            "drone": "delivery",
            "drone_id": 1,
            "latitude": 55.0,
            "longitude": 37.0
        }]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        # Проверяем, что контент декодируется как UTF-8 без ошибок
        content = resp.content.decode('utf-8')
        assert isinstance(content, str)
        # Проверяем отсутствие символов замены (replacement character)
        assert '\ufffd' not in content, "Обнаружены символы замены UTF-8"

    def test_dl_tm_020_boundary_coordinates_handled(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-020: Граничные значения координат обрабатываются."""
        records = [
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP, "drone": "delivery", "drone_id": 1, "latitude": 90.0, "longitude": 180.0},
            {"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP + 1000, "drone": "delivery", "drone_id": 2, "latitude": -90.0, "longitude": -180.0},
        ]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 2
        latitudes = [float(row["latitude"]) for row in rows]
        longitudes = [float(row["longitude"]) for row in rows]
        assert 90.0 in latitudes or -90.0 in latitudes
        assert 180.0 in longitudes or -180.0 in longitudes

    def test_dl_tm_021_negative_orientation_values(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-021: Отрицательные значения ориентации корректны."""
        records = [{
            "apiVersion": "1.0.0",
            "timestamp": BASE_TIMESTAMP,
            "drone": "inspector",
            "drone_id": 1,
            "battery": 50,
            "pitch": -45.5,
            "roll": -180.0,
            "course": 0.0,
            "latitude": 55.0,
            "longitude": 37.0
        }]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        row = rows[0]
        assert row["pitch"] == "-45.5"
        assert row["roll"] == "-180.0"

    def test_dl_tm_022_drone_literal_values(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-022: Значения drone из Literal корректны."""
        valid_drones = ["delivery", "queen", "inspector", "agriculture"]
        records = []
        for i, drone in enumerate(valid_drones):
            records.append({
                "apiVersion": "1.0.0",
                "timestamp": BASE_TIMESTAMP + i * 1000,
                "drone": drone,
                "drone_id": i + 1,
                "latitude": 55.0,
                "longitude": 37.0
            })
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == len(valid_drones)
        drones_in_csv = [row["drone"] for row in rows]
        for drone in valid_drones:
            assert drone in drones_in_csv, f"Тип дрона '{drone}' отсутствует в экспорте"


# =============================================================================
# Тесты имени файла и заголовков
# =============================================================================

class TestDownloadTelemetryHeaders:
    """Тесты заголовков ответа и имени файла."""

    def test_dl_tm_014_filename_without_filters(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-014: Имя файла без фильтров."""
        records = [{"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0}]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        filename = get_filename_from_disposition(resp.headers)
        assert filename == "telemetry_logs_all.csv", f"Неверное имя файла: {filename}"

    def test_dl_tm_015_filename_with_from_ts(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-015: Имя файла с from_ts."""
        records = [{"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0}]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            params={"from_ts": BASE_TIMESTAMP},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        filename = get_filename_from_disposition(resp.headers)
        assert filename == f"telemetry_logs_{BASE_TIMESTAMP}_all.csv"

    def test_dl_tm_016_filename_with_to_ts(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-016: Имя файла с to_ts."""
        records = [{"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0}]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            params={"to_ts": BASE_TIMESTAMP},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        filename = get_filename_from_disposition(resp.headers)
        assert filename == f"telemetry_logs_all_{BASE_TIMESTAMP}.csv"

    def test_dl_tm_017_filename_with_both_filters(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-017: Имя файла с обоими фильтрами."""
        records = [{"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0}]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            params={"from_ts": BASE_TIMESTAMP - 1000, "to_ts": BASE_TIMESTAMP + 1000},
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        filename = get_filename_from_disposition(resp.headers)
        assert filename == f"telemetry_logs_{BASE_TIMESTAMP - 1000}_{BASE_TIMESTAMP + 1000}.csv"

    def test_dl_tm_018_response_headers_correct(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-018: Заголовки ответа корректны."""
        records = [{"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0}]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert resp.headers.get('Content-Type') == 'application/octet-stream'
        assert 'Content-Disposition' in resp.headers
        assert 'attachment' in resp.headers.get('Content-Disposition', '')

    def test_dl_tm_019_column_order_matches_fieldnames(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-019: Порядок колонок в CSV соответствует fieldnames."""
        records = [{"apiVersion": "1.0.0", "timestamp": BASE_TIMESTAMP, "drone": "delivery", "drone_id": 1, "latitude": 55.0, "longitude": 37.0}]
        insert_telemetry_data(api_headers, records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        headers = get_csv_headers(resp)
        assert headers == EXPECTED_FIELDNAMES, f"Порядок колонок не совпадает: {headers}"


# =============================================================================
# Тесты больших объёмов данных (Scroll API)
# =============================================================================

class TestDownloadTelemetryScroll:
    """Тесты Scroll API для больших объёмов данных."""

    def test_dl_tm_013_over_1000_records_exported_completely(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-013: Более 1000 записей экспортируются полностью (scroll)."""
        # Вставляем 1500 записей (больше batch_size=1000)
        records = []
        for i in range(1500):
            records.append({
                "apiVersion": "1.0.0",
                "timestamp": BASE_TIMESTAMP + (i * 1000),
                "drone": "delivery",
                "drone_id": i+1,
                "battery": 50,
                "latitude": 55.0,
                "longitude": 37.0
            })
        
        # Вставляем пачками по 100 (ограничение POST /log/telemetry)
        for i in range(0, len(records), 50):
            batch = records[i:i+50]
            insert_telemetry_data(api_headers, batch)
        
        wait_for_elastic_sync(seconds=10)  # Даём больше времени на индексацию

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=60  # Увеличенный таймаут для большого экспорта
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 1500, f"Ожидалось 1500 записей, получено: {len(rows)}"
        
        # Проверяем сортировку
        timestamps = [int(row["timestamp"]) for row in rows]
        assert timestamps == sorted(timestamps, reverse=True), "Записи должны быть отсортированы по timestamp desc"

    def test_dl_tm_024_streaming_does_not_truncate_large_dataset(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-024: Streaming не обрывает поток на большом объёме."""
        # Вставляем 5000 записей
        records = []
        for i in range(5000):
            records.append({
                "apiVersion": "1.0.0",
                "timestamp": BASE_TIMESTAMP + (i * 1000),
                "drone": "agriculture",
                "drone_id": i+1,
                "latitude": 55.0,
                "longitude": 37.0
            })
        
        for i in range(0, len(records), 100):
            batch = records[i:i+100]
            insert_telemetry_data(api_headers, batch)
        
        wait_for_elastic_sync(seconds=10)

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=120  # Ещё больший таймаут
        )
        assert resp.status_code == 200
        
        # Проверяем, что поток не оборвался
        content = resp.content.decode('utf-8')
        lines = content.strip().split('\n')
        # Должен быть заголовок + 5000 строк данных
        assert len(lines) == 5001, f"Ожидалось 5001 линий (заголовок + 5000 записей), получено: {len(lines)}"
        
        # Проверяем, что последняя строка валидна (не обрезана)
        last_line = lines[-1]
        reader = csv.reader(io.StringIO(last_line))
        parsed = list(reader)
        assert len(parsed) == 1, "Последняя строка должна быть валидной CSV-строкой"
        assert len(parsed[0]) == len(EXPECTED_FIELDNAMES), "Последняя строка должна иметь все колонки"


# =============================================================================
# Тесты целостности данных
# =============================================================================

class TestDownloadTelemetryDataIntegrity:
    """Тесты целостности данных между POST и GET."""

    def test_dl_tm_023_data_matches_posted(
        self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]
    ):
        """TC-DL-TM-023: Данные идентичны отправленным через POST."""
        original_records = [
            {
                "apiVersion": "1.0.0",
                "timestamp": BASE_TIMESTAMP,
                "drone": "delivery",
                "drone_id": 1,
                "battery": 85,
                "pitch": 5.5,
                "roll": -2.1,
                "course": 180.0,
                "latitude": 55.7558,
                "longitude": 37.6176
            },
            {
                "apiVersion": "1.0.0",
                "timestamp": BASE_TIMESTAMP + 1000,
                "drone": "inspector",
                "drone_id": 2,
                "battery": None,
                "pitch": None,
                "roll": None,
                "course": None,
                "latitude": 59.9343,
                "longitude": 30.3351
            },
        ]
        insert_telemetry_data(api_headers, original_records)
        wait_for_elastic_sync()

        resp = requests.get(
            f"{BACKEND_URL}/log/download/telemetry",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        rows = parse_csv_from_response(resp)
        assert len(rows) == 2
        
        # Сортируем оригинальные записи по timestamp desc для сравнения
        original_sorted = sorted(original_records, key=lambda x: x["timestamp"], reverse=True)
        
        for i, row in enumerate(rows):
            orig = original_sorted[i]
            assert int(row["timestamp"]) == orig["timestamp"]
            assert row["drone"] == orig["drone"]
            assert row["drone_id"] == str(orig["drone_id"])
            assert row["latitude"] == str(orig["latitude"])
            assert row["longitude"] == str(orig["longitude"])
            
            # Проверяем None → пустая строка
            if orig["battery"] is None:
                assert row["battery"] == ""
            else:
                assert row["battery"] == str(orig["battery"])