#!/usr/bin/env bash
# Примерные логи на localhost через HTTPS (прокси /api → backend).
# Самоподписанный сертификат: по умолчанию curl -k (отключить проверку TLS).
#
#   ./scripts/seed_sample_logs.sh
#   BASE_URL=https://127.0.0.1/api X_API_KEY=change-me-api-key ./scripts/seed_sample_logs.sh
#
# CURL_INSECURE=0 — проверять сертификат (нужен доверенный CA).
set -euo pipefail

BASE_URL="${BASE_URL:-https://localhost/api}"
BASE_URL="${BASE_URL%/}"
X_API_KEY="${X_API_KEY:-${DRONE_API_KEY:-change-me-api-key}}"
CURL_INSECURE="${CURL_INSECURE:-1}"

curl_opts=(-sS -f)
if [[ "${CURL_INSECURE}" == "1" ]]; then
  curl_opts+=(-k)
fi

NOW_MS="$(($(date +%s) * 1000))"

post_json() {
  local url_path="$1"
  curl "${curl_opts[@]}" -X POST "${BASE_URL}${url_path}" \
    -H "Content-Type: application/json; charset=utf-8" \
    -H "X-API-Key: ${X_API_KEY}" \
    --data-binary @-
}

echo "POST ${BASE_URL}/log/basic ..."
post_json /log/basic <<EOF
[
  {"timestamp": $((NOW_MS)), "message": "[seed] basic heartbeat #1"},
  {"timestamp": $((NOW_MS - 60000)), "message": "[seed] basic heartbeat #2"},
  {"timestamp": $((NOW_MS - 120000)), "message": "[seed] basic heartbeat #3"}
]
EOF

echo "POST ${BASE_URL}/log/telemetry ..."
post_json /log/telemetry <<EOF
[
  {
    "apiVersion": "1.0.0",
    "timestamp": $((NOW_MS)),
    "drone": "delivery",
    "drone_id": 1,
    "battery": 82,
    "pitch": 1.2,
    "roll": -0.5,
    "course": 90.0,
    "latitude": 55.7522,
    "longitude": 37.6156
  },
  {
    "apiVersion": "1.0.0",
    "timestamp": $((NOW_MS - 120000)),
    "drone": "inspector",
    "drone_id": 2,
    "battery": 71,
    "latitude": 55.7530,
    "longitude": 37.6160
  }
]
EOF

echo "POST ${BASE_URL}/log/event ..."
post_json /log/event <<EOF
[
  {
    "apiVersion": "1.0.0",
    "timestamp": $((NOW_MS)),
    "event_type": "event",
    "service": "GCS",
    "service_id": 1,
    "severity": "info",
    "message": "[seed] GCS link check"
  },
  {
    "apiVersion": "1.0.0",
    "timestamp": $((NOW_MS - 60000)),
    "event_type": "safety_event",
    "service": "infopanel",
    "service_id": 1,
    "severity": "warning",
    "message": "[seed] safety demo: geofence proximity"
  }
]
EOF

echo "Готово."
