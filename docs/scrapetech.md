# Whydud Scraping System — Complete Technical Reference

## Table of Contents
- [1. How Scraping is Triggered](#1-how-scraping-is-triggered)
- [2. Why Flower Doesn't Show Spider Work](#2-why-flower-doesnt-show-spider-work)
- [3. Data Flow: Spider → Pipeline → Database](#3-data-flow-spider--pipeline--database)
- [4. Pipeline Stages (In Detail)](#4-pipeline-stages-in-detail)
- [5. Product Matching Engine (Deduplication)](#5-product-matching-engine-deduplication)
- [6. Where Data is Stored](#6-where-data-is-stored)
- [7. PriceSnapshot & TimescaleDB](#7-pricesnapshot--timescaledb)
- [8. Meilisearch Indexing](#8-meilisearch-indexing)
- [9. ScraperJob Tracking & Getting Stats](#9-scraperjob-tracking--getting-stats)
- [10. Update Process (Re-scrapes)](#10-update-process-re-scrapes)
- [11. Spider Implementations](#11-spider-implementations)
- [12. The Complete Tool Stack](#12-the-complete-tool-stack)
- [13. Environment Variables](#13-environment-variables)
- [14. Step-by-Step Server Deployment](#14-step-by-step-server-deployment)
- [15. Resource Requirements](#15-resource-requirements)
- [16. Ongoing Monitoring](#16-ongoing-monitoring)
- [17. Key Design Decisions](#17-key-design-decisions)

---

## 1. How Scraping is Triggered

There are **3 ways** to trigger a scrape:

| Method | Command / Trigger | When to Use |
|--------|-------------------|-------------|
| **Direct CLI** | `python -m apps.scraping.runner amazon_in --max-pages 2` | Testing / debugging |
| **Celery Task** (on-demand) | `run_marketplace_spider.delay("amazon-in")` | Ad-hoc from code / admin |
| **Celery Beat** (scheduled) | Automatic via crontab | Production (every 6h) |

### Celery Beat Schedule (UTC)

Defined in `whydud/celery.py`:

| Task | Schedule |
|------|----------|
| `scrape-amazon-in-6h` | 00:00, 06:00, 12:00, 18:00 UTC |
| `scrape-flipkart-6h` | 03:00, 09:00, 15:00, 21:00 UTC (offset +3h) |
| `check-price-alerts-4h` | Every 4 hours |
| `meilisearch-full-reindex-daily` | 01:00 UTC |
| `dudscore-full-recalc-monthly` | 1st of month, 03:00 UTC |
| `detect-deals-2h` | Every 2 hours |
| `publish-pending-reviews-hourly` | Every hour |
| `update-reviewer-profiles-weekly` | Monday 00:00 |

### CLI Arguments

```bash
python -m apps.scraping.runner <spider_name> [options]

Options:
  --job-id UUID       ScraperJob UUID (for tracking)
  --urls url1,url2    Override seed URLs (testing)
  --max-pages N       Override MAX_LISTING_PAGES per category
  --save-html         Save raw HTML to data/raw_html/ for debugging
```

---

## 2. Why Flower Doesn't Show Spider Work

Spiders run as **subprocesses**, NOT as Celery tasks themselves.

```
Celery Beat
  → triggers run_marketplace_spider()         ← THIS appears in Flower (brief)
    → subprocess.run(                         ← THIS does NOT appear in Flower
        "python -m apps.scraping.runner amazon_in"
      )
      → Scrapy crawls with Playwright (Twisted reactor)
      → Pipeline processes items into DB
      → 30+ minutes of work, invisible to Flower
    → subprocess returns exit code
  → task marks ScraperJob as COMPLETED        ← Flower shows task done
```

### Why Subprocess?

Scrapy uses Twisted's reactor, which **cannot be restarted** within the same Python process. If you ran a spider directly inside a Celery worker, the second spider run in that worker would crash with `ReactorNotRestartable`. The subprocess gives each spider a fresh Python process with a fresh reactor.

### What You'd See in Flower

- `run_marketplace_spider` task appears as "STARTED"
- It stays "STARTED" for the entire subprocess duration (30+ min)
- When subprocess exits, task transitions to "SUCCESS" or "FAILURE"
- The actual item-by-item scraping work is invisible

### When You Run via CLI

Running `python -m apps.scraping.runner amazon_in --max-pages 2` **bypasses Celery entirely** — no Celery task is created, no ScraperJob record, nothing in Flower. The output goes directly to your terminal.

---

## 3. Data Flow: Spider → Pipeline → Database

```
Amazon.in / Flipkart page
  ↓ Playwright renders JavaScript (prices, availability)
  ↓ Spider extracts fields into ProductItem
  ↓
╔════════════════════════════════════════════════════════════╗
║ PIPELINE (4 stages, in-process)                           ║
║                                                           ║
║ Stage 1: ValidationPipeline (priority 100)                ║
║   → Drop if missing: marketplace_slug, external_id,       ║
║     url, title                                            ║
║   → Increment spider.items_failed counter                 ║
║                                                           ║
║ Stage 2: NormalizationPipeline (priority 200)             ║
║   → Clean title whitespace                                ║
║   → Normalize brand names                                 ║
║   → Deduplicate image URLs                                ║
║   → Strip spec key/value whitespace                       ║
║                                                           ║
║ Stage 3: ProductPipeline (priority 400) — CORE            ║
║   → Resolve Marketplace (by slug)                         ║
║   → Find/Create Seller                                    ║
║   → Resolve Brand (alias-aware)                           ║
║   → Match or Create Product (4-step matching)             ║
║   → Create/Update ProductListing                          ║
║   → Record PriceSnapshot (raw SQL → TimescaleDB)          ║
║   → Recalculate canonical Product aggregates              ║
║                                                           ║
║ Stage 4: MeilisearchIndexPipeline (priority 500)          ║
║   → Collect product IDs during spider run                 ║
║   → On spider close: batch sync to Meilisearch            ║
╚════════════════════════════════════════════════════════════╝
  ↓
Post-completion tasks (if triggered via Celery):
  → sync_products_to_meilisearch.delay()
  → check_price_alerts.delay()
```

---

## 4. Pipeline Stages (In Detail)

### Stage 1: ValidationPipeline

**File:** `apps/scraping/pipelines.py` (priority 100)

- Required fields: `marketplace_slug`, `external_id`, `url`, `title`
- Any item missing a required field is **dropped** (not saved)
- Increments `spider.items_failed` counter for tracking

### Stage 2: NormalizationPipeline

**File:** `apps/scraping/pipelines.py` (priority 200)

| Field | Normalization |
|-------|--------------|
| Title | Collapse multiple whitespace, strip |
| Brand | Remove prefixes ("Visit the", "Brand:"), title-case multi-word, UPPER for ≤4 char brands (e.g., "HP", "LG") |
| Specs | Strip whitespace from keys/values, remove empty pairs |
| Images | Deduplicate URLs while preserving order |
| About Bullets | Filter out empty strings |

### Stage 3: ProductPipeline

**File:** `apps/scraping/pipelines.py` (priority 400) — The critical stage.

Per-item workflow (7 steps):

1. **Resolve Marketplace** by slug (e.g., `"amazon_in"` → Marketplace record). Fail if not found.

2. **Find or Create Seller** using `(marketplace, external_seller_id)` unique constraint. Falls back to slug-derived ID.

3. **Resolve Brand** via `resolve_or_create_brand()`. Checks `Brand.aliases` JSONField for synonyms (e.g., "MI" → "Xiaomi").

4. **Find or Create ProductListing** by `(marketplace, external_id)`:
   - **If found:** Update existing listing + push data up to canonical Product
   - **If not found:** Run 4-step matching engine → create new listing linked to matched/new Product

5. **Record PriceSnapshot** — raw SQL INSERT (see [Section 7](#7-pricesnapshot--timescaledb)).

6. **Recalculate Canonical Product** — weighted avg rating, total reviews, best price, best marketplace, lowest price ever.

7. **Track Product ID** on spider for batch Meilisearch sync.

### Stage 4: MeilisearchIndexPipeline

**File:** `apps/scraping/pipelines.py` (priority 500)

- During spider run: stashes product IDs on `spider._synced_product_ids`
- On `close_spider()` event: queues `sync_products_to_meilisearch.delay(product_ids=[...])`
- Only indexes touched products (incremental, not full reindex)

---

## 5. Product Matching Engine (Deduplication)

**File:** `apps/products/matching.py`

When a new listing arrives, the pipeline determines: "Is this the same product as something we already have?"

### 4-Step Matching (Priority Order)

| Step | Method | Confidence | What it Does |
|------|--------|-----------|--------------|
| 1 | **EAN/GTIN exact** | 1.00 | Both have same barcode `8906012345678` |
| 2 | **Brand + Model + Variant** | 0.95 | Same brand, model, storage, RAM, color |
| 3 | **Brand + Model** (variant differs) | 0.85 | Same base model, different storage/color |
| 4 | **Fuzzy title match** | 0.70 | SequenceMatcher ratio ≥ 0.80 threshold |

If **nothing matches** at any step → create a new canonical Product.

### Step 1: Extract Canonical Identifiers

- **EAN/GTIN/UPC**: Extracted from specs keys `{ean, ean13, gtin, gtin14, upc, barcode, item model number}`
- **Model Info**: Title parsing via regex extracts model name, storage (GB/TB), RAM (GB), color
  - Example: `"Samsung Galaxy S24 FE 5G (Mint, 8GB, 256GB)"` → `ModelInfo(model="Galaxy S24 FE 5G", storage="256GB", ram="8GB", color="Mint")`

### Tunable Thresholds (via `common/app_settings.py`)

| Setting | Default | Purpose |
|---------|---------|---------|
| `auto_merge_threshold` | 0.85 | Auto-merge confidence cutoff |
| `review_threshold` | 0.60 | Below this = always new product |
| `fuzzy_title_threshold` | 0.80 | SequenceMatcher ratio minimum |
| `max_candidates` | 500 | Max products to compare against |

### Example Output from a Scrape

```
Created new canonical product: oneplus-nord-ce5-...          # No match → new
Matched 'Magnetic Shelf...' → product magnetic-shelf-...     # Match found
  (confidence=0.95, method=brand_model_variant)
```

---

## 6. Where Data is Stored

| Data | Model / Table | Storage Engine |
|------|--------------|----------------|
| Canonical products (deduplicated) | `products.Product` | PostgreSQL |
| Per-marketplace listings | `products.ProductListing` | PostgreSQL (unique: marketplace + external_id) |
| Price history (time-series) | `price_snapshots` | **TimescaleDB hypertable** (raw SQL) |
| Brands (with aliases) | `products.Brand` | PostgreSQL (`aliases` JSONField) |
| Sellers | `products.Seller` | PostgreSQL |
| Marketplaces | `products.Marketplace` | PostgreSQL |
| Categories | `products.Category` | PostgreSQL (MPTT tree) |
| Scraper job tracking | `scraping.ScraperJob` | PostgreSQL |
| Full-text search index | `products` index | **Meilisearch** |
| Cache / sessions / broker | — | **Redis** |

### Relationship Model

```
Marketplace (Amazon.in, Flipkart, Croma)
  └── ProductListing (one per marketplace per product)
        ├── linked to → Product (canonical, deduplicated)
        ├── linked to → Seller
        └── generates → PriceSnapshot (one per scrape)

Product (canonical)
  ├── Brand
  ├── Category
  ├── multiple ProductListings (one per marketplace)
  ├── aggregated: best_price, avg_rating, total_reviews
  └── indexed in → Meilisearch
```

---

## 7. PriceSnapshot & TimescaleDB

### Why Raw SQL?

TimescaleDB hypertables don't have an auto-increment `id` column. Django ORM's `.create()` expects one and fails:

```
ERROR: column price_snapshots.id does not exist
```

**Solution in `pipelines.py`:**

```python
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        INSERT INTO price_snapshots
            (time, listing_id, product_id, marketplace_id, price, mrp, in_stock, seller_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, [now, listing.id, product.id, marketplace.id, price, mrp, in_stock, seller_name])
```

### PriceSnapshot Model

```python
class PriceSnapshot(models.Model):
    time = models.DateTimeField()                    # Hypertable partition key
    listing = models.ForeignKey(ProductListing)
    product = models.ForeignKey(Product)
    marketplace = models.ForeignKey(Marketplace)
    price = models.DecimalField(max_digits=12, decimal_places=2)  # In paisa
    mrp = models.DecimalField(max_digits=12, decimal_places=2)    # In paisa
    discount_pct = models.DecimalField(...)
    in_stock = models.BooleanField()
    seller_name = models.CharField(max_length=500)

    class Meta:
        db_table = "price_snapshots"
        managed = False  # TimescaleDB manages the table
```

### Price Convention

All prices stored in **paisa** (Indian currency subunit):
- `₹24,999` → `2499900` (Decimal)
- `₹1,24,999` → `12499900`

### Why Record Every Scrape?

Even if the price hasn't changed, a new snapshot is created. This enables:
- Price history charts (30, 90, 365 days)
- Price volatility calculation (coefficient of variation)
- Flash sale detection
- "Lowest price ever" tracking
- Stock availability history

---

## 8. Meilisearch Indexing

### Two Sync Modes

| Mode | Trigger | Scope |
|------|---------|-------|
| **Incremental** | After each spider run (via MeilisearchIndexPipeline) | Only touched products |
| **Full reindex** | Daily at 01:00 UTC (Celery Beat) | All ACTIVE products |

### Document Format

Each product is indexed with:

```python
{
    "id": str(product.id),
    "slug": product.slug,
    "title": product.title,
    "description": product.description,
    "brand_name": product.brand.name,
    "brand_slug": product.brand.slug,
    "category_name": product.category.name,
    "category_slug": product.category.slug,
    "current_best_price": float(product.current_best_price),
    "current_best_marketplace": product.current_best_marketplace,
    "lowest_price_ever": float(product.lowest_price_ever),
    "avg_rating": float(product.avg_rating),
    "total_reviews": product.total_reviews,
    "dud_score": float(product.dud_score),
    "images": product.images,
    "image_url": product.images[0],
    "in_stock": bool,
    "created_at": timestamp,
}
```

### Index Configuration

- **Searchable:** title, brand_name, category_name, description
- **Filterable:** category_slug, brand_slug, current_best_price, dud_score, status, in_stock
- **Sortable:** current_best_price, dud_score, avg_rating, total_reviews, created_at

---

## 9. ScraperJob Tracking & Getting Stats

### ScraperJob Model

```python
class ScraperJob(models.Model):
    id              = UUIDField(primary_key=True)
    marketplace     = ForeignKey(Marketplace)
    spider_name     = CharField()              # "amazon_in", "flipkart"
    status          = CharField(choices=[       # QUEUED → RUNNING → COMPLETED/FAILED/PARTIAL
                        "queued", "running", "completed", "failed", "partial"
                      ])
    started_at      = DateTimeField(null=True)
    finished_at     = DateTimeField(null=True)
    items_scraped   = IntegerField(default=0)
    items_failed    = IntegerField(default=0)
    error_message   = TextField(blank=True)
    triggered_by    = CharField()              # "scheduled" | "adhoc"
    created_at      = DateTimeField(auto_now_add=True)
```

### Status Lifecycle

```
QUEUED → RUNNING → COMPLETED (exit code 0)
                 → FAILED (exit code != 0 / timeout / exception)
                 → PARTIAL (some items succeeded, some failed)
```

### How to Get Stats

**Query ScraperJob records:**

```bash
python manage.py shell -c "
from apps.scraping.models import ScraperJob
for j in ScraperJob.objects.order_by('-created_at')[:10]:
    duration = (j.finished_at - j.started_at).total_seconds() / 60 if j.finished_at and j.started_at else 0
    print(f'{j.spider_name:12} | {j.status:10} | scraped: {j.items_scraped:4} | failed: {j.items_failed:3} | {duration:.0f}min | {j.created_at:%Y-%m-%d %H:%M}')
"
```

**Query product/listing counts:**

```bash
python manage.py shell -c "
from apps.products.models import Product, ProductListing, Marketplace
from apps.pricing.models import PriceSnapshot

print(f'Products:  {Product.objects.count()}')
print(f'Listings:  {ProductListing.objects.count()}')
print(f'Snapshots: {PriceSnapshot.objects.count()}')

for m in Marketplace.objects.all():
    lc = ProductListing.objects.filter(marketplace=m).count()
    if lc > 0:
        print(f'  {m.name}: {lc} listings')
"
```

**Note:** CLI runs (`python -m apps.scraping.runner`) bypass Celery, so no ScraperJob is created. ScraperJob records are only created when `run_marketplace_spider()` or `run_spider()` Celery tasks are the entry point.

---

## 10. Update Process (Re-scrapes)

On subsequent scrapes of the same product:

1. Spider hits the same product page (same ASIN / FPID)
2. Pipeline finds existing `ProductListing` by `(marketplace, external_id)` — unique constraint
3. **Updates the listing** with fresh data (price, stock status, seller, images, specs)
4. Records a **new PriceSnapshot** (time-series grows, never overwrites)
5. **Recalculates canonical Product aggregates:**
   - Weighted average rating across all listings
   - Total reviews (sum across listings)
   - Current best price (minimum across in-stock listings)
   - Best marketplace (where cheapest price is)
   - Lowest price ever + date
6. If Meilisearch pipeline active: queues re-index of this product

---

## 11. Spider Implementations

### Amazon India Spider (`amazon_spider.py`)

| Property | Value |
|----------|-------|
| **Spider name** | `amazon_in` |
| **Rendering** | Playwright for ALL pages (listing + detail) |
| **Seed categories** | 8: smartphones, laptops, headphones, air purifiers, washing machines, refrigerators, TVs, cameras |
| **Max listing pages** | 5 (default), configurable via `--max-pages` |
| **Download delay** | 2-5s per request |
| **Concurrent requests** | 2 per domain |

**Extraction strategy:**
- ASIN from URL regex: `/(?:dp|gp/product)/([A-Z0-9]{10})`
- Title from `#productTitle`
- Price from multiple selectors (Amazon changes markup frequently)
- Images: main image + alt thumbnails, upgraded to `_SL1500_` high-res
- Specs from tech specs table (key-value pairs)
- Seller, rating, offers, about bullets

### Flipkart Spider (`flipkart_spider.py`)

| Property | Value |
|----------|-------|
| **Spider name** | `flipkart` |
| **Rendering** | Playwright for ALL pages (Flipkart blocks plain HTTP with 403) |
| **Seed categories** | 8: same categories as Amazon |
| **Primary extraction** | JSON-LD structured data (`<script type="application/ld+json">`) |
| **Fallback extraction** | CSS selectors (class names change frequently) |

**Extraction strategy:**
- FPID from URL regex: `/p/(itm[a-zA-Z0-9]+)`
- JSON-LD first (more stable): title, brand, price, images, rating, availability
- CSS fallbacks for MRP, seller rating, highlights, offers
- Images upgraded to `/image/832/832/` high-res

### Base Spider (`base_spider.py`)

Shared anti-detection features for both spiders:

- **User-Agent rotation:** 10 realistic browser strings (Chrome, Firefox, Edge, Safari)
- **Download delay:** 2s base + random 0-1s jitter
- **Concurrent requests:** 2 per domain
- **Robots.txt:** Obeyed
- **Accept-Language:** `en-IN, hi` (India-focused)

---

## 12. The Complete Tool Stack

| Tool | Role | Port | Container |
|------|------|------|-----------|
| **Scrapy** | Web crawling framework | — | celery-worker |
| **Playwright** | JS rendering (headless Chromium) | — | celery-worker |
| **Celery** | Task queue (schedules spider runs) | — | celery-worker |
| **Celery Beat** | Cron-like scheduler | — | celery-beat |
| **Redis 7** | Celery broker + cache + sessions | 6379 | redis |
| **PostgreSQL 16** | Primary database | 5432 | postgres |
| **TimescaleDB** | Price time-series extension | (on PG) | postgres |
| **Meilisearch 1.7** | Full-text product search | 7700 | meilisearch |
| **Flower** | Celery task monitoring UI | 5555 | flower |
| **Caddy** | Reverse proxy + auto-SSL | 80/443 | caddy |
| **Gunicorn** | Django WSGI server (3 workers) | 8000 | backend |
| **Next.js** | Frontend SSR | 3000 | frontend |

---

## 13. Environment Variables

### Required (Production)

```bash
# Django
DJANGO_SECRET_KEY=<generate: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DJANGO_SETTINGS_MODULE=whydud.settings.prod

# Database (PostgreSQL 16 + TimescaleDB)
POSTGRES_DB=whydud
POSTGRES_USER=whydud
POSTGRES_PASSWORD=<strong password>
POSTGRES_HOST=postgres          # container name in Docker
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0

# Meilisearch
MEILISEARCH_URL=http://meilisearch:7700
MEILISEARCH_MASTER_KEY=<strong key>

# Encryption (AES-256-GCM, 32-byte base64 keys)
EMAIL_ENCRYPTION_KEY=<required>
OAUTH_ENCRYPTION_KEY=<required>

# Domain & URLs
SITE_DOMAIN=whydud.com
FRONTEND_URL=https://whydud.com
NEXT_PUBLIC_API_URL=https://whydud.com
NEXT_PUBLIC_SITE_URL=https://whydud.com

# External Services
RESEND_API_KEY=<from resend.com>
RAZORPAY_KEY_ID=<from razorpay>
RAZORPAY_KEY_SECRET=<from razorpay>
GOOGLE_CLIENT_ID=<OAuth>
GOOGLE_CLIENT_SECRET=<OAuth>
CLOUDFLARE_EMAIL_WEBHOOK_SECRET=<from Cloudflare>

# Monitoring
FLOWER_BASIC_AUTH=admin:<strong password>
```

### Scraping-Specific (Tunable via `common/app_settings.py`)

```bash
SCRAPING_SPIDER_TIMEOUT=3600              # seconds, default 1 hour
SCRAPING_MAX_LISTING_PAGES=5              # pages per category
SCRAPING_RAW_HTML_DIR=data/raw_html       # debug, optional

MATCHING_FUZZY_TITLE_THRESHOLD=0.80
MATCHING_AUTO_MERGE_THRESHOLD=0.85
MATCHING_REVIEW_THRESHOLD=0.60
MATCHING_MAX_CANDIDATES=500

SCRAPING_SPIDER_MAP={"amazon-in": "amazon_in", "flipkart": "flipkart"}
```

---

## 14. Step-by-Step Server Deployment

### Prerequisites

- Linux server (Ubuntu 22.04+ recommended)
- **8-core CPU, 16 GB RAM, 100 GB SSD** minimum
- Docker + Docker Compose installed
- Domain name pointing to server IP (A record)

### Step 1: Clone & Configure

```bash
git clone <repo-url> /opt/whydud
cd /opt/whydud/platform/whydud

# Copy and fill environment variables
cp docker/.env.example docker/.env
nano docker/.env
# Fill ALL required variables listed in Section 13
```

### Step 2: Update Caddyfile Domain

Edit `docker/Caddyfile` — replace the domain placeholder with your actual domain:

```
whydud.com {
    ...
}
```

Caddy handles SSL automatically via Let's Encrypt — no manual cert setup needed.

### Step 3: Build Images

```bash
cd /opt/whydud/platform/whydud/docker

# Build all images
docker compose build
```

### Step 4: Start Infrastructure

```bash
# Start database, cache, search engine first
docker compose up -d postgres redis meilisearch

# Wait for healthy status
docker compose ps
# Repeat until postgres, redis, meilisearch show "healthy"
```

### Step 5: Initialize Database

```bash
# Run Django migrations (creates all tables + TimescaleDB hypertables)
docker compose run --rm backend python manage.py migrate

# Create admin superuser
docker compose run --rm backend python manage.py createsuperuser

# Seed marketplace data
docker compose run --rm backend python manage.py shell -c "
from apps.products.models import Marketplace
Marketplace.objects.get_or_create(
    slug='amazon-in',
    defaults={'name': 'Amazon.in', 'base_url': 'https://www.amazon.in', 'is_active': True}
)
Marketplace.objects.get_or_create(
    slug='flipkart',
    defaults={'name': 'Flipkart', 'base_url': 'https://www.flipkart.com', 'is_active': True}
)
print('Marketplaces seeded.')
"
```

### Step 6: Install Playwright Browsers

```bash
# Playwright needs Chromium installed inside the worker container
docker compose run --rm celery-worker playwright install chromium
```

### Step 7: Launch Everything

```bash
docker compose up -d
```

This starts all 10 services:
- caddy, postgres, redis, meilisearch
- backend, celery-worker, celery-beat, email-worker
- flower, frontend

### Step 8: Verify Services

```bash
# Check all containers
docker compose ps
# All should show "Up" or "Up (healthy)"

# Check logs for errors
docker compose logs -f backend        # Django API server
docker compose logs -f celery-worker   # Spider tasks
docker compose logs -f celery-beat     # Scheduler

# Verify endpoints
curl https://whydud.com/api/health/    # API health check
curl https://whydud.com                 # Frontend
```

### Step 9: Verify Scraping Works

```bash
# Trigger a manual scrape VIA CELERY (this will appear in Flower)
docker compose exec celery-worker python -c "
from apps.scraping.tasks import run_marketplace_spider
result = run_marketplace_spider.delay('amazon-in')
print(f'Task ID: {result.id}')
"

# Monitor in Flower
# Visit: https://whydud.com/flower/
# Login with FLOWER_BASIC_AUTH credentials

# Check ScraperJob in DB
docker compose exec backend python manage.py shell -c "
from apps.scraping.models import ScraperJob
for j in ScraperJob.objects.order_by('-created_at')[:3]:
    print(f'{j.spider_name} | {j.status} | items: {j.items_scraped}/{j.items_failed}')
"
```

### Step 10: Verify Data in Database

```bash
docker compose exec backend python manage.py shell -c "
from apps.products.models import Product, ProductListing
from apps.pricing.models import PriceSnapshot
print(f'Products:  {Product.objects.count()}')
print(f'Listings:  {ProductListing.objects.count()}')
print(f'Snapshots: {PriceSnapshot.objects.count()}')
"
```

---

## 15. Resource Requirements

### Production Server

| Service | RAM | CPU | Notes |
|---------|-----|-----|-------|
| PostgreSQL + TimescaleDB | 2 GB | 1 core | Shared memory for query cache |
| Redis | 512 MB | 0.5 core | 400MB max policy, LRU eviction |
| Meilisearch | 1 GB | 1 core | Scales with index size |
| Django (3 Gunicorn workers) | 1 GB | 1 core | Each worker ~300MB |
| Celery Worker (4 concurrent) | 2 GB | 2 cores | Playwright browsers use RAM |
| Celery Beat | 256 MB | 0.25 core | Lightweight scheduler |
| Email Worker | 512 MB | 0.5 core | Isolated email queue |
| Flower | 128 MB | 0.25 core | Monitoring dashboard |
| Next.js Frontend | 1 GB | 1 core | SSR rendering |
| Caddy | 64 MB | 0.25 core | Reverse proxy |
| **Total** | **~8.5 GB** | **~7 cores** | |

**Recommended:** 8-core CPU, 16 GB RAM, 100 GB SSD

### Development (Local)

Only infrastructure services run in Docker (via `docker-compose.dev.yml`):
- PostgreSQL, Redis, Meilisearch, Flower
- Django and Next.js run locally for hot-reload

---

## 16. Ongoing Monitoring

| What to Monitor | Where | How |
|----------------|-------|-----|
| Celery task status | Flower UI | `https://whydud.com/flower/` |
| Scrape job results | ScraperJob table | Django admin at `/admin/` or shell query |
| Product/listing counts | Database | Shell query (see Section 9) |
| Price history | `price_snapshots` hypertable | TimescaleDB queries |
| Search index health | Meilisearch | `curl http://localhost:7700/indexes/products/stats` |
| Container health | Docker | `docker compose ps` |
| Application logs | Docker logs | `docker compose logs -f <service>` |
| Error tracking (prod) | Sentry | Configured via `sentry-sdk[django]` in prod requirements |

### Useful Monitoring Commands

```bash
# Live scraping logs
docker compose logs -f celery-worker | grep -E "Created|Matched|Scraped|Failed"

# Recent ScraperJob summary
docker compose exec backend python manage.py shell -c "
from apps.scraping.models import ScraperJob
for j in ScraperJob.objects.order_by('-created_at')[:5]:
    print(f'{j.spider_name:12} | {j.status:10} | {j.items_scraped} scraped / {j.items_failed} failed')
"

# Price snapshot count by day (last 7 days)
docker compose exec postgres psql -U whydud -c "
SELECT date_trunc('day', time) AS day, COUNT(*)
FROM price_snapshots
WHERE time > NOW() - INTERVAL '7 days'
GROUP BY day ORDER BY day DESC;
"

# Meilisearch index stats
curl -s http://localhost:7700/indexes/products/stats \
  -H "Authorization: Bearer $MEILISEARCH_MASTER_KEY" | python -m json.tool
```

---

## 17. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Subprocess spiders** | Avoids Twisted reactor restart issues; each process gets a fresh reactor |
| **Raw SQL for PriceSnapshot** | TimescaleDB hypertable has no auto-pk; Django ORM fails |
| **4-step product matching** | EAN → Brand+Model+Variant → Brand+Model → Fuzzy Title → New Product |
| **Playwright for all pages** | Both Amazon and Flipkart render prices/availability via JavaScript |
| **Staggered spider schedules** | Amazon 00/06/12/18 UTC, Flipkart +3h offset → distributes infra load |
| **Price snapshot on every scrape** | Enables time-series analytics even when price unchanged |
| **Batch Meilisearch sync** | ProductPipeline stashes IDs; MeilisearchIndexPipeline batches on spider close |
| **User-Agent rotation** | Anti-detection; 10 realistic UA strings rotated per request |
| **Celery queue separation** | default, scraping, email, scoring, alerts — isolates workloads |
| **Modular monolith** | 13 Django apps, single deployment, shared DB — avoids microservice complexity |
| **Prices in paisa** | Avoids floating-point precision issues with Indian Rupee amounts |
| **Brand aliases** | `Brand.aliases` JSONField maps variant names (e.g., "MI" → "Xiaomi") |
