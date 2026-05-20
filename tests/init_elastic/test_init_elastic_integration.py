import os
import time
from typing import Any, Dict

import pytest
import requests


ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elastic:9200")

EXPECTED_INDEX_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "telemetry": {
        "settings": {"number_of_shards": "1", "number_of_replicas": "0"},
        "dynamic": "strict",
        "properties": {
            "timestamp": {"type": "date", "format": "epoch_millis"},
            "drone": {"type": "keyword"},
            "drone_id": {"type": "short", "null_value": 1},
            "battery": {"type": "short", "null_value": 100},
            "pitch": {"type": "double", "null_value": 0},
            "roll": {"type": "double", "null_value": 0},
            "course": {"type": "double", "null_value": 0},
            "latitude": {"type": "double"},
            "longitude": {"type": "double"},
            "height": {"type": "double", "null_value": 0},
        },
    },
    "basic": {
        "settings": {"number_of_shards": "1", "number_of_replicas": "0"},
        "dynamic": "strict",
        "properties": {
            "timestamp": {"type": "date", "format": "epoch_millis"},
            "message": {"type": "text", "analyzer": "standard"},
        },
    },
    "event": {
        "settings": {"number_of_shards": "1", "number_of_replicas": "0"},
        "dynamic": "strict",
        "properties": {
            "timestamp": {"type": "date", "format": "epoch_millis"},
            "service": {"type": "keyword"},
            "service_id": {"type": "short", "null_value": 1},
            "severity": {"type": "keyword"},
            "message": {"type": "text", "analyzer": "standard"},
        },
    },
    "safety": {
        "settings": {"number_of_shards": "1", "number_of_replicas": "0"},
        "dynamic": "strict",
        "properties": {
            "timestamp": {"type": "date", "format": "epoch_millis"},
            "service": {"type": "keyword"},
            "service_id": {"type": "short", "null_value": 1},
            "severity": {"type": "keyword"},
            "message": {"type": "text", "analyzer": "standard"},
        },
    },
}


def _wait_for_elastic(timeout_seconds: int = 60) -> None:
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            response = requests.get(f"{ELASTIC_URL}/_cluster/health", timeout=3)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    pytest.skip(f"ElasticSearch is unavailable at {ELASTIC_URL}")


@pytest.fixture(scope="session", autouse=True)
def ensure_elastic_ready() -> None:
    _wait_for_elastic(timeout_seconds=90)


@pytest.mark.parametrize("index_name", sorted(EXPECTED_INDEX_DEFINITIONS.keys()))
def test_init_elastic_creates_expected_indices(index_name: str) -> None:
    response = requests.get(f"{ELASTIC_URL}/{index_name}", timeout=5)
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("index_name,expected", sorted(EXPECTED_INDEX_DEFINITIONS.items()))
def test_init_elastic_applies_expected_settings(index_name: str, expected: Dict[str, Any]) -> None:
    response = requests.get(f"{ELASTIC_URL}/{index_name}/_settings", timeout=5)
    assert response.status_code == 200, response.text

    index_settings = response.json()[index_name]["settings"]["index"]
    assert index_settings["number_of_shards"] == expected["settings"]["number_of_shards"]
    assert index_settings["number_of_replicas"] == expected["settings"]["number_of_replicas"]


@pytest.mark.parametrize("index_name,expected", sorted(EXPECTED_INDEX_DEFINITIONS.items()))
def test_init_elastic_applies_expected_mappings(index_name: str, expected: Dict[str, Any]) -> None:
    response = requests.get(f"{ELASTIC_URL}/{index_name}/_mapping", timeout=5)
    assert response.status_code == 200, response.text

    mapping = response.json()[index_name]["mappings"]
    assert mapping.get("dynamic") == expected["dynamic"]

    actual_properties = mapping.get("properties", {})
    assert set(actual_properties.keys()) == set(expected["properties"].keys())

    for field_name, expected_config in expected["properties"].items():
        field_mapping = actual_properties[field_name]
        assert field_mapping.get("type") == expected_config["type"]

        if "format" in expected_config:
            assert field_mapping.get("format") == expected_config["format"]

        if "analyzer" in expected_config:
            assert field_mapping.get("analyzer") == expected_config["analyzer"]

        if "null_value" in expected_config:
            assert field_mapping.get("null_value") == expected_config["null_value"]


def test_init_elastic_mappings_reject_unknown_fields_due_to_strict_mode() -> None:
    unique_index = "telemetry"
    invalid_doc = {
        "timestamp": 1716200000000,
        "drone": "delivery",
        "latitude": 59.93,
        "longitude": 30.31,
        "unexpected_field": "should fail",
    }

    response = requests.post(
        f"{ELASTIC_URL}/{unique_index}/_doc",
        json=invalid_doc,
        timeout=5,
    )

    assert response.status_code == 400, response.text
    body = response.json()
    reason = body.get("error", {}).get("reason", "")
    assert "strict_dynamic_mapping_exception" in response.text or "dynamic introduction" in reason


@pytest.mark.parametrize(
    "index_name,document",
    [
        (
            "telemetry",
            {
                "timestamp": 1716200001000,
                "drone": "delivery",
                "drone_id": 7,
                "battery": 55,
                "pitch": 1.0,
                "roll": 0.0,
                "course": 180.0,
                "latitude": 59.93,
                "longitude": 30.31,
                "height": 120.0,
            },
        ),
        (
            "basic",
            {
                "timestamp": 1716200001001,
                "message": "basic integration check",
            },
        ),
        (
            "event",
            {
                "timestamp": 1716200001002,
                "service": "gcs",
                "service_id": 1,
                "severity": "info",
                "message": "event integration check",
            },
        ),
        (
            "safety",
            {
                "timestamp": 1716200001003,
                "service": "dronePort",
                "service_id": 2,
                "severity": "warning",
                "message": "safety integration check",
            },
        ),
    ],
)
def test_init_elastic_indices_accept_valid_documents(index_name: str, document: Dict[str, Any]) -> None:
    response = requests.post(f"{ELASTIC_URL}/{index_name}/_doc?refresh=true", json=document, timeout=5)
    assert response.status_code in (200, 201), response.text

    doc_id = response.json()["_id"]
    get_response = requests.get(f"{ELASTIC_URL}/{index_name}/_doc/{doc_id}", timeout=5)
    assert get_response.status_code == 200, get_response.text
    source = get_response.json().get("_source", {})

    for key, value in document.items():
        assert source.get(key) == value
