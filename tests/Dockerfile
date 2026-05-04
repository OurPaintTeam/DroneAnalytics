FROM python:3.12.3-slim
RUN useradd appuser
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/coverage_data && chown -R appuser:appuser /app/coverage_data
RUN chown -R appuser:appuser /app
USER appuser
CMD ["sh", "-c", "pytest ./proxy && sleep 3 && if ls /app/coverage_data/.coverage.* 1>/dev/null 2>&1; then coverage combine --keep /app/coverage_data/.coverage.* 2>/dev/null || true; COVERAGE_RCFILE=/dev/null coverage report --fail-under=0 --show-missing; else echo 'No coverage data found in /app/coverage_data/'; fi"]