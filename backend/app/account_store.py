import json
from collections.abc import Iterable

from pydantic import ValidationError
from redis import Redis
from redis.exceptions import RedisError

from app.config import ACCOUNT_SEEDS, REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, REDIS_USER
from app.models import AccountStateResponse, AccountsStateResponse


ACCOUNT_IDS_KEY = "accounts:v1:ids"
ACCOUNT_KEY_PREFIX = "accounts:v1:state"
ACCOUNT_SERVICES_FIELD = "services"
ACCOUNT_UPDATED_AT_FIELD = "updated_at"


def _account_ids() -> list[str]:
    return [account["account_id"] for account in ACCOUNT_SEEDS]


def _account_service_index() -> dict[str, tuple[str, ...]]:
    index: dict[str, list[str]] = {}
    for account in ACCOUNT_SEEDS:
        account_id = account["account_id"]
        for service in account["services"]:
            index.setdefault(service, []).append(account_id)
    return {service: tuple(account_ids) for service, account_ids in index.items()}


ACCOUNT_SERVICE_INDEX = _account_service_index()


class AccountStoreError(RuntimeError):
    pass


def _account_key(account_id: str) -> str:
    return f"{ACCOUNT_KEY_PREFIX}:{account_id}"


def _redis() -> Redis:
    return Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        username=REDIS_USER,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def _seed_mapping(account: dict[str, object], updated_at: str | None) -> dict[str, str]:
    services = account["services"]
    if not isinstance(services, list):
        raise AccountStoreError("Invalid account seed data")

    return {
        "name": str(account["name"]),
        "service": services[0] if services else "",
        ACCOUNT_SERVICES_FIELD: json.dumps(services, ensure_ascii=False),
        "balance": str(account["balance"]),
        "reserved": str(account["reserved"]),
        ACCOUNT_UPDATED_AT_FIELD: updated_at or "0",
    }


def _ensure_accounts_seeded(client: Redis) -> None:
    account_ids = _account_ids()
    existing_updated_at = {
        account_id: client.hget(_account_key(account_id), ACCOUNT_UPDATED_AT_FIELD)
        for account_id in account_ids
    }

    pipeline = client.pipeline(transaction=False)
    pipeline.delete(ACCOUNT_IDS_KEY)
    if account_ids:
        pipeline.rpush(ACCOUNT_IDS_KEY, *account_ids)
    for account in ACCOUNT_SEEDS:
        account_id = str(account["account_id"])
        pipeline.hset(
            _account_key(account_id),
            mapping=_seed_mapping(account, existing_updated_at.get(account_id)),
        )
    pipeline.execute()


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
    updated_at = _parse_int(data.get(ACCOUNT_UPDATED_AT_FIELD), ACCOUNT_UPDATED_AT_FIELD, account_id)
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
        _ensure_accounts_seeded(client)
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


def ensure_accounts_seeded() -> None:
    try:
        _ensure_accounts_seeded(_redis())
    except RedisError as exc:
        raise AccountStoreError("Redis is unavailable") from exc


def touch_accounts_for_services(service_timestamps: Iterable[tuple[str, int]]) -> None:
    max_timestamp_by_account: dict[str, int] = {}
    for service, timestamp in service_timestamps:
        if timestamp < 0:
            continue
        for account_id in ACCOUNT_SERVICE_INDEX.get(service, ()):
            current = max_timestamp_by_account.get(account_id, 0)
            if timestamp > current:
                max_timestamp_by_account[account_id] = timestamp

    if not max_timestamp_by_account:
        return

    try:
        client = _redis()
        _ensure_accounts_seeded(client)
        pipeline = client.pipeline(transaction=False)
        for account_id, timestamp in max_timestamp_by_account.items():
            current_raw = client.hget(_account_key(account_id), ACCOUNT_UPDATED_AT_FIELD)
            current = 0 if current_raw is None else _parse_int(current_raw, ACCOUNT_UPDATED_AT_FIELD, account_id)
            if timestamp > current:
                pipeline.hset(_account_key(account_id), ACCOUNT_UPDATED_AT_FIELD, timestamp)
        pipeline.execute()
    except RedisError as exc:
        raise AccountStoreError("Redis is unavailable") from exc
