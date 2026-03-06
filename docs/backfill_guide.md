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
# Rebuild celery-worker (now includes scraping queue) and start flower
docker compose -f docker-compose.primary.yml up -d --build celery-worker flower

# Reload Caddy to pick up the /flower/* route
docker compose -f docker-compose.primary.yml exec caddy caddy reload --config /etc/caddy/Caddyfile
```

### 3. Access Flower Dashboard

```
https://whydud.com/flower/
```

Login with the credentials from `FLOWER_BASIC_AUTH`.

## Running the Pipeline

### Full Pipeline (recommended)

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

### Individual Phases (via management command)

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

### Individual Phases (via Celery tasks)

```bash
docker compose -f docker-compose.primary.yml exec backend python -c "
from apps.pricing.tasks import run_phase1_discover
r = run_phase1_discover.delay(sitemap_start=1, sitemap_end=5, filter_electronics=False)
print(f'Task ID: {r.id}')
"
```

Replace `run_phase1_discover` with any task:
- `run_phase1_discover`
- `run_phase2_buyhatke`
- `run_phase3_extend`
- `run_phase4_inject`
- `scrape_backfill_products_task`
- `refresh_price_daily_aggregate`

## Monitoring Progress

### Flower Dashboard (remote)

Visit `https://whydud.com/flower/`:

- **Tasks tab** — see each phase running/completed with return values
- **Worker tab** — see celery-worker load, active tasks, queues
- **Monitor tab** — real-time graphs of task throughput and latency

### DB-level Status (SSH)

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

### Check a Specific Task

```bash
docker compose -f docker-compose.primary.yml exec backend python -c "
from celery.result import AsyncResult
r = AsyncResult('PASTE-TASK-ID-HERE')
print(f'State: {r.state}')
print(f'Result: {r.result}')
"
```

### Celery Worker Logs

```bash
docker compose -f docker-compose.primary.yml logs -f celery-worker
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

## Architecture Notes

- All backfill tasks run on the `scraping` Celery queue
- Products are saved to DB immediately (not batched), so `status` shows real-time progress
- The `BackfillProduct` model tracks each product's journey through the pipeline
- Price data lands in the `price_snapshots` TimescaleDB hypertable
- The `price_daily` continuous aggregate auto-summarizes daily min/max/avg prices

## Troubleshooting

### Tasks stuck in PENDING
The celery-worker might not be listening on the `scraping` queue. Verify:
```bash
docker compose -f docker-compose.primary.yml exec celery-worker \
  celery -A whydud inspect active_queues
```

### Flower not accessible
Check the container is running:
```bash
docker compose -f docker-compose.primary.yml ps flower
docker compose -f docker-compose.primary.yml logs flower
```

### Reset failed products
```bash
docker compose -f docker-compose.primary.yml exec backend \
  python manage.py backfill_prices reset-failed
```
