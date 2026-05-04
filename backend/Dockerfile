FROM python:3.12.3-slim
RUN useradd appuser
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
# Создаем папку для данных покрытия и даем права appuser
RUN mkdir -p /app/coverage_data && chown appuser:appuser /app/coverage_data
USER appuser
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]