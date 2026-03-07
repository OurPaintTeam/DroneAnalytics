from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.dependencies import require_api_key
from app.models import BasicLogItem, EventLogItem, TelemetryLogItem
from app.config import ELASTIC_URL


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

    payload = resp.json()
    if payload.get("errors"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Log storage service reported an internal error while processing the request.",
        )

    return len(docs)


@router.post("/telemetry")
def ingest_telemetry(
    payload: list[TelemetryLogItem] = Body(..., min_length=1, max_length=1000),
    _: str = Depends(require_api_key),
) -> dict[str, int]:
    docs = [item.model_dump() for item in payload]
    indexed = _bulk_index("telemetry", docs)
    return {"accepted": indexed}


@router.post("/basic")
def ingest_basic(
    payload: list[BasicLogItem] = Body(..., min_length=1, max_length=1000),
    _: str = Depends(require_api_key),
) -> dict[str, int]:
    docs = [item.model_dump() for item in payload]
    indexed = _bulk_index("basic", docs)
    return {"accepted": indexed}


@router.post("/event")
def ingest_event(
    payload: list[EventLogItem] = Body(..., min_length=1, max_length=1000),
    _: str = Depends(require_api_key),
) -> dict[str, int]:
    event_docs: list[dict] = []
    safety_docs: list[dict] = []

    for item in payload:
        doc = item.model_dump()
        if doc.get("event_type") == "safety_event":
            safety_docs.append(doc)
        else:
            event_docs.append(doc)

    indexed = 0
    if event_docs:
        indexed += _bulk_index("event", event_docs)
    if safety_docs:
        indexed += _bulk_index("safety", safety_docs)

    return {"accepted": indexed}
