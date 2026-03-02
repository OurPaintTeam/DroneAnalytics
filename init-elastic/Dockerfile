FROM python:3.12.3-slim

RUN useradd appuser

WORKDIR /app

COPY requirements.txt .
COPY main.py .

RUN pip install --no-cache-dir -r requirements.txt

USER appuser
ENTRYPOINT ["python", "main.py"]