import requests
import pytest
import time
from typing import List, Optional
from .conftest import ELASTIC_URL
INDICES = ["telemetry", "basic", "event", "safety"]


def elastic_health_check(timeout: int = 30) -> bool:
    """Проверяет, что ElasticSearch доступен и в статусе green/yellow."""
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{ELASTIC_URL}/_cluster/health", timeout=2)
            if resp.status_code == 200:
                status = resp.json().get("status")
                if status in ("green", "yellow"):
                    return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False

def get_recent_audit_log(expected_substring: str, severity: str) -> Optional[dict]:
    """
    Ищет самую свежую запись аудита, содержащую подстроку и severity.
    
    Args:
        expected_substring: Часть сообщения, которую ожидаем (без IP)
        severity: Ожидаемый уровень (info/warning)
            
    Returns:
        dict с _source записи или None, если не найдено
    """        
    # Ждем применения изменений в ES (eventual consistency)
    time.sleep(1.5)
    
    # Получаем текущее время в миллисекундах для фильтра
    now_ms = int(time.time() * 1000)
    # Ищем записи за последние 10 секунд
    time_range_ms = 10000
    
    try:
        # Поиск с сортировкой по timestamp (desc) - берем самую свежую
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"message": expected_substring}},
                        {"term": {"severity": severity}},
                        {
                            "range": {
                                "timestamp": {
                                    "gte": now_ms - time_range_ms,
                                    "lte": now_ms + time_range_ms  # Небольшой запас на рассинхрон часов
                                }
                            }
                        }
                    ]
                }
            },
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": 1
        }
        resp = requests.post(
            f"{ELASTIC_URL}/safety/_search",
            json=query,
            timeout=5
        )
        if resp.status_code != 200:
            pytest.skip(f"ElasticSearch returned status {resp.status_code}")
                
        hits = resp.json().get("hits", {}).get("hits", [])
        return hits[0]["_source"] if hits else None
            
    except requests.RequestException as e:
        pytest.skip(f"ElasticSearch unavailable for audit check: {e}")

def clean_index(index_name: str) -> bool:
    """Удаляет все документы из индекса, не удаляя сам индекс (сохраняет маппинг)."""
    try:
        # DELETE by query удаляет все документы, оставляя индекс с маппингом
        resp = requests.post(
            f"{ELASTIC_URL}/{index_name}/_delete_by_query",
            json={"query": {"match_all": {}}},
            timeout=5
        )
        return resp.status_code in (200, 404)  # 404 если индекс ещё не создан
    except requests.RequestException:
        return False


def clean_all_indices() -> None:
    """Очищает все тестовые индексы в ElasticSearch."""
    for index in INDICES:
        clean_index(index)

# На всякий случай

def delete_index(index_name: str) -> bool:
    """Полностью удаляет индекс (если нужно создать с нуля)."""
    try:
        resp = requests.delete(f"{ELASTIC_URL}/{index_name}", timeout=5)
        return resp.status_code in (200, 404)
    except requests.RequestException:
        return False


def recreate_indices() -> bool:
    """Пересоздаёт индексы с маппингами (как в init-elastic)."""
    # Маппинги копируются из init-elastic/main.py
    mappings = {
        "telemetry": {
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {
                "properties": {
                    "timestamp": {"type": "date", "format": "epoch_millis"},
                    "drone": {"type": "keyword"},
                    "drone_id": {"type": "short", "null_value": 1},
                    "battery": {"type": "short", "null_value": 100},
                    "pitch": {"type": "double", "null_value": 0},
                    "roll": {"type": "double", "null_value": 0},
                    "course": {"type": "double", "null_value": 0},
                    "latitude": {"type": "double"},
                    "longitude": {"type": "double"},
                }
            }
        },
        "basic": {
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "timestamp": {"type": "date", "format": "epoch_millis"},
                    "message": {"type": "text", "analyzer": "standard"}
                }
            }
        },
        "event": {
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "timestamp": {"type": "date", "format": "epoch_millis"},
                    "service": {"type": "keyword"},
                    "service_id": {"type": "short", "null_value": 1},
                    "severity": {"type": "keyword"},
                    "message": {"type": "text", "analyzer": "standard"}
                }
            }
        },
        "safety": {
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "timestamp": {"type": "date", "format": "epoch_millis"},
                    "service": {"type": "keyword"},
                    "service_id": {"type": "short", "null_value": 1},
                    "severity": {"type": "keyword"},
                    "message": {"type": "text", "analyzer": "standard"}
                }
            }
        }
    }
    
    for index_name, mapping in mappings.items():
        try:
            # Сначала удаляем, если существует
            requests.delete(f"{ELASTIC_URL}/{index_name}", timeout=2)
            # Создаём заново
            resp = requests.put(
                f"{ELASTIC_URL}/{index_name}",
                json=mapping,
                timeout=5
            )
            if resp.status_code not in (200, 201):
                return False
        except requests.RequestException:
            return False
    return True