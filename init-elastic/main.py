import os
import requests
import signal
import sys


def shutdown(signum, frame):
    print("Shutting down... I didn't have time to finish the script correctly.")
    sys.exit(0)

def main():
    ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elastic:9200")
    ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD", "changeme")

    f_index = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "timestamp": { "type": "data", "format": "epoch_millis"},
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
    head = {
        "Content-Type": "application/json"
    }
    request = requests.put(f"{ELASTIC_URL}/telemetry", json=f_index, headers=head)
    if request.status_code >= 200 and request.status_code < 300:
        print(f"OK. Status code: {request.status_code}. Message: {request.text}")
    else:
        print(f"Error. Status code: {request.status_code}. Message: {request.text}")
        sys.exit(1)

signal.signal(signal.SIGTERM, shutdown)

if __name__ == "__main__":
    main()