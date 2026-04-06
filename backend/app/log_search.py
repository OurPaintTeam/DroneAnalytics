"""Сборка запросов Elasticsearch для чтения логов (фильтры опциональны — без них эквивалент match_all)."""

from __future__ import annotations

from fastapi import HTTPException, status


def validate_timestamp_range(from_ts: int | None, to_ts: int | None) -> None:
    if from_ts is not None and to_ts is not None and from_ts > to_ts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": status.HTTP_400_BAD_REQUEST, "message": "from_ts must be less than or equal to to_ts"},
        )


def build_log_list_query(
    *,
    exclude_service: str | None = None,
    from_ts: int | None = None,
    to_ts: int | None = None,
    term_filters: dict[str, str | int] | None = None,
    message_match: str | None = None,
) -> dict | None:
    """
    Возвращает тело поля 'query' для search API или None (тогда не передаём query — match_all).
    Использует filter для точных полей и range, must — для полнотекста по message.
    """
    filters: list[dict] = []
    if from_ts is not None or to_ts is not None:
        rng: dict[str, int] = {}
        if from_ts is not None:
            rng["gte"] = from_ts
        if to_ts is not None:
            rng["lte"] = to_ts
        filters.append({"range": {"timestamp": rng}})
    if term_filters:
        for field, value in term_filters.items():
            filters.append({"term": {field: value}})

    must: list[dict] = []
    if message_match:
        must.append(
            {
                "match_bool_prefix": {
                    "message": {
                        "query": message_match,
                    }
                }
            }
        )

    must_not: list[dict] = []
    if exclude_service:
        must_not.append({"term": {"service": exclude_service}})

    if not filters and not must and not must_not:
        return None

    bool_q: dict = {}
    if filters:
        bool_q["filter"] = filters
    if must:
        bool_q["must"] = must
    if must_not:
        bool_q["must_not"] = must_not
    return {"bool": bool_q}
