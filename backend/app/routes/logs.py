from fastapi import APIRouter, Body, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app.audit import AUDIT_SERVICE, audit_event
from app.dependencies import require_api_key, require_bearer_payload
from app.models import (
    BasicLogItem,
    EventLogItem,
    EventLogResponse,
    LogDroneType,
    LogServiceType,
    LogSeverityType,
    TelemetryLogItem,
    TelemetryLogResponse,
)
from app.log_search import build_log_list_query, validate_timestamp_range
from app.config import ELASTIC_URL
from pydantic import ValidationError

import io
import csv
from typing import Iterable, Optional

from fastapi.responses import StreamingResponse

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
        audit_event("info", f"action=bulk_index status=success index={index} accepted={len(docs)} total={len(docs)}")
        return len(docs), []
    items = payload.get("items", [])
    if not isinstance(items, list):
        audit_event("error", f"action=bulk_index status=failure index={index} reason=invalid_items_format")
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
    if indexed == 0:
        audit_event("error", f"action=bulk_index status=failure index={index} accepted=0 total={len(docs)}")
    elif indexed < len(docs):
        audit_event("warning", f"action=bulk_index status=partial index={index} accepted={indexed} total={len(docs)}")
    else:
        audit_event("info", f"action=bulk_index status=success index={index} accepted={indexed} total={len(docs)}")
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


def _get_logs_from_index(
    index: str,
    start: int,
    size: int,
    *,
    exclude_service: str | None = None,
    from_ts: int | None = None,
    to_ts: int | None = None,
    term_filters: dict[str, str | int] | None = None,
    message_match: str | None = None,
):
    query_body: dict = {
        "from": start,
        "size": size,
        "sort": [{"timestamp": {"order": "desc"}}],
    }
    q = build_log_list_query(
        exclude_service=exclude_service,
        from_ts=from_ts,
        to_ts=to_ts,
        term_filters=term_filters,
        message_match=message_match,
    )
    if q is not None:
        query_body["query"] = q

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



def _es_scroll_iter(
    index: str,
    from_ms: Optional[int],
    to_ms: Optional[int],
    _source: Optional[list] = None,
    batch_size: int = 1000,
    *,
    exclude_service: str | None = None,
    term_filters: dict[str, str | int] | None = None,
    message_match: str | None = None,
):
    """
    Итератор, который возвращает документы из ES используя scroll API.
    Пагинация выполняется через scroll, возвращает документный _source словарь.
    Сортировка: timestamp desc
    """
    query: dict = {
        "size": batch_size,
        "sort": [{"timestamp": {"order": "desc"}}],
    }
    q = build_log_list_query(
        exclude_service=exclude_service,
        from_ts=from_ms,
        to_ts=to_ms,
        term_filters=term_filters,
        message_match=message_match,
    )
    if q is not None:
        query["query"] = q
    if _source is not None:
        query["_source"] = _source

    try:
        # initial search with scroll
        resp = requests.post(f"{ELASTIC_URL}/{index}/_search?scroll=1m", json=query, timeout=30)
    except requests.RequestException:
        audit_event("error", f"action=download_query status=failure index={index} reason=connection_error")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Log storage service is temporarily unavailable.")

    if resp.status_code >= 300:
        audit_event("error", f"action=download_query status=failure index={index} reason=upstream_error http_status={resp.status_code}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Log storage service returned an internal error.")

    try:
        data = resp.json()
    except ValueError:
        audit_event("error", f"action=download_query status=failure index={index} reason=invalid_json")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Log storage service returned an invalid response.")

    scroll_id = data.get("_scroll_id")
    hits = data.get("hits", {}).get("hits", [])
    for h in hits:
        yield h.get("_source", {})

    # loop scroll
    while True:
        if not scroll_id:
            break
        try:
            resp2 = requests.post(f"{ELASTIC_URL}/_search/scroll", json={"scroll": "1m", "scroll_id": scroll_id}, timeout=30)
        except requests.RequestException:
            audit_event("error", f"action=download_scroll status=failure index={index} reason=connection_error")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Log storage service is temporarily unavailable.")

        if resp2.status_code >= 300:
            audit_event("error", f"action=download_scroll status=failure index={index} reason=upstream_error http_status={resp2.status_code}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Log storage service returned an internal error.")

        try:
            data2 = resp2.json()
        except ValueError:
            audit_event("error", f"action=download_scroll status=failure index={index} reason=invalid_json")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Log storage service returned an invalid response.")

        scroll_id = data2.get("_scroll_id")
        hits2 = data2.get("hits", {}).get("hits", [])
        if not hits2:
            break
        for h in hits2:
            yield h.get("_source", {})

    # try to clear scroll (best-effort). Swallow errors but record them for diagnostics.
    try:
        if scroll_id:
            requests.delete(f"{ELASTIC_URL}/_search/scroll", json={"scroll_id": [scroll_id]}, timeout=5)
    except Exception as e:
        audit_event("error", f"action=clear_scroll status=failure index={index} reason={type(e).__name__}")


def _es_scroll_iter_multi(indices: str, from_ms: Optional[int], to_ms: Optional[int], _source: Optional[list] = None, batch_size: int = 1000):
    """
    Multi-index scroll iterator. Возвращает документы из нескольких индексов ES, отсортированные по timestamp desc.
    Обрабатывает ошибки так же, как `_es_scroll_iter` (connection error, http status, invalid json) и очищает scroll в finally.
    Каждый yielded документ — копия _source с дополнительным полем "index".
    """
    query: dict = {
        "size": batch_size,
        "sort": [{"timestamp": {"order": "desc"}}],
    }

    bool_filter = []
    if from_ms is not None or to_ms is not None:
        rng: dict = {}
        if from_ms is not None:
            rng["gte"] = from_ms
        if to_ms is not None:
            rng["lte"] = to_ms
        bool_filter.append({"range": {"timestamp": rng}})

    if bool_filter:
        query["query"] = {"bool": {"filter": bool_filter}}
    if _source is not None:
        query["_source"] = _source

    try:
        resp = requests.post(f"{ELASTIC_URL}/{indices}/_search?scroll=1m", json=query, timeout=30)
    except requests.RequestException:
        audit_event("error", f"action=download_query status=failure index={indices} reason=connection_error")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Log storage service is temporarily unavailable.")

    if resp.status_code >= 300:
        audit_event("error", f"action=download_query status=failure index={indices} reason=upstream_error http_status={resp.status_code}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Log storage service returned an internal error.")

    try:
        data = resp.json()
    except ValueError:
        audit_event("error", f"action=download_query status=failure index={indices} reason=invalid_json")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Log storage service returned an invalid response.")

    scroll_id = data.get("_scroll_id")
    try:
        hits = data.get("hits", {}).get("hits", [])
        for h in hits:
            src = dict(h.get("_source", {}))
            src["index"] = h.get("_index")
            yield src

        # loop scroll
        while True:
            if not scroll_id:
                break
            try:
                resp2 = requests.post(
                    f"{ELASTIC_URL}/_search/scroll",
                    json={"scroll": "1m", "scroll_id": scroll_id},
                    timeout=30,
                )
            except requests.RequestException:
                audit_event("error", f"action=download_scroll status=failure index={indices} reason=connection_error")
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Log storage service is temporarily unavailable.")

            if resp2.status_code >= 300:
                audit_event("error", f"action=download_scroll status=failure index={indices} reason=upstream_error http_status={resp2.status_code}")
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Log storage service returned an internal error.")

            try:
                data2 = resp2.json()
            except ValueError:
                audit_event("error", f"action=download_scroll status=failure index={indices} reason=invalid_json")
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Log storage service returned an invalid response.")

            scroll_id = data2.get("_scroll_id")
            hits2 = data2.get("hits", {}).get("hits", [])
            if not hits2:
                break
            for h in hits2:
                src = dict(h.get("_source", {}))
                src["index"] = h.get("_index")
                yield src

    finally:
        # try to clear scroll (best-effort)
        try:
            if scroll_id:
                requests.delete(f"{ELASTIC_URL}/_search/scroll", json={"scroll_id": [scroll_id]}, timeout=5)
        except Exception as exc:
            # Log but do not propagate errors during scroll cleanup to avoid masking original issues.
            audit_event("error", f"action=download_query status=failure index={indices} reason=scroll_clear_failed error={exc}")


def _csv_bytes_generator(rows_iter: Iterable[dict], fieldnames: list[str]):
    buf = io.StringIO()
    writer = csv.writer(buf)
    # header
    writer.writerow(fieldnames)
    yield buf.getvalue().encode("utf-8")
    buf.seek(0)
    buf.truncate(0)
    # rows
    for doc in rows_iter:
        row = []
        for f in fieldnames:
            v = doc.get(f, "")
            if v is None:
                v = ""
            if isinstance(v, (dict, list)):
                try:
                    v = json.dumps(v, ensure_ascii=False)
                except Exception:
                    v = str(v)
            row.append(str(v))
        writer.writerow(row)
        yield buf.getvalue().encode("utf-8")
        buf.seek(0)
        buf.truncate(0)


def _make_filename(base: str, from_ts: Optional[int], to_ts: Optional[int]) -> str:
    if from_ts or to_ts:
        return f"{base}_{from_ts or 'all'}_{to_ts or 'all'}.csv"
    return f"{base}_all.csv"


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

    total = len(payload)
    all_errors = errors + indexing_errors
    if indexed == 0:
        status_str = "failure"
    elif all_errors:
        status_str = "partial"
    else:
        status_str = "success"

    audit_event(
        "info",
        f"action=ingest_telemetry status={status_str} "
        f"received={total} validated={len(docs)} accepted={indexed} rejected={total - indexed}"
    )

    return _partial_or_ok_response(total, indexed, all_errors)


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
    total = len(payload)
    all_errors = errors + indexing_errors
    if indexed == 0:
        status_str = "failure"
    elif all_errors:
        status_str = "partial"
    else:
        status_str = "success"
    audit_event(
        "info",
        f"action=ingest_basic status={status_str} "
        f"received={total} validated={len(docs)} accepted={indexed} rejected={total - indexed}"
    )
    return _partial_or_ok_response(total, indexed, all_errors)


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

    total = len(payload)
    if indexed == 0:
        status_str = "failure"
    elif errors:
        status_str = "partial"
    else:
        status_str = "success"

    audit_event(
        "info",
        f"action=ingest_event status={status_str} "
        f"received={total} accepted={indexed} "
        f"event_count={len(event_docs)} safety_count={len(safety_docs)} rejected={total - indexed}",
    )

    return _partial_or_ok_response(total, indexed, errors)


@router.get(
    "/basic",
    response_model=list[BasicLogItem],
    summary="Get basic logs",
    description="Returns basic logs sorted by timestamp"
)
def get_basic(
    limit: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    from_ts: int | None = Query(None, ge=0, description="Нижняя граница timestamp (мс), включительно"),
    to_ts: int | None = Query(None, ge=0, description="Верхняя граница timestamp (мс), включительно"),
    message: str | None = Query(None, max_length=512, description="Полнотекстовый поиск по полю message"),
    _: dict = Depends(require_bearer_payload),
):
    validate_timestamp_range(from_ts, to_ts)
    message_match = message.strip() if message else None
    if message_match == "":
        message_match = None
    start = (page - 1) * limit
    return _get_logs_from_index(
        "basic",
        start,
        limit,
        from_ts=from_ts,
        to_ts=to_ts,
        message_match=message_match,
    )


@router.get(
    "/telemetry",
    response_model=list[TelemetryLogResponse],
    summary="Get telemetry logs",
    description="Returns telemetry logs sorted by timestamp"
)
def get_telemetry(
    limit: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    from_ts: int | None = Query(None, ge=0, description="Нижняя граница timestamp (мс), включительно"),
    to_ts: int | None = Query(None, ge=0, description="Верхняя граница timestamp (мс), включительно"),
    drone: LogDroneType | None = Query(None),
    drone_id: int | None = Query(None, ge=1),
    _: dict = Depends(require_bearer_payload),
):
    validate_timestamp_range(from_ts, to_ts)
    term_filters: dict[str, str | int] = {}
    if drone is not None:
        term_filters["drone"] = drone
    if drone_id is not None:
        term_filters["drone_id"] = drone_id
    start = (page - 1) * limit
    return _get_logs_from_index(
        "telemetry",
        start,
        limit,
        from_ts=from_ts,
        to_ts=to_ts,
        term_filters=term_filters if term_filters else None,
    )


@router.get(
    "/event",
    response_model=list[EventLogResponse],
    summary="Get event logs",
    description="Returns event logs sorted by timestamp"
)
def get_event(
    limit: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    from_ts: int | None = Query(None, ge=0, description="Нижняя граница timestamp (мс), включительно"),
    to_ts: int | None = Query(None, ge=0, description="Верхняя граница timestamp (мс), включительно"),
    service: LogServiceType | None = Query(None),
    service_id: int | None = Query(None, ge=1),
    severity: LogSeverityType | None = Query(None),
    message: str | None = Query(None, max_length=512, description="Полнотекстовый поиск по полю message"),
    _: dict = Depends(require_bearer_payload),
):
    validate_timestamp_range(from_ts, to_ts)
    message_match = message.strip() if message else None
    if message_match == "":
        message_match = None
    term_filters: dict[str, str | int] = {}
    if service is not None:
        term_filters["service"] = service
    if service_id is not None:
        term_filters["service_id"] = service_id
    if severity is not None:
        term_filters["severity"] = severity
    start = (page - 1) * limit
    return _get_logs_from_index(
        "event",
        start,
        limit,
        exclude_service=AUDIT_SERVICE,
        from_ts=from_ts,
        to_ts=to_ts,
        term_filters=term_filters if term_filters else None,
        message_match=message_match,
    )


@router.get(
    "/safety",
    response_model=list[EventLogResponse],
    summary="Get safety event logs",
    description="Returns safety events sorted by timestamp"
)
def get_safety(
    limit: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    from_ts: int | None = Query(None, ge=0, description="Нижняя граница timestamp (мс), включительно"),
    to_ts: int | None = Query(None, ge=0, description="Верхняя граница timestamp (мс), включительно"),
    service: LogServiceType | None = Query(None),
    service_id: int | None = Query(None, ge=1),
    severity: LogSeverityType | None = Query(None),
    message: str | None = Query(None, max_length=512, description="Полнотекстовый поиск по полю message"),
    _: dict = Depends(require_bearer_payload),
):
    validate_timestamp_range(from_ts, to_ts)
    message_match = message.strip() if message else None
    if message_match == "":
        message_match = None
    term_filters: dict[str, str | int] = {}
    if service is not None:
        term_filters["service"] = service
    if service_id is not None:
        term_filters["service_id"] = service_id
    if severity is not None:
        term_filters["severity"] = severity
    start = (page - 1) * limit
    return _get_logs_from_index(
        "safety",
        start,
        limit,
        exclude_service=AUDIT_SERVICE,
        from_ts=from_ts,
        to_ts=to_ts,
        term_filters=term_filters if term_filters else None,
        message_match=message_match,
    )


@router.get("/download/basic", summary="Download basic logs as CSV (by timestamp range)")
def download_basic_csv(
    from_ts: int | None = Query(None, description="Unix timestamp (ms) start"),
    to_ts: int | None = Query(None, description="Unix timestamp (ms) end"),
    message: str | None = Query(None, max_length=512, description="Full-text search in message"),
    _: dict = Depends(require_bearer_payload),
):
    validate_timestamp_range(from_ts, to_ts)
    message_match = message.strip() if message else None
    if message_match == "":
        message_match = None
    fieldnames = ["timestamp", "message"]

    rows_iter = _es_scroll_iter(
        "basic",
        from_ts,
        to_ts,
        _source=fieldnames,
        message_match=message_match,
    )

    filename = _make_filename("basic_logs", from_ts, to_ts)

    generator = _csv_bytes_generator(rows_iter, fieldnames)

    return StreamingResponse(
        generator,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )



@router.get("/download/telemetry", summary="Download telemetry logs as CSV (by timestamp range)")
def download_telemetry_csv(
    from_ts: int | None = Query(None, description="Unix timestamp (ms) start"),
    to_ts: int | None = Query(None, description="Unix timestamp (ms) end"),
    drone: LogDroneType | None = Query(None),
    drone_id: int | None = Query(None, ge=1),
    _: dict = Depends(require_bearer_payload),
):
    validate_timestamp_range(from_ts, to_ts)
    term_filters: dict[str, str | int] = {}
    if drone is not None:
        term_filters["drone"] = drone
    if drone_id is not None:
        term_filters["drone_id"] = drone_id

    fieldnames = ["timestamp", "drone", "drone_id", "battery", "pitch", "roll", "course", "latitude", "longitude"]

    rows_iter = _es_scroll_iter(
        "telemetry",
        from_ts,
        to_ts,
        _source=fieldnames,
        term_filters=term_filters if term_filters else None,
    )

    filename = _make_filename("telemetry_logs", from_ts, to_ts)

    generator = _csv_bytes_generator(rows_iter, fieldnames)

    return StreamingResponse(
        generator,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )



@router.get("/download/event", summary="Download event logs as CSV (by timestamp range)")
def download_event_csv(
    from_ts: int | None = Query(None, description="Unix timestamp (ms) start"),
    to_ts: int | None = Query(None, description="Unix timestamp (ms) end"),
    service: LogServiceType | None = Query(None),
    service_id: int | None = Query(None, ge=1),
    severity: LogSeverityType | None = Query(None),
    _: dict = Depends(require_bearer_payload),
):
    validate_timestamp_range(from_ts, to_ts)
    term_filters: dict[str, str | int] = {}
    if service is not None:
        term_filters["service"] = service
    if service_id is not None:
        term_filters["service_id"] = service_id
    if severity is not None:
        term_filters["severity"] = severity

    fieldnames = ["timestamp", "service", "service_id", "severity", "message"]

    rows_iter = _es_scroll_iter(
        "event",
        from_ts,
        to_ts,
        _source=fieldnames,
        exclude_service=AUDIT_SERVICE,
        term_filters=term_filters if term_filters else None,
    )

    filename = _make_filename("event_logs", from_ts, to_ts)

    generator = _csv_bytes_generator(rows_iter, fieldnames)

    return StreamingResponse(
        generator,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )



@router.get("/download/safety", summary="Download safety logs as CSV (by timestamp range)")
def download_safety_csv(
    from_ts: int | None = Query(None, description="Unix timestamp (ms) start"),
    to_ts: int | None = Query(None, description="Unix timestamp (ms) end"),
    service: LogServiceType | None = Query(None),
    service_id: int | None = Query(None, ge=1),
    severity: LogSeverityType | None = Query(None),
    _: dict = Depends(require_bearer_payload),
):
    validate_timestamp_range(from_ts, to_ts)
    term_filters: dict[str, str | int] = {}
    if service is not None:
        term_filters["service"] = service
    if service_id is not None:
        term_filters["service_id"] = service_id
    if severity is not None:
        term_filters["severity"] = severity

    fieldnames = ["timestamp", "service", "service_id", "severity", "message"]

    rows_iter = _es_scroll_iter(
        "safety",
        from_ts,
        to_ts,
        _source=fieldnames,
        exclude_service=AUDIT_SERVICE,
        term_filters=term_filters if term_filters else None,
    )

    filename = _make_filename("safety_logs", from_ts, to_ts)

    generator = _csv_bytes_generator(rows_iter, fieldnames)

    return StreamingResponse(
        generator,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )



@router.get("/download/all")
def download_all_csv(
    from_ts: int | None = Query(None, description="Unix timestamp (ms) start"),
    to_ts: int | None = Query(None, description="Unix timestamp (ms) end"),
    _: dict = Depends(require_bearer_payload),
):

    rows_iter = _es_scroll_iter_multi(
        "basic,telemetry,event,safety",
        from_ts,
        to_ts
    )

    fieldnames = [
        "index",
        "timestamp",
        "message",
        "drone",
        "drone_id",
        "battery",
        "pitch",
        "roll",
        "course",
        "latitude",
        "longitude",
        "service",
        "service_id",
        "severity",
    ]

    filename = _make_filename("all_logs", from_ts, to_ts)

    generator = _csv_bytes_generator(rows_iter, fieldnames)

    return StreamingResponse(
        generator,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
