# Bookmark Fetcher Dockerfile

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fetcher ./fetcher
COPY config.py .

RUN mkdir -p /data

CMD ["python", "-m", "fetcher.main"]
