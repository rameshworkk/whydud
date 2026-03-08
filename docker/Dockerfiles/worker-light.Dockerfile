# ============================================================
# Whydud — Lightweight Celery Worker
#
# For low-RAM nodes (1GB OCI). Runs backfill HTTP tasks only.
# NO Playwright, NO Chromium, NO spaCy.
# ~200MB image vs ~1.2GB for full backend.
# ============================================================

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# System deps for psycopg, cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    g++ \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install Python deps (same as prod, but skip playwright/spacy post-install)
COPY backend/requirements/base.txt requirements/base.txt
COPY backend/requirements/prod.txt requirements/prod.txt
RUN pip install -r requirements/prod.txt

# Copy backend code
COPY backend/ .

# Non-root user
RUN useradd --system --no-create-home whydud
USER whydud

CMD ["celery", "-A", "whydud", "worker", "--loglevel=info", "--concurrency=1", "--queues=scraping"]
