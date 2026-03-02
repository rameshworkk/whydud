# Whydud — Complete Setup & Infrastructure Guide

## Table of Contents
- [1. Architecture Overview](#1-architecture-overview)
- [2. Database: PostgreSQL + TimescaleDB (Single Container)](#2-database-postgresql--timescaledb-single-container)
- [3. The setup_dev Command](#3-the-setup_dev-command)
- [4. All Management Commands](#4-all-management-commands)
- [5. New Environment Setup (Step by Step)](#5-new-environment-setup-step-by-step)
- [6. What Each Docker Container Does](#6-what-each-docker-container-does)
- [7. Environment Variables Reference](#7-environment-variables-reference)
- [8. Starting the Application](#8-starting-the-application)
- [9. Production Deployment (Server)](#9-production-deployment-server)
- [10. Common Tasks & Troubleshooting](#10-common-tasks--troubleshooting)

---

## 1. Architecture Overview

### Dev Environment

```
┌─────────────────────────────────────────────────────┐
│  YOUR MACHINE (run locally)                         │
│                                                     │
│  Django (runserver)         → localhost:8000         │
│  Celery Worker              → background            │
│  Celery Beat (optional)     → background            │
│  Next.js (npm run dev)      → localhost:3000         │
└───────────────┬─────────────────────────────────────┘
                │ connects to
┌───────────────▼─────────────────────────────────────┐
│  DOCKER (docker-compose.dev.yml)                    │
│                                                     │
│  PostgreSQL 16 + TimescaleDB  → localhost:5432      │
│  Redis 7                      → localhost:6379      │
│  Meilisearch 1.7              → localhost:7700      │
│  Flower (Celery monitor)      → localhost:5555      │
└─────────────────────────────────────────────────────┘
```

### Production Environment

```
┌─────────────────────────────────────────────────────┐
│  DOCKER (docker-compose.yml) — ALL 10 containers    │
│                                                     │
│  Caddy (reverse proxy + SSL)  → ports 80, 443      │
│  PostgreSQL 16 + TimescaleDB  → internal :5432      │
│  Redis 7                      → internal :6379      │
│  Meilisearch 1.7              → internal :7700      │
│  Django (Gunicorn, 3 workers) → internal :8000      │
│  Celery Worker (4 concurrent) → background          │
│  Celery Beat (scheduler)      → background          │
│  Email Worker (2 concurrent)  → background          │
│  Flower (monitoring UI)       → internal :5555      │
│  Next.js (SSR production)     → internal :3000      │
└─────────────────────────────────────────────────────┘
```

---

## 2. Database: PostgreSQL + TimescaleDB (Single Container)

### They Are NOT Separate

TimescaleDB is a **PostgreSQL extension**, not a separate database or container. The Docker image `timescale/timescaledb:latest-pg16` is PostgreSQL 16 with TimescaleDB pre-installed.

**One container. One database. One connection string.**

```yaml
# docker-compose.dev.yml
postgres:
  image: timescale/timescaledb:latest-pg16   # PostgreSQL 16 WITH TimescaleDB baked in
  environment:
    POSTGRES_DB: whydud
    POSTGRES_USER: whydud
    POSTGRES_PASSWORD: whydud_dev
  ports:
    - "5432:5432"
  volumes:
    - postgres_dev_data:/var/lib/postgresql/data
    - ./postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
```

### What Happens on First Container Start

The file `docker/postgres/init.sql` runs automatically (via Docker's `docker-entrypoint-initdb.d` mechanism):

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create 7 custom schemas
CREATE SCHEMA IF NOT EXISTS users;
CREATE SCHEMA IF NOT EXISTS email_intel;
CREATE SCHEMA IF NOT EXISTS scoring;
CREATE SCHEMA IF NOT EXISTS tco;
CREATE SCHEMA IF NOT EXISTS community;
CREATE SCHEMA IF NOT EXISTS admin;

-- Grant all privileges to whydud user on all schemas
GRANT ALL PRIVILEGES ON SCHEMA public TO whydud;
GRANT ALL PRIVILEGES ON SCHEMA users TO whydud;
-- ... (all schemas)
```

### What Happens During Migrations

Django migrations then create all the tables. Two special migrations convert tables into TimescaleDB hypertables:

**1. `apps/pricing/migrations/0002_timescaledb_setup.py`**
- Converts `price_snapshots` into a hypertable (partitioned by `time` column)
- Adds automatic compression policy (compress data older than 30 days)
- Creates `price_daily` continuous aggregate (hourly-refreshed daily price summary)

**2. `apps/scoring/migrations/0002_dudscore_history_hypertable.py`**
- Converts `scoring.dudscore_history` into a hypertable (partitioned by `time`)

These use a special migration pattern because `create_hypertable()` cannot run inside a transaction:

```python
# Migration class has atomic = False
# Uses raw psycopg3 connection with autocommit = True
raw_conn = schema_editor.connection.connection
raw_conn.autocommit = True
with raw_conn.cursor() as cur:
    cur.execute("SELECT create_hypertable('price_snapshots', 'time')")
```

### Database Schema Map

```
whydud (database)
├── public schema
│   ├── products_product
│   ├── products_productlisting
│   ├── products_marketplace
│   ├── products_brand
│   ├── products_seller
│   ├── products_category
│   ├── price_snapshots          ← TimescaleDB hypertable
│   ├── price_daily              ← TimescaleDB continuous aggregate
│   ├── scraper_jobs
│   ├── django_* tables          ← Django internals
│   └── ... (other app tables)
├── users schema
│   └── accounts_user, profiles, etc.
├── email_intel schema
│   └── email intelligence tables
├── scoring schema
│   ├── dudscore tables
│   └── dudscore_history         ← TimescaleDB hypertable
├── tco schema
│   └── total cost of ownership tables
├── community schema
│   └── discussions, comments, etc.
└── admin schema
    └── admin tool tables
```

Django connects with a search_path that includes all schemas:

```python
# settings/base.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "whydud",
        "USER": "whydud",
        "PASSWORD": "whydud_dev",
        "HOST": "localhost",
        "PORT": "5432",
        "OPTIONS": {
            "options": "-c search_path=public,users,email_intel,scoring,tco,community,admin"
        },
    }
}
```

---

## 3. The setup_dev Command

**File:** `backend/apps/accounts/management/commands/setup_dev.py`

```bash
python manage.py setup_dev
```

This is the **one-command dev setup** that runs after fresh migrations. It's idempotent (safe to run multiple times).

### What It Does

| Step | Action | Details |
|------|--------|---------|
| 1 | **Site config** | Sets Django Site domain to `localhost:8000`, name to "Whydud Dev" |
| 2 | **Google OAuth cleanup** | Removes stale DB entries (allauth 65+ reads credentials from settings.py, not DB) |
| 3 | **Superuser creation** | Creates `admin@whydud.com` with password `admin123` (skips if already exists) |
| 4 | **Seed data** | Calls `seed_data` command which runs all sub-seeders |

### Output

```
  Site: localhost:8000
  Google OAuth: configured via settings.py (SOCIALACCOUNT_PROVIDERS)
  Superuser: admin@whydud.com / admin123
  Seed data: loaded

Dev setup complete.
```

### Source Code

```python
class Command(BaseCommand):
    help = "Configure Site, OAuth, superuser, and seed data for local dev."

    def handle(self, *args, **options):
        self._setup_site()
        self._setup_google_oauth()
        self._setup_superuser()
        self._run_seed_data()
        self.stdout.write(self.style.SUCCESS("\nDev setup complete."))

    def _setup_site(self):
        from django.contrib.sites.models import Site
        site = Site.objects.get(id=1)
        site.domain = "localhost:8000"
        site.name = "Whydud Dev"
        site.save()

    def _setup_google_oauth(self):
        from allauth.socialaccount.models import SocialApp
        deleted, _ = SocialApp.objects.filter(provider="google").delete()

    def _setup_superuser(self):
        from apps.accounts.models import User
        email = "admin@whydud.com"
        if User.objects.filter(email=email).exists():
            return
        User.objects.create_superuser(email=email, password="admin123")

    def _run_seed_data(self):
        from django.core.management import call_command
        call_command("seed_data")
```

---

## 4. All Management Commands

| Command | App | Purpose |
|---------|-----|---------|
| `setup_dev` | accounts | One-command dev setup (site + OAuth + superuser + seeds) |
| `seed_data` | products | Master seeder — runs all sub-seeders below |
| `seed_marketplaces` | products | Creates Amazon.in, Flipkart, Croma marketplace records |
| `seed_review_features` | reviews (via products) | Initializes review analysis feature definitions |
| `seed_preference_schemas` | products | Product preference schemas for recommendations |
| `seed_tco_models` | tco (via products) | TCO calculator model definitions |
| `sync_meilisearch` | search | Full sync of all products to Meilisearch index |

### Data Also Seeded Via Migrations

These run automatically during `manage.py migrate`:
- `accounts/migrations/0002_seed_reserved_usernames.py` — Reserved usernames list
- `products/migrations/0002_seed_marketplaces.py` — Initial marketplace records

---

## 5. New Environment Setup (Step by Step)

### Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 22+ | Frontend runtime |
| Docker Desktop | Latest | Infrastructure services |
| Git | Latest | Version control |

### Step 1: Clone the Repository

```bash
git clone <repo-url>
cd platform/whydud
```

### Step 2: Start Docker Infrastructure

```bash
cd docker
docker compose -f docker-compose.dev.yml up -d
```

Wait for all containers to be healthy:

```bash
docker compose -f docker-compose.dev.yml ps
```

Expected output — all should show `Up (healthy)`:

```
NAME                STATUS              PORTS
docker-postgres-1   Up (healthy)        0.0.0.0:5432->5432/tcp
docker-redis-1      Up (healthy)        0.0.0.0:6379->6379/tcp
docker-meilisearch  Up (healthy)        0.0.0.0:7700->7700/tcp
docker-flower-1     Up                  0.0.0.0:5555->5555/tcp
```

**What this starts:**

| Container | Image | Port | Credentials |
|-----------|-------|------|-------------|
| PostgreSQL + TimescaleDB | `timescale/timescaledb:latest-pg16` | 5432 | whydud / whydud_dev |
| Redis | `redis:7-alpine` | 6379 | no auth |
| Meilisearch | `getmeili/meilisearch:v1.7` | 7700 | key: `whydud_dev_meili_key_32chars!!` |
| Flower | `mher/flower:2.0.1` | 5555 | admin / admin |

On first start, `init.sql` runs automatically to enable TimescaleDB, create schemas, and grant privileges.

### Step 3: Set Up Backend Python Environment

```bash
cd backend

# Create .env from template
cp .env.example .env
# Defaults work for local dev — edit only if your ports differ

# Create virtual environment
python -m venv venv

# Activate (choose your OS)
source venv/bin/activate          # macOS / Linux
venv\Scripts\activate             # Windows CMD
source venv/Scripts/activate      # Windows Git Bash

# Install Python dependencies
pip install -r requirements/base.txt

# Install Playwright browsers (needed for web scraping)
playwright install chromium
```

### Step 4: Run Database Migrations

```bash
python manage.py migrate
```

This creates:
- All Django tables across 7 schemas
- TimescaleDB hypertables (`price_snapshots`, `dudscore_history`)
- Continuous aggregates (`price_daily`)
- Compression policies
- Seeds reserved usernames and initial marketplace data (via data migrations)

### Step 5: Run the Setup Command

```bash
python manage.py setup_dev
```

This creates:
- Django Site configuration (localhost:8000)
- Superuser account (admin@whydud.com / admin123)
- All seed data (marketplaces, review features, preference schemas, TCO models)

### Step 6: Sync Meilisearch Index

```bash
python manage.py sync_meilisearch
```

Configures the Meilisearch `products` index with searchable/filterable/sortable fields and syncs any existing products.

### Step 7: Set Up Frontend

```bash
cd frontend

# Create .env from template
cp .env.example .env.local

# Install Node dependencies
npm install
```

### Step 8: Start Everything

You need **3-4 terminal windows**:

**Terminal 1 — Django API server:**
```bash
cd backend
source venv/bin/activate          # or venv\Scripts\activate on Windows
python manage.py runserver 0.0.0.0:8000
```

**Terminal 2 — Celery worker (handles scraping, alerts, scoring):**
```bash
cd backend
source venv/bin/activate
celery -A whydud worker --loglevel=info -Q default,scraping,scoring,alerts
```

**Terminal 3 — Celery Beat scheduler (optional for dev, needed for scheduled scrapes):**
```bash
cd backend
source venv/bin/activate
celery -A whydud beat --loglevel=info
```

**Terminal 4 — Next.js frontend:**
```bash
cd frontend
npm run dev
```

### Verification Checklist

| Service | URL | Expected |
|---------|-----|----------|
| Frontend | http://localhost:3000 | Whydud homepage |
| Backend API | http://localhost:8000/api/ | DRF browsable API |
| Admin panel | http://localhost:8000/admin/ | Login with admin@whydud.com / admin123 |
| Flower | http://localhost:5555 | Celery dashboard (admin / admin) |
| Meilisearch | http://localhost:7700 | Health check JSON |
| PostgreSQL | localhost:5432 | Connect with whydud / whydud_dev |
| Redis | localhost:6379 | `redis-cli ping` → `PONG` |

---

## 6. What Each Docker Container Does

### Dev Environment (docker-compose.dev.yml)

| Service | Image | Port | RAM | Purpose |
|---------|-------|------|-----|---------|
| **postgres** | `timescale/timescaledb:latest-pg16` | 5432 | ~512MB | Database with TimescaleDB extension for time-series price data |
| **redis** | `redis:7-alpine` | 6379 | 200MB max | Celery broker, Django cache (DB 1), session storage |
| **meilisearch** | `getmeili/meilisearch:v1.7` | 7700 | ~256MB | Full-text product search with typo tolerance, filtering, sorting |
| **flower** | `mher/flower:2.0.1` | 5555 | ~64MB | Celery task monitoring dashboard |

### Production Environment (docker-compose.yml)

All dev services plus:

| Service | Port | RAM | Purpose |
|---------|------|-----|---------|
| **caddy** | 80, 443 | 64MB | Reverse proxy, auto-SSL via Let's Encrypt, security headers |
| **backend** | 8000 (internal) | 1GB | Django API via Gunicorn (3 workers) |
| **celery-worker** | — | 2GB | Task execution: scraping, scoring, alerts, deals (4 concurrent) |
| **celery-beat** | — | 256MB | Cron scheduler for periodic tasks |
| **email-worker** | — | 512MB | Isolated email queue (2 concurrent) |
| **frontend** | 3000 (internal) | 1GB | Next.js SSR production build |

### Docker Volumes (Persistent Data)

| Volume | Mounted To | Contains |
|--------|-----------|----------|
| `postgres_dev_data` | `/var/lib/postgresql/data` | All database data |
| `redis_dev_data` | `/data` | Redis AOF persistence |
| `meilisearch_dev_data` | `/meili_data` | Search index data |
| `flower_dev_data` | `/data` | Flower task history DB |

---

## 7. Environment Variables Reference

### Backend `.env` (Development Defaults)

```bash
# Django
DJANGO_SETTINGS_MODULE=whydud.settings.dev
DJANGO_SECRET_KEY=dev-secret-key-change-in-production

# Database (matches docker-compose.dev.yml)
POSTGRES_DB=whydud
POSTGRES_USER=whydud
POSTGRES_PASSWORD=whydud_dev
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Meilisearch
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_MASTER_KEY=whydud_dev_meili_key_32chars!!

# Encryption (generate real keys for prod)
EMAIL_ENCRYPTION_KEY=dev-email-key-32-bytes-change-me
OAUTH_ENCRYPTION_KEY=dev-oauth-key-32-bytes-change-me

# External services (optional for dev)
RESEND_API_KEY=
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
CLOUDFLARE_EMAIL_WEBHOOK_SECRET=
```

### Frontend `.env.local` (Development Defaults)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
# For SSR (server-side API calls within Docker)
INTERNAL_API_URL=http://localhost:8000
```

### Production `.env` (Required — No Defaults)

```bash
DJANGO_SETTINGS_MODULE=whydud.settings.prod
DJANGO_SECRET_KEY=<generate: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">

POSTGRES_DB=whydud
POSTGRES_USER=whydud
POSTGRES_PASSWORD=<strong random password>
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0

MEILISEARCH_URL=http://meilisearch:7700
MEILISEARCH_MASTER_KEY=<strong random key, 32+ chars>

EMAIL_ENCRYPTION_KEY=<32-byte base64 key for AES-256-GCM>
OAUTH_ENCRYPTION_KEY=<32-byte base64 key for AES-256-GCM>

SITE_DOMAIN=whydud.com
FRONTEND_URL=https://whydud.com
NEXT_PUBLIC_API_URL=https://whydud.com
NEXT_PUBLIC_SITE_URL=https://whydud.com
INTERNAL_API_URL=http://backend:8000

RESEND_API_KEY=<from resend.com>
RAZORPAY_KEY_ID=<from razorpay dashboard>
RAZORPAY_KEY_SECRET=<from razorpay dashboard>
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
CLOUDFLARE_EMAIL_WEBHOOK_SECRET=<from Cloudflare>

FLOWER_BASIC_AUTH=admin:<strong password>
```

---

## 8. Starting the Application

### Quick Start (After Initial Setup)

If Docker infrastructure is already running and migrations are done:

```bash
# Terminal 1: Django
cd backend && python manage.py runserver 0.0.0.0:8000

# Terminal 2: Celery worker
cd backend && celery -A whydud worker --loglevel=info -Q default,scraping,scoring,alerts

# Terminal 3: Frontend
cd frontend && npm run dev
```

### Full Restart (After Machine Reboot)

```bash
# 1. Start Docker containers
cd docker && docker compose -f docker-compose.dev.yml up -d

# 2. Wait for healthy
docker compose -f docker-compose.dev.yml ps

# 3. Start Django, Celery, Frontend (3 terminals as above)
```

### Stopping Everything

```bash
# Stop local processes: Ctrl+C in each terminal

# Stop Docker infrastructure
cd docker && docker compose -f docker-compose.dev.yml down

# Stop AND delete data (fresh start)
cd docker && docker compose -f docker-compose.dev.yml down -v
```

### Complete Fresh Reset

If you need to start completely from scratch:

```bash
# 1. Destroy all Docker volumes (deletes all data)
cd docker && docker compose -f docker-compose.dev.yml down -v

# 2. Restart infrastructure
docker compose -f docker-compose.dev.yml up -d

# 3. Wait for healthy
docker compose -f docker-compose.dev.yml ps

# 4. Run migrations (recreates all tables + hypertables)
cd backend && python manage.py migrate

# 5. Run setup command (recreates superuser + seed data)
python manage.py setup_dev

# 6. Sync Meilisearch
python manage.py sync_meilisearch
```

---

## 9. Production Deployment (Server)

### Server Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Storage | 50 GB SSD | 100 GB SSD |
| OS | Ubuntu 22.04+ | Ubuntu 24.04 LTS |
| Network | Public IP, ports 80/443 open | — |

### Resource Breakdown by Service

| Service | RAM | CPU |
|---------|-----|-----|
| PostgreSQL + TimescaleDB | 2 GB | 1 core |
| Redis | 512 MB | 0.5 core |
| Meilisearch | 1 GB | 1 core |
| Django (Gunicorn, 3 workers) | 1 GB | 1 core |
| Celery Worker (4 concurrent) | 2 GB | 2 cores |
| Celery Beat | 256 MB | 0.25 core |
| Email Worker | 512 MB | 0.5 core |
| Flower | 128 MB | 0.25 core |
| Next.js Frontend | 1 GB | 1 core |
| Caddy | 64 MB | 0.25 core |
| **Total** | **~8.5 GB** | **~7 cores** |

### Step-by-Step Production Deployment

#### 1. Server Preparation

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt install docker-compose-plugin

# Log out and back in for group changes
```

#### 2. Clone and Configure

```bash
git clone <repo-url> /opt/whydud
cd /opt/whydud/platform/whydud

# Create production env file
cp docker/.env.example docker/.env
nano docker/.env
# Fill ALL required variables (see Section 7 — Production .env)
```

#### 3. Update Caddyfile Domain

Edit `docker/Caddyfile` — replace the domain with your actual domain:

```
whydud.com {
    ...
}
```

Caddy handles SSL automatically via Let's Encrypt — no manual cert management.

#### 4. Build All Images

```bash
cd /opt/whydud/platform/whydud/docker
docker compose build
```

#### 5. Start Infrastructure First

```bash
docker compose up -d postgres redis meilisearch

# Wait until healthy
watch docker compose ps
# All three should show "healthy" before proceeding
```

#### 6. Initialize Database

```bash
# Run all Django migrations
docker compose run --rm backend python manage.py migrate

# Create superuser
docker compose run --rm backend python manage.py createsuperuser

# Seed marketplace and reference data
docker compose run --rm backend python manage.py seed_data

# Configure Meilisearch index
docker compose run --rm backend python manage.py sync_meilisearch
```

#### 7. Install Playwright in Worker

```bash
docker compose run --rm celery-worker playwright install chromium
```

#### 8. Launch All Services

```bash
docker compose up -d
```

#### 9. Verify

```bash
# All 10 containers should be running
docker compose ps

# Check endpoints
curl https://whydud.com/api/health/    # API
curl https://whydud.com                 # Frontend

# Check logs for errors
docker compose logs -f backend
docker compose logs -f celery-worker
```

### Caddy Routing (Production)

| Path | Routed To | Service |
|------|-----------|---------|
| `/api/*` | backend:8000 | Django API |
| `/admin/*` | backend:8000 | Django Admin |
| `/webhooks/*` | backend:8000 | Cloudflare email webhooks |
| `/static/*` | file server | Collected static files |
| `/flower/*` | flower:5555 | Celery monitoring (basic auth) |
| `/*` (everything else) | frontend:3000 | Next.js SSR |

### Celery Beat Schedule (Production)

These run automatically once Celery Beat is started:

| Task | Schedule (UTC) | What It Does |
|------|---------------|--------------|
| `scrape-amazon-in-6h` | 00:00, 06:00, 12:00, 18:00 | Scrape Amazon.in products |
| `scrape-flipkart-6h` | 03:00, 09:00, 15:00, 21:00 | Scrape Flipkart products |
| `check-price-alerts-4h` | Every 4 hours | Check and trigger price alerts |
| `detect-deals-2h` | Every 2 hours | Detect flash deals |
| `meilisearch-full-reindex-daily` | 01:00 | Full search index rebuild |
| `publish-pending-reviews-hourly` | Every hour | Publish queued reviews |
| `update-reviewer-profiles-weekly` | Monday 00:00 | Recalculate reviewer stats |
| `dudscore-full-recalc-monthly` | 1st of month, 03:00 | Recalculate all DudScores |

---

## 10. Common Tasks & Troubleshooting

### Database Access

```bash
# Dev — connect to PostgreSQL
psql -h localhost -U whydud -d whydud
# Password: whydud_dev

# Production — via Docker
docker compose exec postgres psql -U whydud -d whydud

# Check TimescaleDB is working
SELECT default_version, installed_version FROM pg_available_extensions WHERE name = 'timescaledb';

# Check hypertables exist
SELECT hypertable_name FROM timescaledb_information.hypertables;
# Expected: price_snapshots, dudscore_history

# Price snapshot count by day (last 7 days)
SELECT date_trunc('day', time) AS day, COUNT(*)
FROM price_snapshots
WHERE time > NOW() - INTERVAL '7 days'
GROUP BY day ORDER BY day DESC;
```

### Trigger a Manual Scrape

```bash
# Via CLI (bypasses Celery — good for testing, won't appear in Flower)
cd backend
python -m apps.scraping.runner amazon_in --max-pages 2

# Via Celery task (appears in Flower, creates ScraperJob record)
python manage.py shell -c "
from apps.scraping.tasks import run_marketplace_spider
result = run_marketplace_spider.delay('amazon-in')
print(f'Task ID: {result.id}')
"
```

### Check Scraping Stats

```bash
python manage.py shell -c "
from apps.products.models import Product, ProductListing
from apps.pricing.models import PriceSnapshot
print(f'Products:  {Product.objects.count()}')
print(f'Listings:  {ProductListing.objects.count()}')
print(f'Snapshots: {PriceSnapshot.objects.count()}')
"
```

### Reset Meilisearch Index

```bash
python manage.py sync_meilisearch
```

### View Celery Worker Status

```bash
# Via Flower UI
# Dev:  http://localhost:5555 (admin / admin)
# Prod: https://whydud.com/flower/ (FLOWER_BASIC_AUTH credentials)

# Via CLI
celery -A whydud inspect active
celery -A whydud inspect stats
```

### Docker Volume Locations (Dev)

```bash
# List volumes
docker volume ls | grep dev

# Inspect a volume (see mount point)
docker volume inspect docker_postgres_dev_data
```

### If Database Gets Corrupted

```bash
# Nuclear option: destroy and recreate
cd docker
docker compose -f docker-compose.dev.yml down -v    # deletes all data
docker compose -f docker-compose.dev.yml up -d       # fresh containers
cd ../backend
python manage.py migrate                              # recreate tables
python manage.py setup_dev                            # reseed data
python manage.py sync_meilisearch                     # rebuild search index
```

### If Playwright Fails (Scraping)

```bash
# Reinstall browser
playwright install chromium

# Check it's installed
playwright install --dry-run

# On production (inside container)
docker compose exec celery-worker playwright install chromium
```

### If Migrations Fail on Hypertable Creation

The TimescaleDB migrations require the extension to be enabled first. If `init.sql` didn't run (e.g., volume already existed from a plain PostgreSQL container):

```bash
# Connect to PostgreSQL and enable manually
psql -h localhost -U whydud -d whydud -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"

# Then retry migrations
python manage.py migrate
```
