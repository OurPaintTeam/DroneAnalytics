FROM python:3.12.3-slim
RUN useradd appuser
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN chown -R appuser:appuser /app
USER appuser
CMD ["pytest", "./endpoints/", "-v", "-s"]