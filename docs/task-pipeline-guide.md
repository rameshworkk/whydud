# Whydud — Full Pipeline Execution Guide (Task-by-Task)

> **Purpose:** Step-by-step operational playbook for running the entire backfill pipeline
> across distributed worker nodes. Covers every phase from discovery to lightweight records,
> with exact commands, flags, risks, monitoring, and troubleshooting.
>
> **Last updated:** 2026-03-10

---

## TABLE OF CONTENTS

```
1. CLUSTER OVERVIEW
   1.1 Node Topology
   1.2 How Workers Pick Up Tasks
   1.3 SKIP LOCKED — Why There's No Overlap

2. PRE-FLIGHT CHECKLIST

3. PHASE 1: DISCOVERY
   3.1 What It Does
   3.2 Commands
   3.3 Targeting Specific Nodes
   3.4 Flags Reference
   3.5 Monitoring
   3.6 Risks & Mitigations

4. PHASE 2: BH-FILL (BuyHatke Price History)
   4.1 What It Does
   4.2 Commands — The Main Workhorse
   4.3 How --repeat Works (Auto-Batching)
   4.4 How --workers Distributes Work
   4.5 Targeting Specific Nodes
   4.6 Flags Reference
   4.7 Speed & Throughput
   4.8 Monitoring
   4.9 Risks & Mitigations

5. PHASE 3: PH-EXTEND (PriceHistory Deep History)
   5.1 What It Does
   5.2 Commands
   5.3 Flags Reference
   5.4 Monitoring
   5.5 Risks & Mitigations

6. PHASE 3B: CREATE-LIGHTWEIGHT (Product Records)
   6.1 What It Does
   6.2 Commands
   6.3 Flags Reference
   6.4 Monitoring
   6.5 Risks & Mitigations

7. FULL PIPELINE SEQUENCE (Copy-Paste Playbook)
   7.1 Option A: Automated (Celery Dispatch)
   7.2 Option B: Manual Per-Phase

8. CELERY TASK ROUTING & NODE TARGETING
   8.1 Default Routing (Any Worker Picks Up)
   8.2 Send Task to Specific Node
   8.3 Worker Hostname Patterns
   8.4 Inspecting Worker State

9. SETTINGS & ENVIRONMENT
   9.1 Environment Variables That Affect Pipeline
   9.2 Celery Concurrency Settings
   9.3 Rate Limiting

10. MONITORING & OBSERVABILITY
    10.1 Status Dashboard
    10.2 Flower Dashboard
    10.3 Worker Logs
    10.4 Database-Level Checks

11. FAILURE RECOVERY
    11.1 Stale Claims (Crashed Workers)
    11.2 Failed Products
    11.3 Stuck Tasks
    11.4 Worker Node Down
    11.5 Redis/DB Connection Lost

12. RISKS, GOTCHAS & THINGS TO NOTE

13. QUICK REFERENCE CARD
```

---

# 1. CLUSTER OVERVIEW

## 1.1 Node Topology

```
┌──────────────────────────────────────────────────────────────────┐
│  PRIMARY (Contabo VPS — 95.111.232.70)                          │
│  WireGuard: 10.8.0.1                                            │
│                                                                  │
│  Services: PostgreSQL, Redis, Meilisearch, Django Backend,       │
│            Celery Worker (default/scraping/scoring/alerts),      │
│            Celery Beat, Email Worker, Flower, Frontend           │
│                                                                  │
│  Celery hostname: primary@<hostname>                             │
│  Queues: default, scraping, scoring, alerts                      │
└────────────────────────┬─────────────────────────────────────────┘
                         │ WireGuard VPN (10.8.0.0/24)
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  whyd1 (OCI)    │ │  whyd2 (OCI)    │ │  Future nodes   │
│  10.8.0.3       │ │  10.8.0.4       │ │  10.8.0.5+      │
│  CELERY_WORKER  │ │  CELERY_WORKER  │ │                  │
│  _ID=oci-w1     │ │  _ID=oci-w2     │ │                  │
│                  │ │                  │ │                  │
│  Queue: scraping │ │  Queue: scraping │ │  Queue: scraping │
│  Concurrency: 2  │ │  Concurrency: 2  │ │                  │
│  RAM: 1GB        │ │  RAM: 1GB        │ │                  │
└─────────────────┘ └─────────────────┘ └─────────────────┘

⚠️  OCI 1GB workers: ONLY for BH-fill, PH-extend, curl_cffi enrichment.
    NEVER run discovery on 1GB nodes — it OOMs and crashes the instance.
    Run discovery ONLY on primary (2GB+ worker RAM).
```

## 1.2 How Workers Pick Up Tasks

All workers listen on the `scraping` queue via Redis. When you dispatch tasks:

1. Task lands in Redis `scraping` queue
2. **Any idle worker** picks it up (round-robin prefetch)
3. Worker claims a batch from PostgreSQL using `SELECT ... FOR UPDATE SKIP LOCKED`
4. No two workers ever process the same product

You do NOT need to specify which worker runs what. Celery auto-distributes.
But you CAN target specific nodes if needed (see Section 8).

## 1.3 SKIP LOCKED — Why There's No Overlap

```sql
-- Each worker runs this atomically:
SELECT id FROM pricing_backfillproduct
WHERE status = 'Discovered'
ORDER BY created_at
LIMIT 5000
FOR UPDATE SKIP LOCKED;

-- Worker 1 gets rows 1-5000
-- Worker 2's query SKIPs those locked rows, gets 5001-10000
-- Worker 3 gets 10001-15000
-- No duplicates. No overlap. Database-guaranteed.
```

This is why `--workers 4 --repeat` is safe. Each worker claims its own batch,
processes it, then claims the next available batch. Continues until nothing left.

---

# 2. PRE-FLIGHT CHECKLIST

Run these BEFORE starting any pipeline phase:

```bash
# ── 1. Check all workers are online ──────────────────────────────
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud inspect ping
# Expected: pong from primary@..., oci-w1@..., oci-w2@...

# ── 2. Check what queues each worker listens on ──────────────────
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud inspect active_queues
# All should show 'scraping' queue

# ── 3. Check WireGuard connectivity to each worker ───────────────
ping -c 2 10.8.0.3   # whyd1
ping -c 2 10.8.0.4   # whyd2

# ── 4. Check current pipeline status ─────────────────────────────
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices status

# ── 5. Check no tasks are currently running ───────────────────────
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud inspect active
# Should show empty or only beat tasks

# ── 6. Check Redis is accessible ─────────────────────────────────
docker compose -f docker-compose.yml exec redis redis-cli ping
# Expected: PONG

# ── 7. Check DB disk space ────────────────────────────────────────
docker exec whydud-postgres psql -U whydud -c \
  "SELECT pg_size_pretty(pg_database_size('whydud'));"
```

---

# 3. PHASE 1: DISCOVERY

## 3.1 What It Does

- Crawls PriceHistory.app sitemaps (343 available, ~49K products each)
- Parses HTML pages to extract: title, ASIN/FPID, marketplace URL, current price, image
- Creates `BackfillProduct` records in `Discovered` status
- **Idempotent:** Products upserted by ASIN — re-running same range is safe
- **Free:** No proxy bandwidth cost (hits public tracker pages)

## 3.2 Commands

### Option A: Dispatch to Celery Workers (Recommended)

```bash
# Dispatch 2 parallel discovery tasks (split sitemap ranges)
docker compose -f docker-compose.yml exec backend python -c "
from apps.pricing.tasks import run_phase1_discover

# Worker 1 gets sitemaps 1-5, Worker 2 gets 6-10
r1 = run_phase1_discover.delay(sitemap_start=6, sitemap_end=9, filter_electronics=False)
r2 = run_phase1_discover.delay(sitemap_start=10, sitemap_end=15, filter_electronics=False)

print(f'Task 1 (sitemaps 1-5):  {r1.id}')
print(f'Task 2 (sitemaps 6-10): {r2.id}')
"
```

### Option B: Management Command (Blocks Terminal)

```bash
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices discover \
    --start 1 --end 5 --delay 0.5
```

### Option C: Large-Scale Discovery (Many Sitemaps)

```bash
# Spread across all workers — 10 sitemaps each
docker compose -f docker-compose.yml exec backend python -c "
from apps.pricing.tasks import run_phase1_discover

ranges = [(1,10), (11,20), (21,30), (31,40)]
for start, end in ranges:
    r = run_phase1_discover.delay(
        sitemap_start=start, sitemap_end=end,
        filter_electronics=False
    )
    print(f'Sitemaps {start}-{end}: {r.id}')
"
```

## 3.3 Targeting Specific Nodes

Discovery tasks don't use SKIP LOCKED (they use sitemap ranges instead).
To send to a specific worker:

```bash
docker compose -f docker-compose.yml exec backend python -c "
from apps.pricing.tasks import run_phase1_discover

# Send ONLY to oci-w1 (whyd1)
r = run_phase1_discover.apply_async(
    kwargs={'sitemap_start': 1, 'sitemap_end': 5, 'filter_electronics': False},
    queue='scraping',
    routing_key='scraping',
    headers={'destination': 'oci-w1'}
)
print(f'Task ID: {r.id}')
"
```

Or use Celery's `-d` flag to target:

```bash
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud call apps.pricing.tasks.run_phase1_discover \
    --kwargs='{"sitemap_start": 1, "sitemap_end": 5}' \
    -d 'oci-w1@*'
```

## 3.4 Flags Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--start N` | 1 | First sitemap index |
| `--end N` | 5 | Last sitemap index (343 total available) |
| `--limit N` | None | Cap max products discovered |
| `--filter-electronics` | False | Only keep electronics/tech products |
| `--delay N` | 0.5 | Seconds between HTTP requests |

**Celery task kwargs:** `sitemap_start`, `sitemap_end`, `filter_electronics`, `max_products`

## 3.5 Monitoring

```bash
# Watch discovery progress (live updating)
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices status --watch

# Tail worker logs for discovery progress
docker compose -f docker-compose.yml logs -f celery-default --tail 50 \
  | grep -i "phase 1\|progress\|created\|parsed\|discover"

# Check task status by ID
docker compose -f docker-compose.yml exec backend python -c "
from celery.result import AsyncResult
r = AsyncResult('PASTE-TASK-ID-HERE')
print(f'State: {r.state}')
print(f'Result: {r.result}')
"
```

## 3.6 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| PriceHistory rate limits (HTTP 429) | Discovery slows/stops | Keep `--delay 0.5`+ per request. Run during IST midnight-6am |
| Sitemap structure changes | Parser fails | Check worker logs for parse errors before scaling up |
| OOM on 1GB workers | Worker crash | Discovery is memory-light, should be fine. If not, increase `--delay` |
| Duplicate runs | Wasted time, no data harm | Products upserted by ASIN — duplicates silently skipped |

---

# 4. PHASE 2: BH-FILL (BuyHatke Price History)

## 4.1 What It Does

- Fetches bulk price history from BuyHatke API for discovered products
- Each product gets 50-500 price data points spanning months/years
- Stores in `BackfillProduct.price_data` (JSONB) + injects to `price_snapshots`
- Status moves: `Discovered` → `bh_filling` (transient) → `BH Filled`
- **Uses SKIP LOCKED** — safe for parallel execution across all workers

## 4.2 Commands — The Main Workhorse

### Recommended: Parallel Workers with Auto-Repeat

```bash
# THIS IS THE COMMAND YOU WANT FOR 80K PRODUCTS
# 4 workers, each claims 5000-product batches, repeats until all 80K done
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices bh-fill \
    --celery --workers 4 --batch 5000 --repeat
```

**What happens:**
1. Dispatches 4 Celery tasks to the `scraping` queue
2. Workers (primary + oci-w1 + oci-w2) pick them up
3. Each task claims 5000 products via SKIP LOCKED
4. Processes the batch (async HTTP, ~300 products/min)
5. `--repeat` → claims next 5000, processes, claims next... until 0 remaining
6. All 4 tasks run in parallel, never overlapping

```
Worker 1: [batch 1-5000] → [batch 20001-25000] → [batch 40001-45000] → done
Worker 2: [batch 5001-10000] → [batch 25001-30000] → [batch 45001-50000] → done
Worker 3: [batch 10001-15000] → [batch 30001-35000] → [batch 50001-55000] → done
Worker 4: [batch 15001-20000] → [batch 35001-40000] → [batch 55001-60000] → done
... each claims the NEXT available batch, NOT pre-assigned ranges
```

### Alternative: Single In-Process Run

```bash
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices bh-fill --batch 5000
```

### Alternative: Direct Celery Task Call

```bash
docker compose -f docker-compose.yml exec backend python -c "
from apps.pricing.tasks import run_phase2_buyhatke

# Single task with repeat
r = run_phase2_buyhatke.delay(batch_size=5000, repeat=True)
print(f'Task ID: {r.id}')
"
```

### Alternative: Multiple Tasks Manually

```bash
docker compose -f docker-compose.yml exec backend python -c "
from apps.pricing.tasks import run_phase2_buyhatke

for i in range(4):
    r = run_phase2_buyhatke.delay(batch_size=5000, repeat=True)
    print(f'Worker {i+1}: {r.id}')
"
```

## 4.3 How --repeat Works (Auto-Batching)

```
                 ┌──────────────────────┐
                 │  Task starts          │
                 └──────────┬───────────┘
                            ▼
                 ┌──────────────────────┐
            ┌───→│  Claim batch (5000)   │
            │    │  via SKIP LOCKED      │
            │    └──────────┬───────────┘
            │               ▼
            │    ┌──────────────────────┐
            │    │  batch.count == 0?   │──yes──→ DONE (return stats)
            │    └──────────┬───────────┘
            │               │ no
            │               ▼
            │    ┌──────────────────────┐
            │    │  Process batch       │
            │    │  (async HTTP calls)  │
            │    └──────────┬───────────┘
            │               ▼
            │    ┌──────────────────────┐
            └────│  --repeat? loop back │
                 └──────────────────────┘
```

Without `--repeat`, each task processes ONE batch and exits.
With `--repeat`, each task loops until the queue is empty.

**80K products / 5000 batch = 16 batches**
With 4 workers: each worker does ~4 batches = ~20K products each.

## 4.4 How --workers Distributes Work

```bash
python manage.py backfill_prices bh-fill --celery --workers 4 --batch 5000 --repeat
```

The management command dispatches 4 independent Celery tasks:

```python
# Internally does this:
for i in range(4):
    run_phase2_buyhatke.apply_async(kwargs={
        'batch_size': 5000,
        'repeat': True,
        'delay': delay_override,
        'marketplace_slug': marketplace_filter,
    })
```

Celery distributes these 4 tasks across available workers:
- If you have 3 workers (primary + 2 OCI), one worker gets 2 tasks
- Each task runs in its own process/thread (depending on concurrency)
- All 4 tasks compete for batches via SKIP LOCKED — no coordination needed

**Pro tip:** Set `--workers` to your total Celery concurrency across all nodes:
- Primary: concurrency=4 → can run 4 tasks
- oci-w1: concurrency=2 → can run 2 tasks
- oci-w2: concurrency=2 → can run 2 tasks
- Total capacity: 8 → set `--workers 6` (leave 2 slots for beat tasks)

## 4.5 Targeting Specific Nodes

### Send bh-fill ONLY to a specific worker

```bash
docker compose -f docker-compose.yml exec backend python -c "
from apps.pricing.tasks import run_phase2_buyhatke
from kombu import Queue

# Target oci-w1 specifically
r = run_phase2_buyhatke.apply_async(
    kwargs={'batch_size': 5000, 'repeat': True},
    queue='scraping',
)
print(f'Task ID: {r.id}')
print('Note: Task goes to scraping queue, any worker on that queue can pick it up.')
print('To truly target one worker, use Celery routing or worker-specific queues.')
"
```

### Worker-Specific Queue (Advanced)

To guarantee a task runs on a specific node, create per-worker queues:

```bash
# On the worker node, start celery with an extra queue:
celery -A whydud worker --queues=scraping,scraping-oci-w1 --hostname=oci-w1@%h

# Then dispatch to that specific queue:
run_phase2_buyhatke.apply_async(
    kwargs={'batch_size': 5000, 'repeat': True},
    queue='scraping-oci-w1'
)
```

**But you usually don't need this.** SKIP LOCKED means any worker can safely
pick up any task. The only reason to target a specific node is for debugging
or if one node has special capabilities (e.g., Playwright installed).

## 4.6 Flags Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--batch N` | 5000 | Products per batch claim |
| `--celery` | False | Dispatch to Celery workers (vs run in-process) |
| `--workers N` | 2 | Number of parallel Celery tasks to dispatch |
| `--repeat` | False | Keep claiming batches until queue empty |
| `--marketplace` | None | Filter by marketplace slug (e.g., `amazon-in`) |
| `--delay N` | None | Override seconds between BuyHatke API requests |

**Celery task kwargs:** `batch_size`, `marketplace_slug`, `delay`, `repeat`

## 4.7 Speed & Throughput

| Config | Rate | 80K Products |
|--------|------|--------------|
| 1 worker, no repeat | ~300/min | ~4.5 hours (only does 1 batch of 5000) |
| 1 worker, repeat | ~300/min | ~4.5 hours |
| 4 workers, repeat | ~1,200/min | ~67 minutes |
| 6 workers, repeat | ~1,800/min | ~45 minutes |

**Concurrency within each worker:** 5 async HTTP requests (default), 1s delay between.
Configured via `BACKFILL_BH_CONCURRENCY` and `BACKFILL_BH_DELAY` env vars.

**Slow down if needed:**

```bash
# Set via environment (affects all workers)
BACKFILL_BH_DELAY=1.5         # 1.5s between requests (default: 1.0)
BACKFILL_BH_CONCURRENCY=2     # 2 concurrent (default: 5)

# Or via command flag
python manage.py backfill_prices bh-fill --celery --workers 4 --repeat --delay 1.5
```

## 4.8 Monitoring

```bash
# ── Pipeline status (counts by status) ────────────────────────────
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices status

# ── Live updating (every 30s) ─────────────────────────────────────
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices status --watch

# ── Worker logs (BuyHatke progress) ───────────────────────────────
docker compose -f docker-compose.yml logs -f celery-default --tail 20

# ── From a remote worker ──────────────────────────────────────────
# SSH into whyd1:
docker logs celery-enrichment -f --tail 20

# ── Flower dashboard (all workers) ────────────────────────────────
# Open http://<PRIMARY-IP>:5555/
# Tasks tab → filter by 'run_phase2_buyhatke'

# ── Check remaining work ──────────────────────────────────────────
docker exec whydud-postgres psql -U whydud -c "
  SELECT status, COUNT(*) FROM pricing_backfillproduct
  GROUP BY status ORDER BY count DESC;
"

# ── Check active tasks ────────────────────────────────────────────
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud inspect active

# ── Check specific task result ────────────────────────────────────
docker compose -f docker-compose.yml exec backend python -c "
from celery.result import AsyncResult
r = AsyncResult('PASTE-TASK-ID')
print(f'State: {r.state}, Info: {r.info}')
"
```

## 4.9 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| BuyHatke rate limit (429) | Worker retries, slows down | Built-in exponential backoff. Increase `--delay` if persistent |
| Worker crash mid-batch | Products stuck in `bh_filling` | `retry-failed --history` resets stale claims after 1 hour |
| OOM on 1GB worker | Container killed | Reduce `--batch` to 2000. BH-fill is HTTP-only, low memory |
| Network timeout to BuyHatke | Individual product fails | Built-in retry (3 attempts). Failed products marked, retryable |
| Too many workers overwhelm BH | API ban | Start with 2-3 workers. Monitor 429 rate in logs |
| Price data in wrong unit | Bad price charts | BuyHatke returns paisa. Injection divides by 100 for rupees |

---

# 5. PHASE 3: PH-EXTEND (PriceHistory Deep History)

## 5.1 What It Does

- Extends price history using PriceHistory.app API (deeper than BuyHatke)
- Targets products already `BH Filled` — adds more data points
- Status moves: `BH Filled` → `ph_extending` (transient) → `PH Extended`
- Same SKIP LOCKED pattern as Phase 2

## 5.2 Commands

### Recommended: Parallel with Repeat

```bash
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices ph-extend \
    --celery --workers 4 --limit 5000 --repeat
```

### Direct Celery Dispatch

```bash
docker compose -f docker-compose.yml exec backend python -c "
from apps.pricing.tasks import run_phase3_extend

for i in range(4):
    r = run_phase3_extend.delay(limit=5000, repeat=True)
    print(f'Worker {i+1}: {r.id}')
"
```

### In-Process (Blocking)

```bash
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices ph-extend --limit 5000 --repeat
```

## 5.3 Flags Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--limit N` | 5000 | Products per batch claim |
| `--celery` | False | Dispatch to Celery workers |
| `--workers N` | 2 | Number of parallel Celery tasks |
| `--repeat` | False | Keep claiming batches until empty |
| `--marketplace` | None | Filter by marketplace slug |
| `--delay N` | None | Override request delay |

**Celery task kwargs:** `limit`, `marketplace_slug`, `delay`, `repeat`

## 5.4 Monitoring

Same as Phase 2 — use `backfill_prices status`, Flower, worker logs.
Look for `PH Extended` count increasing in status output.

## 5.5 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| PH token expiration | API calls fail | Task handles token refresh. If persistent, check logs |
| PH rate limiting | Slower throughput | Keep `--delay 0.5`+. Run IST midnight-6am |
| Duplicate history points | Inflated price charts | Injection uses `ON CONFLICT DO NOTHING` on (time, listing_id) |
| PH API changes | Parser breaks | Monitor error rate in first 100 products before scaling |

---

# 6. PHASE 3B: CREATE-LIGHTWEIGHT (Product Records)

## 6.1 What It Does

- Creates real `Product` + `ProductListing` records from tracker data
- **No marketplace scraping required** — uses data from Phases 1-3
- Injects price history into `price_snapshots` hypertable
- Products become **immediately visible on the site** with price charts
- Marks `Product.is_lightweight = True` (missing: images, specs, reviews)

## 6.2 Commands

```bash
# Create lightweight records in batches of 2000
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices create-lightweight --batch 2000
```

**Important:** This command runs in a loop internally. It keeps creating records
until no more candidates remain. You don't need `--repeat`.

Run it again after each Phase 2/3 round to create records for newly filled products.

## 6.3 Flags Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--batch N` | 1000 | Products per iteration |

**Note:** No `--celery` flag for this command. It runs in-process.
Keep `--batch` <= 5000 (CLAUDE.md safety rule).

## 6.4 Monitoring

```bash
# Check how many lightweight products exist
docker compose -f docker-compose.yml exec backend python -c "
from apps.products.models import Product
print(f'Total products: {Product.objects.count()}')
print(f'Lightweight: {Product.objects.filter(is_lightweight=True).count()}')
print(f'Full: {Product.objects.filter(is_lightweight=False).count()}')
"

# Price snapshots injected
docker exec whydud-postgres psql -U whydud -c "
  SELECT source, COUNT(*) FROM price_snapshots GROUP BY source ORDER BY count DESC;
"
```

## 6.5 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Batch > 5000 | Memory spike | Keep <= 5000 per CLAUDE.md safety rules |
| Duplicate products | Wasted DB space | `ProductListing` has unique constraint on (marketplace, external_id) |
| Missing marketplace | Products not created | Only creates for known marketplaces (amazon-in, flipkart, etc.) |
| Price unit mismatch | Wrong prices | Tracker data in paisa, divided by 100 for `price_snapshots` |
| Meilisearch out of sync | Products not searchable | Run `sync_meilisearch` after creating lightweight records |

---

# 7. FULL PIPELINE SEQUENCE (Copy-Paste Playbook)

## 7.1 Option A: Automated (Celery Dispatch — Recommended)

Run these commands **sequentially**. Wait for each phase to complete before starting the next.

```bash
# ═══════════════════════════════════════════════════════════════
# STEP 0: Pre-flight checks
# ═══════════════════════════════════════════════════════════════
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud inspect ping

docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices status


# ═══════════════════════════════════════════════════════════════
# STEP 1: DISCOVERY (if needed — skip if products already discovered)
# ~45 min per sitemap of ~49K products
# ═══════════════════════════════════════════════════════════════
docker compose -f docker-compose.yml exec backend python -c "
from apps.pricing.tasks import run_phase1_discover
r1 = run_phase1_discover.delay(sitemap_start=1, sitemap_end=2, filter_electronics=False)
r2 = run_phase1_discover.delay(sitemap_start=3, sitemap_end=4, filter_electronics=False)
print(f'Task 1: {r1.id}')
print(f'Task 2: {r2.id}')
"

# Monitor: watch status, wait for Discovered count to stabilize
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices status --watch


# ═══════════════════════════════════════════════════════════════
# STEP 2: BH-FILL (BuyHatke price history)
# 80K products ÷ 1200/min = ~67 minutes with 4 workers
# ═══════════════════════════════════════════════════════════════
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices bh-fill \
    --celery --workers 4 --batch 5000 --repeat

# Monitor progress
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices status --watch

# Wait until "BH Filled" count matches total Discovered count


# ═══════════════════════════════════════════════════════════════
# STEP 3: PH-EXTEND (PriceHistory deep history)
# Optional but recommended — adds more data points
# ═══════════════════════════════════════════════════════════════
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices ph-extend \
    --celery --workers 4 --limit 5000 --repeat

# Monitor progress
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices status --watch

# Wait until "PH Extended" count stabilizes


# ═══════════════════════════════════════════════════════════════
# STEP 4: CREATE LIGHTWEIGHT RECORDS
# Converts BackfillProduct → real Product + ProductListing
# ~1-2 min per batch of 2000
# ═══════════════════════════════════════════════════════════════
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices create-lightweight --batch 2000

# Verify
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices status


# ═══════════════════════════════════════════════════════════════
# STEP 5: ASSIGN PRIORITIES (for future enrichment)
# ═══════════════════════════════════════════════════════════════
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices assign-priorities

# Verify priority distribution
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices status


# ═══════════════════════════════════════════════════════════════
# STEP 6: DATA VERIFICATION
# ═══════════════════════════════════════════════════════════════
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices verify-data


# ═══════════════════════════════════════════════════════════════
# STEP 7: REFRESH AGGREGATE (TimescaleDB)
# ═══════════════════════════════════════════════════════════════
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices refresh-aggregate


# ═══════════════════════════════════════════════════════════════
# STEP 8: SYNC SEARCH INDEX
# ═══════════════════════════════════════════════════════════════
docker compose -f docker-compose.yml exec backend \
  python manage.py sync_meilisearch
```

## 7.2 Option B: Manual Per-Phase (More Control)

```bash
# Phase 2 — Run 1 batch at a time, check after each
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices bh-fill --batch 5000

# Check progress
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices status

# Run another batch
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices bh-fill --batch 5000

# ... repeat until Discovered count reaches 0
```

---

# 8. CELERY TASK ROUTING & NODE TARGETING

## 8.1 Default Routing (Any Worker Picks Up)

```bash
# These go to the 'scraping' queue — ANY worker can pick up
run_phase2_buyhatke.delay(batch_size=5000, repeat=True)
```

All workers listen on `scraping`. Celery's prefetch mechanism distributes tasks.

## 8.2 Send Task to Specific Node

### Method 1: Worker-Specific Queue (Recommended for Production)

On the target worker, start Celery with an extra queue:

```yaml
# docker-compose.worker.yml — add worker-specific queue
command: >
  celery -A whydud worker
    --loglevel=info
    --concurrency=2
    --queues=scraping,worker-oci-w1
    --hostname=oci-w1@%h
```

Then dispatch to that queue:

```python
run_phase2_buyhatke.apply_async(
    kwargs={'batch_size': 5000, 'repeat': True},
    queue='worker-oci-w1'
)
```

### Method 2: Use `celery call` CLI with `-d` (Destination)

```bash
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud call apps.pricing.tasks.run_phase2_buyhatke \
    --kwargs='{"batch_size": 5000, "repeat": true}'
```

**Note:** `-d` flag for targeting in `celery call` is not always reliable.
Worker-specific queues (Method 1) are more dependable.

### Method 3: Direct Python with `apply_async`

```python
# This dispatches to the default scraping queue
# Any worker can pick it up
run_phase2_buyhatke.apply_async(
    kwargs={'batch_size': 5000, 'repeat': True},
    queue='scraping',
)
```

## 8.3 Worker Hostname Patterns

| Node | Celery Hostname | CELERY_WORKER_ID |
|------|----------------|-------------------|
| Primary | `primary@<machine-hostname>` | (not set — uses default) |
| whyd1 (OCI) | `oci-w1@<machine-hostname>` | `oci-w1` |
| whyd2 (OCI) | `oci-w2@<machine-hostname>` | `oci-w2` |

## 8.4 Inspecting Worker State

```bash
# All workers — ping
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud inspect ping

# All workers — active tasks
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud inspect active

# Specific worker — active tasks
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud inspect active --destination='oci-w1@*'

# All workers — registered tasks
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud inspect registered

# All workers — queue info
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud inspect active_queues

# All workers — stats (CPU, memory, uptime)
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud inspect stats

# Redis queue depth (how many tasks waiting)
docker compose -f docker-compose.yml exec redis \
  redis-cli LLEN scraping
```

---

# 9. SETTINGS & ENVIRONMENT

## 9.1 Environment Variables That Affect Pipeline

| Variable | Default | Where | Effect |
|----------|---------|-------|--------|
| `BACKFILL_BH_DELAY` | `1.0` | All workers | Seconds between BuyHatke API calls |
| `BACKFILL_BH_CONCURRENCY` | `5` | All workers | Concurrent async HTTP requests per task |
| `BACKFILL_PH_DELAY` | `0.5` | All workers | Seconds between PriceHistory API calls |
| `CELERY_WORKER_ID` | `remote-w1` | Worker nodes | Unique ID for proxy session routing |
| `SCRAPING_PROXY_LIST` | None | Worker nodes | Proxy URL (for enrichment, not BH/PH) |
| `SCRAPING_PROXY_TYPE` | `rotating` | Worker nodes | Proxy rotation type |

## 9.2 Celery Concurrency Settings

| Node | Concurrency | Queues | RAM |
|------|-------------|--------|-----|
| Primary worker | 4 | default, scraping, scoring, alerts | 2GB |
| Primary email | 2 | email | 512MB |
| OCI worker (1GB + 8GB swap) | 1 | scraping | 1GB + 8GB swap |

**Change concurrency** in docker-compose:

```yaml
# docker-compose.worker.yml
command: >
  celery -A whydud worker
    --concurrency=1          # ← 1 for 1GB OCI nodes
    --queues=scraping
```

**Warning:** On 1GB OCI instances with swap, use concurrency=1.
Higher concurrency causes excessive swapping and eventual OOM kills.

## 9.2b OCI Worker — Swap Setup (REQUIRED)

OCI Always Free instances have only 1GB RAM. Without swap, Celery + Docker
overhead will OOM-kill the worker and drop SSH. **Add 8GB swap on first boot:**

```bash
# Check available disk (OCI boot volume = 47GB, 8GB swap is fine)
df -h /

# Create and enable 8GB swap
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Persist across reboots
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Tune: only swap when RAM is nearly full
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# Verify
free -h
# Expected: Swap: 8.0G total
```

**After adding swap, reduce concurrency to 1 and rebuild:**
```bash
cd /opt/whydud/whydud/docker
docker compose -f docker-compose.worker.yml --env-file /opt/whydud/.env.worker up -d --build
```

## 9.3 Rate Limiting

The pipeline has multiple rate-limiting layers:

1. **Per-request delay:** `asyncio.sleep(delay)` between HTTP calls
2. **Concurrency semaphore:** Limits concurrent outbound connections per task
3. **Celery task rate limit:** `rate_limit='30/m'` on enrichment tasks
4. **Celery Beat scheduling:** Tasks dispatched at fixed intervals

For BH-fill and PH-extend, only layers 1 and 2 apply:
- Default: 5 concurrent requests, 1.0s delay = ~300 products/min per task
- Conservative: 2 concurrent, 1.5s delay = ~80 products/min per task
- Aggressive: 10 concurrent, 0.3s delay = ~2000 products/min per task (risky)

---

# 10. MONITORING & OBSERVABILITY

## 10.1 Status Dashboard

```bash
# One-shot status
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices status

# Live-updating (refreshes every 30s)
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices status --watch

# Machine-readable JSON
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices status --json
```

**Example output:**

```
═══════════════════════════════════════════════════
 BACKFILL PIPELINE STATUS
═══════════════════════════════════════════════════

BY STATUS:
  Discovered          80,000
  BH Filling           5,000  (4 workers active)
  BH Filled           12,350
  PH Extended              0
  Done                   153
  Failed                 904

BY SCRAPE STATUS:
  pending             92,203
  enriching               12
  scraped                153
  failed                  30

PRICE SNAPSHOTS:
  buyhatke            34,000
  pricehistory_app    34,000
  scraper              4,570
```

## 10.2 Flower Dashboard

Open `http://<PRIMARY-IP>:5555/` (credentials from `FLOWER_BASIC_AUTH`).

| Tab | What to Check |
|-----|---------------|
| **Workers** | All nodes online, queues correct, no high load |
| **Tasks** | Filter by `run_phase2_buyhatke` — check STARTED/SUCCESS/FAILURE |
| **Monitor** | Task throughput graph — should show steady processing |
| **Broker** | Redis queue depth — should be decreasing during pipeline run |

## 10.3 Worker Logs

```bash
# Primary worker logs
docker compose -f docker-compose.yml logs -f celery-default --tail 50

# Remote worker logs (SSH into whyd1 first)
docker logs celery-enrichment -f --tail 50

# Filter for specific phase
docker compose -f docker-compose.yml logs celery-default 2>&1 \
  | grep -i "phase 2\|buyhatke\|bh_fill\|round\|batch"
```

## 10.4 Database-Level Checks

```bash
# Products by status
docker exec whydud-postgres psql -U whydud -c "
  SELECT status, COUNT(*) as cnt
  FROM pricing_backfillproduct
  GROUP BY status ORDER BY cnt DESC;
"

# Actively being processed (transient states)
docker exec whydud-postgres psql -U whydud -c "
  SELECT status, COUNT(*)
  FROM pricing_backfillproduct
  WHERE status IN ('bh_filling', 'ph_extending')
  GROUP BY status;
"

# Price snapshots growth
docker exec whydud-postgres psql -U whydud -c "
  SELECT source, COUNT(*), MAX(time) as latest
  FROM price_snapshots
  GROUP BY source ORDER BY count DESC;
"

# DB size
docker exec whydud-postgres psql -U whydud -c "
  SELECT pg_size_pretty(pg_database_size('whydud'));
"

# Table sizes
docker exec whydud-postgres psql -U whydud -c "
  SELECT relname, pg_size_pretty(pg_total_relation_size(oid))
  FROM pg_class WHERE relname IN ('pricing_backfillproduct', 'price_snapshots',
    'products_product', 'products_productlisting')
  ORDER BY pg_total_relation_size(oid) DESC;
"
```

---

# 11. FAILURE RECOVERY

## 11.1 Stale Claims (Crashed Workers)

If a worker crashes mid-batch, products get stuck in `bh_filling` or `ph_extending`.

```bash
# Check for stale claims
docker exec whydud-postgres psql -U whydud -c "
  SELECT status, COUNT(*)
  FROM pricing_backfillproduct
  WHERE status IN ('bh_filling', 'ph_extending')
  GROUP BY status;
"

# Reset stale claims (products stuck for >1 hour)
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices retry-failed --history

# Preview first (dry run)
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices retry-failed --history --dry-run
```

**Automatic recovery:** The `cleanup_stale_enrichments` Celery Beat task
runs hourly and resets stuck enrichments. For BH/PH phases, manual recovery
via `retry-failed --history` is needed.

## 11.2 Failed Products

```bash
# Check failure count
docker exec whydud-postgres psql -U whydud -c "
  SELECT COUNT(*) FROM pricing_backfillproduct WHERE status = 'Failed';
"

# See error messages
docker exec whydud-postgres psql -U whydud -c "
  SELECT error_message, COUNT(*)
  FROM pricing_backfillproduct
  WHERE status = 'Failed'
  GROUP BY error_message
  ORDER BY count DESC LIMIT 10;
"

# Reset all failed for retry
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices reset-failed

# Or use retry-failed with specific flags
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices retry-failed --history   # Phase 2/3 failures
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices retry-failed --scrape    # Phase 4 failures
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices retry-failed --reviews   # Phase 5 failures
```

## 11.3 Stuck Tasks

```bash
# Check if tasks are actually running
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud inspect active

# If a task appears stuck (running for hours), revoke it
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud control revoke TASK-ID-HERE --terminate

# Then reset the stale claims it left behind
docker compose -f docker-compose.yml exec backend \
  python manage.py backfill_prices retry-failed --history
```

## 11.4 Worker Node Down

```bash
# From primary — check which workers are up
docker compose -f docker-compose.yml exec celery-default \
  celery -A whydud inspect ping

# SSH into the worker node
ssh root@<worker-ip>

# Check WireGuard
ping 10.8.0.1

# If WireGuard down
systemctl restart wg-quick@wg0

# Check Docker container
docker ps

# If container down
cd /opt/whydud/whydud/docker
docker compose -f docker-compose.worker.yml \
  --env-file /opt/whydud/.env.worker up -d

# If code is stale
/opt/scripts/update-worker.sh

# Full restart
systemctl restart whydud-worker.service
```

## 11.5 Redis/DB Connection Lost

```bash
# Worker will auto-reconnect on next task. If persistent:

# Check Redis from primary
docker compose -f docker-compose.yml exec redis redis-cli ping

# Check Redis from worker (via WireGuard)
redis-cli -h 10.8.0.1 -a <password> ping

# Check PostgreSQL
docker exec whydud-postgres psql -U whydud -c "SELECT 1;"

# If Redis OOM
docker compose -f docker-compose.yml exec redis redis-cli info memory
# If used_memory > maxmemory: flush task results
docker compose -f docker-compose.yml exec redis redis-cli FLUSHDB
# WARNING: This clears all task results. Only do if Redis is full.

# Restart the problematic service
docker compose -f docker-compose.yml restart redis
docker compose -f docker-compose.yml restart postgres
```

---

# 12. RISKS, GOTCHAS & THINGS TO NOTE

## Critical Safety Rules

1. **Price units:** Tracker data is in **paisa** (6499900 = Rs.64,999). `price_snapshots` stores **rupees** (Decimal 64999.00). The injection code divides by 100.

2. **Never `--batch > 5000`** for `create-lightweight` without confirmation.

3. **Never `--concurrency > 30`** for async discovery.

4. **Always check status** before and after any pipeline operation.

5. **Run during IST midnight-6am** for best success rates (fewer bot challenges).

## Common Gotchas

| Gotcha | Symptom | Fix |
|--------|---------|-----|
| Worker doesn't have latest code | `NotRegistered` error | SSH → `/opt/scripts/update-worker.sh` |
| Worker listening on wrong queue | Tasks stay PENDING | Check `inspect active_queues` |
| `time.sleep()` in async code | Event loop blocked, very slow | Must use `asyncio.sleep()` |
| Django ORM in async context | `SynchronousOnlyOperation` | Wrap with `sync_to_async()` |
| WireGuard subnet conflicts (OCI) | Can't reach primary from worker | WG uses 10.8.0.0/24, OCI VCN uses 10.0.0.0/24 |
| Flower shows task SUCCESS immediately | `run_full_backfill_pipeline` is just an orchestrator | Check the chained sub-tasks |
| Redis full | Tasks not dispatching | `FLUSHDB` or increase `maxmemory` |
| OCI iptables drops WG traffic | Worker can't connect | Run the OCI iptables fix in cloud-init |

## Advantages of This Architecture

1. **Zero overlap guaranteed** — SKIP LOCKED is a PostgreSQL primitive, not application logic
2. **Crash-safe** — Worker crash leaves products in transient state, recoverable via `retry-failed`
3. **Auto-scaling** — Add more workers, they auto-join via Redis queue
4. **Cost-efficient** — OCI Always Free (1GB ARM instances) = $0/month per worker
5. **Idempotent** — Re-running any phase is safe (duplicates skipped)
6. **Observable** — Flower, status command, worker logs, Discord notifications
7. **Resumable** — `--repeat` picks up where crashed workers left off

## Performance Expectations

| Metric | Value |
|--------|-------|
| Discovery speed | ~49K products per sitemap (~2 hours) |
| BH-fill speed (per worker) | ~300 products/min |
| BH-fill speed (4 workers) | ~1,200 products/min |
| PH-extend speed (per worker) | ~200 products/min |
| Lightweight creation | ~2000 products/min |
| Enrichment P1 (Playwright) | ~2 products/min |
| Enrichment P2-P3 (curl_cffi) | ~30 products/min |
| 80K BH-fill with 4 workers | ~67 minutes |
| 80K PH-extend with 4 workers | ~100 minutes |

---

# 13. QUICK REFERENCE CARD

```
╔══════════════════════════════════════════════════════════════════╗
║  WHYDUD PIPELINE — QUICK REFERENCE                             ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  STATUS:                                                         ║
║    backfill_prices status                                        ║
║    backfill_prices status --watch                                ║
║                                                                  ║
║  DISCOVERY:                                                      ║
║    backfill_prices discover --start 1 --end 10                   ║
║                                                                  ║
║  BH-FILL (the big one):                                         ║
║    backfill_prices bh-fill --celery --workers 4                  ║
║      --batch 5000 --repeat                                       ║
║                                                                  ║
║  PH-EXTEND:                                                      ║
║    backfill_prices ph-extend --celery --workers 4                ║
║      --limit 5000 --repeat                                       ║
║                                                                  ║
║  LIGHTWEIGHT RECORDS:                                            ║
║    backfill_prices create-lightweight --batch 2000               ║
║                                                                  ║
║  PRIORITIES:                                                      ║
║    backfill_prices assign-priorities                              ║
║                                                                  ║
║  VERIFY:                                                          ║
║    backfill_prices verify-data                                    ║
║                                                                  ║
║  RECOVERY:                                                        ║
║    backfill_prices retry-failed --history                        ║
║    backfill_prices retry-failed --scrape                         ║
║    backfill_prices reset-failed                                  ║
║                                                                  ║
║  WORKERS:                                                         ║
║    celery -A whydud inspect ping                                 ║
║    celery -A whydud inspect active                               ║
║    celery -A whydud inspect active_queues                        ║
║                                                                  ║
║  WORKER NODE UPDATE:                                              ║
║    ssh root@<ip> /opt/scripts/update-worker.sh                   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

All commands above are prefixed with:
  docker compose -f docker-compose.yml exec backend python manage.py

Except celery inspect commands which use:
  docker compose -f docker-compose.yml exec celery-default
```

---

## APPENDIX A: Worker Node Setup (New Node Checklist)

1. Generate WireGuard keys: `wg genkey | tee private.key | wg pubkey > public.key`
2. Customize `cloud-init-worker.yml` (10 values — see comments in file)
3. On PRIMARY: Add worker's public key to `/etc/wireguard/wg0.conf`
4. On PRIMARY: `sudo wg-quick down wg0 && sudo wg-quick up wg0`
5. On PRIMARY: `ufw allow from 10.8.0.X to any port 6379`
6. On PRIMARY: `ufw allow from 10.8.0.X to any port 5432`
7. Launch OCI instance with cloud-init
8. Wait ~5 min for provisioning
9. Verify: `ping 10.8.0.X` from primary
10. Verify: `celery -A whydud inspect ping` shows new worker

## APPENDIX B: Docker Compose Reference

| File | Location | Nodes | Services |
|------|----------|-------|----------|
| `docker-compose.yml` | `docker/` | Primary | All 10 services |
| `docker-compose.worker.yml` | `docker/` | Remote workers | `celery-enrichment` only |
| `docker-compose.dev.yml` | `docker/` | Local dev | PostgreSQL, Redis, Meilisearch, Flower |

## APPENDIX C: Celery Queue Reference

| Queue | Workers | Tasks |
|-------|---------|-------|
| `default` | Primary | Cleanup, aggregation, general |
| `scraping` | Primary + All workers | Discovery, BH-fill, PH-extend, enrichment |
| `scoring` | Primary | DudScore, fake review detection |
| `alerts` | Primary | Price alerts |
| `email` | Primary (email worker) | Email processing |
