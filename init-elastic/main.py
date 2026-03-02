import os
import requests
import signal
import sys


def shutdown(signum, frame):
    print("Shutting down... I didn't have time to finish the script correctly.")
    sys.exit(0)

def main():
    ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elastic:9200")

    f_index = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "timestamp": { "type": "date", "format": "epoch_millis"},
                "drone": { "type": "keyword" },
                "drone_id": { "type": "short", "null_value": 1 },
                "battery": { "type": "short", "null_value": 100 },
                "pitch": {"type": "short", "null_value": "0"},
                "roll": {"type": "short", "null_value": "0"},
                "course": {"type": "short", "null_value": "0"},
                "latitude": {"type": "double"},
                "longitude": {"type": "double"},
            }
        }
    }

    s_index = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "timestamp": {"type": "date", "format": "epoch_millis"},
                "message": {"type": "text", "analyzer": "standard"}
            }
        }
    }

    t_index = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "timestamp": {"type": "date", "format": "epoch_millis"},
                "service": {"type": "keyword"},
                "service_id": { "type": "short", "null_value": 1 },
                "severity": {"type": "keyword"},
                "message": {"type": "text", "analyzer": "standard"}
            }
        }
    }

    fd_index = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "timestamp": {"type": "date", "format": "epoch_millis"},
                "service": {"type": "keyword"},
                "service_id": { "type": "short", "null_value": 1 },
                "severity": {"type": "keyword"},
                "message": {"type": "text", "analyzer": "standard"}
            }
        }
    }

    indexes = [(f_index, "telemetry"), (s_index, "basic"), (t_index, "event"), (fd_index, "safety")]
    try:
        for index, name in indexes:
            request = requests.put(
                f"{ELASTIC_URL}/{name}",
                json=f_index,
                timeout=10
            )
            if request.status_code >= 200 and request.status_code < 300:
                print(f"OK. Status code: {request.status_code}. Message: {request.text}")
            elif request.status_code == 400 and request.json()["error"]["type"] == "resource_already_exists_exception":
                print(f"OK. Status code: {request.status_code}. Message: {request.text}")
            else:
                print(f"Error. Status code: {request.status_code}. Message: {request.text}")
                sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error. Message: {e}")
        sys.exit(1)

signal.signal(signal.SIGTERM, shutdown)

if __name__ == "__main__":
    main()