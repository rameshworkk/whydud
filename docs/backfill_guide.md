# Backfill Pipeline Guide

## Overview

The backfill pipeline imports product data and price history from external sources (PriceHistory.app, BuyHatke) into Whydud's database. It runs as Celery tasks, monitored via Flower.

## Pipeline Phases

| Phase | Task | What it does |
|---|---|---|
| 1 - Discover | `run_phase1_discover` | Parse PH sitemaps → fetch product pages → extract ASINs/FSIDs → create `BackfillProduct` records |
| 2 - BH Fill | `run_phase2_buyhatke` | Bulk fetch price history from BuyHatke for discovered products |
| 3 - PH Extend | `run_phase3_extend` | Deep price history from PriceHistory.app for top products |
| 4 - Inject | `run_phase4_inject` | Inject cached price data into `price_snapshots` hypertable |
| 5 - Refresh | `refresh_price_daily_aggregate` | Refresh the `price_daily` continuous aggregate |

Each phase runs sequentially — the next starts only after the previous completes.

## Setup

### 1. Environment Variables

Add to your `.env` file:

```bash
# Flower dashboard credentials (change in production!)
FLOWER_BASIC_AUTH=admin:your-secure-password
```

### 2. Deploy

```bash
# Rebuild celery-worker (includes scraping queue) and start flower
docker compose -f docker-compose.primary.yml up -d --build celery-worker flower

# Open firewall for Flower direct access
sudo ufw allow 5555/tcp
```

### 3. Access Flower Dashboard

```
http://<SERVER-IP>:5555/
```

Login with the credentials from `FLOWER_BASIC_AUTH` (default: `admin:admin`).

**Note:** The Caddy `/flower` route currently doesn't work (Next.js catches it). Use direct port 5555 access instead.

## Workers

When you open Flower's **Workers** tab, you'll see:

| Worker | Node | Role |
|---|---|---|
| `primary@<hostname>` | Primary server | Main worker — handles queues: `default`, `scoring`, `alerts`, `email`, `scraping` |
| `scraping@<hostname>` | Replica server | Replica worker — handles `scraping` queue |

Both workers listen on `scraping`, so Celery load-balances backfill tasks across them randomly.

## Running the Pipeline

### Option 1: Full Pipeline (single range)

Runs all phases sequentially as a Celery chain:

```bash
docker compose -f docker-compose.primary.yml exec backend python -c "
from apps.pricing.tasks import run_full_backfill_pipeline
r = run_full_backfill_pipeline.delay(sitemap_start=1, sitemap_end=115, filter_electronics=False)
print(f'Task ID: {r.id}')
"
```

Parameters:
- `sitemap_start` / `sitemap_end` — PH sitemap range (1–344 available, each has ~49k products)
- `filter_electronics=False` — import ALL products (set `True` for electronics only)
- `batch_size=5000` — batch size for phases 2–4

**Important:** `run_full_backfill_pipeline` is just an orchestrator — it fires off the chain and returns SUCCESS immediately. The actual work runs as separate chained tasks.

### Option 2: Parallel Multi-Node (faster)

Split sitemaps across both workers for 2x speed. Run individual phases manually.

**Step 1: Update both nodes**
```bash
# On both primary and replica
cd /opt/whydud/whydud && git pull
docker compose -f docker-compose.<node>.yml up -d --build celery-worker
```

**Step 2: Launch Phase 1 with split ranges**
```bash
docker compose -f docker-compose.primary.yml exec backend python -c "
from apps.pricing.tasks import run_phase1_discover
r1 = run_phase1_discover.delay(sitemap_start=2, sitemap_end=2, filter_electronics=False)
r2 = run_phase1_discover.delay(sitemap_start=3, sitemap_end=3, filter_electronics=False)
print(f'Task 1: {r1.id}')
print(f'Task 2: {r2.id}')
"
```

Celery distributes one task per worker — both run in parallel.

**Step 3: After both Phase 1 tasks finish, run Phase 2**
```bash
docker compose -f docker-compose.primary.yml exec backend python -c "
from apps.pricing.tasks import run_phase2_buyhatke
r = run_phase2_buyhatke.delay(batch_size=5000)
print(f'Task ID: {r.id}')
"
```

**Step 4: Continue with Phase 3, 4, 5 similarly**
```bash
# Phase 3
docker compose -f docker-compose.primary.yml exec backend python -c "
from apps.pricing.tasks import run_phase3_extend
r = run_phase3_extend.delay(limit=5000)
print(f'Task ID: {r.id}')
"

# Phase 4
docker compose -f docker-compose.primary.yml exec backend python -c "
from apps.pricing.tasks import run_phase4_inject
r = run_phase4_inject.delay(batch_size=5000)
print(f'Task ID: {r.id}')
"

# Phase 5
docker compose -f docker-compose.primary.yml exec backend python -c "
from apps.pricing.tasks import refresh_price_daily_aggregate
r = refresh_price_daily_aggregate.delay()
print(f'Task ID: {r.id}')
"
```

### Option 3: Management Command (runs directly, not via Celery)

```bash
# Phase 1: Discover
docker compose -f docker-compose.primary.yml exec backend \
  python manage.py backfill_prices discover --start 1 --end 5 --no-filter

# Phase 2: BuyHatke fill
docker compose -f docker-compose.primary.yml exec backend \
  python manage.py backfill_prices bh-fill --batch 5000

# Phase 3: PH deep history
docker compose -f docker-compose.primary.yml exec backend \
  python manage.py backfill_prices ph-extend --limit 5000

# Phase 4a: Targeted scrape
docker compose -f docker-compose.primary.yml exec backend \
  python manage.py backfill_prices scrape --marketplace amazon-in --limit 50

# Phase 4b: Inject cached data
docker compose -f docker-compose.primary.yml exec backend \
  python manage.py backfill_prices inject --batch 5000

# Refresh aggregate
docker compose -f docker-compose.primary.yml exec backend \
  python manage.py backfill_prices refresh-aggregate
```

**Note:** Management commands run directly in the backend container — no time limits, but they stop if you close the terminal. Use `nohup` or `tmux` for long runs.

## Monitoring Progress

### Flower Dashboard (remote)

Visit `http://<SERVER-IP>:5555/`:

- **Workers tab** — see workers online, active tasks, load average
- **Tasks tab** — see each task's state (STARTED, SUCCESS, FAILURE), runtime, kwargs, result
- **Monitor tab** — real-time graphs of task throughput and latency

Click a task's **UUID** link to see full details including traceback on failure.

**Task states:**
- **SUCCESS** on `run_full_backfill_pipeline` = normal (it's just the orchestrator)
- **STARTED** on `run_phase1_discover` = the actual work is happening
- **FAILURE** with `SoftTimeLimitExceeded` = task hit time limit (fixed — now set to None)
- **FAILURE** with `NotRegistered` = worker doesn't have updated code (rebuild it)

### Real-Time Worker Logs (SSH)

Most detailed output — shows every HTTP request, product discovered, errors:

```bash
docker compose -f docker-compose.primary.yml logs -f celery-worker
```

You can close this terminal anytime — it's just viewing logs, not running the task.

### DB-Level Status

```bash
docker compose -f docker-compose.primary.yml exec backend \
  python manage.py backfill_prices status
```

Shows:
- `BackfillProduct` counts by status (discovered, bh_filled, ph_extended, etc.)
- Counts by marketplace (amazon-in, flipkart, etc.)
- `price_snapshots` counts by source
- Existing listing coverage
- Injectable candidates for Phase 4
- Scrape status (pending, scraped, failed)

Run this twice a few minutes apart — if counts increase, tasks are still running.

### Check a Specific Task

```bash
docker compose -f docker-compose.primary.yml exec backend python -c "
from celery.result import AsyncResult
r = AsyncResult('PASTE-TASK-ID-HERE')
print(f'State: {r.state}')
print(f'Result: {r.result}')
"
```

## Key Flags

| Flag | Default | Description |
|---|---|---|
| `--no-filter` | electronics only | Skip the electronics keyword filter, import ALL product categories |
| `--start` / `--end` | 1–5 | Sitemap index range (344 total, ~49k products each) |
| `--limit` | unlimited | Cap max products to process |
| `--batch` | 5000 | Batch size for BH fill / inject phases |
| `--marketplace` | all | Filter by marketplace slug (e.g., `amazon-in`, `flipkart`) |
| `--dry-run` | off | Fetch data but don't write to DB |

## Scraping Considerations

- PriceHistory.app is hit at ~1 request every 2 seconds (~1,800/hour) per worker
- 115 sitemaps × ~49k products = ~5.6 million pages total
- **Run during off-peak hours** (night IST) to reduce chance of rate limiting
- **Start small** (e.g., 1–10 sitemaps) and watch for HTTP 403/429 errors in worker logs
- **Spread over multiple days** — do 10–20 sitemaps per night
- Products are upserted by ASIN — running the same range twice won't create duplicates

## Architecture Notes

- All backfill tasks run on the `scraping` Celery queue
- Backfill tasks have `soft_time_limit=None, time_limit=None` (no timeout)
- Global Celery default is 25 min soft / 30 min hard — backfill tasks override this
- Products are saved to DB immediately (not batched), so `status` shows real-time progress
- The `BackfillProduct` model tracks each product's journey through the pipeline
- Price data lands in the `price_snapshots` TimescaleDB hypertable
- The `price_daily` continuous aggregate auto-summarizes daily min/max/avg prices
- Tasks submitted from any container go to Redis queue — any worker can pick them up

## Troubleshooting

### `SoftTimeLimitExceeded`
The task hit Celery's time limit. Fixed by setting `soft_time_limit=None` on all backfill tasks. Ensure you've deployed the latest code and rebuilt the celery-worker.

### `NotRegistered('apps.pricing.tasks.run_full_backfill_pipeline')`
The worker that picked up the task doesn't have the latest code. Fix:
```bash
cd /opt/whydud/whydud && git pull
docker compose -f docker-compose.<node>.yml up -d --build celery-worker
```

### Tasks stuck in PENDING
The celery-worker might not be listening on the `scraping` queue. Verify:
```bash
docker compose -f docker-compose.primary.yml exec celery-worker \
  celery -A whydud inspect active_queues
```

### Flower not accessible
```bash
# Check container is running
docker compose -f docker-compose.primary.yml ps flower
docker compose -f docker-compose.primary.yml logs flower

# Check firewall
sudo ufw status | grep 5555
```

### Check if management command is still running
```bash
docker compose -f docker-compose.primary.yml exec backend ps aux | grep backfill
```

### Reset failed products
```bash
docker compose -f docker-compose.primary.yml exec backend \
  python manage.py backfill_prices reset-failed
```
### Trigger via Celery (from the server):

docker compose -f docker-compose.primary.yml exec backend python -c "
from apps.pricing.tasks import run_phase1_discover
result = run_phase1_discover.delay(sitemap_start=1, sitemap_end=1, filter_electronics=False)
print(f'Task ID: {result.id}')
"
## Monitor progress
docker compose -f docker-compose.primary.yml exec backend python manage.py backfill_prices status

docker compose -f docker-compose.primary.yml logs -f celery-worker

docker compose -f docker-compose.primary.yml logs -f celery-worker --tail 50 | grep -i "phase 1\|progress\|created\|parsed"