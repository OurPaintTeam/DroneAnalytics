"""Security scenario: Threat 5 — DoS через массовую отправку логов."""
from __future__ import annotations

import concurrent.futures
import os
import time

import pytest

from security_scenario.utils import proxy_request


AUTH_USERNAME = os.getenv("AUTH_USERNAME", "user")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "password")


pytestmark = pytest.mark.filterwarnings(
    "ignore::urllib3.exceptions.InsecureRequestWarning"
)


def _post_basic(proxy_base_url: str, api_headers: dict[str, str], payload: list[dict], **kwargs) -> int:
    response = proxy_request(
        "POST",
        f"{proxy_base_url}/log/basic",
        json=payload,
        headers=api_headers,
        **kwargs, 
    )
    return response.status_code


class TestThreat5DosResilience:
    """Проверки базовой устойчивости API к DoS-паттернам."""

    def test_step_1_reject_batch_over_limit(self, proxy_base_url: str, api_headers: dict[str, str]) -> None:
        """Массив > 1000 элементов должен отклоняться валидацией."""
        payload = [{"timestamp": int(time.time() * 1000), "message": "batch-over-limit"}] * 1001

        response = proxy_request(
            "POST",
            f"{proxy_base_url}/log/basic",
            json=payload,
            headers=api_headers,
            timeout=5.0,  # Защита от зависаний при сериализации большого payload
        )

        assert response.status_code in {207, 400, 422}, f"Unexpected status {response.status_code}: {response.text[:300]}"

        if response.status_code == 207:
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type:
                pytest.fail(f"Expected JSON for 207, but got: {content_type}. Body: {response.text[:200]}")

            body = response.json()
            assert body.get("accepted") == 0, f"Expected 0 accepted, got {body.get('accepted')}"
            assert body.get("rejected") == 1, f"Expected 1 rejected (batch-level), got {body.get('rejected')}"


    def test_step_2_reject_oversized_message(self, proxy_base_url: str, api_headers: dict[str, str]) -> None:
        """Слишком длинный message (более 1024) должен отклоняться."""
        payload = [{
            "timestamp": int(time.time() * 1000),
            "message": "X" * 1025,
        }]

        response = proxy_request(
            "POST",
            f"{proxy_base_url}/log/basic",
            json=payload,
            headers=api_headers,
            timeout=5.0,
        )

        assert response.status_code in {207, 400, 422}, f"Unexpected status {response.status_code}: {response.text[:300]}"

        if response.status_code == 207:
            if "application/json" not in response.headers.get("content-type", ""):
                pytest.fail(f"Expected JSON for 207, but got non-JSON response")

            body = response.json()
            assert body.get("accepted") == 0
            assert body.get("rejected") == 1


    def test_step_3_burst_ingest_no_5xx(self, proxy_base_url: str, api_headers: dict[str, str]) -> None:
        """Умеренный burst POST /log/basic не должен приводить к 5xx."""

        def send_one(i: int) -> int:
            payload = [{"timestamp": int(time.time() * 1000), "message": f"burst-{i}"}]
            try:
                # Явный таймаут предотвращает бесконечное ожидание
                return _post_basic(proxy_base_url, api_headers, payload, timeout=3.0)
            except Exception as exc:
                # Сетевая ошибка = проблема инфраструктуры, тест должен чётко на это указать
                raise AssertionError(f"Burst request {i} failed: {exc}") from exc

        # 12 воркеров обрабатывают 160 задач асинхронно (не пакетами по 12)
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            statuses = list(executor.map(send_one, range(160)))

        assert statuses, "No statuses returned from burst test"
        assert all(code < 500 for code in statuses), f"Got server errors during burst: {statuses}"

    def test_step_4_auth_available_during_ingest_burst(
        self, proxy_base_url: str, api_headers: dict[str, str]
    ) -> None:
        """На фоне burst логов /auth/login должен оставаться доступным."""
        
        # 1. Функция для конкурентной отправки логов
        def send_one_log(i: int) -> int:
            payload = [{"timestamp": int(time.time() * 1000), "message": f"auth-burst-{i}"}]
            return _post_basic(proxy_base_url, api_headers, payload)

        # 2. Используем больше воркеров для реального burst
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Запускаем 80 запросов параллельно
            ingest_futures = [executor.submit(send_one_log, i) for i in range(80)]

            # 3. Выполняем логин-запросы параллельно с инжестом
            login_statuses: list[int] = []
            for _ in range(8):
                resp = proxy_request(
                    "POST",
                    f"{proxy_base_url}/auth/login",
                    json={"username": AUTH_USERNAME, "password": AUTH_PASSWORD},
                    timeout=5.0,  # Защита от зависаний
                )
                login_statuses.append(resp.status_code)
                time.sleep(0.05)

            # 4. Ожидаем завершения инжеста с таймаутом
            done, not_done = concurrent.futures.wait(
                ingest_futures, timeout=15.0, return_when=concurrent.futures.ALL_COMPLETED
            )
            if not_done:
                pytest.fail(f"{len(not_done)} log requests did not complete within timeout")
                
            ingest_statuses = [f.result() for f in ingest_futures]

        # 5. Ассерты
        assert all(code < 500 for code in ingest_statuses), f"Ingest returned 5xx: {ingest_statuses}"
        assert all(code < 500 for code in login_statuses), f"Auth returned 5xx under load: {login_statuses}"
        
        # Разрешаем 429, если включён rate-limiting. Если 200 нет вообще — тест падает.
        successful_login = any(code == 200 for code in login_statuses)
        rate_limited = any(code == 429 for code in login_statuses)
        
        if not successful_login:
            if rate_limited:
                pytest.skip("Auth is rate-limited under load; no 200 observed (may be intentional)")
            else:
                pytest.fail(f"Auth never succeeded or was properly throttled: {login_statuses}")

    def test_step_5_rate_limit_signal_if_configured(self, proxy_base_url: str, api_headers: dict[str, str]) -> None:
        """
        Если rate limiting настроен, при агрессивном burst должны появиться 429.
        Если 429 нет — тест помечается как skip (в окружении может не быть limit_req).
        """

        def aggressive_send(i: int) -> int:
            payload = [{"timestamp": int(time.time() * 1000), "message": f"rl-probe-{i}"}]
            try:
                # Явный таймаут предотвращает бесконечное ожидание в CI
                resp = _post_basic(
                    "POST",
                    f"{proxy_base_url}/log/basic",
                    json=payload,
                    headers=api_headers,
                    timeout=5.0,
                )
                return resp.status_code
            except Exception as exc:
                # Сетевая ошибка = сервер недоступен. Тест должен упасть, а не висеть.
                raise AssertionError(f"Request {i} failed with network error: {exc}") from exc

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # executor.map гарантирует порядок и блокирует до завершения всех задач
            statuses = list(executor.map(aggressive_send, range(300)))

        # 1. Никаких 5xx и сетевых падений
        assert all(code < 500 for code in statuses), f"Got server errors in rate-limit probe: {statuses}"

        # 2. Проверяем наличие 429 только среди успешных ответов
        has_rate_limit = 429 in set(statuses)
        if not has_rate_limit:
            # Если нет 429, но есть другие 4xx (например, 403/400) — это подозрительно.
            # Оставляем skip, но добавляем информативное сообщение с распределением статусов.
            from collections import Counter
            status_dist = Counter(statuses)
            pytest.skip(
                f"No 429 observed; rate limiting may be disabled. "
                f"Response distribution: {dict(status_dist)}"
            )
