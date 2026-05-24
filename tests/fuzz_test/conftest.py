import os
from typing import Dict

import pytest


BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8080")
API_KEY = os.getenv("DRONE_API_KEY", "change-me-api-key")


@pytest.fixture
def api_headers() -> Dict[str, str]:
    """Headers for authenticated ingest endpoints."""
    return {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    }
