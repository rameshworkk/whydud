# ============================================================
# Whydud Backend — Multi-stage Dockerfile
# Base: Python 3.12-slim
# ============================================================

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS base

WORKDIR /app

# System deps needed for psycopg, Pillow, cryptography
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

# ---------------------------------------------------------------------------
# Dependencies layer (cached separately from code)
# ---------------------------------------------------------------------------
FROM base AS deps

COPY backend/requirements/base.txt requirements/base.txt
COPY backend/requirements/prod.txt requirements/prod.txt

RUN pip install -r requirements/prod.txt

# Install spaCy English model
RUN python -m spacy download en_core_web_sm

# Install Playwright Chromium + system deps for scraping spiders
RUN playwright install-deps chromium && playwright install chromium

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------
FROM deps AS development

COPY backend/requirements/dev.txt requirements/dev.txt
RUN pip install -r requirements/dev.txt

COPY backend/ .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---------------------------------------------------------------------------
# Production
# ---------------------------------------------------------------------------
FROM deps AS production

COPY backend/ .

# Collect static files (Django admin, DRF browsable API, etc.)
# DJANGO_SECRET_KEY is needed for settings import; a dummy value is fine at build time.
# DATABASE_URL is not needed — collectstatic doesn't touch the database.
RUN DJANGO_SECRET_KEY=build-only-collectstatic-key \
    python manage.py collectstatic --no-input --settings=whydud.settings.prod

# Non-root user
RUN useradd --system --no-create-home whydud
USER whydud

EXPOSE 8000

CMD ["gunicorn", "whydud.wsgi:application", "--workers", "3", "--bind", "0.0.0.0:8000", "--timeout", "60"]
