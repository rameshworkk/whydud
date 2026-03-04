FROM python:3.12-slim

# System deps for camoufox (Firefox) and curl_cffi
RUN apt-get update && apt-get install -y --no-install-recommends \
    # camoufox Firefox dependencies
    libgtk-3-0 libdbus-glib-1-2 libxt6 libasound2 libx11-xcb1 \
    libxcomposite1 libxdamage1 libxrandr2 libxcursor1 libxi6 \
    libpango-1.0-0 libpangocairo-1.0-0 libatk1.0-0 libcairo2 \
    libgdk-pixbuf-2.0-0 libnspr4 libnss3 libxss1 fonts-liberation \
    # curl_cffi build deps
    gcc libffi-dev libssl-dev \
    # general
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install only scraping-related Python deps (no Django, no Postgres, no Celery)
COPY docker/test-meesho/requirements-test.txt /tmp/requirements-test.txt
RUN pip install --no-cache-dir -r /tmp/requirements-test.txt

# Pre-download camoufox browser binary
RUN python -c "import camoufox; camoufox.sync_api" 2>/dev/null; \
    python -c "from camoufox.sync_api import Camoufox; print('camoufox browser binary ready')" || \
    echo "camoufox binary download will happen at runtime"

# Copy backend source (spider code)
COPY backend/ /app/

# Copy the test runner
COPY docker/test-meesho/test_spider.py /app/test_spider.py

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "/app/test_spider.py"]
