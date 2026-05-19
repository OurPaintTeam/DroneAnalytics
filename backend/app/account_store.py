from pydantic import ValidationError
from redis import Redis
from redis.exceptions import RedisError

from app.config import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, REDIS_USER
from app.models import AccountStateResponse, AccountsStateResponse


ACCOUNT_IDS_KEY = "accounts:v1:ids"
ACCOUNT_KEY_PREFIX = "accounts:v1:state"

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
