"""Общие вспомогательные функции для security_scenario тестов."""
from __future__ import annotations

import os
import time
import uuid
from typing import Any

import jwt
import requests


ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elastic:9200")
JWT_ALGORITHM = "HS256"
TEST_INDICES = ["telemetry", "basic", "event", "safety"]


def proxy_request(method: str, url: str, **kwargs: Any) -> requests.Response:
    """HTTP-запрос через proxy без использования системных proxy-переменных."""
    kwargs.setdefault("timeout", 10)
    
    with requests.Session() as session:
        session.trust_env = False
        return session.request(method, url, verify=False, **kwargs)


def elastic_health_check(timeout: int = 60) -> bool:
    """Проверяет доступность ElasticSearch."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{ELASTIC_URL}/_cluster/health", timeout=2)
            if resp.status_code == 200 and resp.json().get("status") in {"green", "yellow"}:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def clean_all_indices() -> None:
    """Очищает все тестовые индексы."""
    for index in TEST_INDICES:
        try:
            requests.post(
                f"{ELASTIC_URL}/{index}/_delete_by_query",
                json={"query": {"match_all": {}}},
                timeout=5,
            )
        except requests.RequestException:
            continue


def wait_for_elastic_sync(seconds: float = 1.5) -> None:
    """Ждёт консистентности Elasticsearch после записи."""
    time.sleep(seconds)


def count_basic_docs_by_message(marker: str) -> int:
    """Подсчитывает документы в индексе basic по точному совпадению message."""
    query = {"query": {"match_phrase": {"message": marker}}}
    resp = requests.post(f"{ELASTIC_URL}/basic/_count", json=query, timeout=5)
    if resp.status_code != 200:
        return 0
    return int(resp.json().get("count", 0))


def forge_access_token(secret_key: str, *, subject: str, exp_delta_sec: int = 900) -> str:
    """Генерирует forged access token для сценариев компрометации секрета."""
    now = int(time.time())
    payload = {
        "sub": subject,
        "type": "access",
        "iat": now,
        "exp": now + exp_delta_sec,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, secret_key, algorithm=JWT_ALGORITHM)
