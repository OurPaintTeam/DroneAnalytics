"""Интеграционные тесты для GET /accounts."""

from typing import Dict

import requests

from .conftest import BACKEND_URL


EXPECTED_ACCOUNT_IDS = [
    "aggregator",
    "operator",
    "insurance",
    "developer",
    "regulator",
    "orat_bas",
    "customer",
]


class TestGetAccounts:
    def test_get_accounts_returns_main_players(self, bearer_headers: Dict[str, str]):
        """GET /accounts возвращает только игроков из ТЗ без student/auth сущностей."""
        resp = requests.get(
            f"{BACKEND_URL}/accounts",
            headers=bearer_headers,
            timeout=10,
        )

        assert resp.status_code == 200
        data = resp.json()

        accounts = data["accounts"]
        assert [account["account_id"] for account in accounts] == EXPECTED_ACCOUNT_IDS
        assert [account["name"] for account in accounts] == [
            "Агрегатор",
            "Эксплуатант",
            "Страховая компания",
            "Разработчик",
            "Регулятор",
            "ОрВД БАС",
            "Заказчик",
        ]

        forbidden_keys = {"student", "login", "password", "key", "api_key"}
        for account in accounts:
            assert forbidden_keys.isdisjoint(account.keys())

    def test_get_accounts_totals_match_rows(self, bearer_headers: Dict[str, str]):
        """Итоговые значения соответствуют сумме строк."""
        resp = requests.get(
            f"{BACKEND_URL}/accounts",
            headers=bearer_headers,
            timeout=10,
        )

        assert resp.status_code == 200
        data = resp.json()
        accounts = data["accounts"]

        assert data["total_balance"] == sum(account["balance"] for account in accounts)
        assert data["total_reserved"] == sum(account["reserved"] for account in accounts)
        assert data["total_available"] == sum(account["available"] for account in accounts)
        assert data["updated_at"] == max(account["updated_at"] for account in accounts)

        for account in accounts:
            assert account["available"] == max(account["balance"] - account["reserved"], 0)
