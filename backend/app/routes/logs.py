from fastapi import APIRouter, Body, Depends

from app.dependencies import require_api_key
from app.models import BasicLogItem, EventLogItem, TelemetryLogItem


router = APIRouter(prefix="/log", tags=["log"])


@router.post("/telemetry")
def ingest_telemetry(
    payload: list[TelemetryLogItem] = Body(..., min_length=1, max_length=1000),
    _: str = Depends(require_api_key),
) -> dict[str, int]:
    return {"accepted": len(payload)}


@router.post("/basic")
def ingest_basic(
    payload: list[BasicLogItem] = Body(..., min_length=1, max_length=1000),
    _: str = Depends(require_api_key),
) -> dict[str, int]:
    return {"accepted": len(payload)}


@router.post("/event")
def ingest_event(
    payload: list[EventLogItem] = Body(..., min_length=1, max_length=1000),
    _: str = Depends(require_api_key),
) -> dict[str, int]:
    return {"accepted": len(payload)}
