"""Интеграционные тесты для GET /log/basic."""
import pytest
import requests
from typing import Dict, Any, List

from .conftest import BACKEND_URL
from .utils import clean_index, wait_for_elastic_sync, get_timestamp_ms


# ============================================================================
# Вспомогательные функции
# ============================================================================

def write_basic_logs(count: int, base_timestamp: int = None, 
                     message_prefix: str = "TestMsg") -> List[Dict[str, Any]]:
    """
    Записывает заданное количество базовых логов через POST /log/basic.
    Возвращает список записанных данных для последующей проверки.
    """
    if base_timestamp is None:
        base_timestamp = get_timestamp_ms()
    
    api_headers = {
        "X-API-Key": "change-me",  # Значение по умолчанию из .env
        "Content-Type": "application/json"
    }
    
    logs_to_write = []
    if (count !=1):
        for i in range(count):
            logs_to_write.append({
                "timestamp": base_timestamp + i,
                "message": f"{message_prefix}_{i}"
            })
    else:
        logs_to_write.append({
            "timestamp": base_timestamp ,
            "message": f"{message_prefix}"
        })

    resp = requests.post(
        f"{BACKEND_URL}/log/basic",
        json=logs_to_write,
        headers=api_headers,
        timeout=10
    )
    assert resp.status_code == 200, f"Failed to write logs: {resp.text}"
    return logs_to_write


def get_basic_logs(bearer_headers: Dict[str, str], 
                   limit: int = None, 
                   page: int = None) -> requests.Response:
    """Выполняет GET-запрос к /log/basic с указанными параметрами."""
    params = {}
    if limit is not None:
        params["limit"] = limit
    if page is not None:
        params["page"] = page
    
    return requests.get(
        f"{BACKEND_URL}/log/basic",
        headers=bearer_headers,
        params=params,
        timeout=10
    )


# ============================================================================
# Тестовые классы
# ============================================================================

class TestGetBasicEmptyState:
    """Тесты поведения эндпоинта при отсутствии данных."""

    def test_empty_index_returns_empty_array(self, bearer_headers: Dict[str, str]):
        """TC-001: Получение логов из пустого индекса."""
        # Предусловие: индекс очищен фикстурой conftest.py
        
        resp = get_basic_logs(bearer_headers)
        
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 0, "Ожидался пустой массив для пустого индекса"


class TestGetBasicSingleRecord:
    """Тесты работы с одиночной записью."""

    def test_single_log_after_insert(self, bearer_headers: Dict[str, str]):
        """TC-002: Получение одного лога после записи."""
        base_ts = get_timestamp_ms()
        expected_message = "SingleLogTest_Message"
        
        # Записываем один лог
        write_basic_logs(1, base_timestamp=base_ts, message_prefix=expected_message)
        wait_for_elastic_sync()
        
        # Читаем
        resp = get_basic_logs(bearer_headers)
        assert resp.status_code == 200
        
        logs = resp.json()
        assert len(logs) == 1
        
        # Проверка целостности данных (TC-012)
        returned = logs[0]
        assert returned["timestamp"] == base_ts
        assert returned["message"] == expected_message
        # Проверка, что возвращены только поля модели BasicLogItem
        assert set(returned.keys()) == {"timestamp", "message"}


class TestGetBasicSorting:
    """Тесты проверки сортировки по времени."""

    def test_logs_sorted_by_timestamp_desc(self, bearer_headers: Dict[str, str]):
        """TC-003: Логи возвращаются в порядке убывания timestamp."""
        base_ts = get_timestamp_ms()
        # Записываем логи в произвольном порядке по timestamp
        timestamps = [base_ts + 100, base_ts + 10, base_ts + 500, base_ts + 1, base_ts + 50]
        for ts in timestamps:
            write_basic_logs(1, base_timestamp=ts, message_prefix=f"TS_{ts}")
        
        wait_for_elastic_sync()
        
        resp = get_basic_logs(bearer_headers, limit=10)
        assert resp.status_code == 200
        logs = resp.json()
        
        # Извлекаем timestamp из ответа
        returned_ts = [log["timestamp"] for log in logs]
        expected_ts = sorted(timestamps, reverse=True)
        
        assert returned_ts == expected_ts, f"Ожидалась сортировка по убыванию: {expected_ts}, получено: {returned_ts}"

    def test_same_timestamp_all_returned(self, bearer_headers: Dict[str, str]):
        """TC-014: Логи с одинаковым timestamp возвращаются все."""
        base_ts = get_timestamp_ms()
        # Записываем 3 лога с идентичным timestamp
        for i in range(3):
            write_basic_logs(1, base_timestamp=base_ts, message_prefix=f"SameTS_{i}")
        
        wait_for_elastic_sync()
        
        resp = get_basic_logs(bearer_headers, limit=10)
        assert resp.status_code == 200
        logs = resp.json()
        
        # Все 3 лога должны быть в ответе
        logs_with_same_ts = [log for log in logs if log["timestamp"] == base_ts]
        assert len(logs_with_same_ts) == 3

class TestGetBasicPagination:
    """Тесты пагинации: limit, page, расчёт смещения."""

    def test_pagination_page1_limit10(self, bearer_headers: Dict[str, str]):
        """TC-004: Первая страница, limit=10."""
        base_ts = get_timestamp_ms()
        write_basic_logs(25, base_timestamp=base_ts, message_prefix="PagTest_P1")
        wait_for_elastic_sync()  # ← КРИТИЧНО: ждём синхронизации с ES
        
        resp = get_basic_logs(bearer_headers, limit=10, page=1)
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 10
        # Проверка, что это самые новые логи (сортировка desc)
        assert logs[0]["message"].startswith("PagTest_P1_24")

    def test_pagination_page2_limit10(self, bearer_headers: Dict[str, str]):
        """TC-005: Вторая страница, limit=10."""
        base_ts = get_timestamp_ms()
        write_basic_logs(25, base_timestamp=base_ts, message_prefix="PagTest_P2")
        wait_for_elastic_sync()  # ← КРИТИЧНО: ждём синхронизации с ES
        
        # Получаем первую страницу для сравнения
        resp1 = get_basic_logs(bearer_headers, limit=10, page=1)
        page1_msgs = {log["message"] for log in resp1.json()}
        
        resp2 = get_basic_logs(bearer_headers, limit=10, page=2)
        assert resp2.status_code == 200
        logs_page2 = resp2.json()
        assert len(logs_page2) == 10
        
        # Проверка отсутствия пересечений между страницами
        page2_msgs = {log["message"] for log in logs_page2}
        assert page1_msgs.isdisjoint(page2_msgs), "Страницы не должны содержать одинаковые логи"

    def test_pagination_last_partial_page(self, bearer_headers: Dict[str, str]):
        """TC-006: Последняя неполная страница (25 логов, limit=10, page=3)."""
        base_ts = get_timestamp_ms()
        write_basic_logs(25, base_timestamp=base_ts, message_prefix="PagTest_P3")
        wait_for_elastic_sync()  # ← КРИТИЧНО: ждём синхронизации с ES
        
        resp = get_basic_logs(bearer_headers, limit=10, page=3)
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 5

    def test_pagination_beyond_data_returns_empty(self, bearer_headers: Dict[str, str]):
        """TC-007: Запрос страницы за пределами доступных данных."""
        # В индексе 0 логов (очищен фикстурой)
        resp = get_basic_logs(bearer_headers, limit=10, page=100)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_pagination_limit1_sequential(self, bearer_headers: Dict[str, str]):
        """TC-008: Последовательное получение по одному логу (limit=1)."""
        base_ts = get_timestamp_ms()
        write_basic_logs(3, base_timestamp=base_ts, message_prefix="Limit1")
        wait_for_elastic_sync()
        
        # Получаем по одному
        msgs_received = []
        for page in [1, 2, 3]:
            resp = get_basic_logs(bearer_headers, limit=1, page=page)
            assert resp.status_code == 200
            logs = resp.json()
            assert len(logs) == 1
            msgs_received.append(logs[0]["message"])
        
        # Проверка порядка (должны идти от нового к старому)
        assert msgs_received == ["Limit1_2", "Limit1_1", "Limit1_0"]


class TestGetBasicLimitBoundaries:
    """Тесты граничных значений параметра limit."""

    def test_limit_min_value_1(self, bearer_headers: Dict[str, str]):
        """TC-008 (доп.): Минимальное допустимое значение limit=1."""
        base_ts = get_timestamp_ms()
        write_basic_logs(5, base_timestamp=base_ts, message_prefix="MinLimit")
        wait_for_elastic_sync()
        
        resp = get_basic_logs(bearer_headers, limit=1, page=1)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_limit_max_value_100(self, bearer_headers: Dict[str, str]):
        """TC-009: Максимальное допустимое значение limit=100."""
        base_ts = get_timestamp_ms()
        write_basic_logs(150, base_timestamp=base_ts, message_prefix="MaxLimit")
        wait_for_elastic_sync()
        
        resp = get_basic_logs(bearer_headers, limit=100, page=1)
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 100
        # Проверка, что получены самые новые 100 из 150
        assert logs[0]["message"] == "MaxLimit_149"
        assert logs[-1]["message"] == "MaxLimit_50"

    def test_limit_default_value(self, bearer_headers: Dict[str, str]):
        """TC-010: Значение limit по умолчанию равно 10."""
        base_ts = get_timestamp_ms()
        write_basic_logs(20, base_timestamp=base_ts, message_prefix="Default")
        wait_for_elastic_sync()
        
        # Запрос без указания limit
        resp = requests.get(
            f"{BACKEND_URL}/log/basic",
            headers=bearer_headers,
            timeout=10
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 10


class TestGetBasicPageParameter:
    """Тесты параметра page."""

    def test_page_default_value(self, bearer_headers: Dict[str, str]):
        """TC-011: Значение page по умолчанию равно 1."""
        base_ts = get_timestamp_ms()
        write_basic_logs(15, base_timestamp=base_ts, message_prefix="PageDef")
        wait_for_elastic_sync()
        
        # Запрос только с limit, без page
        resp = requests.get(
            f"{BACKEND_URL}/log/basic",
            headers=bearer_headers,
            params={"limit": 5},
            timeout=10
        )
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 5
        # Должны быть самые новые (как при page=1)
        assert logs[0]["message"] == "PageDef_14"


class TestGetDataIntegrity:
    """Тесты целостности и корректности возвращаемых данных."""

    def test_message_max_length_1024(self, bearer_headers: Dict[str, str]):
        """TC-013: Сообщение максимальной длины (1024 символа) возвращается без обрезки."""
        base_ts = get_timestamp_ms()
        max_message = "x" * 1024
        
        write_basic_logs(1, base_timestamp=base_ts, message_prefix=max_message)
        wait_for_elastic_sync()
        
        resp = get_basic_logs(bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 1
        assert logs[0]["message"] == max_message
        assert len(logs[0]["message"]) == 1024

    def test_special_characters_in_message(self, bearer_headers: Dict[str, str]):
        """TC-017: Специальные символы в message не искажаются."""
        base_ts = get_timestamp_ms()
        special_msg = 'Special: \n\t"quotes"\\backslash/кириллица/🚀/emoji'
        
        write_basic_logs(1, base_timestamp=base_ts, message_prefix=special_msg)
        wait_for_elastic_sync()
        
        resp = get_basic_logs(bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        assert logs[0]["message"] == special_msg

    def test_timestamp_zero_boundary(self, bearer_headers: Dict[str, str]):
        """TC-015: Timestamp = 0 (граничное значение) обрабатывается корректно."""
        # Записываем лог с timestamp = 0
        api_headers = {"X-API-Key": "change-me", "Content-Type": "application/json"}
        payload = [{"timestamp": 0, "message": "EpochZero"}]
        resp_post = requests.post(
            f"{BACKEND_URL}/log/basic",
            json=payload,
            headers=api_headers,
            timeout=10
        )
        assert resp_post.status_code == 200
        wait_for_elastic_sync()
        
        resp = get_basic_logs(bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        # Находим наш лог
        zero_ts_logs = [log for log in logs if log["timestamp"] == 0]
        assert len(zero_ts_logs) == 1
        assert zero_ts_logs[0]["message"] == "EpochZero"

    def test_timestamp_type_is_integer(self, bearer_headers: Dict[str, str]):
        """Проверка, что timestamp возвращается как int, а не str или float."""
        base_ts = get_timestamp_ms()
        write_basic_logs(1, base_timestamp=base_ts, message_prefix="TypeCheck")
        wait_for_elastic_sync()
        
        resp = get_basic_logs(bearer_headers)
        assert resp.status_code == 200
        logs = resp.json()
        assert isinstance(logs[0]["timestamp"], int)
        assert not isinstance(logs[0]["timestamp"], bool)  # bool — подкласс int в Python


class TestGetBasicEventualConsistency:
    """Тесты, учитывающие eventual consistency ElasticSearch."""

    def test_read_after_write_with_sync_delay(self, bearer_headers: Dict[str, str]):
        """TC-018: Быстрая последовательность записи и чтения с учётом задержки синхронизации."""
        base_ts = get_timestamp_ms()
        logs_written = write_basic_logs(10, base_timestamp=base_ts, message_prefix="SyncTest")
        
        # Ждём применения изменений в ES
        wait_for_elastic_sync()
        
        resp = get_basic_logs(bearer_headers, limit=20)
        assert resp.status_code == 200
        logs_read = resp.json()
        
        # Все 10 записанных логов должны быть доступны
        read_messages = {log["message"] for log in logs_read}
        written_messages = {log["message"] for log in logs_written}
        
        assert written_messages.issubset(read_messages), \
            f"Не все записанные логи доступны для чтения. Записано: {len(written_messages)}, найдено: {len(read_messages & written_messages)}"


class TestGetBasicLargeDataset:
    """Тесты работы с большим объёмом данных."""

    def test_iterate_all_pages_no_duplicates(self, bearer_headers: Dict[str, str]):
        """TC-016: Последовательный обход всех страниц не даёт дубликатов."""
        base_ts = get_timestamp_ms()
        total_logs = 150
        write_basic_logs(total_logs, base_timestamp=base_ts, message_prefix="Large")
        wait_for_elastic_sync()
        
        all_messages = []
        page = 1
        limit = 25
        
        while True:
            resp = get_basic_logs(bearer_headers, limit=limit, page=page)
            assert resp.status_code == 200
            logs = resp.json()
            
            if not logs:
                break
                
            all_messages.extend([log["message"] for log in logs])
            page += 1
            
            # Защита от бесконечного цикла
            if page > 20:
                pytest.fail("Слишком много итераций, возможна ошибка в пагинации")
        
        # Проверки
        assert len(all_messages) == total_logs, \
            f"Ожидалось {total_logs} логов, получено {len(all_messages)}"
        
        # Проверка на дубликаты
        assert len(all_messages) == len(set(all_messages)), "Обнаружены дубликаты логов при пагинации"
        
        # Проверка сортировки (сообщения должны идти от "Large_149" до "Large_0")
        expected_order = [f"Large_{i}" for i in range(total_logs - 1, -1, -1)]
        assert all_messages == expected_order