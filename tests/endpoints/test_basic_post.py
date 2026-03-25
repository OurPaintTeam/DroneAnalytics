"""
Интеграционные тесты для POST /log/basic.

Проверяют:
- Валидацию входных данных через Pydantic
- Корректность ответов (200/207/400)
- Фактическое состояние индекса 'basic' в ElasticSearch
- Частичный успех при пакетной отправке
"""
import pytest
import requests
from typing import Dict, Any, List

from .conftest import BACKEND_URL, API_KEY
from .utils import wait_for_elastic_sync, ELASTIC_URL


# ============================================================================
# Вспомогательные функции
# ============================================================================


def get_basic_logs_from_es(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Прямой запрос к ElasticSearch для получения документов из индекса 'basic'.
    Используется для верификации фактической записи данных.
    """
    try:
        resp = requests.post(
            f"{ELASTIC_URL}/basic/_search",
            json={
                "size": limit,
                "sort": [{"timestamp": {"order": "asc"}}]
            },
            timeout=5
        )
        if resp.status_code == 200:
            hits = resp.json().get("hits", {}).get("hits", [])
            return [hit["_source"] for hit in hits]
    except requests.RequestException:
        pytest.fail("Failed to query ElasticSearch for verification")
    return []


def count_docs_in_basic_index() -> int:
    """Возвращает количество документов в индексе 'basic'."""
    return len(get_basic_logs_from_es())


# ============================================================================
# Тестовый класс
# ============================================================================

class TestPostLogBasic:
    """Интеграционные тесты для POST /log/basic."""

    # -------------------------------------------------------------------------
    # Успешные сценарии (Happy Path)
    # -------------------------------------------------------------------------

    def test_tc01_single_valid_log(self):
        """TC-01: Успешная запись одного валидного лога."""
        payload = [{
            "timestamp": 1700000000000,
            "message": "Test log"
        }]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=10)
        
        # Проверка ответа
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["accepted"] == 1
        assert data["rejected"] == 0
        assert data["errors"] == []
        
        # Проверка ElasticSearch
        wait_for_elastic_sync()
        docs = get_basic_logs_from_es()
        assert len(docs) == 1
        assert docs[0]["timestamp"] == 1700000000000
        assert docs[0]["message"] == "Test log"

    def test_tc02_multiple_valid_logs(self):
        """TC-02: Успешная запись пакета из нескольких валидных логов."""
        payload = [
            {"timestamp": 1700000000001, "message": "Log one"},
            {"timestamp": 1700000000002, "message": "Log two"},
            {"timestamp": 1700000000003, "message": "Log three"},
            {"timestamp": 1700000000004, "message": "Log four"},
            {"timestamp": 1700000000005, "message": "Log five"},
        ]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=10)
        
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert data["accepted"] == 5
        assert data["rejected"] == 0
        
        wait_for_elastic_sync()
        docs = get_basic_logs_from_es()
        assert len(docs) == 5
        # Проверяем, что все сообщения записаны
        messages = {doc["message"] for doc in docs}
        assert messages == {"Log one", "Log two", "Log three", "Log four", "Log five"}

    # -------------------------------------------------------------------------
    # Валидация: отрицательные сценарии (400 Bad Request)
    # -------------------------------------------------------------------------

    def test_tc03_negative_timestamp(self):
        """TC-03: Отрицательный timestamp (нарушение ge=0)."""
        payload = [{"timestamp": -1, "message": "Invalid"}]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=5)
        
        assert resp.status_code == 207
        
        wait_for_elastic_sync()
        assert count_docs_in_basic_index() == 0

    def test_tc04_empty_message(self):
        """TC-04: Пустое сообщение (нарушение min_length=1)."""
        payload = [{"timestamp": 1700000000000, "message": ""}]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=5)
        
        assert resp.status_code == 207
        wait_for_elastic_sync()
        assert count_docs_in_basic_index() == 0

    def test_tc05_message_too_long(self):
        """TC-05: Сообщение >1024 символов (нарушение max_length)."""
        payload = [{"timestamp": 1700000000000, "message": "x" * 1025}]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=5)
        
        assert resp.status_code == 207
        wait_for_elastic_sync()
        assert count_docs_in_basic_index() == 0

    def test_tc06_missing_message_field(self):
        """TC-06: Отсутствие обязательного поля message."""
        payload = [{"timestamp": 1700000000000}]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=5)
        
        assert resp.status_code == 207
        wait_for_elastic_sync()
        assert count_docs_in_basic_index() == 0

    def test_tc07_extra_field_forbidden(self):
        """TC-07: Наличие лишнего поля (нарушение extra='forbid')."""
        payload = [{
            "timestamp": 1700000000000,
            "message": "Test",
            "extra_field": "bad"
        }]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=5)
        
        assert resp.status_code == 207
        wait_for_elastic_sync()
        assert count_docs_in_basic_index() == 0

    def test_tc14_invalid_timestamp_type(self):
        """TC-14: Некорректный тип данных для timestamp (строка вместо int)."""
        payload = [{"timestamp": "not-an-int", "message": "Test"}]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=5)
        
        assert resp.status_code == 207
        wait_for_elastic_sync()
        assert count_docs_in_basic_index() == 0

    # -------------------------------------------------------------------------
    # Частичный успех (207 Multi-Status)
    # -------------------------------------------------------------------------

    def test_tc08_partial_success_mixed_payload(self):
        """
        TC-08: Частичный успех — смесь валидных и невалидных записей.
        Проверяет, что валидные записи сохраняются, а невалидные отклоняются.
        """
        payload = [
            {"timestamp": -1, "message": "Bad"},  # index 0: invalid
            {"timestamp": 1700000000000, "message": "Good"},  # index 1: valid
            {"timestamp": 1700000000001, "message": ""},  # index 2: invalid (empty message)
            {"timestamp": 1700000000002, "message": "Also Good"},  # index 3: valid
        ]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=10)
        
        # Ожидаем 207 при наличии ошибок
        assert resp.status_code == 207
        data = resp.json()
        assert data["total"] == 4
        assert data["accepted"] == 2
        assert data["rejected"] == 2
        assert len(data["errors"]) == 2
        
        # Проверяем, что ошибки указывают на правильные индексы исходного массива
        error_indices = {err["index"] for err in data["errors"]}
        assert error_indices == {0, 2}
        
        wait_for_elastic_sync()
        docs = get_basic_logs_from_es()
        assert len(docs) == 2
        
        # Проверяем, что записаны только валидные сообщения
        messages = {doc["message"] for doc in docs}
        assert messages == {"Good", "Also Good"}

    # -------------------------------------------------------------------------
    # Валидация массива (параметры тела запроса)
    # -------------------------------------------------------------------------

    def test_tc09_empty_array(self):
        """TC-09: Пустой массив (нарушение min_length=1 для списка)."""
        payload = []
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=5)
        
        assert resp.status_code == 400
        wait_for_elastic_sync()
        assert count_docs_in_basic_index() == 0

    def test_tc10_array_too_large(self):
        """TC-10: Массив из 1001 элемента (нарушение max_length=1000)."""
        # Генерируем 1001 валидный объект
        payload = [
            {"timestamp": 1700000000000 + i, "message": f"Log {i}"}
            for i in range(1001)
        ]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=10)
        
        assert resp.status_code == 400
        wait_for_elastic_sync()
        assert count_docs_in_basic_index() == 0

    # -------------------------------------------------------------------------
    # Граничные значения (Boundary Values)
    # -------------------------------------------------------------------------

    def test_tc11_timestamp_zero(self):
        """TC-11: Граничное значение: timestamp = 0."""
        payload = [{"timestamp": 0, "message": "Epoch"}]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=10)
        
        assert resp.status_code == 200
        assert resp.json()["accepted"] == 1
        
        wait_for_elastic_sync()
        docs = get_basic_logs_from_es()
        assert len(docs) == 1
        assert docs[0]["timestamp"] == 0
        assert docs[0]["message"] == "Epoch"

    def test_tc12_message_max_length(self):
        """TC-12: Граничное значение: message длиной ровно 1024 символа."""
        payload = [{"timestamp": 1700000000000, "message": "x" * 1024}]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=10)
        
        assert resp.status_code == 200
        assert resp.json()["accepted"] == 1
        
        wait_for_elastic_sync()
        docs = get_basic_logs_from_es()
        assert len(docs) == 1
        assert len(docs[0]["message"]) == 1024

    def test_tc13_message_min_length(self):
        """TC-13: Граничное значение: message длиной 1 символ."""
        payload = [{"timestamp": 1700000000000, "message": "x"}]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=10)
        
        assert resp.status_code == 200
        assert resp.json()["accepted"] == 1
        
        wait_for_elastic_sync()
        docs = get_basic_logs_from_es()
        assert len(docs) == 1
        assert docs[0]["message"] == "x"

    # -------------------------------------------------------------------------
    # Логические и дополнительные проверки
    # -------------------------------------------------------------------------

    def test_tc15_timestamp_in_seconds_logic_check(self):
        """
        TC-15: Логическая проверка: timestamp в секундах вместо миллисекунд.
        Валидация проходит (это просто число >= 0), но значение может быть
        некорректным для бизнес-логики. Тест фиксирует это поведение.
        """
        payload = [{"timestamp": 1700000000, "message": "Small ts"}]  # Секунды, не миллисекунды
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=10)
        
        # Валидация проходит, так как 1700000000 >= 0 и тип int
        assert resp.status_code == 200
        assert resp.json()["accepted"] == 1
        
        wait_for_elastic_sync()
        docs = get_basic_logs_from_es()
        assert len(docs) == 1
        # Документ записан "как есть" — ответственность за корректность формата на клиенте
        assert docs[0]["timestamp"] == 1700000000

    def test_tc16_idempotency_check(self):
        """
        TC-16: Проверка идемпотентности: повторная отправка того же пакета.
        Ожидается, что оба пакета будут записаны (ES не дедуплицирует без _id).
        """
        payload = [{"timestamp": 1700000000999, "message": "Duplicate?"}]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        # Первая отправка
        resp1 = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=10)
        assert resp1.status_code == 200
        assert resp1.json()["accepted"] == 1
        
        # Вторая отправка (идентичный пакет)
        resp2 = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=10)
        assert resp2.status_code == 200
        assert resp2.json()["accepted"] == 1
        
        wait_for_elastic_sync()
        docs = get_basic_logs_from_es()
        # Ожидаем 2 документа с одинаковыми данными
        assert len(docs) == 2
        assert all(doc["message"] == "Duplicate?" for doc in docs)

    def test_tc17_unicode_and_emoji(self):
        """TC-17: Кодировка: сообщение с кириллицей и эмодзи."""
        payload = [{"timestamp": 1700000000000, "message": "Тест 🚀 Привет мир"}]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=10)
        
        assert resp.status_code == 200
        assert resp.json()["accepted"] == 1
        
        wait_for_elastic_sync()
        docs = get_basic_logs_from_es()
        assert len(docs) == 1
        assert docs[0]["message"] == "Тест 🚀 Привет мир"

    def test_tc18_special_json_characters(self):
        """TC-18: Специальные JSON-символы в message."""
        payload = [{
            "timestamp": 1700000000000,
            "message": "Line\nBreak\tTab\"Quote\\Backslash"
        }]
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(f"{BACKEND_URL}/log/basic", json=payload, headers=headers, timeout=10)
        
        assert resp.status_code == 200
        assert resp.json()["accepted"] == 1
        
        wait_for_elastic_sync()
        docs = get_basic_logs_from_es()
        assert len(docs) == 1
        # Проверяем, что спецсимволы сохранились корректно
        assert docs[0]["message"] == "Line\nBreak\tTab\"Quote\\Backslash"