# Whydud Scraping System — Complete Technical Reference

> **Audience:** Any developer working on or debugging the scraping subsystem.
> **Last updated:** 2026-03-04

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [File Structure](#2-file-structure)
3. [How a Spider Run Works (End-to-End)](#3-how-a-spider-run-works-end-to-end)
4. [Infrastructure Components](#4-infrastructure-components)
   - [BaseWhydudSpider](#basewhydudspider)
   - [Middlewares](#middlewares)
   - [Pipelines](#pipelines)
   - [Runner (Subprocess Launcher)](#runner)
   - [Celery Tasks](#celery-tasks)
   - [Scrapy Settings](#scrapy-settings)
   - [ScraperJob Model](#scraperjob-model)
5. [All 15 Spiders — Detailed Reference](#5-all-15-spiders)
6. [Anti-Bot Bypass Strategies](#6-anti-bot-bypass-strategies)
7. [Proxy System](#7-proxy-system)
8. [Price Handling](#8-price-handling)
9. [Product Matching & Dedup](#9-product-matching--dedup)
10. [How to Use](#10-how-to-use)
11. [Celery Beat Schedule](#11-celery-beat-schedule)
12. [Known Bottlenecks & Issues](#12-known-bottlenecks--issues)
13. [Future Updates & Roadmap](#13-future-updates--roadmap)
14. [Dependencies](#14-dependencies)

---

## 1. Architecture Overview

The scraping system collects product data from **13 Indian marketplaces** (+ 2 review spiders) using **Scrapy** as the crawling framework, with **Playwright** for JavaScript-heavy sites and **curl_cffi** / **camoufox** for TLS fingerprint impersonation.

```
Celery Beat (scheduler)
    │
    ▼
Celery Task (run_marketplace_spider)
    │
    ▼
Subprocess (python -m apps.scraping.runner <spider>)
    │
    ▼
Scrapy CrawlerProcess
    ├── Spider (discovery + extraction logic)
    ├── Downloader Middlewares
    │   ├── BackoffRetryMiddleware (exponential backoff)
    │   └── PlaywrightProxyMiddleware (proxy assignment)
    ├── Download Handlers
    │   ├── scrapy-playwright (Chromium for JS-rendered pages)
    │   └── curl_cffi / camoufox (TLS impersonation middlewares)
    └── Item Pipelines
        ├── ValidationPipeline (drop items missing required fields)
        ├── NormalizationPipeline (clean titles, specs, images)
        ├── ProductPipeline (match/create Product, Listing, PriceSnapshot)
        ├── ReviewPersistencePipeline (persist reviews to DB)
        ├── MeilisearchIndexPipeline (batch search index sync)
        └── SpiderStatsUpdatePipeline (update ScraperJob stats)
```

### Key Design Decisions

- **Subprocess isolation:** Scrapy runs in a subprocess (not inside the Celery worker) to avoid Twisted reactor restart issues.
- **All prices in paisa:** ₹24,999 → `2499900` (integer). Display layer converts to rupees. Never use floats.
- **Two-phase crawling:** Most spiders first scrape listing pages (fast, minimal data) then detail pages (slow, rich data).
- **No scraping in request cycle:** All scraping is background Celery tasks. User-facing APIs never block on scrapes.

---

## 2. File Structure

```
apps/scraping/
├── spiders/
│   ├── base_spider.py              # BaseWhydudSpider (UA rotation, headers, stealth)
│   ├── amazon_spider.py            # Amazon.in products (HTTP listing → Playwright detail)
│   ├── flipkart_spider.py          # Flipkart (Playwright listing → HTTP+JSON-LD detail)
│   ├── amazon_review_spider.py     # Amazon reviews (Playwright)
│   ├── flipkart_review_spider.py   # Flipkart reviews (Playwright + custom JS)
│   ├── tatacliq_spider.py          # Tata CLiQ (Playwright + XHR interception + DataImpulse proxy)
│   ├── croma_spider.py             # Croma (HTTP + curl_cffi Chrome TLS)
│   ├── meesho_spider.py            # Meesho (camoufox anti-detection Firefox)
│   ├── jiomart_spider.py           # JioMart (sitemap discovery + curl_cffi)
│   ├── nykaa_spider.py             # Nykaa (HTTP + curl_cffi Chrome/120)
│   ├── snapdeal_spider.py          # Snapdeal (plain HTTP, microdata)
│   ├── myntra_spider.py            # Myntra (Playwright, __myx state)
│   ├── ajio_spider.py              # AJIO (Playwright, __PRELOADED_STATE__)
│   ├── reliance_digital_spider.py  # Reliance Digital (HTTP JSON API)
│   ├── vijay_sales_spider.py       # Vijay Sales (Unbxd API + Magento GraphQL)
│   └── firstcry_spider.py          # FirstCry (HTTP + curl_cffi, embedded JS)
├── middlewares.py          # ProxyPool, PlaywrightProxyMiddleware, BackoffRetryMiddleware
├── pipelines.py            # Validation → Normalization → Product → Review → Meilisearch → Stats
├── items.py                # ProductItem, ReviewItem (Scrapy Item definitions)
├── runner.py               # Subprocess entry point (CLI arg parser + CrawlerProcess)
├── scrapy_settings.py      # Global Scrapy settings (Playwright, pipelines, throttle)
├── tasks.py                # Celery tasks (run_marketplace_spider, run_review_spider)
└── models.py               # ScraperJob (job tracking model)
```

---

## 3. How a Spider Run Works (End-to-End)

### Automated (Celery Beat)

```
1. Celery Beat fires "scrape-amazon-in-6h" at 00:00 UTC
2. → run_marketplace_spider.delay("amazon-in")
3. Task creates ScraperJob(status=QUEUED) in DB
4. Task resolves "amazon-in" → spider name "amazon_in" via ScrapingConfig.spider_map()
5. Task spawns subprocess:
     python -m apps.scraping.runner amazon_in --job-id <uuid>
6. runner.py loads Django, creates CrawlerProcess, starts spider
7. Spider crawls listing pages → yields product detail requests
8. Detail pages parsed → ProductItem yielded
9. Pipelines process each item:
     Validate → Normalize → Match Product → Create Listing → Record PriceSnapshot → Queue Meilisearch
10. Spider closes → SpiderStatsUpdatePipeline writes final counts
11. Subprocess exits → Celery task updates ScraperJob(status=COMPLETED)
12. Task queues downstream:
     - sync_products_to_meilisearch (search index)
     - check_price_alerts (user notifications)
     - run_review_spider (chain review scraping)
```

### Manual Testing

```bash
cd backend
python -m apps.scraping.runner <spider_name> --max-pages 1
python -m apps.scraping.runner <spider_name> --urls "https://example.com/product/123" --max-pages 1
```

| Argument | Description |
|----------|-------------|
| `spider_name` | Required. Spider module name (e.g., `amazon_in`, `flipkart`) |
| `--max-pages N` | Limit listing pages per category (use 1 for testing) |
| `--urls url1,url2` | Override seed URLs with specific URLs |
| `--job-id UUID` | ScraperJob UUID for tracking |
| `--save-html` | Save raw HTML responses for debugging |
| `--max-review-pages N` | Limit review pages (review spiders) |
| `--proxy-list url1,url2` | Override proxy list |

---

## 4. Infrastructure Components


### BaseWhydudSpider

All spiders inherit from `BaseWhydudSpider(scrapy.Spider)` which provides:

- **User-Agent rotation**: 25+ UAs (Chrome, Firefox, Edge, Safari, Chrome Mobile) weighted ~70% Chrome to match Indian market share.
- **Viewport randomization**: 6 desktop resolutions (1920x1080, 1366x768, etc.) — one per spider instance.
- **Accept-Language headers**: 5 variants, all including `en-IN` to signal Indian user.
- **Sec-CH-UA Client Hints**: Chrome UAs get proper client hints headers.
- **Download delay**: 3s base + random 0-100% jitter.
- **Error tracking**: `items_scraped`, `items_failed` counters.
- **Stealth object**: `self.STEALTH = Stealth()` from `playwright-stealth` for Playwright spiders.

### Middlewares

Three middlewares handle the request/response lifecycle:

#### PlaywrightProxyMiddleware

Assigns Playwright browser contexts and proxies to requests. Two modes controlled by `SCRAPING_PROXY_TYPE` env var:

**Rotating mode** (DataImpulse — used by TataCLiQ):
- ONE gateway URL, each TCP connection gets a different exit IP.
- 5 context slots (rotating_0 through rotating_4) force 5 new IPs.
- NEVER bans the gateway. CAPTCHA/403 is expected (~20-30%), spider skips and retries.
- Tracks exit IPs via response headers (X-Client-IP, CF-Connecting-IP).

**Static mode** (WebShare-style individual proxies):
- Multiple fixed-IP proxies, round-robin assignment.
- Bans individual proxies on 403/429/CAPTCHA with exponential backoff.
- Session stickiness: same session key → same proxy (for multi-step flows).

**CAPTCHA detection**: Checks first 5KB of response body for `b"captcha"`, `b"validatecaptcha"`, `b"robot check"`.

**Skip flag**: Spiders that manage their own proxy/context (like TataCLiQ) set `_skip_proxy_middleware: True` in request meta. The middleware skips both `process_request` and `process_response` for these requests, preventing it from overwriting spider-specific Playwright context kwargs (e.g. `bypass_csp`, custom proxy config).

#### BackoffRetryMiddleware

Extends Scrapy's RetryMiddleware with non-blocking exponential backoff:
- Base: 5s, Max: 60s, Jitter: ±30%
- Formula: `delay = min(5 * 2^retry_count, 60)` + jitter

### Pipelines

Processed in order (lower number = earlier):

| Priority | Pipeline | What it does |
|----------|----------|--------------|
| 100 | **ValidationPipeline** | Drops ProductItems missing `marketplace_slug`, `external_id`, `url`, or `title` |
| 150 | **ReviewValidationPipeline** | Drops ReviewItems missing `marketplace_slug`, `product_external_id`, `rating`, or `body` (min 5 chars) |
| 200 | **NormalizationPipeline** | Cleans titles (whitespace), brands (casing), specs (strip), images (dedup) |
| 400 | **ProductPipeline** | Core persistence: match/create Brand, Category, Product, ProductListing, PriceSnapshot |
| 450 | **ReviewPersistencePipeline** | Persist reviews with dedup by external_review_id hash |
| 500 | **MeilisearchIndexPipeline** | Batch-sync scraped products to Meilisearch at spider close |
| 600 | **SpiderStatsUpdatePipeline** | Update ScraperJob with item counts (batched every 50 items) |

#### ProductPipeline — 6-Step Workflow

1. **Resolve Marketplace** — lookup by slug, drop if not found.
2. **Resolve/Create Seller** — `get_or_create` by (marketplace, external_seller_id or slugified name).
3. **Resolve/Create Brand & Category** — Alias-aware brand lookup. Category from slug or auto-inferred from breadcrumbs.
4. **Find/Create ProductListing & Product** — Check (marketplace, external_id). If new: run 4-step product matching. If exists: update fields.
5. **Record PriceSnapshot** — Raw SQL INSERT into TimescaleDB hypertable (ORM fails on hypertables).
6. **Update Canonical Product** — Recalculate `current_best_price` across all listings.

### Runner

`runner.py` is the subprocess entry point invoked by Celery tasks. It:
1. Loads `.env` file
2. Sets `DJANGO_SETTINGS_MODULE = whydud.settings.dev`
3. Calls `django.setup()`
4. Creates `CrawlerProcess` with merged settings
5. Runs `process.crawl()` and `process.start()` (blocks until done)

**Why subprocess?** Scrapy uses Twisted reactor which cannot be restarted. Running in subprocess isolates each crawl.

### Celery Tasks

| Task | Queue | Purpose |
|------|-------|---------|
| `run_marketplace_spider` | scraping | Primary Beat entry point. Creates ScraperJob, runs spider subprocess, queues downstream tasks. |
| `run_review_spider` | scraping | Runs review spider. On success: queues fraud detection + DudScore per product. |
| `run_spider` | scraping | Lower-level spider runner for ad-hoc jobs. |
| `scrape_product_adhoc` | scraping | On-demand single product scrape (120s timeout). |
| `scrape_daily_prices` | scraping | Batch: launches all active marketplace spiders in parallel. |

**Downstream task chain:**
```
Product Spider completes
  → sync_products_to_meilisearch (search index)
  → check_price_alerts (user price notifications)
  → run_review_spider (chain review scraping)

Review Spider completes
  → detect_fake_reviews (per product with new reviews)
  → compute_dudscore (per product with new reviews)
```

### Scrapy Settings

Key settings from `scrapy_settings.py`:

| Setting | Value | Notes |
|---------|-------|-------|
| `DOWNLOAD_TIMEOUT` | 90s | Proxy connections need more time |
| `DOWNLOAD_MAXSIZE` | 10MB | Max response size |
| `RETRY_TIMES` | 2 | Retries per request |
| `AUTOTHROTTLE_ENABLED` | True | Dynamic rate limiting |
| `AUTOTHROTTLE_START_DELAY` | 2s | Initial delay |
| `AUTOTHROTTLE_MAX_DELAY` | 20s | Max delay under load |
| `AUTOTHROTTLE_TARGET_CONCURRENCY` | 4.0 | Target concurrent requests |
| `MEMUSAGE_LIMIT_MB` | 2048 | Kill spider if >2GB RAM |
| `PLAYWRIGHT_MAX_CONTEXTS` | 6 | Max browser contexts |
| `PLAYWRIGHT_MAX_PAGES_PER_CONTEXT` | 4 | Pages per context |

### ScraperJob Model

Tracks every spider execution in the `scraper_jobs` table:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `marketplace` | FK | Link to Marketplace model |
| `spider_name` | string | e.g., "amazon_in" |
| `status` | enum | QUEUED → RUNNING → COMPLETED/FAILED |
| `items_scraped` | int | Products successfully processed |
| `items_failed` | int | Products dropped (validation/error) |
| `error_message` | text | Last 2000 chars of error output |
| `triggered_by` | string | "scheduled" (Beat) or "adhoc" (manual) |
| `started_at` / `finished_at` | datetime | Timing |

---

## 5. All 15 Spiders

### Tier 1 — High Priority (scraped every 6 hours)

#### Amazon.in (`amazon_in`)
- **Architecture:** Two-phase — HTTP listing → Playwright detail
- **Anti-bot:** Amazon CAPTCHA + rate limiting
- **Discovery:** 30+ search keywords (electronics, home, fashion)
- **Extraction:** CSS selectors (listing), JS rendering + structured data (detail)
- **Settings:** `CONCURRENT_REQUESTS=4`, `DOWNLOAD_DELAY=3s`
- **Status:** Production-ready

#### Flipkart (`flipkart`)
- **Architecture:** Two-phase — Playwright listing → HTTP+JSON-LD detail
- **Anti-bot:** 403/429 block detection
- **Discovery:** 30+ search keywords
- **Extraction:** JSON-LD `<script type="application/ld+json">` (primary), CSS/XPath (fallback)
- **Settings:** `CONCURRENT_REQUESTS=4`, `DOWNLOAD_DELAY=3s`
- **Status:** Production-ready

### Tier 2 — Medium Priority (daily scrapes)

#### Croma (`croma`)
- **Architecture:** HTTP-only with curl_cffi Chrome TLS impersonation
- **Anti-bot:** Akamai Bot Manager (JA3/JA4 fingerprinting)
- **Discovery:** 39 seed category URLs (electronics, appliances, kitchen, gaming)
- **Extraction:** `window.__INITIAL_DATA__` Redux store → `plpReducer`/`pdpReducer` (primary), JSON-LD (fallback)
- **Critical:** JS `undefined` replaced with `null` before JSON parse
- **Settings:** `CONCURRENT_REQUESTS=4`, `DOWNLOAD_DELAY=3s`
- **Status:** Production-ready (curl_cffi bypasses Akamai)

#### JioMart (`jiomart`)
- **Architecture:** HTTP-only with curl_cffi + sitemap discovery
- **Anti-bot:** Akamai WAF (HEAD requests blocked, only GET works)
- **Discovery:** Sitemap XML → sub-sitemaps (electronics, cdit) → product URLs
- **Extraction:** SSR HTML parsing (title, prices, specs, breadcrumbs)
- **Settings:** `CONCURRENT_REQUESTS=4`, `DOWNLOAD_DELAY=3s`
- **Status:** Production-ready (97% extraction rate, handles stale 404s)

#### Nykaa (`nykaa`)
- **Architecture:** HTTP-only with curl_cffi Chrome/120 TLS impersonation
- **Anti-bot:** Akamai Bot Manager (blocks Chrome 131+, only Chrome/120 works)
- **Discovery:** 20 seed category URLs (beauty, skincare, haircare)
- **Extraction:** `window.__PRELOADED_STATE__` Redux store (primary), JSON-LD (fallback), `window.dataLayer` (listing fallback)
- **Settings:** `CONCURRENT_REQUESTS=4`, `DOWNLOAD_DELAY=3s`
- **Status:** Production-ready (Chrome/120 header requirement is critical)

#### Snapdeal (`snapdeal`)
- **Architecture:** Plain HTTP (no Playwright, no proxy)
- **Anti-bot:** None (AWS CloudFront only, no WAF)
- **Discovery:** 16 search queries
- **Extraction:** schema.org microdata (`itemprop` attributes)
- **Critical:** Never follow `/honeybot` links (honeypot trap)
- **Settings:** `CONCURRENT_REQUESTS=8`, `DOWNLOAD_DELAY=2s`
- **Status:** Production-ready

#### Reliance Digital (`reliance_digital`)
- **Architecture:** HTTP-only JSON API (Fynd Commerce)
- **Anti-bot:** None (open API)
- **Discovery:** 10 search queries
- **Extraction:** `/ext/raven-api/catalog/v1.0/products` JSON response
- **Settings:** `CONCURRENT_REQUESTS=4`, `DOWNLOAD_DELAY=1.5s`
- **Status:** Production-ready

#### Vijay Sales (`vijay_sales`)
- **Architecture:** Two-phase — Unbxd Search API (listing) → Magento GraphQL (enrichment)
- **Anti-bot:** None (both APIs open)
- **Discovery:** 10 search queries
- **Extraction:** Unbxd JSON products (listing), GraphQL enrichment (description, images, rating). Batched: 10 SKUs per GraphQL request.
- **Settings:** `CONCURRENT_REQUESTS=4`, `DOWNLOAD_DELAY=1.5s`
- **Status:** Production-ready

#### FirstCry (`firstcry`)
- **Architecture:** HTTP-only with curl_cffi Chrome/131 TLS impersonation
- **Anti-bot:** None detected (Apache/OpenSSL, no Cloudflare/Akamai)
- **Discovery:** Search-based — 24 seed queries across baby care, feeding, clothing, toys, gear, nursery, footwear, school supplies. Category URLs (`/baby-care`, `/toys`) return 404; `/search?q={query}` redirects to listing pages.
- **Extraction:** `CurrentProductDetailJSON` embedded JavaScript variable (primary). Contains full product data: name, MRP, discount%, images, age groups, colors, sizes. Rating/review count from `avg_rating`/`totalreview` JS vars. JSON-LD on product pages is empty/broken.
- **Price calc:** MRP in rupees from `CurrentProductDetailJSON`, selling price = `mrp * (100 - Dis) / 100`, then * 100 for paisa.
- **Special:** Age group extraction from `hashAgeG` field (e.g., "0-3 Months", "3-6 Months") stored in variant_options. Color extraction from `hashCols` field.
- **Pagination:** `?page=N` appended to listing URLs, 20 products per page.
- **Settings:** `CONCURRENT_REQUESTS=4`, `DOWNLOAD_DELAY=1.5s`
- **Status:** Production-ready

#### Myntra (`myntra`)
- **Architecture:** Playwright-only (React SPA)
- **Anti-bot:** Advanced fingerprinting + behavior analysis
- **Discovery:** 25 seed category URLs (men, women, kids, footwear)
- **Extraction:** `window.__myx` React state (primary), product card links (fallback)
- **Settings:** `CONCURRENT_REQUESTS=4`, `DOWNLOAD_DELAY=3s`
- **Status:** Production-ready

#### AJIO (`ajio`)
- **Architecture:** Playwright-only (React SPA / Next.js)
- **Anti-bot:** PerimeterX (Reliance-owned)
- **Discovery:** 24 seed category URLs (men, women, kids, home)
- **Extraction:** `__PRELOADED_STATE__` or `__NEXT_DATA__` (primary), product links (fallback)
- **Settings:** `CONCURRENT_REQUESTS=4`, `DOWNLOAD_DELAY=3s`
- **Status:** Production-ready (detects "Pardon" block page)

### Tier 3 — Low Priority (hardest to scrape, daily)

#### Tata CLiQ (`tata_cliq`)
- **Architecture:** Playwright-only with optional DataImpulse rotating proxy + XHR interception. **Listing-only extraction** — all product data extracted from search page XHR/DOM, no individual product page visits.
- **Anti-bot:** Cloudflare Bot Management (`__cf_bm` cookie). Requires homepage warmup visit to establish session cookies before search requests.
- **Discovery:** Search-based — 22 seed search queries (brand-specific for reliability). Category URLs do NOT work (SPA routes to 404). Generic search terms (e.g. "laptops") redirect to promo CLP pages and are detected as blocks.
- **Extraction chain:** Hybris `searchab` API via XHR interception (primary) → rendered DOM product cards (fallback) → JSON-LD (fallback)
- **Proxy:** DataImpulse `gw.dataimpulse.com:823` with 2 context slots for IP rotation. **Optional** — reads from `SCRAPING_PROXY_LIST` env var, works without proxy (direct connections).
- **Settings:** `CONCURRENT_REQUESTS=2`, `DOWNLOAD_DELAY=5s`, wait 8-15s per page for SPA hydration
- **Status:** Production-ready (tested 2026-03-04: 40 items/run, 100% extraction rate, 0 failures)

#### Meesho (`meesho`)
- **Architecture:** Camoufox-only (anti-detection patched Firefox)
- **Anti-bot:** Akamai Bot Manager (most aggressive — blocks Playwright, curl_cffi, headed Chrome)
- **Discovery:** 17 seed search queries (women's fashion focus: sarees, kurtis, lehengas)
- **Extraction:** `__NEXT_DATA__` → `product.details.data` (primary), DOM parsing (fallback)
- **Settings:** `CONCURRENT_REQUESTS=1`, `DOWNLOAD_DELAY=5s`
- **Status:** Production-ready (camoufox is the only thing that bypasses Akamai here)

### Review Spiders

#### Amazon Reviews (`amazon_in_reviews`)
- **Architecture:** Playwright-only, scrapes reviews embedded on product detail pages
- **Discovery:** DB query for Amazon products with < 10 reviews
- **Extraction:** CSS selectors for `[data-hook="review"]` containers
- **Status:** Production-ready (~8 reviews per product page)

#### Flipkart Reviews (`flipkart_reviews`)
- **Architecture:** Playwright-only with custom JS extraction
- **Discovery:** DB query for Flipkart products with < 10 reviews
- **Extraction:** Custom JavaScript walks DOM from "Verified Purchase" anchors to find review containers
- **Status:** Production-ready (~10 reviews per page)

---

## 6. Anti-Bot Bypass Strategies

Each Indian marketplace uses different protection. Here's what works:

| Protection | Sites | Bypass Strategy |
|------------|-------|-----------------|
| **None** | Snapdeal, Reliance Digital, Vijay Sales, FirstCry | Plain HTTP requests (FirstCry uses curl_cffi for consistency) |
| **Amazon CAPTCHA** | Amazon.in | Playwright (solves JS challenge), skip CAPTCHA pages |
| **Rate limiting** | Flipkart | Playwright + throttling + retry on 403/429 |
| **Akamai (JA3/JA4)** | Croma, JioMart, Nykaa | `curl_cffi` Chrome TLS fingerprint impersonation |
| **Akamai (aggressive)** | Meesho | `camoufox` (patched Firefox — only browser that bypasses) |
| **Cloudflare Bot Mgmt** | Tata CLiQ | Playwright + `playwright-stealth` + DataImpulse rotating proxy |
| **Fingerprinting** | Myntra | Playwright with stealth |
| **PerimeterX** | AJIO | Playwright with stealth |

### curl_cffi TLS Impersonation

For Akamai-protected sites (Croma, Nykaa, JioMart), browsers are identified by their TLS handshake fingerprint (JA3/JA4 hash). Python's `requests` library has a different TLS fingerprint than Chrome, so Akamai blocks it.

`curl_cffi` solves this by using curl's TLS library to impersonate Chrome's exact handshake:
```python
from curl_cffi.requests import Session
session = Session(impersonate="chrome120")  # Nykaa requires Chrome 120 specifically
response = session.get(url, headers=headers)
```

Each site has its own custom middleware (e.g., `CromaCurlCffiMiddleware`, `NykaaCurlCffiMiddleware`) that replaces Scrapy's default download handler for that spider.

### camoufox (Anti-Detection Firefox)

Meesho's Akamai implementation is the most aggressive. It blocks:
- All automated Chromium (even with stealth patches)
- curl_cffi TLS impersonation
- Even headed Chrome with regular user interaction

Only `camoufox` works — it's a patched version of Firefox that:
- Removes all automation indicators
- Randomizes canvas/WebGL/audio fingerprints
- Uses genuine Firefox TLS fingerprint (not Chrome)
- Runs in a real display context (not headless)

### XHR Interception Pattern (Tata CLiQ)

For pure SPAs where all data comes from API calls:

```javascript
// Injected BEFORE page scripts load via page.add_init_script()
window.__whydud_xhr = [];
const _wf = window.fetch;
window.fetch = async function() {
    const r = await _wf.apply(this, arguments);
    try {
        // Handle both string URLs and Request objects (new Request(url))
        const a0 = arguments[0];
        const u = typeof a0 === 'string' ? a0 : (a0 && a0.url ? a0.url : (r.url || ''));
        if (r.ok) {
            const c = r.headers.get('content-type') || '';
            if (c.includes('json')) {
                const d = await r.clone().json();
                window.__whydud_xhr.push({u: u, d: d});
            }
        }
    } catch(e) {}
    return r;
};
// Also patches XMLHttpRequest.prototype.open/send
```

After page load, a PageMethod evaluates JS to inject captured data into the DOM as `<script id="__whydud_data">`, which Scrapy can then parse from the response HTML.

**Important:** The spider sets `_skip_proxy_middleware: True` in request meta to prevent `PlaywrightProxyMiddleware` from overriding its Playwright context kwargs (which include `bypass_csp: True` and proxy config). Without this, the middleware strips spider-specific browser settings.

---

## 7. Proxy System

### Current Setup

Only **Tata CLiQ** uses proxies (optionally). All other spiders bypass anti-bot via TLS impersonation or browser stealth.

**DataImpulse Rotating Proxy (optional):**
```
Gateway: http://gw.dataimpulse.com:823
Auth: configured via SCRAPING_PROXY_LIST env var
```
- Each TCP connection gets a different exit IP (Indian datacenter IPs)
- Configured directly in Playwright context kwargs (not via middleware — spider sets `_skip_proxy_middleware: True`)
- 2 context slots per spider for IP diversity
- **Optional:** If `SCRAPING_PROXY_LIST` env var is empty, spider runs without proxy (direct connections). Useful for testing or when proxy bandwidth is exhausted.

### Proxy Configuration

```bash
# .env
SCRAPING_PROXY_TYPE=rotating          # "rotating" or "static"
SCRAPING_PROXY_LIST=http://user:pass@gw.dataimpulse.com:823
```

### Rotating vs Static Mode

| Feature | Rotating (DataImpulse) | Static (WebShare) |
|---------|----------------------|-------------------|
| IP per request | Different (automatic) | Same per proxy |
| Ban strategy | Never ban gateway | Ban individual proxies |
| CAPTCHA handling | Expected ~20-30%, skip & retry | Exponential backoff |
| Context slots | 5 slots = 5 IPs | 1 slot per proxy |
| Session stickiness | Not supported | Supported (same proxy for related requests) |

---

## 8. Price Handling

**All prices stored as integers in paisa (1 rupee = 100 paisa).**

```python
# In spider: convert rupees to paisa
price_rupees = 24999.00   # from website
price_paisa = int(Decimal(str(price_rupees)) * 100)  # 2499900

# In ProductItem
item["price"] = price_paisa  # Decimal field
item["mrp"] = mrp_paisa      # Maximum retail price
```

**Why paisa?** Avoids floating-point precision issues. `Decimal(12,2)` in DB. Display layer converts back to `₹24,999.00`.

**PriceSnapshot** recorded via raw SQL (TimescaleDB hypertable):
```sql
INSERT INTO price_snapshots (time, listing_id, product_id, marketplace_id, price, mrp, in_stock, seller_name)
VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s)
```

---

## 9. Product Matching & Dedup

### Product Dedup

Products are deduplicated by `(marketplace, external_id)`:
- Amazon: ASIN (e.g., `B0CX23GFMV`)
- Flipkart: FPID (e.g., `MOBGN9VHKZ8DTFT4`)
- Each marketplace has its own ID format

If a product already exists: **update** fields (price, stock, rating).
If new: run 4-step matching to find cross-marketplace canonical product, then create `ProductListing`.

### Review Dedup

Reviews deduplicated by `external_review_id`:
- If provided by spider: use platform's review ID
- If not: generate hash from `(marketplace + product_id + reviewer + date + body[:100])`
- Safe to re-run spider — duplicates are silently skipped

### Category Inference

If spider doesn't provide `category_slug`, the pipeline auto-infers from breadcrumbs:
1. Walk breadcrumbs deepest → shallowest
2. Skip generic terms: "home", "all categories", "search", "products"
3. Match against existing categories
4. Create parent categories as needed

---

## 10. How to Use

### Test a Single Spider

```bash
cd backend

# Quick test — 1 page per category
python -m apps.scraping.runner amazon_in --max-pages 1

# Test specific URL
python -m apps.scraping.runner flipkart --urls "https://www.flipkart.com/search?q=iphone" --max-pages 1

# Save HTML for debugging
python -m apps.scraping.runner croma --max-pages 1 --save-html

# Test reviews
python -m apps.scraping.runner amazon_in_reviews --max-review-pages 1
```

### Run via Celery

```python
from apps.scraping.tasks import run_marketplace_spider, scrape_product_adhoc

# Run full spider
run_marketplace_spider.delay("amazon-in")

# Scrape single product
scrape_product_adhoc.delay("https://www.amazon.in/dp/B0CX23GFMV", "amazon-in")
```

### Monitor Jobs

```python
from apps.scraping.models import ScraperJob

# Recent jobs
ScraperJob.objects.all()[:10]

# Failed jobs
ScraperJob.objects.filter(status="failed")

# Job with most items
ScraperJob.objects.order_by("-items_scraped").first()
```

### Check Spider Map

```python
from common.app_settings import ScrapingConfig

ScrapingConfig.spider_map()
# {'amazon-in': 'amazon_in', 'flipkart': 'flipkart', 'croma': 'croma', ...}

ScrapingConfig.review_spider_map()
# {'amazon-in': 'amazon_in_reviews', 'flipkart': 'flipkart_reviews'}
```

---

## 11. Celery Beat Schedule

All schedules defined in `backend/whydud/celery.py`.

### Product Spiders

| Spider | Schedule | IST | Notes |
|--------|----------|-----|-------|
| amazon-in | Every 6h (00, 06, 12, 18 UTC) | 05:30, 11:30, 17:30, 23:30 | Highest priority |
| flipkart | Every 6h (03, 09, 15, 21 UTC) | 08:30, 14:30, 20:30, 02:30 | Offset from Amazon |
| croma | Daily 08:00 UTC | 13:30 IST | |
| reliance-digital | Daily 04:30 UTC | 10:00 IST | |
| vijay-sales | Daily 05:00 UTC | 10:30 IST | |
| snapdeal | Daily 07:30 UTC | 13:00 IST | |
| nykaa | Daily 08:00 UTC | 13:30 IST | |
| tata-cliq | Daily 06:30 UTC | 12:00 IST | DataImpulse proxy |
| jiomart | Daily 13:00 UTC | 18:30 IST | |
| myntra | Daily 16:00 UTC | 21:30 IST | |
| ajio | Daily 19:00 UTC | 00:30 IST | |
| meesho | Daily 10:00 UTC | 15:30 IST | Camoufox |
| firstcry | Daily 09:30 UTC | 15:00 IST | curl_cffi |

### Review Spiders

| Spider | Schedule | IST |
|--------|----------|-----|
| amazon-in reviews | Daily 04:00 UTC | 09:30 IST |
| flipkart reviews | Daily 07:00 UTC | 12:30 IST |

### Other Scheduled Tasks

| Task | Schedule | Purpose |
|------|----------|---------|
| Meilisearch full reindex | Daily 01:00 UTC | Full search index rebuild |
| DudScore recalc | Monthly 1st 03:00 UTC | Full trust score recalculation |
| Price alerts | Every 4h | Check user price alert thresholds |
| Deal detection | Every 2h | Find blockbuster deals |
| Publish pending reviews | Every hour | Auto-publish moderated reviews |

---

## 12. Known Bottlenecks & Issues

### Critical Issues

1. ~~**Tata CLiQ — SPA 404 routing**~~ **RESOLVED (2026-03-04)**: Switched to search-based discovery (`/search/?searchCategory=all&text={query}`). Category URLs no longer used. Brand-specific search queries (e.g. "samsung mobile", "sony headphones") are more reliable than generic terms which redirect to promo CLP pages. Products extracted directly from Hybris `searchab` XHR on listing pages — no product page visits needed.

2. **Meesho — camoufox dependency**: Only works with camoufox (patched Firefox). Akamai blocks everything else. camoufox requires a real display context and is slower than Playwright. `CONCURRENT_REQUESTS=1` — serial scraping only.

3. **Nykaa — Chrome/120 pinning**: Only Chrome/120 TLS fingerprint works. If curl_cffi stops supporting this impersonation or Akamai updates, the spider breaks. No fallback strategy.

### Performance Bottlenecks

4. **Playwright memory**: Each Chromium context uses ~150-300MB RAM. With `PLAYWRIGHT_MAX_CONTEXTS=6`, peak memory is ~2GB. `MEMUSAGE_LIMIT_MB=2048` kills the process if exceeded.

5. **Subprocess overhead**: Each spider run spawns a new Python process, imports Django, and launches Chromium. Cold start is 5-15 seconds per spider.

6. **Serial review scraping**: Review spiders query the DB for products needing reviews, then scrape one-by-one. No parallelism across products.

7. **TimescaleDB PriceSnapshot insertion**: Raw SQL INSERT per item (ORM fails on hypertables). No batch insert optimization.

### Reliability Issues

8. **Proxy cost**: DataImpulse charges per GB. Playwright pages with images/scripts are 1-5MB each. TataCLiQ spider is the most expensive to run. Proxy is now optional — spider works without proxy for testing, but production runs benefit from IP rotation to avoid Cloudflare rate limits.

9. **Sitemap staleness**: JioMart sitemap contains URLs from 2023-2024 that return 404. Spider handles gracefully but wastes requests.

10. **No alerting on 0-item runs**: If a spider completes with 0 items (all blocked), it reports success. No automatic alerting on degraded performance.

11. **CAPTCHA false positives**: The middleware's CAPTCHA detection (`b"captcha"` in body) triggers on normal pages that mention "captcha" in their JS bundles (e.g., Cloudflare-protected sites always contain this string).

---

## 13. Future Updates & Roadmap

### Short-term Fixes

- [x] **Tata CLiQ: Switch to search-based discovery** — *(Done 2026-03-04)* Uses `/search/?searchCategory=all&text=<keyword>` with 22 brand-specific queries. Also fixed: homepage warmup, listing-only extraction, middleware conflict (`_skip_proxy_middleware`), optional proxy, pagination query param preservation.
- [ ] **Add 0-item alerting** — Discord/Slack webhook when a spider finishes with 0 items scraped.
- [x] **Fix CAPTCHA false positive detection** — *(Done 2026-03-04)* TataCLiQ spider now only checks for captcha markers in pages < 50KB (avoids false positives from large SPA bundles containing "captcha" in JS).
- [ ] **Batch PriceSnapshot inserts** — Collect snapshots in pipeline, flush in `close_spider()` with a single `INSERT ... VALUES (...), (...), ...`.

### Medium-term Improvements

- [ ] **Add review spiders for more marketplaces** — Currently only Amazon and Flipkart have review spiders. Croma, Nykaa, Myntra reviews would improve DudScore accuracy.
- [ ] **Headless camoufox** — Investigate camoufox headless mode to reduce resource usage for Meesho spider.
- [ ] **Dynamic category discovery** — Instead of hardcoded seed URLs, discover categories by crawling the homepage navigation. Prevents stale URL issues.
- [ ] **Request-level cost tracking** — Track DataImpulse bandwidth per spider run for cost optimization.
- [ ] **Spider health dashboard** — Expose ScraperJob stats via API endpoint for monitoring dashboard.

### Long-term Architecture

- [ ] **Move to Scrapy Cloud / Zyte** — Off-load spider execution to managed infrastructure. Reduces server memory pressure and provides built-in proxy rotation.
- [ ] **GraphQL product API for ad-hoc scraping** — Let users request a product scrape via API and get results pushed via WebSocket.
- [ ] **ML-based extraction** — Train models to extract product data from arbitrary HTML, reducing per-marketplace spider maintenance.
- [ ] **Distributed scraping** — Run spiders across multiple workers with shared job queue for horizontal scaling.

---

## 14. Dependencies

```
# Core
scrapy==2.14.1                  # Crawling framework
scrapy-playwright==0.0.46       # Playwright integration for Scrapy
playwright==1.58.0              # Browser automation (Chromium)
playwright-stealth==2.0.2       # Anti-detection patches for Playwright

# TLS Impersonation
curl_cffi>=0.14.0               # Chrome TLS fingerprint for Akamai-protected sites

# Anti-Detection Browser
camoufox[geoip]>=0.4.11         # Patched Firefox for aggressive Akamai (Meesho)

# Search
meilisearch==0.40.0             # Product search index sync
```

**Install Playwright browsers after pip install:**
```bash
playwright install chromium
```

**Install camoufox browser:**
```bash
python -m camoufox fetch
```
