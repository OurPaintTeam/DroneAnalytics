"""Интеграционные тесты для GET /log/telemetry."""
from typing import Dict, Any, List

import requests

from .conftest import BACKEND_URL
from .utils import (
    wait_for_elastic_sync,
    get_timestamp_ms,
    create_telemetry_payload,
    post_telemetry_logs,
    get_paginated_logs,
)

# =============================================================================
# Вспомогательные функции
# =============================================================================

def insert_telemetry_records(
    records: List[Dict[str, Any]],
    api_headers: Dict[str, str]
) -> requests.Response:
    """Вспомогательная функция для записи тестовых данных в телеметрию."""
    return post_telemetry_logs(BACKEND_URL, api_headers, records)


def fetch_telemetry(
    bearer_headers: Dict[str, str],
    limit: int = 10,
    page: int = 1
) -> requests.Response:
    """Вспомогательная функция для получения телеметрии."""
    return get_paginated_logs(
        BACKEND_URL,
        "/log/telemetry",
        bearer_headers,
        limit=limit,
        page=page,
        timeout=5,
    )



# =============================================================================
# Тест-кейсы: базовая функциональность
# =============================================================================

class TestTelemetryBasic:
    """Базовые тесты получения телеметрии."""

    def test_TC_TEL_001_empty_index(self, bearer_headers: Dict[str, str]):
        """TC-TEL-001: Получение телеметрии из пустой базы."""
        wait_for_elastic_sync()
        resp = fetch_telemetry(bearer_headers)
        
        assert resp.status_code == 200
        assert resp.json() == []

    def test_TC_TEL_002_single_record(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-002: Получение одной записи телеметрии."""
        timestamp = get_timestamp_ms()
        test_record = create_telemetry_payload(
            timestamp=timestamp,
            drone="inspector",
            drone_id=42,
            latitude=59.9343,
            longitude=30.3351
        )
        
        # Записываем тестовые данные
        post_resp = insert_telemetry_records([test_record], api_headers)
        assert post_resp.status_code == 200
        wait_for_elastic_sync()
        
        # Читаем и проверяем
        resp = fetch_telemetry(bearer_headers, limit=1)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 1
        log = logs[0]
        assert log["timestamp"] == timestamp
        assert log["drone"] == "inspector"
        assert log["drone_id"] == 42
        assert log["latitude"] == 59.9343
        assert log["longitude"] == 30.3351
        # Опциональные поля должны присутствовать
        assert log["battery"] == 85
        assert log["pitch"] == 5.5

    def test_TC_TEL_003_sorting_desc(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-003: Проверка сортировки по времени (desc)."""
        base_ts = get_timestamp_ms()
        # Записываем записи в случайном порядке по времени
        records = [
            create_telemetry_payload(timestamp=base_ts + 1000, drone_id=1),
            create_telemetry_payload(timestamp=base_ts + 5000, drone_id=2),
            create_telemetry_payload(timestamp=base_ts + 3000, drone_id=3),
            create_telemetry_payload(timestamp=base_ts + 100, drone_id=4),
            create_telemetry_payload(timestamp=base_ts + 4000, drone_id=5),
        ]
        
        insert_telemetry_records(records, api_headers)
        wait_for_elastic_sync()
        
        resp = fetch_telemetry(bearer_headers, limit=10)
        assert resp.status_code == 200
        logs = resp.json()
        
        timestamps = [log["timestamp"] for log in logs]
        assert timestamps == sorted(timestamps, reverse=True), "Логи не отсортированы по убыванию времени"


# =============================================================================
# Тест-кейсы: пагинация
# =============================================================================

class TestTelemetryPagination:
    """Тесты пагинации эндпоинта телеметрии."""

    def test_TC_TEL_004_pagination_page1(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-004: Пагинация: первая страница."""
        base_ts = get_timestamp_ms()
        records = [create_telemetry_payload(timestamp=base_ts + i*100, drone_id=i) for i in range(15)]
        
        insert_telemetry_records(records, api_headers)
        wait_for_elastic_sync()
        
        resp = fetch_telemetry(bearer_headers, limit=5, page=1)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 5
        # Первая страница должна содержать самые новые записи
        expected_ids = [14, 13, 12, 11, 10]  # drone_id соответствуют порядку записи
        returned_ids = [log["drone_id"] for log in logs]
        assert returned_ids == expected_ids

    def test_TC_TEL_005_pagination_page2(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-005: Пагинация: вторая страница."""
        base_ts = get_timestamp_ms()
        records = [create_telemetry_payload(timestamp=base_ts + i*100, drone_id=i) for i in range(15)]
        
        insert_telemetry_records(records, api_headers)
        wait_for_elastic_sync()
        
        # Получаем первую и вторую страницы
        resp1 = fetch_telemetry(bearer_headers, limit=5, page=1)
        resp2 = fetch_telemetry(bearer_headers, limit=5, page=2)
        
        ids_page1 = {log["drone_id"] for log in resp1.json()}
        ids_page2 = {log["drone_id"] for log in resp2.json()}
        
        # Не должно быть пересечений
        assert ids_page1.isdisjoint(ids_page2), "Страницы содержат дубликаты"
        # Вторая страница должна содержать более старые записи
        assert max(ids_page2) < min(ids_page1)

    def test_TC_TEL_006_pagination_last_page_partial(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-006: Пагинация: последняя страница с неполным набором."""
        base_ts = get_timestamp_ms()
        records = [create_telemetry_payload(timestamp=base_ts + i*100, drone_id=i) for i in range(1, 13)]
        
        insert_telemetry_records(records, api_headers)
        wait_for_elastic_sync()
        
        # Страница 3 при limit=5 должна вернуть 2 записи (12 - 5*2 = 2)
        resp = fetch_telemetry(bearer_headers, limit=5, page=3)
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 2

    def test_TC_TEL_007_pagination_out_of_range(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-007: Пагинация: запрос страницы за пределами данных."""
        base_ts = get_timestamp_ms()
        records = [create_telemetry_payload(timestamp=base_ts + i*100, drone_id=i) for i in range(1, 11)]
        
        insert_telemetry_records(records, api_headers)
        wait_for_elastic_sync()
        
        # Страница 10 при 10 записях и limit=5 не существует
        resp = fetch_telemetry(bearer_headers, limit=5, page=10)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_TC_TEL_017_pagination_no_duplicates(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-017: Временна́я целостность: записи не теряются при пагинации."""
        base_ts = get_timestamp_ms()
        records = [create_telemetry_payload(timestamp=base_ts + i*100, drone_id=i) for i in range(1, 26)]
        
        insert_telemetry_records(records, api_headers)
        wait_for_elastic_sync()
        
        # Собираем все записи постранично
        all_logs = []
        for page in range(1, 4):  # 3 страницы по 10 = 30, но записей только 25
            resp = fetch_telemetry(bearer_headers, limit=10, page=page)
            all_logs.extend(resp.json())
        
        # Проверяем уникальность и количество
        unique_ids = {log["drone_id"] for log in all_logs}
        assert len(unique_ids) == 25, "Потеряны или продублированы записи при пагинации"
        assert len(all_logs) == 25


# =============================================================================
# Тест-кейсы: граничные значения параметров
# =============================================================================

class TestTelemetryLimits:
    """Тесты граничных значений query-параметров."""

    def test_TC_TEL_008_limit_min(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-008: Граничное значение limit=1."""
        base_ts = get_timestamp_ms()
        records = [create_telemetry_payload(timestamp=base_ts + i*100, drone_id=i) for i in range(1, 3)]
        
        insert_telemetry_records(records, api_headers)
        wait_for_elastic_sync()
        
        resp = fetch_telemetry(bearer_headers, limit=1, page=1)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_TC_TEL_009_limit_max(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-009: Граничное значение limit=100."""
        base_ts = get_timestamp_ms()
        records = [create_telemetry_payload(timestamp=base_ts + i*10, drone_id=i) for i in range(1, 101)]
        
        insert_telemetry_records(records, api_headers)
        wait_for_elastic_sync()
        
        resp = fetch_telemetry(bearer_headers, limit=100, page=1)
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 100

    def test_TC_TEL_010_limit_greater_than_data(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-010: Значение limit больше количества записей."""
        base_ts = get_timestamp_ms()
        records = [create_telemetry_payload(timestamp=base_ts + i*100, drone_id=i) for i in range(1, 4)]
        
        insert_telemetry_records(records, api_headers)
        wait_for_elastic_sync()
        
        resp = fetch_telemetry(bearer_headers, limit=50, page=1)
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_TC_TEL_018_default_params(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-018: Дефолтные параметры запроса."""
        base_ts = get_timestamp_ms()
        records = [create_telemetry_payload(timestamp=base_ts + i*100, drone_id=i) for i in range(1, 16)]
        
        insert_telemetry_records(records, api_headers)
        wait_for_elastic_sync()
        
        # Запрос без параметров должен использовать limit=10, page=1
        resp = requests.get(
            f"{BACKEND_URL}/log/telemetry",
            headers=bearer_headers,
            timeout=5
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 10


# =============================================================================
# Тест-кейсы: валидация данных и форматов
# =============================================================================

class TestTelemetryDataValidation:
    """Тесты корректности возвращаемых данных."""

    def test_TC_TEL_011_optional_fields_null(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-011: Проверка обработки опциональных полей (null)."""
        timestamp = get_timestamp_ms()
        # Запись только с обязательными полями
        record = {
            "apiVersion": "1.0.0",
            "timestamp": timestamp,
            "drone": "agriculture",
            "drone_id": 99,
            "latitude": 45.0,
            "longitude": 75.0
            # battery, pitch, roll, course намеренно опущены
        }
        
        insert_telemetry_records([record], api_headers)
        wait_for_elastic_sync()
        
        resp = fetch_telemetry(bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 1
        
        log = logs[0]
        # Обязательные поля на месте
        assert log["drone_id"] == 99
        assert log["latitude"] == 45.0
        assert log["timestamp"] == timestamp

    def test_TC_TEL_012_drone_types(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-012: Разные типы дронов в ответе."""
        base_ts = get_timestamp_ms()
        drone_types = ["delivery", "queen", "inspector", "agriculture"]
        records = [
            create_telemetry_payload(timestamp=base_ts + i*100, drone=drone, drone_id=i)
            for i, drone in enumerate(drone_types, start=1)
        ]
        
        insert_telemetry_records(records, api_headers)
        wait_for_elastic_sync()
        
        resp = fetch_telemetry(bearer_headers, limit=10)
        assert resp.status_code == 200
        logs = resp.json()
        
        returned_drones = {log["drone"] for log in logs}
        assert returned_drones == set(drone_types)

    def test_TC_TEL_013_timestamp_format(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-013: Валидация формата timestamp в ответе."""
        base_ts = get_timestamp_ms()
        record = create_telemetry_payload(timestamp=base_ts)
        
        insert_telemetry_records([record], api_headers)
        wait_for_elastic_sync()
        
        resp = fetch_telemetry(bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 1
        ts = logs[0]["timestamp"]
        assert isinstance(ts, int), "timestamp должен быть целым числом"
        assert ts > 0, "timestamp должен быть положительным"
        # Проверяем, что это миллисекунды (а не секунды)
        assert ts > 1_000_000_000_000, "timestamp должен быть в миллисекундах"

    def test_TC_TEL_014_coordinates_range(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-014: Координаты в допустимых диапазонах."""
        test_cases = [
            {"lat": -90, "lon": -180},  # Минимальные значения
            {"lat": 90, "lon": 180},    # Максимальные значения
            {"lat": 0, "lon": 0},       # Экватор/нулевой меридиан
            {"lat": 55.7558, "lon": 37.6176},  # Реальные координаты
        ]
        
        base_ts = get_timestamp_ms()
        records = [
            create_telemetry_payload(
                timestamp=base_ts + i*100,
                latitude=tc["lat"],
                longitude=tc["lon"],
                drone_id=i
            )
            for i, tc in enumerate(test_cases, start=1)
        ]
        
        insert_telemetry_records(records, api_headers)
        wait_for_elastic_sync()
        
        resp = fetch_telemetry(bearer_headers, limit=10)
        assert resp.status_code == 200
        logs = resp.json()
        
        returned_coords = {(log["latitude"], log["longitude"]) for log in logs}
        expected_coords = {(tc["lat"], tc["lon"]) for tc in test_cases}
        assert returned_coords == expected_coords
        
        # Проверяем диапазоны
        for log in logs:
            assert -90 <= log["latitude"] <= 90
            assert -180 <= log["longitude"] <= 180

    def test_TC_TEL_015_large_drone_id(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-015: Большие значения drone_id (граница short)."""
        timestamp = get_timestamp_ms()
        # 32767 — максимальное значение для signed short
        record = create_telemetry_payload(timestamp=timestamp, drone_id=32767)
        
        insert_telemetry_records([record], api_headers)
        wait_for_elastic_sync()
        
        resp = fetch_telemetry(bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert logs[0]["drone_id"] == 32767

    def test_TC_TEL_016_mixed_optional_fields(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-016: Смешанные данные: обязательные и опциональные поля."""
        base_ts = get_timestamp_ms()
        records = [
            # Только обязательные
            {
                "apiVersion": "1.0.0",
                "timestamp": base_ts,
                "drone": "delivery",
                "drone_id": 1,
                "latitude": 1.0,
                "longitude": 1.0
            },
            # Все поля
            create_telemetry_payload(timestamp=base_ts + 100, drone_id=2)
        ]
        
        insert_telemetry_records(records, api_headers)
        wait_for_elastic_sync()
        
        resp = fetch_telemetry(bearer_headers, limit=10)
        assert resp.status_code == 200
        logs = resp.json()
        
        assert len(logs) == 2
        # Обе записи должны вернуться без ошибок
        drone_ids = {log["drone_id"] for log in logs}
        assert drone_ids == {1, 2}

    def test_TC_TEL_020_orientation_boundaries(self, bearer_headers: Dict[str, str], api_headers: Dict[str, str]):
        """TC-TEL-020: Обработка записей с пограничными значениями ориентации."""
        base_ts = get_timestamp_ms()
        test_cases = [
            {"pitch": -90, "roll": -180, "course": 0},
            {"pitch": 90, "roll": 180, "course": 360},
        ]
        
        records = [
            create_telemetry_payload(
                timestamp=base_ts + i*100,
                pitch=tc["pitch"],
                roll=tc["roll"],
                course=tc["course"],
                drone_id=i
            )
            for i, tc in enumerate(test_cases, start=1)
        ]
        
        insert_telemetry_records(records, api_headers)
        wait_for_elastic_sync()
        
        resp = fetch_telemetry(bearer_headers, limit=10)
        assert resp.status_code == 200
        logs = resp.json()
        
        returned_pitches = {log["pitch"] for log in logs}
        expected_pitches = {tc["pitch"] for tc in test_cases}
        assert returned_pitches == expected_pitches
        
        returned_rolls = {log["roll"] for log in logs}
        expected_rolls = {tc["roll"] for tc in test_cases}
        assert returned_rolls == expected_rolls
        
        returned_courses = {log["course"] for log in logs}
        expected_courses = {tc["course"] for tc in test_cases}
        assert returned_courses == expected_courses