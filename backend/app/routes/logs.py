from fastapi import APIRouter, Body, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app.dependencies import require_api_key, require_bearer_payload
from app.models import BasicLogItem, EventLogItem, TelemetryLogItem, TelemetryLogResponse, EventLogResponse
from app.config import ELASTIC_URL
from pydantic import ValidationError


import json
import requests


router = APIRouter(prefix="/log", tags=["log"])


def _bulk_index(index: str, docs: list[dict], source_indices: list[int]) -> tuple[int, list[dict]]:
    if not docs:
        return 0, []

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
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Log storage service is temporarily unavailable.",
        )

    if resp.status_code >= 300:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Log storage service returned an internal error.",
        )

    try:
        payload = resp.json()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Log storage service returned an invalid response.",
        )

    if not payload.get("errors"):
        return len(docs), []

    items = payload.get("items", [])
    if not isinstance(items, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Log storage service returned an invalid response.",
        )

    indexed = 0
    failed_items: list[dict] = []
    for pos, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        index_result = item.get("index", {})
        if not isinstance(index_result, dict):
            continue
        if index_result.get("status", 500) < 300:
            indexed += 1
            continue
        error_obj = index_result.get("error")
        reason = "Indexing failed."
        if isinstance(error_obj, dict):
            reason = (
                error_obj.get("reason")
                or error_obj.get("type")
                or reason
            )
        failed_items.append(
            {
                "index": source_indices[pos] if pos < len(source_indices) else pos,
                "reason": reason,
            }
        )

    return indexed, failed_items


def _partial_or_ok_response(total: int, accepted: int, errors: list[dict]) -> JSONResponse:
    body = {
        "total": total,
        "accepted": accepted,
        "rejected": total - accepted,
        "errors": errors,
    }
    status_code = status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS
    return JSONResponse(status_code=status_code, content=body)


def _get_logs_from_index(index: str, start: int, size: int):
    try:
        resp = requests.post(
            f"{ELASTIC_URL}/{index}/_search",
            json={
                "from": start,
                "size": size,
                "sort": [{"timestamp": {"order": "desc"}}],
            },
            timeout=5,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Log storage service is temporarily unavailable.",
        )

    if resp.status_code >= 300:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Log storage service returned an internal error.",
        )

    try:
        data = resp.json()
    except ValueError:
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
) -> JSONResponse:
    docs: list[dict] = []
    valid_indices: list[int] = []
    errors: list[dict] = []
    for idx, item in enumerate(payload):
        try:
            valid_item = TelemetryLogItem.model_validate(item)
        except ValidationError as exc:
            validation_errors = exc.errors()
            reason = validation_errors[0].get("msg", "Validation failed.") if validation_errors else "Validation failed."
            errors.append({"index": idx, "reason": reason})
            continue
        doc = valid_item.model_dump()
        doc.pop("apiVersion", None)
        docs.append(doc)
        valid_indices.append(idx)
    indexed, indexing_errors = _bulk_index("telemetry", docs, valid_indices)
    return _partial_or_ok_response(len(payload), indexed, errors + indexing_errors)


@router.post("/basic")
def ingest_basic(
    payload: list[dict] = Body(..., min_length=1, max_length=1000),
    _: str = Depends(require_api_key),
) -> JSONResponse:
    docs: list[dict] = []
    valid_indices: list[int] = []
    errors: list[dict] = []
    for idx, item in enumerate(payload):
        try:
            valid_item = BasicLogItem.model_validate(item)
        except ValidationError as exc:
            validation_errors = exc.errors()
            reason = validation_errors[0].get("msg", "Validation failed.") if validation_errors else "Validation failed."
            errors.append({"index": idx, "reason": reason})
            continue
        docs.append(valid_item.model_dump())
        valid_indices.append(idx)
    indexed, indexing_errors = _bulk_index("basic", docs, valid_indices)
    return _partial_or_ok_response(len(payload), indexed, errors + indexing_errors)


@router.post("/event")
def ingest_event(
    payload: list[dict] = Body(..., min_length=1, max_length=1000),
    _: str = Depends(require_api_key),
) -> JSONResponse:
    event_docs: list[dict] = []
    safety_docs: list[dict] = []
    event_doc_indices: list[int] = []
    safety_doc_indices: list[int] = []
    errors: list[dict] = []

    for idx, item in enumerate(payload):
        try:
            valid_item = EventLogItem.model_validate(item)
        except ValidationError as exc:
            validation_errors = exc.errors()
            reason = validation_errors[0].get("msg", "Validation failed.") if validation_errors else "Validation failed."
            errors.append({"index": idx, "reason": reason})
            continue
        doc = valid_item.model_dump()
        event_type = doc.pop("event_type", None)
        doc.pop("apiVersion", None)
        if event_type == "safety_event":
            safety_docs.append(doc)
            safety_doc_indices.append(idx)
        else:
            event_docs.append(doc)
            event_doc_indices.append(idx)

    indexed = 0
    if event_docs:
        event_indexed, event_errors = _bulk_index("event", event_docs, event_doc_indices)
        indexed += event_indexed
        errors.extend(event_errors)
    if safety_docs:
        safety_indexed, safety_errors = _bulk_index("safety", safety_docs, safety_doc_indices)
        indexed += safety_indexed
        errors.extend(safety_errors)

    return _partial_or_ok_response(len(payload), indexed, errors)


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
    return _get_logs_from_index("event", start, limit)


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
    return _get_logs_from_index("safety", start, limit)