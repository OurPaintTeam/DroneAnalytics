import os
import requests
import signal
import sys
import time
import yaml


def shutdown(signum, frame):
    print("Shutting down... I didn't have time to finish the script correctly.")
    sys.exit(0)

def main():
    # Загрузка конфигурации из файла
    try:
        with open('/etc/init-elastic.yaml', 'r') as file:
            config = yaml.safe_load(file)
        ELASTIC_URL = config.get('elastic_url', 'http://elastic:9200')
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    telemetry = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "timestamp": { "type": "date", "format": "epoch_millis"},
                "drone": { "type": "keyword" },
                "drone_id": { "type": "short", "null_value": 1 },
                "battery": { "type": "short", "null_value": 100 },
                "pitch": {"type": "double", "null_value": "0"},
                "roll": {"type": "double", "null_value": "0"},
                "course": {"type": "double", "null_value": "0"},
                "latitude": {"type": "double"},
                "longitude": {"type": "double"},
                "height": {"type": "double", "null_value": "0"}
            }
        }
    }

    basic = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "timestamp": {"type": "date", "format": "epoch_millis"},
                "message": {"type": "text", "analyzer": "standard"}
            }
        }
    }

    event = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "timestamp": {"type": "date", "format": "epoch_millis"},
                "service": {"type": "keyword"},
                "service_id": { "type": "short", "null_value": 1 },
                "severity": {"type": "keyword"},
                "message": {"type": "text", "analyzer": "standard"}
            }
        }
    }

    safety = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "timestamp": {"type": "date", "format": "epoch_millis"},
                "service": {"type": "keyword"},
                "service_id": { "type": "short", "null_value": 1 },
                "severity": {"type": "keyword"},
                "message": {"type": "text", "analyzer": "standard"}
            }
        }
    }

    indexes = [(telemetry, "telemetry"), (basic, "basic"), (event, "event"), (safety, "safety")]

    print("Waiting for ElasticSearch...")
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
            time.sleep(5)
            continue
        time.sleep(5)
    if not ok:
        print("Error. I can't connect to ElasticSearch.")
        sys.exit(1)

    try:
        for index, name in indexes:
            request = requests.put(
                f"{ELASTIC_URL}/{name}",
                json=index,
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
