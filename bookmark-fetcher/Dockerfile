# Bookmark Fetcher Dockerfile
#
# NOTE: Python 3.11-3.12 is required for Playwright compatibility.
# Python 3.14+ may have issues with Playwright's bundled Node.js.
# See: https://github.com/microsoft/playwright-python/issues/2506

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-playwright.txt .
RUN pip install --no-cache-dir -r requirements-playwright.txt

# Install Playwright browsers
RUN playwright install chromium --with-deps

COPY fetcher ./fetcher
COPY config.py .

RUN mkdir -p /data

CMD ["python", "-m", "fetcher.main_playwright"]
