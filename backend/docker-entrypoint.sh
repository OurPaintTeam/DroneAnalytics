#!/bin/bash
set -e

if [ "$COVERAGE_MODE" = "true" ]; then
    echo "Starting backend with coverage..."
    # Запускаем coverage с явным указанием пути к файлу данных и source
    exec coverage run --parallel-mode --source=/app/app --data-file=/app/coverage_data/.coverage -m uvicorn main:app --host 0.0.0.0 --port 8080
else
    echo "Starting backend in normal mode..."
    exec uvicorn main:app --host 0.0.0.0 --port 8080
fi