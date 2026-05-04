FROM python:3.12.3-slim
RUN useradd appuser
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/coverage_data && chown -R appuser:appuser /app/coverage_data
RUN chown -R appuser:appuser /app
USER appuser
CMD ["sh", "-c", "pytest ./"]