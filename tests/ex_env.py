#!/usr/bin/env python3
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://localhost/api"
API_KEY = "change-me"  # Replace with your actual API key

# Headers for authentication
headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def login():
    """
    Authenticate with the API and return authentication headers
    """
    login_url = f"{BASE_URL}/auth/login"
    login_data = {
        "username": USER,
        "password": PASSWORD
    }
    
    response = requests.post(login_url, json=login_data, verify=False)
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data["access_token"]
        print("Successfully authenticated")
        
        # Update headers with Bearer token for subsequent requests
        headers["Authorization"] = f"Bearer {access_token}"
    else:
        print("Authentication failed")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")

# Function to send POST request
def send_logs(endpoint, logs):
    url = f"{BASE_URL}{endpoint}"
    response = requests.post(url, headers=headers, data=json.dumps(logs), verify=False)

    if response.status_code == 200:
        print(f"Successfully sent logs to {endpoint}")
        print(f"Response: {response.json()}")
    else:
        print(f"Failed to send logs to {endpoint}")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")

def get_logs(endpoint, params=None):
    """
    Send GET request to retrieve logs from the specified endpoint
    """
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, headers=headers, params=params, verify=False)

    if response.status_code == 200:
        print(f"Successfully retrieved logs from {endpoint}")
        logs = response.json()
        print(f"Number of logs retrieved: {len(logs)}")
        return logs
    else:
        print(f"Failed to retrieve logs from {endpoint}")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return None

# Example telemetry logs
telemetry_logs = [
    {
        "apiVersion": "1.0.0",
        "timestamp": int(datetime.now().timestamp() * 1000),
        "drone": "delivery",
        "drone_id": 1,
        "battery": 75,
        "pitch": 5.5,
        "roll": 2.3,
        "course": 45.0,
        "latitude": 55.7558,
        "longitude": 37.6176
    },
    {
        "apiVersion": "1.0.0",
        "timestamp": int(datetime.now().timestamp() * 1000),
        "drone": "inspector",
        "drone_id": 2,
        "battery": 60,
        "pitch": 3.2,
        "roll": 1.8,
        "course": 90.0,
        "latitude": 59.9343,
        "longitude": 30.3351
    }
]

# Example basic logs
basic_logs = [
    {
        "timestamp": int(datetime.now().timestamp() * 1000),
        "message": "Drone system initialized successfully"
    },
    {
        "timestamp": int(datetime.now().timestamp() * 1000),
        "message": "Navigation system online"
    }
]

# Example event logs
event_logs = [
    {
        "apiVersion": "1.0.0",
        "timestamp": int(datetime.now().timestamp() * 1000),
        "event_type": "event",
        "service": "GCS",
        "service_id": 1,
        "severity": "info",
        "message": "Mission started successfully"
    },
    {
        "apiVersion": "1.0.0",
        "timestamp": int(datetime.now().timestamp() * 1000),
        "event_type": "safety_event",
        "service": "dronePort",
        "service_id": 2,
        "severity": "warning",
        "message": "High wind conditions detected"
    }
]

# Send all logs
print("Sending telemetry logs...")
send_logs("/log/telemetry", telemetry_logs)

print("\nSending basic logs...")
send_logs("/log/basic", basic_logs)

print("\nSending event logs...")
send_logs("/log/event", event_logs)

# ---

USER = "user"
PASSWORD = "password"

# Authentication
print("\nLogging in...")
login()

# Retrieve logs
print("\nRetrieving telemetry logs...")
get_logs("/log/telemetry", {"limit": 10, "page": 1})

print("\nRetrieving basic logs...")
get_logs("/log/basic", {"limit": 10, "page": 1})

print("\nRetrieving event logs...")
get_logs("/log/event", {"limit": 10, "page": 1})

print("\nRetrieving safety events...")
get_logs("/log/safety", {"limit": 10, "page": 1})
