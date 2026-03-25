import requests
import pytest
import time
import os
import csv
import io
from typing import List, Optional, Dict, Any
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elastic:9200")
INDICES = ["telemetry", "basic", "event", "safety"]

def filter_rows_by_match(
    rows: List[Dict[str, str]],
    value: str,
    field: str = "message",
    startswith: bool = False,
) -> List[Dict[str, str]]:
    """Фильтрует CSV-строки по значению в указанном поле."""
    if startswith:
        return [row for row in rows if row.get(field, "").startswith(value)]
    return [row for row in rows if value in row.get(field, "")]


def auth_login(
    backend_url: str,
    credentials: Optional[Dict[str, Any]] = None,
    *,
    json: Optional[Dict[str, Any]] = None,
    timeout: int = 5,
) -> requests.Response:
    """Выполняет POST /auth/login."""
    payload = json if json is not None else credentials
    if payload is None:
        payload = {}
    return requests.post(
        f"{backend_url}/auth/login",
        json=payload,
        timeout=timeout,
    )


def auth_refresh(
    backend_url: str,
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    data: Optional[str] = None,
    timeout: int = 5,
) -> requests.Response:
    """Выполняет POST /auth/refresh."""
    request_kwargs: Dict[str, Any] = {"timeout": timeout}
    if headers is not None:
        request_kwargs["headers"] = headers
    if data is not None:
        request_kwargs["data"] = data
    else:
        request_kwargs["json"] = payload if payload is not None else {}
    return requests.post(f"{backend_url}/auth/refresh", **request_kwargs)


def auth_logout(
    backend_url: str,
    payload: Dict[str, Any],
    access_token: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 5,
) -> requests.Response:
    """Выполняет POST /auth/logout."""
    request_headers = dict(headers or {})
    if access_token is not None:
        request_headers.setdefault("Authorization", f"Bearer {access_token}")
    return requests.post(
        f"{backend_url}/auth/logout",
        json=payload,
        headers=request_headers or None,
        timeout=timeout,
    )


def assert_api_error(
    response: requests.Response,
    expected_status: int,
    message_contains: Optional[str] = None,
    message_exact: Optional[str] = None,
) -> Dict[str, Any]:
    """Проверяет стандартный формат ошибки API: code/message."""
    assert response.status_code == expected_status
    data = response.json()
    assert data.get("code") == expected_status
    assert "message" in data and isinstance(data["message"], str)
    if message_exact is not None:
        assert data["message"] == message_exact
    if message_contains is not None:
        assert message_contains in data["message"]
    return data


def create_event_payload(
    timestamp: Optional[int] = None,
    service: str = "GCS",
    service_id: int = 1,
    message: str = "Test event",
    severity: str | None = None,
    event_type: str = "event",
) -> Dict[str, Any]:
    """Создаёт валидный payload для POST /log/event."""
    payload = {
        "apiVersion": "1.0.0",
        "timestamp": timestamp if timestamp is not None else get_timestamp_ms(),
        "event_type": event_type,
        "service": service,
        "service_id": service_id,
        "message": message,
    }
    if severity is not None:
        payload["severity"] = severity
    return payload


def post_event_logs(
    backend_url: str,
    api_headers: Dict[str, str],
    events: List[Dict[str, Any]],
    timeout: int = 10,
) -> requests.Response:
    """Отправляет пакет событий через POST /log/event."""
    return requests.post(
        f"{backend_url}/log/event",
        json=events,
        headers=api_headers,
        timeout=timeout,
    )

def post_basic_logs(
    backend_url: str,
    api_headers: Dict[str, str],
    logs: List[Dict[str, Any]],
    timeout: int = 10,
) -> requests.Response:
    """Отправляет пакет basic-логов через POST /log/basic."""
    return requests.post(
        f"{backend_url}/log/basic",
        json=logs,
        headers=api_headers,
        timeout=timeout,
    )


def create_telemetry_payload(
    timestamp: int,
    drone: str = "delivery",
    drone_id: int = 1,
    latitude: float = 55.7558,
    longitude: float = 37.6176,
    battery: int | None = 85,
    pitch: float | None = 5.5,
    roll: float | None = -2.1,
    course: float | None = 180.0,
) -> Dict[str, Any]:
    """Создаёт валидный payload для POST /log/telemetry."""
    payload = {
        "apiVersion": "1.0.0",
        "timestamp": timestamp,
        "drone": drone,
        "drone_id": drone_id,
        "latitude": latitude,
        "longitude": longitude,
    }
    if battery is not None:
        payload["battery"] = battery
    if pitch is not None:
        payload["pitch"] = pitch
    if roll is not None:
        payload["roll"] = roll
    if course is not None:
        payload["course"] = course
    return payload


def post_telemetry_logs(
    backend_url: str,
    api_headers: Dict[str, str],
    telemetry_records: List[Dict[str, Any]],
    timeout: int = 10,
) -> requests.Response:
    """Отправляет пакет telemetry-логов через POST /log/telemetry."""
    return requests.post(
        f"{backend_url}/log/telemetry",
        json=telemetry_records,
        headers=api_headers,
        timeout=timeout,
    )


def get_paginated_logs(
    backend_url: str,
    endpoint: str,
    bearer_headers: Dict[str, str],
    limit: int = 10,
    page: int = 1,
    timeout: int = 10,
) -> requests.Response:
    """Запрашивает логи с параметрами пагинации."""
    return requests.get(
        f"{backend_url}{endpoint}",
        params={"limit": limit, "page": page},
        headers=bearer_headers,
        timeout=timeout,
    )


def insert_safety_log(
    backend_url: str,
    api_headers: Dict[str, str],
    timestamp: Optional[int] = None,
    service: str = "dronePort",
    service_id: int = 2,
    severity: Optional[str] = "warning",
    message: str = "Test safety message",
    timeout: int = 10,
) -> Dict[str, Any]:
    """Создаёт safety event через POST /log/event и возвращает отправленный документ."""
    if timestamp is None:
        timestamp = get_timestamp_ms()

    payload = [{
        "apiVersion": "1.0.0",
        "timestamp": timestamp,
        "event_type": "safety_event",
        "service": service,
        "service_id": service_id,
        "severity": severity,
        "message": message,
    }]
    resp = post_event_logs(backend_url, api_headers, payload, timeout=timeout)
    assert resp.status_code in (200, 207), f"Failed to insert safety log: {resp.text}"
    return payload[0]

def parse_csv_from_response(response: requests.Response) -> List[Dict[str, str]]:
    """
    Парсит CSV из StreamingResponse.
    Возвращает список словарей, где ключи — заголовки колонок.
    """
    content = response.content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def get_csv_headers(response: requests.Response) -> List[str]:
    """Извлекает заголовки колонок из CSV ответа."""
    content = response.content.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    return next(reader)

def get_timestamp_ms() -> int:
    """Возвращает текущее время в миллисекундах (как в приложении)."""
    return int(time.time() * 1000)

def wait_for_elastic_sync(seconds: float = 1.5) -> None:
    """
    Ждёт применения изменений в ElasticSearch.
    ES применяет изменения асинхронно (eventual consistency).
    """
    time.sleep(seconds)

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

def get_recent_audit_log(expected_substring: str, severity: str, index_name: str = "safety") -> Optional[dict]:
    """
    Ищет самую свежую запись аудита, содержащую подстроку и severity.
    
    Args:
        expected_substring: Часть сообщения, которую ожидаем (без IP)
        severity: Ожидаемый уровень (info/warning)
        index_name: Название индекса для поиска (по умолчанию "safety")
            
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
            f"{ELASTIC_URL}/{index_name}/_search",
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