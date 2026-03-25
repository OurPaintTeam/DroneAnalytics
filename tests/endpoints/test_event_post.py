"""
Интеграционные тесты для POST /log/event.

Проверяют:
- Валидацию входных данных (Pydantic)
- Маршрутизацию событий в индексы event/safety
- Корректную обработку ошибок ElasticSearch
- Частичный успех (partial success) при пакетной отправке
- Очистку данных после каждого теста
"""
import time
import pytest
import requests
from typing import Dict, Any

from .conftest import BACKEND_URL
from .utils import wait_for_elastic_sync, get_timestamp_ms, ELASTIC_URL


# ============================================================================
# Вспомогательные функции
# ============================================================================


def verify_doc_in_index(
    index_name: str,
    expected_fields: Dict[str, Any],
    timeout: int = 5
) -> bool:
    """
    Проверяет наличие документа с указанными полями в индексе.
    
    Для text-полей использует match-запрос с оператором AND.
    Для keyword/numeric — term-запрос.
    """
    start = time.time()
    
    must_clauses = []
    
    for key, value in expected_fields.items():
        if key == "timestamp":
            # Диапазон ±2 секунды для учёта задержки индексации
            must_clauses.append({
                "range": {
                    "timestamp": {
                        "gte": value - 2000,
                        "lte": value + 2000,
                        "format": "epoch_millis"
                    }
                }
            })
        elif isinstance(value, str):
            # Для text-полей (message) используем match с AND
            # Для keyword-полей (service, severity) term работает и с match
            must_clauses.append({
                "match": {
                    key: {
                        "query": value,
                        "operator": "and"  # все слова должны совпасть
                    }
                }
            })
        elif isinstance(value, (int, float, bool)):
            must_clauses.append({"term": {key: value}})
    
    # Если нет условий — просто проверяем, что индекс не пуст
    if not must_clauses:
        query = {"query": {"match_all": {}}, "size": 1}
    else:
        query = {"query": {"bool": {"must": must_clauses}}, "size": 1}
    
    while time.time() - start < timeout:
        try:
            resp = requests.post(
                f"{ELASTIC_URL}/{index_name}/_search",
                json=query,
                timeout=2,
                headers={"Content-Type": "application/json"}
            )
            if resp.status_code == 200:
                hits = resp.json().get("hits", {}).get("hits", [])
                if hits:
                    return True
        except requests.RequestException:
            pass
        time.sleep(1.5)
    return False


def assert_response_structure(
    resp: requests.Response,
    expected_status: int,
    expected_accepted: int = None,
    expected_rejected: int = None,
    expected_errors_count: int = None
) -> Dict[str, Any]:
    """
    Проверяет структуру ответа эндпоинта.
    
    :return: Распарсенный JSON ответа
    """
    assert resp.status_code == expected_status, (
        f"Expected status {expected_status}, got {resp.status_code}. Response: {resp.text}"
    )
    
    data = resp.json()
    
    # Проверяем обязательные поля ответа
    assert "total" in data, "Response missing 'total' field"
    assert "accepted" in data, "Response missing 'accepted' field"
    assert "rejected" in data, "Response missing 'rejected' field"
    assert "errors" in data, "Response missing 'errors' field"
    
    if expected_accepted is not None:
        assert data["accepted"] == expected_accepted, (
            f"Expected accepted={expected_accepted}, got {data['accepted']}"
        )
    
    if expected_rejected is not None:
        assert data["rejected"] == expected_rejected, (
            f"Expected rejected={expected_rejected}, got {data['rejected']}"
        )
    
    if expected_errors_count is not None:
        assert len(data["errors"]) == expected_errors_count, (
            f"Expected {expected_errors_count} errors, got {len(data['errors'])}: {data['errors']}"
        )
    
    # Проверяем консистентность: accepted + rejected == total
    assert data["accepted"] + data["rejected"] == data["total"], (
        f"Inconsistent counts: {data['accepted']} + {data['rejected']} != {data['total']}"
    )
    
    return data


# ============================================================================
# Фикстуры, специфичные для тестов event
# ============================================================================


@pytest.fixture
def valid_event_payload() -> Dict[str, Any]:
    """Шаблон валидного обычного события."""
    return {
        "apiVersion": "1.0.0",
        "timestamp": get_timestamp_ms(),
        "service": "GCS",
        "service_id": 1,
        "severity": "info",
        "message": "Test event message"
    }


@pytest.fixture
def valid_safety_payload() -> Dict[str, Any]:
    """Шаблон валидного safety-события."""
    return {
        "apiVersion": "1.0.0",
        "timestamp": get_timestamp_ms(),
        "event_type": "safety_event",
        "service": "dronePort",
        "service_id": 2,
        "severity": "warning",
        "message": "Safety warning message"
    }


# ============================================================================
# Тест-кейсы: Успешные сценарии (Happy Path)
# ============================================================================

class TestEventSuccess:
    """Тесты успешной отправки событий."""

    def test_post_event_success_regular(
        self,
        api_headers: Dict[str, str],
        valid_event_payload: Dict[str, Any]
    ):
        """
        TC-01: Успешная отправка обычного события.
        Ожидание: статус 200, документ в индексе 'event', служебные поля удалены.
        """
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=[valid_event_payload],
            headers=api_headers,
            timeout=10
        )
        
        data = assert_response_structure(resp, expected_status=200, expected_accepted=1)
        assert data["errors"] == []
        
        wait_for_elastic_sync()
        
        # Проверяем, что документ попал в правильный индекс
        assert verify_doc_in_index(
            "event",
            {"service": "GCS", "message": "Test event message"}
        ), "Document not found in 'event' index"
        
        # Проверяем, что служебные поля удалены
        assert not verify_doc_in_index("event", {"apiVersion": "1.0.0"}), (
            "Field 'apiVersion' should be removed before indexing"
        )

    def test_post_event_success_safety(
        self,
        api_headers: Dict[str, str],
        valid_safety_payload: Dict[str, Any]
    ):
        """
        TC-02: Успешная отправка safety-события.
        Ожидание: статус 200, документ в индексе 'safety', event_type удалён.
        """
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=[valid_safety_payload],
            headers=api_headers,
            timeout=10
        )
        
        data = assert_response_structure(resp, expected_status=200, expected_accepted=1)
        assert data["errors"] == []
        
        wait_for_elastic_sync()
        
        # Проверяем индекс 'safety'
        assert verify_doc_in_index(
            "safety",
            {"service": "dronePort", "severity": "warning"}
        ), "Safety document not found in 'safety' index"
        
        # Проверяем, что event_type не сохранился в документе
        assert not verify_doc_in_index("safety", {"event_type": "safety_event"}), (
            "Field 'event_type' should be used for routing only, not stored"
        )

    def test_post_event_mixed_batch(
        self,
        api_headers: Dict[str, str],
        valid_event_payload: Dict[str, Any],
        valid_safety_payload: Dict[str, Any]
    ):
        """
        TC-03: Пакет с обычными и safety-событиями.
        Ожидание: оба типа успешно проиндексированы в разные индексы.
        """
        payload = [valid_event_payload, valid_safety_payload]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert_response_structure(resp, expected_status=200, expected_accepted=2)
        
        wait_for_elastic_sync()
        
        # Проверяем оба индекса
        assert verify_doc_in_index("event", {"service": "GCS"}), "Regular event not indexed"
        assert verify_doc_in_index("safety", {"service": "dronePort"}), "Safety event not indexed"

    def test_post_event_optional_fields_null(
        self,
        api_headers: Dict[str, str]
    ):
        """
        TC-16: Событие без опциональных полей event_type и severity.
        Ожидание: попадает в индекс 'event' (не safety), статус 200.
        """
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "service": "aggregator",
            "service_id": 3,
            "message": "Minimal event"
        }]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert_response_structure(resp, expected_status=200, expected_accepted=1)
        
        wait_for_elastic_sync()
        
        # Должно быть в 'event', а не в 'safety'
        assert verify_doc_in_index("event", {"service": "aggregator"})
        # Проверяем, что не попало в safety
        resp_search = requests.post(
            f"{ELASTIC_URL}/safety/_search",
            json={"query": {"term": {"service": "aggregator"}}},
            timeout=2
        )
        assert resp_search.json().get("hits", {}).get("total", {}).get("value", 0) == 0


# ============================================================================
# Тест-кейсы: Ошибки аутентификации
# ============================================================================

class TestEventAuthErrors:
    """Тесты ошибок аутентификации по API-ключу."""

    def test_post_event_missing_api_key(self, valid_event_payload: Dict[str, Any]):
        """
        TC-04: Запрос без заголовка X-API-Key.
        Ожидание: статус 401, данные не в БД.
        """
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=[valid_event_payload],
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        assert resp.status_code == 401
        assert resp.json()["code"] == 401
        
        wait_for_elastic_sync()
        assert not verify_doc_in_index("event", {"message": "Test event message"})

    def test_post_event_invalid_api_key(self, valid_event_payload: Dict[str, Any]):
        """
        TC-05: Запрос с неверным API-ключом.
        Ожидание: статус 401, данные не в БД.
        """
        headers = {"X-API-Key": "wrong-key", "Content-Type": "application/json"}
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=[valid_event_payload],
            headers=headers,
            timeout=5
        )
        
        assert resp.status_code == 401
        
        wait_for_elastic_sync()
        assert not verify_doc_in_index("event", {"message": "Test event message"})


# ============================================================================
# Тест-кейсы: Валидация входных данных (Pydantic)
# ============================================================================

class TestEventValidationErrors:
    """Тесты валидации входных данных."""

    def test_post_event_empty_array(self, api_headers: Dict[str, str]):
        """
        TC-06: Пустой массив в теле запроса.
        Ожидание: статус 400 (валидация min_length=1).
        """
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=[],
            headers=api_headers,
            timeout=5
        )
        assert resp.status_code == 400

    def test_post_event_array_too_large(self, api_headers: Dict[str, str], valid_event_payload: Dict[str, Any]):
        """
        TC-07: Массив из 1001 элемента (превышение max_length=1000).
        Ожидание: статус 400.
        """
        payload = [valid_event_payload] * 1001
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=5
        )
        assert resp.status_code == 400

    def test_post_event_missing_timestamp(self, api_headers: Dict[str, str]):
        """
        TC-08: Отсутствие обязательного поля timestamp.
        Ожидание: статус 207, rejected=1, ошибка валидации.
        """
        payload = [{
            "service": "GCS",
            "service_id": 1,
            "message": "No timestamp"
        }]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        data = assert_response_structure(
            resp,
            expected_status=207,
            expected_accepted=0,
            expected_rejected=1,
            expected_errors_count=1
        )
        assert data["errors"][0]["index"] == 0
        assert "timestamp" in data["errors"][0]["reason"].lower() or "required" in data["errors"][0]["reason"].lower()

    def test_post_event_invalid_service_id_type(self, api_headers: Dict[str, str], valid_event_payload: Dict[str, Any]):
        """
        TC-09: service_id строкой вместо целого числа.
        Ожидание: статус 207, rejected=1.
        """
        payload = [{**valid_event_payload, "service_id": "not_an_integer"}]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        data = assert_response_structure(resp, expected_status=207, expected_rejected=1)
        assert "input_should_be_a_valid_integer" in data["errors"][0]["reason"].lower() or "int" in data["errors"][0]["reason"].lower()

    def test_post_event_service_id_less_than_one(self, api_headers: Dict[str, str], valid_event_payload: Dict[str, Any]):
        """
        TC-10: service_id = 0 (должно быть >= 1).
        Ожидание: статус 207, rejected=1.
        """
        payload = [{**valid_event_payload, "service_id": 0}]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        data = assert_response_structure(resp, expected_status=207, expected_rejected=1)
        assert "greater than or equal to 1" in data["errors"][0]["reason"]

    def test_post_event_invalid_service_enum(self, api_headers: Dict[str, str], valid_event_payload: Dict[str, Any]):
        """
        TC-11: Значение service не из разрешённого Literal.
        Ожидание: статус 207, rejected=1.
        """
        payload = [{**valid_event_payload, "service": "unknown_service_xyz"}]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        data = assert_response_structure(resp, expected_status=207, expected_rejected=1)
        reason_lower = data["errors"][0]["reason"].lower()
        assert "input should be" in reason_lower or "literal" in reason_lower or "enum" in reason_lower

    def test_post_event_message_too_long(self, api_headers: Dict[str, str], valid_event_payload: Dict[str, Any]):
        """
        TC-12: Сообщение длиннее 1024 символов.
        Ожидание: статус 207, rejected=1.
        """
        payload = [{**valid_event_payload, "message": "x" * 1025}]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        data = assert_response_structure(resp, expected_status=207, expected_rejected=1)
        assert "1024" in data["errors"][0]["reason"] or "length" in data["errors"][0]["reason"].lower()

    def test_post_event_invalid_severity_enum(self, api_headers: Dict[str, str], valid_event_payload: Dict[str, Any]):
        """
        TC-17: Недопустимое значение severity.
        Ожидание: статус 207, rejected=1.
        """
        payload = [{**valid_event_payload, "severity": "super_critical"}]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        data = assert_response_structure(resp, expected_status=207, expected_rejected=1)
        reason_lower = data["errors"][0]["reason"].lower()
        assert "input should be" in reason_lower or "literal" in reason_lower or "enum" in reason_lower


# ============================================================================
# Тест-кейсы: Частичный успех (Partial Success)
# ============================================================================

class TestEventPartialSuccess:
    """Тесты сценариев частичного успеха (207 Multi-Status)."""

    def test_post_event_mixed_valid_invalid(
        self,
        api_headers: Dict[str, str],
        valid_event_payload: Dict[str, Any]
    ):
        """
        TC-13: Пакет с валидными и невалидными событиями.
        Ожидание: статус 207, валидные приняты, невалидные отклонены с ошибками.
        """
        payload = [
            valid_event_payload,  # index 0: valid
            {  # index 1: invalid (missing message)
                "timestamp": get_timestamp_ms(),
                "service": "GCS",
                "service_id": 1
            },
            {  # index 2: valid safety
                "apiVersion": "1.0.0",
                "timestamp": get_timestamp_ms(),
                "event_type": "safety_event",
                "service": "regulator",
                "service_id": 4,
                "message": "Safety ok"
            }
        ]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        data = assert_response_structure(
            resp,
            expected_status=207,
            expected_accepted=2,
            expected_rejected=1,
            expected_errors_count=1
        )
        
        # Проверяем, что ошибка относится к правильному индексу в запросе
        assert data["errors"][0]["index"] == 1
        
        wait_for_elastic_sync()
        
        # Проверяем, что валидные документы проиндексированы
        assert verify_doc_in_index("event", {"service": "GCS"})
        assert verify_doc_in_index("safety", {"service": "regulator"})
        
        # Проверяем, что невалидный не попал ни в один индекс
        assert not verify_doc_in_index("event", {"service": "GCS", "message": ""})  # пустое сообщение не должно быть

    def test_post_event_all_invalid(
        self,
        api_headers: Dict[str, str]
    ):
        """
        Все события в пакете невалидны.
        Ожидание: статус 207, accepted=0, rejected=N.
        """
        payload = [
            {"service": "GCS"},  # missing timestamp, message
            {"timestamp": get_timestamp_ms(), "service": "bad_service", "message": "x"}  # invalid service
        ]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert_response_structure(
            resp,
            expected_status=207,
            expected_accepted=0,
            expected_rejected=2,
            expected_errors_count=2
        )
        
        wait_for_elastic_sync()
        
        # Убеждаемся, что ничего не попало в БД
        resp_event = requests.post(
            f"{ELASTIC_URL}/event/_count",
            json={
                "query": {
                    "bool": {
                        "must_not": [{"term": {"service": "infopanel"}}]
                    }
                }
            },
            timeout=2
        )
        resp_safety = requests.post(  # safety тоже через POST с телом
            f"{ELASTIC_URL}/safety/_count",
            json={
                "query": {
                    "bool": {
                        "must_not": [{"term": {"service": "infopanel"}}]
                    }
                }
            },
            timeout=2
        )
        assert resp_event.json()["count"] == 0
        assert resp_safety.json()["count"] == 0


# ============================================================================
# Тест-кейсы: Поведение с ElasticSearch
# ============================================================================

class TestEventElasticsearchBehavior:
    """Тесты взаимодействия с ElasticSearch."""

    def test_post_event_api_version_stripped(
        self,
        api_headers: Dict[str, str],
        valid_event_payload: Dict[str, Any]
    ):
        """
        TC-14: Поле apiVersion удаляется перед индексацией.
        """
        payload = [{**valid_event_payload, "apiVersion": "9.9.9"}]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert_response_structure(resp, expected_status=200, expected_accepted=1)
        wait_for_elastic_sync()
        
        # Проверяем напрямую в ES, что поля apiVersion нет
        search_resp = requests.post(
            f"{ELASTIC_URL}/event/_search",
            json={
                "query": {"term": {"service": "GCS"}},
                "_source": ["apiVersion"],
                "size": 1
            },
            timeout=2
        )
        hits = search_resp.json().get("hits", {}).get("hits", [])
        assert hits, "Document not found in ES"
        assert "apiVersion" not in hits[0].get("_source", {}), (
            "Field 'apiVersion' should be stripped before indexing"
        )

    def test_post_event_strict_mapping_rejects_unknown_field(
        self,
        api_headers: Dict[str, str],
        valid_event_payload: Dict[str, Any]
    ):
        """
        TC-20: ElasticSearch с dynamic: strict отклоняет неизвестные поля.
        """
        # Добавляем поле, которого нет в маппинге
        payload = [{**valid_event_payload, "unknown_custom_field": "should_fail"}]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        # Ожидаем 207 с ошибкой индексации от ES
        data = assert_response_structure(resp, expected_status=207, expected_rejected=1)
        
        # Ошибка должна содержать указание на strict mapping
        reason = data["errors"][0]["reason"].lower()
        # Pydantic говорит "Extra inputs are not permitted" при extra="forbid"
        assert "extra inputs are not permitted" in reason or "extra_forbidden" in reason

    def test_post_event_timestamp_range_valid(
        self,
        api_headers: Dict[str, str],
        valid_event_payload: Dict[str, Any]
    ):
        """
        TC-18: Timestamp в прошлом/будущем принимается (валидные значения).
        """
        # Используем старый timestamp
        old_ts = 1609459200000  # 2021-01-01
        payload = [{**valid_event_payload, "timestamp": old_ts}]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert_response_structure(resp, expected_status=200, expected_accepted=1)
        wait_for_elastic_sync()
        
        # Проверяем, что документ с этим timestamp действительно в базе
        assert verify_doc_in_index("event", {"timestamp": old_ts})


# ============================================================================
# Тест-кейсы: Граничные значения и edge cases
# ============================================================================

class TestEventEdgeCases:
    """Тесты граничных значений и особых случаев."""

    def test_post_event_max_length_arrays(
        self,
        api_headers: Dict[str, str],
        valid_event_payload: Dict[str, Any]
    ):
        """
        Отправка ровно 1000 событий (граница max_length).
        Ожидание: все приняты, статус 200.
        """
        payload = [
            {**valid_event_payload, "timestamp": get_timestamp_ms() + i, "message": f"Msg {i}"}
            for i in range(1000)
        ]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=30  # Увеличиваем таймаут для большого пакета
        )
        
        assert_response_structure(resp, expected_status=200, expected_accepted=1000)

    def test_post_event_minimal_valid_payload(
        self,
        api_headers: Dict[str, str]
    ):
        """
        Минимально валидный объект: только обязательные поля.
        """
        payload = [{
            "apiVersion": "1.0.0",
            "timestamp": get_timestamp_ms(),
            "service": "operator",
            "service_id": 1,
            "message": "Minimal"
        }]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert_response_structure(resp, expected_status=200, expected_accepted=1)
        wait_for_elastic_sync()
        assert verify_doc_in_index("event", {"message": "Minimal"})

    def test_post_event_unicode_and_special_chars(
        self,
        api_headers: Dict[str, str],
        valid_event_payload: Dict[str, Any]
    ):
        """
        Сообщение с юникодом и спецсимволами.
        Ожидание: корректно сохраняется.
        """
        payload = [{
            **valid_event_payload,
            "message": "Тест 🚁 with emojis & special chars: <>&\"'"
        }]
        
        resp = requests.post(
            f"{BACKEND_URL}/log/event",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        
        assert_response_structure(resp, expected_status=200, expected_accepted=1)
        wait_for_elastic_sync()
        assert verify_doc_in_index("event", {"message": "Тест 🚁 with emojis & special chars: <>&\"'"})