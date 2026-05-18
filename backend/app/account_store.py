import time
from typing import Any

from pydantic import ValidationError
from redis import Redis
from redis.exceptions import RedisError

from app.config import REDIS_URL
from app.models import AccountStateResponse, AccountsStateResponse


ACCOUNT_IDS_KEY = "accounts:v1:ids"
ACCOUNT_KEY_PREFIX = "accounts:v1:state"

DEFAULT_ACCOUNTS: tuple[dict[str, Any], ...] = (
    {
        "account_id": "aggregator",
        "name": "Агрегатор",
        "service": "aggregator",
        "balance": 120_000,
        "reserved": 18_000,
    },
    {
        "account_id": "operator",
        "name": "Эксплуатант",
        "service": "operator",
        "balance": 86_000,
        "reserved": 12_500,
    },
    {
        "account_id": "insurance",
        "name": "Страховая компания",
        "service": "insurance",
        "balance": 64_000,
        "reserved": 9_000,
    },
    {
        "account_id": "developer",
        "name": "Разработчик",
        "service": None,
        "balance": 52_000,
        "reserved": 6_000,
    },
    {
        "account_id": "regulator",
        "name": "Регулятор",
        "service": "regulator",
        "balance": 41_000,
        "reserved": 2_500,
    },
    {
        "account_id": "orat_bas",
        "name": "ОрВД БАС",
        "service": "OrAT_drones",
        "balance": 73_000,
        "reserved": 11_000,
    },
    {
        "account_id": "customer",
        "name": "Заказчик",
        "service": None,
        "balance": 95_000,
        "reserved": 24_000,
    },
)


class AccountStoreError(RuntimeError):
    pass


def _now_ms() -> int:
    return int(time.time() * 1000)


def _account_key(account_id: str) -> str:
    return f"{ACCOUNT_KEY_PREFIX}:{account_id}"


def _redis() -> Redis:
    return Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def _default_payload(account: dict[str, Any], updated_at: int) -> dict[str, str]:
    return {
        "account_id": str(account["account_id"]),
        "name": str(account["name"]),
        "service": "" if account["service"] is None else str(account["service"]),
        "balance": str(account["balance"]),
        "reserved": str(account["reserved"]),
        "updated_at": str(updated_at),
    }


def _ensure_default_accounts(client: Redis) -> None:
    existing_ids = set(client.lrange(ACCOUNT_IDS_KEY, 0, -1))
    updated_at = _now_ms()
    pipe = client.pipeline(transaction=True)

    for account in DEFAULT_ACCOUNTS:
        account_id = str(account["account_id"])
        account_key = _account_key(account_id)

        if account_id not in existing_ids:
            pipe.rpush(ACCOUNT_IDS_KEY, account_id)

        if not client.exists(account_key):
            pipe.hset(account_key, mapping=_default_payload(account, updated_at))

    pipe.execute()


def _parse_int(value: str | None, field: str, account_id: str) -> int:
    if value is None:
        raise AccountStoreError(f"Missing account field {field}: {account_id}")

    try:
        parsed = int(value)
    except ValueError as exc:
        raise AccountStoreError(f"Invalid account field {field}: {account_id}") from exc

    if parsed < 0:
        raise AccountStoreError(f"Negative account field {field}: {account_id}")

    return parsed


def _parse_account(account_id: str, data: dict[str, str]) -> AccountStateResponse:
    if not data:
        raise AccountStoreError(f"Missing account state: {account_id}")

    balance = _parse_int(data.get("balance"), "balance", account_id)
    reserved = _parse_int(data.get("reserved"), "reserved", account_id)
    updated_at = _parse_int(data.get("updated_at"), "updated_at", account_id)
    service = data.get("service") or None

    try:
        return AccountStateResponse(
            account_id=account_id,
            name=data.get("name") or account_id,
            service=service,
            balance=balance,
            reserved=reserved,
            available=max(balance - reserved, 0),
            updated_at=updated_at,
        )
    except ValidationError as exc:
        raise AccountStoreError(f"Invalid account state: {account_id}") from exc


def read_accounts_state() -> AccountsStateResponse:
    try:
        client = _redis()
        _ensure_default_accounts(client)
        account_ids = client.lrange(ACCOUNT_IDS_KEY, 0, -1)
        accounts = [
            _parse_account(account_id, client.hgetall(_account_key(account_id)))
            for account_id in account_ids
        ]
    except RedisError as exc:
        raise AccountStoreError("Redis is unavailable") from exc

    if not accounts:
        raise AccountStoreError("Account list is empty")

    total_balance = sum(account.balance for account in accounts)
    total_reserved = sum(account.reserved for account in accounts)
    total_available = sum(account.available for account in accounts)
    updated_at = max(account.updated_at for account in accounts)

    return AccountsStateResponse(
        accounts=accounts,
        total_balance=total_balance,
        total_reserved=total_reserved,
        total_available=total_available,
        updated_at=updated_at,
    )
