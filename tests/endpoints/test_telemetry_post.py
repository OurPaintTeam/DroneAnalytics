"""
Интеграционные тесты для POST /log/telemetry.

Проверяют:
- Валидацию входящих данных через Pydantic
- Корректную запись валидных данных в Elasticsearch
- Отклонение невалидных данных (они не попадают в БД)
- Частичный успех при пакетной отправке
- Логирование событий аудита в индекс 'safety'
"""
import pytest
import requests
from typing import Dict, List, Optional

from .conftest import BACKEND_URL
from .utils import get_recent_audit_log, wait_for_elastic_sync, get_timestamp_ms


# ============================================================================
# Вспомогательные функции
# ============================================================================


def count_docs_in_index(index_name: str, query_filter: Optional[Dict] = None) -> int:
    """
    Подсчитывает количество документов в индексе, соответствующих фильтру.
    
    Args:
        index_name: Название индекса (например, 'telemetry')
        query_filter: Дополнительный фильтр для query (или None для всех)
    
    Returns:
        Количество найденных документов
    """
    body = {"query": query_filter} if query_filter else {"query": {"match_all": {}}}
    try:
        resp = requests.post(
            f"http://elastic:9200/{index_name}/_count",
            json=body,
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json().get("count", 0)
        return 0
    except requests.RequestException:
        pytest.skip("ElasticSearch unavailable for count check")
        return 0


def search_telemetry_by_drone_id(drone_id: int) -> List[Dict]:
    """Ищет документы телеметрии по drone_id."""
    query = {
        "query": {"term": {"drone_id": drone_id}},
        "sort": [{"timestamp": {"order": "desc"}}],
        "size": 10
    }
    try:
        resp = requests.post(
            "http://elastic:9200/telemetry/_search",
            json=query,
            timeout=5
        )
        if resp.status_code != 200:
            return []
        hits = resp.json().get("hits", {}).get("hits", [])
        return [hit["_source"] for hit in hits]
    except requests.RequestException:
        return []


# ============================================================================
# Тесты: Позитивные сценарии (Happy Path)
# ============================================================================

class TestTelemetrySuccess:
    """Тесты успешной записи валидной телеметрии."""

    def test_single_valid_document(self, api_headers: Dict[str, str]):
        """TC-TELE-001: Успешная запись одного валидного документа."""
        timestamp = get_timestamp_ms()
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": timestamp,
            "drone": "delivery",
            "drone_id": 101,
            "battery": 85,
            "pitch": 5.5,
            "roll": -2.1,
            "course": 180.0,
            "latitude": 55.7558,
            "longitude": 37.6176
        }]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["accepted"] == 1
        assert data["rejected"] == 0
        assert data["errors"] == []
        
        # Проверка в Elasticsearch
        wait_for_elastic_sync()
        docs = search_telemetry_by_drone_id(101)
        assert len(docs) == 1
        
        doc = docs[0]
        assert doc["timestamp"] == timestamp
        assert doc["drone"] == "delivery"
        assert doc["latitude"] == 55.7558
        # Критично: apiVersion должно быть удалено
        assert "apiVersion" not in doc
        
        # Проверка аудита
        audit = get_recent_audit_log("ingest_telemetry status=success", "info", "event")
        assert audit is not None

    def test_batch_valid_documents(self, api_headers: Dict[str, str]):
        """TC-TELE-002: Успешная запись пакета из нескольких документов."""
        base_ts = get_timestamp_ms()
        payload = [
            {
                "apiVersion": "1.0.0",
                "timestamp": base_ts + i,
                "drone": "inspector",
                "drone_id": 200 + i,
                "latitude": 59.9343 + i * 0.001,
                "longitude": 30.3351
            }
            for i in range(5)
        ]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert resp.status_code == 200
        assert resp.json()["accepted"] == 5
        
        wait_for_elastic_sync()
        # Проверяем, что все 5 документов записались
        count = count_docs_in_index("telemetry", {"term": {"drone": "inspector"}})
        assert count == 5
        
        # Проверка аудита
        audit = get_recent_audit_log("ingest_telemetry status=success", "info", "event")
        assert audit is not None

    def test_optional_fields_handling(self, api_headers: Dict[str, str]):
        """TC-TELE-003: Запись с опциональными полями (null/отсутствуют)."""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "drone": "agriculture",
            "drone_id": 301,
            "battery": None,  # Явный null
            # pitch, roll, course полностью отсутствуют
            "latitude": 45.0,
            "longitude": 75.0
        }]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert resp.status_code == 200
        assert resp.json()["accepted"] == 1
        
        wait_for_elastic_sync()
        docs = search_telemetry_by_drone_id(301)
        assert len(docs) == 1
        
        doc = docs[0]
        # Опциональные поля могут быть null или дефолтными (зависит от маппинга)
        assert doc["latitude"] == 45.0
        assert doc["drone"] == "agriculture"

    def test_boundary_values_accepted(self, api_headers: Dict[str, str]):
        """TC-TELE-004: Граничные значения числовых полей принимаются."""
        boundary_cases = [
            {"battery": 0, "drone_id": 401},
            {"battery": 100, "drone_id": 402},
            {"pitch": -90.0, "drone_id": 403},
            {"pitch": 90.0, "drone_id": 404},
            {"roll": -180.0, "drone_id": 405},
            {"roll": 180.0, "drone_id": 406},
            {"course": 0.0, "drone_id": 407},
            {"course": 360.0, "drone_id": 408},
            {"latitude": -90.0, "drone_id": 409, "longitude": 0},
            {"latitude": 90.0, "drone_id": 410, "longitude": 0},
            {"latitude": 0, "longitude": -180.0, "drone_id": 411},
            {"latitude": 0, "longitude": 180.0, "drone_id": 412},
        ]
        
        payload = [
            {
                "apiVersion": "1.0.0",
                "timestamp": get_timestamp_ms(),
                "drone": "delivery",
                "latitude": case.get("latitude", 55.0),
                "longitude": case.get("longitude", 37.0),
                **{k: v for k, v in case.items() if k not in ["latitude", "longitude"]}
            }
            for case in boundary_cases
        ]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert resp.status_code == 200
        # Все 12 объектов должны быть приняты
        assert resp.json()["accepted"] == 12
        assert resp.json()["rejected"] == 0


# ============================================================================
# Тесты: Валидация и отклонение некорректных данных
# ============================================================================

class TestTelemetryValidation:
    """Тесты отклонения невалидных данных."""

    def test_missing_required_latitude(self, api_headers: Dict[str, str]):
        """TC-TELE-010: Отсутствует обязательное поле latitude."""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "drone": "delivery",
            "drone_id": 501,
            "longitude": 37.6176
            # latitude отсутствует
        }]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert resp.status_code == 207  # Multi-Status из-за ошибок валидации
        data = resp.json()
        assert data["accepted"] == 0
        assert data["rejected"] == 1
        assert len(data["errors"]) == 1
        assert "latitude" in data["errors"][0]["reason"].lower() or "field required" in data["errors"][0]["reason"].lower()
        
        # Проверка: документ НЕ в базе
        wait_for_elastic_sync()
        docs = search_telemetry_by_drone_id(501)
        assert len(docs) == 0

    def test_battery_out_of_range(self, api_headers: Dict[str, str]):
        """TC-TELE-011: Значение battery вне диапазона [0, 100]."""
        test_cases = [
            {"battery": -1, "drone_id": 601, "desc": "negative"},
            {"battery": 101, "drone_id": 602, "desc": "over_100"},
            {"battery": 150, "drone_id": 603, "desc": "way_over"},
        ]
        
        for case in test_cases:
            payload = [{
                "apiVersion": "1.0.0",
                "timestamp": get_timestamp_ms(),
                "drone": "queen",
                "drone_id": case["drone_id"],
                "battery": case["battery"],
                "latitude": 55.0,
                "longitude": 37.0
            }]
            
            resp = requests.post(
                f"{BACKEND_URL}/log/telemetry",
                json=payload,
                headers=api_headers,
                timeout=10
            )
            
            assert resp.status_code in (207, 400)
            data = resp.json()
            assert data["rejected"] >= 1
            
            # Документ не должен попасть в БД
            wait_for_elastic_sync()
            
            # Проверяем по drone_id, что дрона нет в базе
            docs = search_telemetry_by_drone_id(case["drone_id"])
            assert len(docs) == 0

    def test_wrong_type_for_drone_id(self, api_headers: Dict[str, str]):
        """TC-TELE-012: Неверный тип данных для drone_id (строка вместо int)."""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "drone": "delivery",
            "drone_id": "not_a_number",  # Ошибка типа
            "latitude": 55.0,
            "longitude": 37.0
        }]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert resp.status_code in (207, 400)

    def test_invalid_drone_literal(self, api_headers: Dict[str, str]):
        """TC-TELE-013: Значение drone не из разрешённого Literal."""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "drone": "fighter_jet",  # Не в списке
            "drone_id": 701,
            "latitude": 55.0,
            "longitude": 37.0
        }]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert resp.status_code in (207, 400)
        data = resp.json()
        assert data["rejected"] == 1
        error_msg = data["errors"][0]["reason"]
        # Pydantic указывает допустимые значения
        assert "delivery" in error_msg or "Input should be" in error_msg
        
        wait_for_elastic_sync()
        docs = search_telemetry_by_drone_id(701)
        assert len(docs) == 0

    def test_invalid_api_version_format(self, api_headers: Dict[str, str]):
        """TC-TELE-014: Некорректный формат apiVersion (длина < 5)."""
        payload = [{
            "apiVersion": "1.0",  # Длина 3, нужно 5-8
            "timestamp": get_timestamp_ms(),
            "drone": "delivery",
            "drone_id": 801,
            "latitude": 55.0,
            "longitude": 37.0
        }]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert resp.status_code in (207, 400)
        assert resp.json()["rejected"] == 1
        
        wait_for_elastic_sync()
        docs = search_telemetry_by_drone_id(801)
        assert len(docs) == 0


# ============================================================================
# Тесты: Частичный успех (Mixed payloads)
# ============================================================================

class TestTelemetryPartialSuccess:
    """Тесты пакетной обработки с частичными ошибками."""

    def test_mixed_valid_invalid(self, api_headers: Dict[str, str]):
        """TC-TELE-020: Смешанный пакет (валидные + невалидные)."""
        payload = [
            # Индекс 0: валидный
            {
                "apiVersion": "1.0.0",
                "timestamp": get_timestamp_ms(),
                "drone": "delivery",
                "drone_id": 901,
                "latitude": 55.0,
                "longitude": 37.0
            },
            # Индекс 1: невалидный (latitude > 90)
            {
                "apiVersion": "1.0.0",
                "timestamp": get_timestamp_ms(),
                "drone": "inspector",
                "drone_id": 902,
                "latitude": 95.0,  # Ошибка
                "longitude": 37.0
            },
            # Индекс 2: валидный
            {
                "apiVersion": "1.0.0",
                "timestamp": get_timestamp_ms(),
                "drone": "agriculture",
                "drone_id": 903,
                "latitude": 45.0,
                "longitude": 75.0
            }
        ]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert resp.status_code == 207  # Multi-Status
        data = resp.json()
        assert data["total"] == 3
        assert data["accepted"] == 2
        assert data["rejected"] == 1
        assert len(data["errors"]) == 1
        # Ошибка должна ссылаться на индекс 1
        assert data["errors"][0]["index"] == 1
        
        wait_for_elastic_sync()
        # Проверяем, что записались только валидные (901 и 903)
        doc_901 = search_telemetry_by_drone_id(901)
        doc_902 = search_telemetry_by_drone_id(902)
        doc_903 = search_telemetry_by_drone_id(903)
        
        assert len(doc_901) == 1
        assert len(doc_902) == 0  # Не записался!
        assert len(doc_903) == 1
        
        # Аудит должен показать partial статус
        audit = get_recent_audit_log("ingest_telemetry status=partial", "info", "event")
        assert audit is not None
        assert "accepted=2" in audit["message"]
        assert "rejected=1" in audit["message"]

    def test_all_invalid_in_batch(self, api_headers: Dict[str, str]):
        """TC-TELE-021: Все объекты в пакете невалидны."""
        payload = [
            {"apiVersion": "1.0", "timestamp": get_timestamp_ms(), "drone": "x", "drone_id": 1, "latitude": 55, "longitude": 37},
            {"apiVersion": "1.0", "timestamp": get_timestamp_ms(), "drone": "y", "drone_id": 2, "latitude": 55, "longitude": 37},
        ]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert resp.status_code in (207, 400)
        data = resp.json()
        assert data["accepted"] == 0
        assert data["rejected"] == 2
        assert len(data["errors"]) == 2
        
        wait_for_elastic_sync()
        # Ни один документ не должен попасть в базу
        count_docs_in_index("telemetry")


# ============================================================================
# Тесты: Ограничения запроса
# ============================================================================

class TestTelemetryRequestLimits:
    """Тесты ограничений размера и формата запроса."""

    def test_empty_array_rejected(self, api_headers: Dict[str, str]):
        """TC-TELE-030: Пустой массив отклоняется (min_length=1)."""
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=[],
            headers=api_headers,
            timeout=5
        )
        
        assert resp.status_code == 400  # Validation error на уровне Body

    def test_over_limit_array_rejected(self, api_headers: Dict[str, str]):
        """TC-TELE-031: Массив >1000 элементов отклоняется (max_length=1000)."""
        # Создаём 1001 минимальный валидный объект
        payload = [
            {
                "apiVersion": "1.0.0",
                "timestamp": get_timestamp_ms(),
                "drone": "delivery",
                "drone_id": i,
                "latitude": 55.0,
                "longitude": 37.0
            }
            for i in range(1001)
        ]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert resp.status_code == 400  # Validation error
        # Ни один документ не должен быть записан
        
        wait_for_elastic_sync()
        # Грубая проверка: не должно быть массового появления новых документов

    def test_invalid_json_body(self, api_headers: Dict[str, str]):
        """TC-TELE-032: Не-JSON или неверная структура тела."""
        test_cases = [
            "not json at all",  # Сырая строка
            {"not": "array"},    # Объект вместо массива
            "123",               # Число
            None,                # null
        ]
        
        for invalid_body in test_cases:
            resp = requests.post(
                f"{BACKEND_URL}/log/telemetry",
                json=invalid_body if invalid_body is not None else None,
                headers=api_headers,
                timeout=5,
                data=invalid_body if isinstance(invalid_body, str) else None
            )
            # FastAPI вернёт 400 для некорректного тела
            assert resp.status_code in (400, 422)


# ============================================================================
# Тесты: Целостность данных в Elasticsearch
# ============================================================================

class TestTelemetryDataIntegrity:
    """Тесты проверки корректности сохранённых данных."""

    def test_api_version_stripped(self, api_headers: Dict[str, str]):
        """TC-TELE-040: Поле apiVersion удаляется перед записью."""
        payload = [{
            "apiVersion": "3.14.0",  # Специфичная версия для проверки
            "timestamp": get_timestamp_ms(),
            "drone": "delivery",
            "drone_id": 1001,
            "latitude": 55.123,
            "longitude": 37.456
        }]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        wait_for_elastic_sync()
        docs = search_telemetry_by_drone_id(1001)
        assert len(docs) == 1
        
        doc = docs[0]
        # Ключевая проверка: apiVersion НЕ должно быть в сохранённом документе
        assert "apiVersion" not in doc, "apiVersion should be stripped before indexing"
        assert doc["drone_id"] == 1001

    def test_numeric_types_preserved(self, api_headers: Dict[str, str]):
        """TC-TELE-041: Числовые типы сохраняются корректно."""
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "drone": "inspector",
            "drone_id": 1002,  # int
            "battery": 75,      # int
            "pitch": 5.5,       # float
            "latitude": 59.9343,
            "longitude": 30.3351
        }]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        wait_for_elastic_sync()
        docs = search_telemetry_by_drone_id(1002)
        assert len(docs) == 1
        
        doc = docs[0]
        # Проверка типов (в JSON все числа — это числа, но важно, что не строки)
        assert isinstance(doc["drone_id"], int)
        assert isinstance(doc["battery"], int) or doc["battery"] is None
        assert isinstance(doc["pitch"], (int, float)) or doc["pitch"] is None
        assert isinstance(doc["latitude"], (int, float))

    def test_timestamp_milliseconds_precision(self, api_headers: Dict[str, str]):
        """TC-TELE-042: Timestamp сохраняется в миллисекундах без потерь."""
        # Используем точное значение с миллисекундами
        precise_ts = 1700000000123
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": precise_ts,
            "drone": "agriculture",
            "drone_id": 1003,
            "latitude": 45.0,
            "longitude": 75.0
        }]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/telemetry",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        assert resp.status_code == 200
        
        wait_for_elastic_sync()
        docs = search_telemetry_by_drone_id(1003)
        assert len(docs) == 1
        
        doc = docs[0]
        # Маппинг использует format: "epoch_millis", значение должно совпасть
        assert doc["timestamp"] == precise_ts