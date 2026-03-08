# Whydud — Operations & Administration Guide

> **Audience:** Solo founder / ops engineer running the Whydud platform.
> **Last updated:** 2026-03-08

---

## TABLE OF CONTENTS

```
1. WAYS TO INTERACT WITH THE BACKEND
   1.1 Management Commands (Direct CLI)
   1.2 Celery Tasks (Background Jobs)
   1.3 Django Admin Panel
   1.4 Flower Dashboard (Task Monitoring)
   1.5 Direct Database Queries

2. BACKFILL PIPELINE — OPERATIONAL GUIDE
   2.1 Pipeline Overview (5 Phases)
   2.2 Discovery (Phase 1)
   2.3 Price History Fill (Phase 2-3)
   2.4 Lightweight Records (Phase 3 — The Fast Path)
   2.5 Enrichment (Phase 4 — The Slow Path)
   2.6 Reviews + DudScore (Phase 5 — The Trust Path)
   2.7 First Run Playbook
   2.8 Scaling to 17M

3. INTERESTING OPERATIONAL FEATURES
   3.1 Tiered Enrichment (Playwright vs curl_cffi)
   3.2 On-Demand Enrichment (User Visit Trigger)
   3.3 Overnight Runner
   3.4 Data Verification
   3.5 Retry & Escalation Logic
   3.6 DataImpulse Session Routing
   3.7 Worker-Only Remote Nodes
   3.8 Review Chaining + DudScore Pipeline

4. ADMIN FEATURES
   4.1 BackfillProduct Admin
   4.2 Celery Beat Schedules
   4.3 Scraping Admin

5. THINGS TO BE CAUTIOUS ABOUT
   5.1 Data Safety Rules
   5.2 Scraping Safety
   5.3 Backfill Safety
   5.4 Price Conversion Gotchas
   5.5 Common Failure Modes & Fixes

6. QUICK REFERENCE — ALL COMMANDS
```

---

# 1. WAYS TO INTERACT WITH THE BACKEND

## 1.1 Management Commands (Direct CLI)

Management commands run **synchronously** inside the backend container. They block your terminal but have no time limits. Use `tmux`/`nohup` for long operations.

### How to Run

```bash
# On server (inside Docker)
docker compose -f docker-compose.primary.yml exec backend \
  python manage.py <command> <subcommand> [options]

# Local development
python manage.py <command> <subcommand> [options]
```

### Available Management Commands

| Command | Subcommand | Purpose |
|---------|-----------|---------|
| `backfill_prices` | `status` | Show full pipeline status dashboard |
| `backfill_prices` | `status --watch` | Live-updating status (refreshes every 30s) |
| `backfill_prices` | `status --json` | Machine-readable JSON output |
| `backfill_prices` | `discover` | Phase 1: Discover products from PH sitemaps |
| `backfill_prices` | `bh-fill` | Phase 2: Bulk BuyHatke price history (`--celery --workers N` for parallel) |
| `backfill_prices` | `ph-extend` | Phase 3: Deep PriceHistory.app data (`--celery --workers N` for parallel) |
| `backfill_prices` | `scrape` | Phase 4a: Targeted marketplace scraping |
| `backfill_prices` | `inject` | Phase 4b: Inject cached price data |
| `backfill_prices` | `create-lightweight` | Create Product+Listing from tracker data |
| `backfill_prices` | `assign-priorities` | Assign P1/P2/P3 + review targets |
| `backfill_prices` | `enrich` | Run tiered enrichment |
| `backfill_prices` | `run-overnight` | All-in-one overnight enrichment |
| `backfill_prices` | `verify-data` | Data quality checks |
| `backfill_prices` | `retry-failed` | Reset failed items for retry |
| `backfill_prices` | `skip-products` | Skip low-value products |
| `backfill_prices` | `reset-failed` | Reset all failed BackfillProducts |
| `backfill_prices` | `refresh-aggregate` | Refresh price_daily TimescaleDB aggregate |
| `backfill_prices` | `existing` | Phase 0: Backfill existing ProductListings |
| `sync_meilisearch` | — | Full Meilisearch reindex |
| `delete_seed_data` | `--confirm` | Delete seed data safely |

---

## 1.2 Celery Tasks (Background Jobs)

Celery tasks run **asynchronously** on worker nodes. Fire-and-forget via `.delay()` or schedule via Celery Beat.

### How to Trigger Tasks Manually

```bash
# From the backend container
docker compose -f docker-compose.primary.yml exec backend python -c "
from apps.pricing.tasks import run_phase1_discover
result = run_phase1_discover.delay(sitemap_start=1, sitemap_end=5, filter_electronics=False)
print(f'Task ID: {result.id}')
"
```

### Check Task Status

```bash
docker compose -f docker-compose.primary.yml exec backend python -c "
from celery.result import AsyncResult
r = AsyncResult('PASTE-TASK-ID-HERE')
print(f'State: {r.state}')
print(f'Result: {r.result}')
"
```

### Key Celery Tasks

| Task | Queue | Trigger | Purpose |
|------|-------|---------|---------|
| `run_phase1_discover` | scraping | Manual / `--celery` | Discover products from PH sitemaps |
| `run_phase2_buyhatke` | scraping | Manual / `--celery` | BuyHatke bulk price history (parallel-safe via SKIP LOCKED) |
| `run_phase3_extend` | scraping | Manual / `--celery` | PH deep history extension (parallel-safe via SKIP LOCKED) |
| `enrich_batch` | scraping | Beat (every 15 min) | Process 100 products by priority |
| `enrich_single_product` | scraping | On-demand | Enrich 1 product (routes to Playwright/curl_cffi) |
| `enrich_via_http` | scraping | Chained | curl_cffi extraction (P2-P3 products) |
| `cleanup_stale_enrichments` | default | Beat (hourly) | Reset stuck enrichments |
| `check_review_completion` | default | Beat (every 15 min) | Detect completed review scrapes |
| `queue_review_scraping` | scraping | Chained | Fire review spider after enrichment |
| `post_review_enrichment` | scoring | Chained | DudScore + fake detection after reviews |
| `run_marketplace_spider` | scraping | Beat (every 6h) | Amazon/Flipkart product scraping |
| `run_review_spider` | scraping | Beat (daily) + chained | Review scraping |
| `scrape_product_adhoc` | scraping | On-demand | Scrape a single product URL |
| `check_price_alerts` | alerts | Beat (every 4h) | Check & trigger price alerts |
| `run_full_backfill_pipeline` | scraping | Manual | Run complete Phase 1→5 chain |
| `refresh_price_daily_aggregate` | default | Manual | Refresh TimescaleDB aggregate |

---

## 1.3 Django Admin Panel

Access at `https://whydud.com/admin/` or `http://localhost:8000/admin/` (dev).

### BackfillProduct Admin Features
- **List view:** external_id, marketplace, title, status, scrape_status, enrichment_priority, enrichment_method, review_status, price_data_points
- **Filters:** status, scrape_status, enrichment_priority, enrichment_method, review_status, marketplace_slug
- **Search:** external_id, title, ph_code
- **Action:** "Mark for review scraping" — bulk-marks scraped products for reviews

### Other Admin Panels
- **Products** — All Product, ProductListing, Marketplace, Category, Brand models
- **Pricing** — PriceAlert, MarketplaceOffer, BackfillProduct
- **Scraping** — ScraperJob (spider run history)
- **Reviews** — Review moderation, ReviewerProfile
- **Scoring** — DudScoreConfig (weight tuning), DudScoreHistory

---

## 1.4 Flower Dashboard (Task Monitoring)

Real-time Celery monitoring at `http://<SERVER-IP>:5555/`.

| Tab | What It Shows |
|-----|--------------|
| **Workers** | Online workers, active tasks, CPU/memory, queues listened |
| **Tasks** | Task state (STARTED/SUCCESS/FAILURE), runtime, arguments, result |
| **Monitor** | Real-time graphs of task throughput and latency |
| **Broker** | Redis queue depths |

**Login:** Credentials from `FLOWER_BASIC_AUTH` env var (default: `admin:admin`).

**Tip:** Click a task's UUID to see full details including traceback on failure.

---

## 1.5 Direct Database Queries

```bash
# From server
docker exec whydud-postgres psql -U whydud -c "YOUR SQL HERE"

# Quick status check
docker exec whydud-postgres psql -U whydud -c "
  SELECT status, COUNT(*) FROM backfill_products GROUP BY status ORDER BY count DESC;
"

# Price snapshots by source
docker exec whydud-postgres psql -U whydud -c "
  SELECT source, COUNT(*) FROM price_snapshots GROUP BY source;
"

# Replication lag (PRIMARY only)
docker exec whydud-postgres psql -U whydud -c "
  SELECT client_addr, state, pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes
  FROM pg_stat_replication;
"
```

---

# 2. BACKFILL PIPELINE — OPERATIONAL GUIDE

## 2.1 Pipeline Overview

```
PHASE 1: DISCOVER          PHASE 2-3: HISTORY          PHASE 3: CREATE
(Crawl tracker sitemaps) → (Fetch price timeseries) → (Lightweight Product records)
     Free, fast                Free, fast                  Free, instant
     50K+/day                  10K+/day                    Usable on site immediately

                    PHASE 4: ENRICH                     PHASE 5: REVIEWS
                    (Scrape marketplace details)   →    (Scrape reviews + DudScore)
                    Costs proxy bandwidth               Only top 100K products
                    P1: Playwright, P2-P3: curl_cffi    Auto-chains after enrichment
```

**Fast Path (Phases 1-3):** Free, zero proxy cost, 50K+ products/day. Products appear on site with title, price, marketplace link, and full price history chart.

**Slow Path (Phase 4):** Costs proxy bandwidth (~$0.70/GB). Fills in images, specs, seller info. Playwright for high-value, curl_cffi for rest.

**Trust Path (Phase 5):** Reviews + DudScore for top 100K. Whydud's core differentiator.

---

## 2.2 Discovery (Phase 1)

```bash
# Discover from PriceHistory.app sitemaps (1-343 available, ~49K products each)
python manage.py backfill_prices discover --start 1 --end 5

# Options
--start N              # First sitemap index (default: 1)
--end N                # Last sitemap index (default: 5)
--limit N              # Cap max products
--filter-electronics   # Only keep electronics/tech (default: all categories)
--delay N              # Seconds between requests (default: 0.5)
```

**Discovery is concurrent:** Sitemaps are parsed in parallel, HTML pages are fetched via `asyncio.gather()` with semaphore-limited concurrency (default: 5). ~45K products from 1 sitemap takes ~2 hours.

**Launch Phase 1 via Celery with split ranges:**
```bash
docker compose -f docker-compose.primary.yml exec backend python -c "
from apps.pricing.tasks import run_phase1_discover
r1 = run_phase1_discover.delay(sitemap_start=1, sitemap_end=1)
r2 = run_phase1_discover.delay(sitemap_start=2, sitemap_end=2)
print(f'Task 1: {r1.id}')
print(f'Task 2: {r2.id}')
"


**Safe to re-run:** Products are upserted by ASIN — duplicates silently skipped.

---

## 2.3 Price History Fill (Phase 2-3)

```bash
# BuyHatke bulk fill — in-process (blocks terminal)
python manage.py backfill_prices bh-fill --batch 5000

# BuyHatke bulk fill — via Celery workers (recommended for large runs)
python manage.py backfill_prices bh-fill --celery --workers 4 --batch 5000

# PriceHistory.app deep extension — in-process
python manage.py backfill_prices ph-extend --limit 5000

# PriceHistory.app deep extension — via Celery workers
python manage.py backfill_prices ph-extend --celery --workers 4 --limit 5000
```

Both phases use `asyncio.gather()` with semaphore-limited concurrency (default: 5 concurrent requests, 0.5s delay per request). Each run claims a batch via `SELECT ... FOR UPDATE SKIP LOCKED` — safe for parallel execution.

### Parallel Workers (Phase 2-3)

Both `bh-fill` and `ph-extend` support **safe parallel execution** across multiple worker nodes using PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED`. Each worker atomically claims a non-overlapping batch — no duplicate work.

**Option A: Celery dispatch (recommended)** — one command dispatches N tasks to your worker pool:

```bash
# Dispatch 4 parallel bh-fill tasks to Celery workers
python manage.py backfill_prices bh-fill --celery --workers 4 --batch 12000

# Dispatch 4 parallel ph-extend tasks to Celery workers
python manage.py backfill_prices ph-extend --celery --workers 4 --limit 5000

# Customize delay per task
python manage.py backfill_prices bh-fill --celery --workers 4 --delay 0.8
```

Each dispatched task claims its own batch via SKIP LOCKED. Monitor via Flower or `celery -A whydud inspect active`.

**Option B: Manual per-node** — run on each node individually:

```bash
# Node 1 (primary)
docker compose -f docker-compose.primary.yml exec \
  backend python manage.py backfill_prices bh-fill --batch 12000

# Node 2 (oracle)
docker compose -f docker-compose.oracle.yml exec \
  backend python manage.py backfill_prices bh-fill --batch 12000

# Node 3, Node 4: same command — each claims its own batch automatically
```

**How it works:**
1. Worker starts → atomically claims N items (status → `bh_filling` / `ph_extending`)
2. Other workers' queries skip locked/claimed rows
3. On success → status moves to `bh_filled` / `ph_extended`
4. On crash → `finally` block releases unclaimed items back to original status
5. Stale claims (>1hr) can be recovered: `backfill_prices retry-failed --history`

**Speed (~300 products/min per node, 5 concurrent requests, 0.5s delay):**
- `bh-fill`: 4 nodes × ~300/min = **~1,200/min → 45K in ~38 minutes**
- `ph-extend`: 4 nodes × 3 concurrent → **12 parallel requests**
- Slow down if needed: `-e BACKFILL_BH_DELAY=1.0 -e BACKFILL_BH_CONCURRENCY=3`

---

## 2.4 Lightweight Records (Phase 3 — The Fast Path)

This is the **critical innovation**. Creates Product + ProductListing records directly from tracker data — no marketplace scraping needed.

```bash
# Create lightweight records (run in loop until 0 candidates remain)
python manage.py backfill_prices create-lightweight --batch 2000
```

**What a lightweight record provides:**
- Title, price, marketplace link, 1 thumbnail image
- Full price history chart (200-500 data points spanning months/years)
- Searchable via Meilisearch immediately

**What's missing (filled by enrichment later):**
- Full image gallery, specs table, seller info
- Reviews, DudScore
- Variant options, bank offers

---

## 2.5 Enrichment (Phase 4)

### Assign Priorities First

```bash
python manage.py backfill_prices assign-priorities
```

This runs 3 sub-steps:
1. **Populate derived fields** — current_price from raw_price_data, category_name from title regex
2. **Assign enrichment priorities:**
   - **P1 (Playwright):** 200+ price points, OR tier-1 category, OR top brand + price > ₹10K
   - **P2 (curl_cffi):** 50+ price points, OR price ₹5K-₹2L, OR tier-2 category
   - **P3 (curl_cffi-low):** Everything else
3. **Mark review targets** — Top 100K products (all P1 + top P2 by popularity)

### Run Enrichment

```bash
# Test with small batch
python manage.py backfill_prices enrich --batch 5

# Single product by ID
python manage.py backfill_prices enrich --id <backfill_product_id>

# Overnight run (auto-stops at 6 AM IST)
python manage.py backfill_prices run-overnight --stop-at 06:00 --batch 100
```

### Enrichment Routing Logic

```
Product arrives for enrichment
  │
  ├── P0 (on-demand, user visited) → Playwright (immediate, priority 9)
  ├── P1 (high-value)              → Playwright (full scrape)
  ├── P2 (mid-value)               → curl_cffi (HTTP only, 10x cheaper)
  │                                     └── 3 failures → escalate to Playwright
  └── P3 (low-value)               → curl_cffi
                                         └── 3 failures → mark failed
```

---

## 2.6 Reviews + DudScore (Phase 5)

Reviews chain **automatically** after detail enrichment for top 100K products:

```
Detail enrichment completes → scrape_status='scraped'
  └── review_status='pending'? → YES → queue_review_scraping
       └── Review spider runs (10-30 reviews per product)
            └── post_review_enrichment
                 ├── detect_fake_reviews
                 └── recalculate_dudscore
                      └── Product FULLY COMPLETE ✅
```

**Manual review scraping:**
```bash
python manage.py backfill_prices scrape-reviews --batch 100
```

---

## 2.7 First Run Playbook

```bash
# Step 1: Create lightweight records from existing ~44K products
python manage.py backfill_prices create-lightweight --batch 2000
# Repeat until status shows 0 candidates

# Step 2: Assign priorities + review targets
python manage.py backfill_prices assign-priorities

# Step 3: Verify everything looks right
python manage.py backfill_prices status
python manage.py backfill_prices verify-data

# Step 4: Test enrichment with a small batch
python manage.py backfill_prices enrich --batch 5
# Wait 2-3 minutes, then check:
python manage.py backfill_prices status

# Step 5: First overnight run
python manage.py backfill_prices run-overnight

# Step 6: Next morning
python manage.py backfill_prices status
```

---

## 2.8 Scaling to 17M

```
Week 1:  500K discovered + history + lightweight records live
         50K P1 enriched overnight
         Site has 500K products with price charts

Week 2:  2M total products, 700K enriched
         100K with reviews + DudScore
         Deploy 3 free worker nodes

Week 3:  5M products (add BuyHatke source)
         1M enriched via curl_cffi

Week 4+: Scale to 17M discovered
         2.5M enriched, 100K with reviews
         Background drip enrichment + on-demand
```

**Bandwidth budget (recommended scenario):**
```
Detail (Playwright P1):   500K × 625KB  = 312 GB  → $219
Detail (curl_cffi P2):    2M × 50KB     = 100 GB  → $70
Reviews (top 100K):       100K × 750KB  = 75 GB   → $53
Skip (14.5M lightweight): 14.5M         = 0 GB    → $0
────────────────────────────────────────────────────────
Total one-time:                           487 GB     $342 (₹28,700)
Ongoing:                                  ~1-2 GB/day  ~$45/month
```

---

# 3. INTERESTING OPERATIONAL FEATURES

## 3.1 Tiered Enrichment (Playwright vs curl_cffi)

curl_cffi impersonates Chrome's TLS fingerprint without launching a browser:
- **10x cheaper** (~50KB vs ~500KB per product)
- **10x faster** (0.3s vs 3-5s per product)
- **~55% success rate** through residential proxy (higher during IST midnight-6am)
- Gets: title, brand, price, MRP, specs, rating, 1 image, seller
- Misses: full image gallery, variants, bank offers

**Auto-escalation:** After 3 curl_cffi failures, product automatically escalates to Playwright.

---

## 3.2 On-Demand Enrichment

When a user visits a **lightweight product page**, the system automatically triggers P0 enrichment:

```python
# In ProductDetailView (automatic):
if product.is_lightweight:
    trigger_on_demand_enrichment(listing.external_id, listing.marketplace.slug)
    # Sets enrichment_priority=0, fires with Celery priority=9
```

Product details typically available within 30-60 seconds of first visit.

---

## 3.3 Overnight Runner

All-in-one command for unattended overnight enrichment:

```bash
python manage.py backfill_prices run-overnight \
  --stop-at 06:00 \        # Stop at 6 AM IST (default)
  --batch 100 \             # Products per iteration
  --progress-interval 300   # Report every 5 minutes
```

Continuously processes enrichment queue, logs progress, auto-stops at cutoff time.

---

## 3.4 Data Verification

```bash
python manage.py backfill_prices verify-data
```

Checks for:
- `is_lightweight=True` but product has full data (should be upgraded)
- `scrape_status='scraped'` but `product_listing` is NULL (broken link)
- `review_status='scraped'` but 0 reviews in DB (phantom completion)
- Duplicate `(marketplace, external_id)` combinations
- Products with `price=0` (invalid data)
- Orphaned BackfillProducts (no matching product)

---

## 3.5 Retry & Escalation Logic

```bash
# Retry failed enrichments
python manage.py backfill_prices retry-failed --scrape

# Retry failed review scraping
python manage.py backfill_prices retry-failed --reviews

# Retry failed history fetches
python manage.py backfill_prices retry-failed --history

# Preview without making changes
python manage.py backfill_prices retry-failed --scrape --dry-run
```

**Automatic retry logic:**
- Stuck in 'enriching' for 2+ hours → reset to 'pending' (if retry_count < 3)
- retry_count >= 3 → marked 'failed'
- curl_cffi failures (3x) → auto-escalate to Playwright
- Review scraping stuck for 3+ hours → marked 'failed'

---

## 3.6 DataImpulse Session Routing

Each Celery worker gets a unique session with the proxy:

```
worker oracle-w1 scraping iPhone  → session: oracle-w1_a3f8b2c1 → IP 103.42.x.x
worker oracle-w2 scraping Samsung → session: oracle-w2_7d2e9f4a → IP 49.207.x.x
worker oci-w1 scraping Laptop     → session: oci-w1_e5c1d8b3   → IP 182.73.x.x
```

Three simultaneous scrapes, three different IPs, each with internal consistency (listing + child pages through same IP).

Set `CELERY_WORKER_ID` env var per worker node.

---

## 3.7 Worker-Only Remote Nodes

Deploy lightweight enrichment workers on free-tier VMs (OCI, GCP):

```bash
# Uses docker/docker-compose.worker.yml
# Single service: celery-enrichment
# Connects to primary via WireGuard
# 1GB memory limit
# No database, no Redis, no web server
```

---

## 3.8 Review Chaining + DudScore Pipeline

After detail enrichment, the system automatically:
1. Fires review spider (Amazon reviews / Flipkart reviews)
2. Saves 10-30 reviews per product
3. Runs `detect_fake_reviews` — rule-based fraud detection
4. Runs `recalculate_dudscore` — Whydud's proprietary trust score
5. Product is FULLY COMPLETE with trust signals

**Two detection paths:**
- **Playwright path:** `ProductPipeline._close_backfill_loop()` chains reviews
- **curl_cffi path:** `enrich_via_http` chains reviews directly

---

# 4. ADMIN FEATURES

## 4.1 BackfillProduct Admin

In Django Admin (`/admin/pricing/backfillproduct/`):

**Filters available:**
- Status (Discovered, BH Filled, PH Extended, Done, Failed, Skipped)
- Scrape Status (pending, enriching, scraped, failed)
- Enrichment Priority (P0, P1, P2, P3)
- Enrichment Method (pending, playwright, curl_cffi, skipped)
- Review Status (skip, pending, scraping, scraped, failed)
- Marketplace (amazon-in, flipkart, etc.)

**Bulk action:** "Mark for review scraping" — select products → mark for reviews.

---

## 4.2 Celery Beat Schedules

All automated schedules (configured in `whydud/celery.py`):

| Schedule | Task | What Happens |
|----------|------|-------------|
| Every 15 min | `enrich_batch` | Process 100 products by priority |
| Every 15 min | `check_review_completion` | Detect finished review scrapes |
| Hourly | `cleanup_stale_enrichments` | Reset stuck enrichments |
| Every 4h | `check_price_alerts` | Trigger price alert notifications |
| Every 6h (staggered) | `run_marketplace_spider` | Amazon/Flipkart product scraping |
| Daily 04:00 UTC | `run_review_spider (amazon)` | Amazon review scraping |
| Daily 07:00 UTC | `run_review_spider (flipkart)` | Flipkart review scraping |
| Daily 01:00 UTC | `meilisearch_full_reindex` | Full search index rebuild |
| Every 30 min | `detect_deals` | Blockbuster deal detection |
| Monthly (1st, 03:00) | `dudscore_full_recalc` | Full DudScore recalculation |

---

## 4.3 Scraping Admin

**ScraperJob model** tracks every spider run:
- Spider name, marketplace, status, start/end time
- Items scraped count, error count
- Full log/traceback on failure

View at `/admin/scraping/scraperjob/`.

---

# 5. THINGS TO BE CAUTIOUS ABOUT

## 5.1 Data Safety Rules (ABSOLUTE — NEVER VIOLATE)

```
❌ NEVER run Product.objects.all().delete() or bulk deletes
❌ NEVER run DELETE FROM or TRUNCATE on any table
❌ NEVER drop a column without explicit confirmation
❌ NEVER use .delete() on a queryset without a specific narrow filter
✅ ALWAYS print count before deleting: print(f"Will delete {qs.count()} items")
✅ To delete seed data: python manage.py delete_seed_data --confirm
```

---

## 5.2 Scraping Safety

```
❌ NEVER scrape with --max-pages > 5 unless explicitly asked
❌ NEVER modify proxy middleware to fall back to direct requests
✅ ALWAYS verify Docker is running: docker compose ps
✅ ALWAYS log item counts at end of every spider run
✅ Run scraping during off-peak IST hours (midnight-6am)
✅ Start small (1-10 sitemaps), watch for HTTP 403/429 errors
```

---

## 5.3 Backfill Safety

```
❌ NEVER run create-lightweight with --batch > 5000 without confirmation
❌ NEVER run async-discover with --concurrency > 30
✅ ALWAYS check status before and after any backfill operation
✅ Rate limit tracker API calls: max 1-2 req/sec per source
✅ Run during IST midnight-6am for best success rates
✅ Pipeline hooks must NEVER crash the main scraping pipeline
   (all wrapped in try/except with pass on ImportError)
```

---

## 5.4 Price Conversion Gotchas

This is a **common source of bugs**:

| Context | Unit | Example |
|---------|------|---------|
| Tracker data (raw_price_data) | Paisa (integer) | `6499900` = ₹64,999 |
| price_snapshots table | Rupees (Decimal 12,2) | `64999.00` |
| Product.current_best_price | Rupees (Decimal 12,2) | `64999.00` |
| Frontend display | ₹ formatted | `₹64,999` |

**Rule:** When injecting tracker data into price_snapshots: **divide paisa by 100**.

---

## 5.5 Common Failure Modes & Fixes

### Tasks stuck in PENDING
```bash
# Worker might not be listening on the right queue
docker compose -f docker-compose.primary.yml exec celery-worker \
  celery -A whydud inspect active_queues
```

### SoftTimeLimitExceeded
Backfill tasks have `soft_time_limit=None`. If you see this, the worker has stale code:
```bash
cd /opt/whydud/whydud && git pull
docker compose -f docker-compose.primary.yml up -d --build celery-worker
```

### NotRegistered error
Worker doesn't have the latest code. Rebuild:
```bash
docker compose -f docker-compose.<node>.yml up -d --build celery-worker
```

### Enrichments stuck in 'enriching'
The `cleanup_stale_enrichments` task runs hourly and auto-resets these. To manually fix:
```bash
python manage.py backfill_prices retry-failed --scrape
```

### Flower not accessible
```bash
docker compose -f docker-compose.primary.yml ps flower
docker compose -f docker-compose.primary.yml logs flower
sudo ufw status | grep 5555
```

### Replication lag
```bash
docker exec whydud-postgres psql -U whydud -c \
  "SELECT client_addr, state, pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes FROM pg_stat_replication;"
```

---

# 6. QUICK REFERENCE — ALL COMMANDS

## Status & Monitoring
```bash
python manage.py backfill_prices status              # Full dashboard
python manage.py backfill_prices status --watch       # Live updating (30s)
python manage.py backfill_prices status --json        # Machine-readable
python manage.py backfill_prices verify-data          # Data quality checks
```

## Discovery & History
```bash
python manage.py backfill_prices discover --start 1 --end 10
python manage.py backfill_prices bh-fill --batch 5000
python manage.py backfill_prices ph-extend --limit 5000

# Via Celery workers (parallel)
python manage.py backfill_prices bh-fill --celery --workers 4 --batch 5000
python manage.py backfill_prices ph-extend --celery --workers 4 --limit 5000
```

## Lightweight Records
```bash
python manage.py backfill_prices create-lightweight --batch 2000
```

## Enrichment
```bash
python manage.py backfill_prices assign-priorities
python manage.py backfill_prices enrich --batch 100
python manage.py backfill_prices enrich --id <backfill_product_id>
python manage.py backfill_prices run-overnight --stop-at 06:00
```

## Retry & Maintenance
```bash
python manage.py backfill_prices retry-failed --scrape
python manage.py backfill_prices retry-failed --reviews
python manage.py backfill_prices retry-failed --history
python manage.py backfill_prices skip-products --price-below 10000
python manage.py backfill_prices skip-products --category "grocery"
python manage.py backfill_prices reset-failed
python manage.py backfill_prices refresh-aggregate
```

## Scraping
```bash
python manage.py backfill_prices scrape --marketplace amazon-in --limit 50
python manage.py backfill_prices scrape-reviews --batch 100
```

## Server Operations
```bash
# Logs
docker compose -f docker-compose.primary.yml logs -f celery-worker
docker compose -f docker-compose.primary.yml logs -f backend

# Deploy
cd /opt/whydud/whydud && git pull
docker compose -f docker-compose.primary.yml build && docker compose -f docker-compose.primary.yml up -d

# Migrations (PRIMARY only)
docker compose -f docker-compose.primary.yml exec backend python manage.py migrate

# Backup
/opt/scripts/backup-db.sh

# Replication check
docker exec whydud-postgres psql -U whydud -c \
  "SELECT client_addr, state, pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes FROM pg_stat_replication;"
```

---

## BackfillProduct Status Field Reference

```
status:              Discovered → [BH Filling] → BH Filled → [PH Extending] → PH Extended → Done → Failed/Skipped
                     (bracketed = transient parallel-worker claim states)
scrape_status:       pending → enriching → scraped → failed
review_status:       skip → pending → scraping → scraped → failed
enrichment_priority: 0=on-demand, 1=Playwright, 2=curl_cffi, 3=curl_cffi-low
enrichment_method:   pending → playwright / curl_cffi / skipped
```

## Product Lifecycle

```
Discovered → History Fetched → Lightweight Record (live on site with price chart)
  → Enrichment (P0-P1: Playwright, P2-P3: curl_cffi) → scrape_status='scraped'
    → Reviews (top 100K) → DudScore calculation → FULLY COMPLETE ✅
```
