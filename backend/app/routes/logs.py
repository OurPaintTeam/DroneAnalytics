from fastapi import APIRouter, Body, Depends, HTTPException, status, Query

from app.audit import AUDIT_SERVICE, audit_event
from app.dependencies import require_api_key, require_bearer_payload
from app.models import BasicLogItem, EventLogItem, TelemetryLogItem, TelemetryLogResponse, EventLogResponse
from app.config import ELASTIC_URL
from pydantic import ValidationError


import json
import requests


router = APIRouter(prefix="/log", tags=["log"])


def _bulk_index(index: str, docs: list[dict]) -> int:
    if not docs:
        return 0

    lines: list[str] = []
    for doc in docs:
        lines.append(json.dumps({"index": {"_index": index}}, ensure_ascii=False))
        lines.append(json.dumps(doc, ensure_ascii=False))

    body = "\n".join(lines) + "\n"

    try:
        resp = requests.post(
            f"{ELASTIC_URL}/_bulk",
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/x-ndjson"},
            timeout=5,
        )
    except requests.RequestException:
        audit_event("error", f"action=bulk_index status=failure index={index} reason=connection_error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Log storage service is temporarily unavailable.",
        )

    if resp.status_code >= 300:
        audit_event("error", f"action=bulk_index status=failure index={index} reason=upstream_error http_status={resp.status_code}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Log storage service returned an internal error.",
        )

    try:
        payload = resp.json()
    except ValueError:
        audit_event("error", f"action=bulk_index status=failure index={index} reason=invalid_response")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Log storage service returned an invalid response.",
        )

    if not payload.get("errors"):
        return len(docs)

    items = payload.get("items", [])
    if not isinstance(items, list):
        audit_event("error", f"action=bulk_index status=failure index={index} reason=invalid_items_format")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Log storage service returned an invalid response.",
        )

    indexed = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        index_result = item.get("index", {})
        if isinstance(index_result, dict) and index_result.get("status", 500) < 300:
            indexed += 1

    if indexed == 0:
        audit_event("error", f"action=bulk_index status=failure index={index} accepted=0 total={len(docs)}")
    elif indexed < len(docs):
        audit_event("warning", f"action=bulk_index status=partial index={index} accepted={indexed} total={len(docs)}")

    return indexed


def _get_logs_from_index(index: str, start: int, size: int, exclude_service: str | None = None):
    query_body: dict = {
        "from": start,
        "size": size,
        "sort": [{"timestamp": {"order": "desc"}}],
    }
    if exclude_service:
        query_body["query"] = {
            "bool": {
                "must_not": [{"term": {"service": exclude_service}}]
            }
        }

    try:
        resp = requests.post(
            f"{ELASTIC_URL}/{index}/_search",
            json=query_body,
            timeout=5,
        )
    except requests.RequestException:
        audit_event("error", f"action=query status=failure index={index} reason=connection_error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Log storage service is temporarily unavailable.",
        )

    if resp.status_code >= 300:
        audit_event("error", f"action=query status=failure index={index} reason=upstream_error http_status={resp.status_code}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Log storage service returned an internal error.",
        )

    try:
        data = resp.json()
    except ValueError:
        audit_event("error", f"action=query status=failure index={index} reason=invalid_response")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Log storage service returned an invalid response.",
        )

    hits = data.get("hits", {}).get("hits", [])
    return [hit["_source"] for hit in hits]

@router.post("/telemetry")
def ingest_telemetry(
    payload: list[dict] = Body(..., min_length=1, max_length=1000),
    _: str = Depends(require_api_key),
) -> dict[str, int]:
    docs: list[dict] = []
    for item in payload:
        try:
            valid_item = TelemetryLogItem.model_validate(item)
        except ValidationError:
            continue
        doc = valid_item.model_dump()
        doc.pop("apiVersion", None)
        docs.append(doc)
    indexed = _bulk_index("telemetry", docs)
    audit_event("info", f"action=ingest_telemetry status=success received={len(payload)} validated={len(docs)} accepted={indexed}")
    return {"accepted": indexed}


@router.post("/basic")
def ingest_basic(
    payload: list[dict] = Body(..., min_length=1, max_length=1000),
    _: str = Depends(require_api_key),
) -> dict[str, int]:
    docs: list[dict] = []
    for item in payload:
        try:
            valid_item = BasicLogItem.model_validate(item)
        except ValidationError:
            continue
        docs.append(valid_item.model_dump())
    indexed = _bulk_index("basic", docs)
    audit_event("info", f"action=ingest_basic status=success received={len(payload)} validated={len(docs)} accepted={indexed}")
    return {"accepted": indexed}


@router.post("/event")
def ingest_event(
    payload: list[dict] = Body(..., min_length=1, max_length=1000),
    _: str = Depends(require_api_key),
) -> dict[str, int]:
    event_docs: list[dict] = []
    safety_docs: list[dict] = []

    for item in payload:
        try:
            valid_item = EventLogItem.model_validate(item)
        except ValidationError:
            continue
        doc = valid_item.model_dump()
        event_type = doc.pop("event_type", None)
        doc.pop("apiVersion", None)
        if event_type == "safety_event":
            safety_docs.append(doc)
        else:
            event_docs.append(doc)

    indexed = 0
    if event_docs:
        indexed += _bulk_index("event", event_docs)
    if safety_docs:
        indexed += _bulk_index("safety", safety_docs)

    audit_event(
        "info",
        f"action=ingest_event status=success received={len(payload)} accepted={indexed} event_count={len(event_docs)} safety_count={len(safety_docs)}",
    )
    return {"accepted": indexed}


@router.get(
    "/basic",
    response_model=list[BasicLogItem],
    summary="Get basic logs",
    description="Returns basic logs sorted by timestamp"
)
def get_basic(
    limit: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    _: dict = Depends(require_bearer_payload)
):
    start = (page - 1) * limit
    return _get_logs_from_index("basic", start, limit)


@router.get(
    "/telemetry",
    response_model=list[TelemetryLogResponse],
    summary="Get telemetry logs",
    description="Returns telemetry logs sorted by timestamp"
)
def get_telemetry(
    limit: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    _: dict = Depends(require_bearer_payload)
):
    start = (page - 1) * limit
    return _get_logs_from_index("telemetry", start, limit)


@router.get(
    "/event",
    response_model=list[EventLogResponse],
    summary="Get event logs",
    description="Returns event logs sorted by timestamp"
)
def get_event(
    limit: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    _: dict = Depends(require_bearer_payload)
):
    start = (page - 1) * limit
    return _get_logs_from_index("event", start, limit, exclude_service=AUDIT_SERVICE)


@router.get(
    "/safety",
    response_model=list[EventLogResponse],
    summary="Get safety event logs",
    description="Returns safety events sorted by timestamp"
)
def get_safety(
    limit: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    _: dict = Depends(require_bearer_payload)
):
    start = (page - 1) * limit
    return _get_logs_from_index("safety", start, limit, exclude_service=AUDIT_SERVICE)
