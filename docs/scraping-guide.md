# Whydud Scraping — Manual Operations Guide

Step-by-step instructions for running, monitoring, and troubleshooting scrapes.

---

## Prerequisites

Before running any spider, ensure these services are running:

```bash
# Start infrastructure (Docker Compose dev)
docker compose -f docker/docker-compose.dev.yml up -d postgres redis meilisearch

# Verify they're healthy
docker compose -f docker/docker-compose.dev.yml ps
```

Required:
- **PostgreSQL 16 + TimescaleDB** — product/listing/price storage
- **Redis** — Celery broker (only needed for Celery-triggered runs)
- **Meilisearch** — search index sync (optional for scraping, required for search)
- **Playwright Chromium** — installed via `playwright install chromium`

---

## 1. Run a Product Spider (CLI)

### Amazon.in

```bash
cd backend/

# Full scrape — all 130+ seed categories, 5 pages each (default)
python -m apps.scraping.runner amazon_in

# Quick test — 1 page per category
python -m apps.scraping.runner amazon_in --max-pages 1

# Specific categories only
python -m apps.scraping.runner amazon_in --urls "https://www.amazon.in/s?k=smartphones,https://www.amazon.in/s?k=laptops" --max-pages 2

# Save raw HTML for debugging (saved to data/raw_html/)
python -m apps.scraping.runner amazon_in --max-pages 1 --save-html
```

### Flipkart

```bash
# Full scrape — all 110+ seed categories
python -m apps.scraping.runner flipkart

# Quick test — 1 page per category
python -m apps.scraping.runner flipkart --max-pages 1

# Specific categories
python -m apps.scraping.runner flipkart --urls "https://www.flipkart.com/search?q=smartphones,https://www.flipkart.com/search?q=laptops" --max-pages 2
```

### With Proxy Rotation

```bash
# Via CLI flag
python -m apps.scraping.runner amazon_in --proxy-list "http://user:pass@proxy1:8080,http://proxy2:8080"

# Via environment variable (persists for all runs)
export SCRAPING_PROXY_LIST="http://user:pass@proxy1:8080,http://proxy2:8080"
python -m apps.scraping.runner amazon_in
```

---

## 2. Run a Review Spider (CLI)

Review spiders scrape customer reviews for products already in the database.

### Amazon.in Reviews

```bash
# Scrape reviews for up to 200 products with <10 reviews
python -m apps.scraping.runner amazon_in_reviews

# Limit review pages per product (default: 1, Amazon embeds ~8 reviews per product page)
python -m apps.scraping.runner amazon_in_reviews --max-review-pages 1
```

### Flipkart Reviews

```bash
# Scrape reviews for up to 200 products with <10 reviews
python -m apps.scraping.runner flipkart_reviews

# More review pages per product (default: 3, ~10 reviews per page)
python -m apps.scraping.runner flipkart_reviews --max-review-pages 5
```

---

## 3. Run via Celery (Tracked in DB)

Celery-triggered runs create a `ScraperJob` record for tracking.

```bash
# Start Celery worker (if not already running)
cd backend/
celery -A whydud worker -l info -Q default,scraping

# Trigger from Python/Django shell
python manage.py shell -c "
from apps.scraping.tasks import run_marketplace_spider
result = run_marketplace_spider.delay('amazon-in')
print(f'Task ID: {result.id}')
"

# Trigger Flipkart
python manage.py shell -c "
from apps.scraping.tasks import run_marketplace_spider
result = run_marketplace_spider.delay('flipkart')
print(f'Task ID: {result.id}')
"

# Trigger review spiders
python manage.py shell -c "
from apps.scraping.tasks import run_review_spider
result = run_review_spider.delay('amazon-in')
print(f'Task ID: {result.id}')
"
```

---

## 4. Automated Schedule (Celery Beat)

These run automatically when Celery Beat is active:

| Task | Schedule (UTC) | Spider |
|------|---------------|--------|
| `scrape-amazon-in-6h` | 00:00, 06:00, 12:00, 18:00 | `amazon_in` |
| `scrape-flipkart-6h` | 03:00, 09:00, 15:00, 21:00 | `flipkart` |
| `scrape-amazon-in-reviews-daily` | 04:00 | `amazon_in_reviews` |
| `scrape-flipkart-reviews-daily` | 07:00 | `flipkart_reviews` |

Start Celery Beat:

```bash
celery -A whydud beat -l info
```

---

## 5. Check Results

### Product/Listing Counts

```bash
python manage.py shell -c "
from apps.products.models import Product, ProductListing, Marketplace
from apps.pricing.models import PriceSnapshot

print(f'Products:  {Product.objects.count()}')
print(f'Listings:  {ProductListing.objects.count()}')
print(f'Snapshots: {PriceSnapshot.objects.count()}')
print()
for m in Marketplace.objects.all():
    lc = ProductListing.objects.filter(marketplace=m).count()
    if lc > 0:
        print(f'  {m.name}: {lc} listings')
"
```

### Review Counts

```bash
python manage.py shell -c "
from apps.reviews.models import Review
from apps.products.models import Marketplace

print(f'Total reviews: {Review.objects.count()}')
print(f'Published:     {Review.objects.filter(status=\"published\").count()}')
print(f'Flagged:       {Review.objects.filter(is_flagged=True).count()}')
print()
for m in Marketplace.objects.all():
    rc = Review.objects.filter(marketplace=m).count()
    if rc > 0:
        print(f'  {m.name}: {rc} reviews')
"
```

### ScraperJob History (Celery runs only)

```bash
python manage.py shell -c "
from apps.scraping.models import ScraperJob
for j in ScraperJob.objects.order_by('-created_at')[:10]:
    duration = (j.finished_at - j.started_at).total_seconds() / 60 if j.finished_at and j.started_at else 0
    print(f'{j.spider_name:20} | {j.status:10} | scraped: {j.items_scraped:4} | failed: {j.items_failed:3} | {duration:.0f}min | {j.created_at:%Y-%m-%d %H:%M}')
"
```

### Cross-Marketplace Matches

```bash
python manage.py shell -c "
from django.db.models import Count
from apps.products.models import Product

multi = Product.objects.annotate(lc=Count('listings')).filter(lc__gte=2)
print(f'Products on 2+ marketplaces: {multi.count()}')
for p in multi[:10]:
    listings = p.listings.select_related('marketplace').all()
    prices = ', '.join(f'{l.marketplace.name}: ₹{l.current_price/100:,.0f}' for l in listings)
    print(f'  {p.title[:60]} → {prices}')
"
```

---

## 6. CLI Arguments Reference

```
python -m apps.scraping.runner <spider_name> [options]

Positional:
  spider_name          amazon_in | flipkart | amazon_in_reviews | flipkart_reviews

Options:
  --job-id UUID        ScraperJob UUID (auto-created by Celery tasks)
  --urls URL,URL       Comma-separated seed URLs (overrides built-in seeds)
  --max-pages N        Max listing pages per category (default: per-category limits)
  --max-review-pages N Max review pages per product (default: 3)
  --save-html          Save raw HTML to data/raw_html/ for debugging
  --proxy-list URL,URL Comma-separated proxy URLs (overrides SCRAPING_PROXY_LIST env)
```

---

## 7. Spider Details

### What Each Spider Scrapes

| Spider | Categories | Fields Extracted |
|--------|-----------|-----------------|
| `amazon_in` | 130+ (smartphones, laptops, TVs, appliances, fashion, books, baby, auto, etc.) | title, brand, price, MRP, images, rating, review_count, specs, seller, stock, offers, about_bullets, description, warranty, delivery_info, return_policy, breadcrumbs, variants, country_of_origin, manufacturer, model_number, weight, dimensions |
| `flipkart` | 110+ (same categories as Amazon) | Same fields — extracted from JSON-LD + CSS fallbacks |
| `amazon_in_reviews` | N/A (product-based) | rating, title, body, reviewer_name, reviewer_id, review_date, is_verified_purchase, helpful_votes, images, variant, country |
| `flipkart_reviews` | N/A (product-based) | Same fields — extracted via JS DOM evaluation |

### Per-Category Page Limits

Both spiders use per-category page limits:
- **Popular categories** (smartphones, laptops, TVs): up to 10 pages
- **Standard categories** (most others): up to 5 pages
- Override with `--max-pages N` to set a uniform limit

### Anti-Detection Features

| Feature | Implementation |
|---------|---------------|
| User-Agent rotation | 25+ real browser UAs (Chrome, Firefox, Edge, Safari, Android) |
| Viewport randomization | 7 sizes, randomized per spider instance |
| Client Hints (Sec-CH-UA) | 4 variants matching Chrome versions |
| Sec-Fetch headers | Full set (Dest, Mode, Site, User) |
| Accept-Language | 5 Indian locale variants |
| Playwright stealth | `playwright-stealth` patches (navigator.webdriver, chrome.runtime, WebGL) |
| Download delay | 3s base + random jitter (2-5s total) |
| Concurrent requests | 2 per domain max |
| Proxy rotation | Optional, round-robin with health tracking + exponential backoff |

---

## 8. Adding New Categories

### Amazon.in

Edit `backend/apps/scraping/spiders/amazon_spider.py`:

1. Add seed URL to `SEED_CATEGORY_URLS`:
```python
("https://www.amazon.in/s?k=your+keyword&rh=n%3ANODE_ID", _STD),
# _TOP = 10 pages, _STD = 5 pages
```

2. Add keyword mapping to `KEYWORD_CATEGORY_MAP`:
```python
"your keyword": "your-category-slug",
```

### Flipkart

Edit `backend/apps/scraping/spiders/flipkart_spider.py`:

1. Add seed URL to `SEED_CATEGORY_URLS`:
```python
("https://www.flipkart.com/search?q=your+keyword", _STD),
```

2. Add keyword mapping to `KEYWORD_CATEGORY_MAP`:
```python
"your keyword": "your-category-slug",
```

### Auto-Category Creation

If a product's breadcrumbs don't match any existing category, the pipeline auto-creates one:
- Walks breadcrumbs deepest-first
- Skips generic terms ("home", "all categories")
- Creates `Category` with slug derived from breadcrumb text
- Sets parent from adjacent breadcrumb level

No manual category setup required for most products.

---

## 9. Proxy Setup

### Configure Proxies

```bash
# .env file
SCRAPING_PROXY_LIST=http://user:pass@proxy1:8080,http://user:pass@proxy2:8080

# Optional tuning
SCRAPING_PROXY_BAN_COOLDOWN_BASE=30    # seconds (exponential backoff start)
SCRAPING_PROXY_BAN_MAX_COOLDOWN=600    # seconds (max backoff cap)
```

### How Proxy Rotation Works

1. Proxies loaded from env or `--proxy-list` CLI arg
2. Each proxy gets a named Playwright browser context
3. Requests assigned via round-robin rotation
4. Ban detection: HTTP 403/429/503 or CAPTCHA markers in response
5. Banned proxies enter exponential backoff (30s → 60s → 120s → ... → 600s max)
6. Session stickiness: listing page + all child product pages use same proxy
7. No proxies configured = direct requests (graceful fallback)

### Recommended Proxy Providers (India)

For scraping Indian marketplaces, use residential proxies with Indian IPs:
- Bright Data (residential)
- Oxylabs (residential)
- SmartProxy (residential)

Datacenter proxies get blocked quickly by Amazon/Flipkart.

---

## 10. Troubleshooting

### Spider scrapes 0 items

1. **Check marketplace exists in DB**:
   ```bash
   python manage.py shell -c "
   from apps.products.models import Marketplace
   print(list(Marketplace.objects.values_list('slug', flat=True)))
   "
   ```
   Must include `amazon-in` and `flipkart`.

2. **Check Playwright is installed**:
   ```bash
   playwright install chromium
   ```

3. **Check with --save-html** to see what the spider receives:
   ```bash
   python -m apps.scraping.runner amazon_in --max-pages 1 --save-html
   # Check data/raw_html/ for saved HTML files
   ```

### All items dropped by pipeline

Check `MARKETPLACE_SLUG` in the spider matches the DB Marketplace `slug` exactly:
- Amazon: `"amazon-in"` (hyphen, not underscore)
- Flipkart: `"flipkart"`

### Amazon CAPTCHA on every page

Amazon is blocking your IP. Options:
1. Add proxy rotation (see Section 9)
2. Wait 30-60 minutes (Amazon's rate limit resets)
3. Reduce concurrency: edit `base_spider.py` → `CONCURRENT_REQUESTS_PER_DOMAIN: 1`

### Flipkart 403 errors

Flipkart blocks all non-browser requests. Ensure Playwright is enabled:
- Product spider: `meta={"playwright": True}` on product page requests
- All handlers should be ScrapyPlaywrightDownloadHandler

### TimescaleDB PriceSnapshot errors

PriceSnapshot uses raw SQL INSERT (not Django ORM). If you see `column "id" does not exist`:
- The hypertable migration hasn't been applied
- Run: `python manage.py migrate pricing`

### Meilisearch not updating

After a CLI scrape, Meilisearch syncs automatically via the pipeline. If products don't appear in search:
```bash
# Force full reindex
python manage.py shell -c "
from apps.search.tasks import sync_products_to_meilisearch
sync_products_to_meilisearch()
"
```

---

## 11. Typical Scrape Workflow

A complete manual scrape session:

```bash
cd backend/

# 1. Start infrastructure
docker compose -f docker/docker-compose.dev.yml up -d postgres redis meilisearch

# 2. Scrape Amazon products (1 page per category for testing)
python -m apps.scraping.runner amazon_in --max-pages 1

# 3. Scrape Flipkart products
python -m apps.scraping.runner flipkart --max-pages 1

# 4. Check product counts
python manage.py shell -c "
from apps.products.models import Product, ProductListing
print(f'Products: {Product.objects.count()}, Listings: {ProductListing.objects.count()}')
"

# 5. Scrape reviews for products that have <10 reviews
python -m apps.scraping.runner amazon_in_reviews
python -m apps.scraping.runner flipkart_reviews

# 6. Run fraud detection on new reviews
python manage.py shell -c "
from apps.reviews.tasks import detect_fake_reviews
from apps.products.models import Product
for p in Product.objects.filter(total_reviews__gt=0)[:50]:
    detect_fake_reviews(str(p.id))
print('Fraud detection complete')
"

# 7. Recompute DudScores
python manage.py shell -c "
from apps.scoring.tasks import compute_dudscore
from apps.products.models import Product
for p in Product.objects.all()[:50]:
    compute_dudscore(str(p.id))
print('DudScores recomputed')
"

# 8. Full Meilisearch reindex
python manage.py shell -c "
from apps.search.tasks import sync_products_to_meilisearch
sync_products_to_meilisearch()
print('Meilisearch synced')
"
```

---

## 12. Configuration Reference

All scraping-related settings in `common/app_settings.py`:

| Config | Method | Default | Purpose |
|--------|--------|---------|---------|
| `ScrapingConfig.spider_timeout()` | `SCRAPING_SPIDER_TIMEOUT` | 3600 | Max runtime per spider (seconds) |
| `ScrapingConfig.max_listing_pages()` | `SCRAPING_MAX_LISTING_PAGES` | 5 | Default max pages per category |
| `ScrapingConfig.raw_html_dir()` | `SCRAPING_RAW_HTML_DIR` | `data/raw_html` | Debug HTML save directory |
| `ScrapingConfig.spider_map()` | `SCRAPING_SPIDER_MAP` | `{amazon-in: amazon_in, flipkart: flipkart}` | Marketplace → spider name |
| `ScrapingConfig.review_spider_map()` | `SCRAPING_REVIEW_SPIDER_MAP` | `{amazon-in: amazon_in_reviews, flipkart: flipkart_reviews}` | Marketplace → review spider |
| `ScrapingConfig.default_max_review_pages()` | `SCRAPING_DEFAULT_MAX_REVIEW_PAGES` | 3 | Review pages per product |
| `ScrapingConfig.proxy_list()` | `SCRAPING_PROXY_LIST` | `[]` | Comma-separated proxy URLs |
| `ScrapingConfig.proxy_ban_cooldown_base()` | `SCRAPING_PROXY_BAN_COOLDOWN_BASE` | 30.0 | Ban backoff base (seconds) |
| `ScrapingConfig.proxy_ban_max_cooldown()` | `SCRAPING_PROXY_BAN_MAX_COOLDOWN` | 600.0 | Max ban backoff (seconds) |
| `MatchingConfig.auto_merge_threshold()` | `MATCHING_AUTO_MERGE_THRESHOLD` | 0.85 | Auto-merge confidence |
| `MatchingConfig.fuzzy_title_threshold()` | `MATCHING_FUZZY_TITLE_THRESHOLD` | 0.80 | Fuzzy match minimum |
| `MatchingConfig.max_candidates()` | `MATCHING_MAX_CANDIDATES` | 500 | Max products to compare |
