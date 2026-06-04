FROM python:3.12.3-slim
RUN useradd appuser
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
USER appuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]