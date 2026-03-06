import os
import requests
import signal
import sys
import time


def shutdown(signum, frame):
    print("Shutting down... I didn't have time to finish the script correctly.")
    sys.exit(0)

def main():
    ELASTIC_URL = os.getenv("ELASTIC_URL", "http://localhost:9200")

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

    print("Waiting for ElasticSearch...")
    time.sleep(60)
    print("Trying to connect to ElasticSearch...")
    ok = False
    for i in range(1000):
        if i % 10 == 0:
            print("Trying to connect to ElasticSearch... -", i)
        try:
            request = requests.get(f"{ELASTIC_URL}/_cluster/health")
            if request.status_code == 200 and request.json()["status"] == "green":
                ok = True
                break
        except:
            continue
        time.sleep(1)
    if not ok:
        print("Error. I can't connect to ElasticSearch.")
        sys.exit(1)

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
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown)

if __name__ == "__main__":
    main()
