import json
import logging
import time

import requests

from app.config import ELASTIC_URL


AUDIT_SERVICE = "infopanel"
AUDIT_SERVICE_ID = 1

_logger = logging.getLogger("droneanalytics.audit")

_SEVERITY_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "notice": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "alert": logging.CRITICAL,
    "emergency": logging.CRITICAL,
}


def _emit(index: str, doc: dict) -> None:
    body = (
        json.dumps({"index": {"_index": index}}) + "\n"
        + json.dumps(doc, ensure_ascii=False) + "\n"
    )
    try:
        requests.post(
            f"{ELASTIC_URL}/_bulk",
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/x-ndjson"},
            timeout=2,
        )
    except Exception:
        _logger.warning("Elasticsearch unavailable for audit index=%s", index)


def audit_event(severity: str, message: str) -> None:
    doc = {
        "timestamp": int(time.time() * 1000),
        "service": AUDIT_SERVICE,
        "service_id": AUDIT_SERVICE_ID,
        "severity": severity,
        "message": message,
    }
    _logger.log(_SEVERITY_MAP.get(severity, logging.INFO), "[event] %s", message)
    _emit("event", doc)


def audit_safety(severity: str, message: str) -> None:
    doc = {
        "timestamp": int(time.time() * 1000),
        "service": AUDIT_SERVICE,
        "service_id": AUDIT_SERVICE_ID,
        "severity": severity,
        "message": message,
    }
    _logger.log(_SEVERITY_MAP.get(severity, logging.INFO), "[safety] %s", message)
    _emit("safety", doc)
