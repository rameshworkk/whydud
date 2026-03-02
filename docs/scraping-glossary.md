# Whydud Scraping Glossary

Every term used in the scraping system, explained with examples from our actual codebase.

---

## Core Concepts

### Product (Canonical Product)

The **single, deduplicated representation** of a real-world product in our database. When the same phone is sold on Amazon, Flipkart, and Croma, we don't create 3 products — we create 1 canonical product and link 3 listings to it.

```
Canonical Product: "Samsung Galaxy S24 FE 5G (Mint, 8GB, 256GB)"
  ├── Amazon listing   (ASIN: B0DJK3P7Y2, ₹42,994)
  ├── Flipkart listing (FPID: itm12345abc, ₹41,999)
  └── Croma listing    (SKU: 271234, ₹43,499)
```

**Why "canonical"?** It means the authoritative, master version. Individual marketplace listings may have slightly different titles, images, or descriptions, but the canonical product holds the aggregated truth — best price across all marketplaces, average rating, total reviews, primary images.

**Model:** `apps/products/models.py → Product`

---

### Product Listing

A **per-marketplace entry** for a product. One listing = one product on one marketplace. It holds marketplace-specific data: that marketplace's price, that marketplace's seller, that marketplace's URL.

```
ProductListing:
  marketplace:   Amazon.in
  external_id:   B0FCMJT7R7          (Amazon's ASIN)
  product:       → (linked to canonical Product)
  current_price: 2499800              (₹24,998 in paisa)
  mrp:           2899900              (₹28,999 in paisa)
  seller:        → Darshita Electronics
  url:           https://www.amazon.in/dp/B0FCMJT7R7
  in_stock:      True
```

The unique constraint is `(marketplace, external_id)` — there can only be one Amazon listing with ASIN `B0FCMJT7R7`.

**Model:** `apps/products/models.py → ProductListing`

---

### Listing Page (Search Results Page)

The **search/category page** on a marketplace that shows a grid of products. When you go to Amazon and search "smartphones", the page showing 16-48 product cards is a listing page.

```
Listing Page URL:
  https://www.amazon.in/s?k=smartphones&rh=n%3A1805560031

What the spider sees:
  ┌────────────┐ ┌────────────┐ ┌────────────┐
  │ Product 1  │ │ Product 2  │ │ Product 3  │
  │ Samsung S24│ │ OnePlus 13 │ │ iPhone 16  │
  │ ₹42,994    │ │ ₹59,999    │ │ ₹79,900    │
  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
        │              │              │
        ▼              ▼              ▼
   Product Page   Product Page   Product Page
   (detail)       (detail)       (detail)
```

The spider extracts all product links from a listing page, then follows each link to the product page for full details.

**In our code:** `parse_listing_page()` method in both spiders.

---

### Product Page (Detail Page / PDP)

The **individual product detail page** on a marketplace. This is the page you'd see if you clicked on a specific product — it has the title, full price, images, specs table, seller info, reviews, offers.

```
Product Page URL:
  https://www.amazon.in/dp/B0FCMJT7R7

What the spider extracts:
  - Title: "OnePlus Nord CE5 | MediaTek Dimensity | 128GB 8GB"
  - Price: ₹24,998 (sale) / ₹28,999 (MRP)
  - Brand: OnePlus
  - Images: 7 URLs
  - Rating: 4.4 / 5
  - Specs: {OS: Android 15, Battery: 7100mAh, ...}
  - Seller: Darshita Electronics
  - Stock: In Stock
  - Offers: [bank offers, coupons, EMI]
```

**In our code:** `parse_product_page()` method in both spiders.

---

### Slug

A **URL-friendly version of a name**, using lowercase letters, numbers, and hyphens. No spaces, no special characters. Used in URLs so they're readable and SEO-friendly.

```
Title:  "Samsung Galaxy S24 FE 5G (Mint, 8GB, 256GB)"
Slug:   "samsung-galaxy-s24-fe-5g-mint-8gb-256gb"

URL:    /product/samsung-galaxy-s24-fe-5g-mint-8gb-256gb
        (instead of /product/1847 or /product?id=a7f3b2c1-...)
```

Slugs are auto-generated from titles. If a collision happens (two products generate the same slug), a suffix is added: `-1`, `-2`, etc.

Used for: products, brands, categories, sellers, marketplaces.

**Examples from our DB:**
```
Product slug:     oneplus-nord-ce5-mediatek-dimensity-massive-7100mah-battery
Brand slug:       samsung
Category slug:    smartphones
Marketplace slug: amazon-in
```

---

### External ID

The **marketplace's own identifier** for a product. Every marketplace has its own ID system:

| Marketplace | ID Name | Format | Example |
|-------------|---------|--------|---------|
| Amazon.in | ASIN | 10 alphanumeric chars | `B0FCMJT7R7` |
| Flipkart | FPID | `itm` + alphanumeric | `itm7a3b5c9d2e` |
| Croma | SKU | Numeric | `271234` |

External IDs are how we identify the same listing across scrapes. If we scrape Amazon tomorrow and find ASIN `B0FCMJT7R7` again, we know it's the same listing — update it, don't create a duplicate.

**In our code:** `ProductListing.external_id` field, unique together with `marketplace`.

---

### Crawl / Crawling

The automated process of **visiting web pages and following links** to discover content. A "crawler" (or "spider") starts at seed URLs, extracts links, follows them, extracts data, follows more links, and so on.

```
Crawl flow:

Seed URL (listing page)
  → Visit page, find 16 product links
  → Follow each link to product pages
  → Extract data from each product page
  → Find "Next page" link on listing page
  → Visit page 2, find 16 more product links
  → ... repeat until max pages reached
```

**"Crawled 87 pages"** in the logs means the spider visited 87 URLs total (listing pages + product pages).

---

### Scrape / Scraping

The process of **extracting structured data from a web page**. Crawling is about discovering and visiting pages. Scraping is about pulling specific data fields out of the HTML.

```
Crawling: "I visited 87 pages"
Scraping: "I extracted 68 product items from those pages"

The difference (87 crawled vs 68 scraped):
  - 8 listing pages (crawled but don't produce items)
  - 8 page-2 listing pages (crawled but don't produce items)
  - 3 product pages that timed out (crawled but failed to scrape)
  - 68 product pages successfully scraped
```

**"Scraped 68 items"** means 68 products had their data successfully extracted and passed to the pipeline.

---

### Spider

A **Scrapy class that defines how to crawl a specific website**. Each marketplace gets its own spider with custom logic for that site's HTML structure.

| Spider | Class | Target |
|--------|-------|--------|
| `amazon_in` | `AmazonIndiaSpider` | amazon.in |
| `flipkart` | `FlipkartSpider` | flipkart.com |

A spider defines:
- **Seed URLs** — where to start crawling (8 category search pages)
- **`parse_listing_page()`** — how to extract product links from search results
- **`parse_product_page()`** — how to extract product data from detail pages
- **Selectors** — CSS/XPath rules for finding specific elements on the page

**File locations:**
- `apps/scraping/spiders/amazon_spider.py`
- `apps/scraping/spiders/flipkart_spider.py`
- `apps/scraping/spiders/base_spider.py` (shared anti-detection logic)

---

### Seed URL

The **starting URLs** that a spider begins crawling from. These are hardcoded category search pages that return popular products.

```python
# Amazon spider seed URLs (8 categories)
SEED_CATEGORY_URLS = [
    "https://www.amazon.in/s?k=smartphones&rh=n%3A1805560031",
    "https://www.amazon.in/s?k=laptops&rh=n%3A1375424031",
    "https://www.amazon.in/s?k=headphones&rh=n%3A1388921031",
    "https://www.amazon.in/s?k=air+purifiers&rh=n%3A5131299031",
    "https://www.amazon.in/s?k=washing+machines&rh=n%3A1380365031",
    "https://www.amazon.in/s?k=refrigerators&rh=n%3A1380369031",
    "https://www.amazon.in/s?k=televisions&rh=n%3A1389396031",
    "https://www.amazon.in/s?k=cameras&rh=n%3A1389175031",
]
```

Each seed URL leads to a listing page, which leads to product pages, which leads to pagination (page 2, 3, ...).

---

### Pagination

Following the **"Next" links** on listing pages to get more results. Amazon shows ~16-24 products per page. With `--max-pages 2`, the spider visits page 1 and page 2 of each category, then stops.

```
Category: smartphones
  Page 1 → 33 product links found
  Page 2 → 24 product links found
  Page 3 → STOPPED (max-pages = 2)

Total: 57 product links to visit for this category
```

**In our code:** `MAX_LISTING_PAGES` setting, overridable with `--max-pages` CLI arg.

---

### Pipeline

The **processing chain** that every scraped item passes through before being saved to the database. Think of it like an assembly line — each stage validates, cleans, transforms, or stores the data.

```
Spider yields ProductItem
  ↓
Stage 1: ValidationPipeline     → Drop invalid items
  ↓
Stage 2: NormalizationPipeline  → Clean and normalize fields
  ↓
Stage 3: ProductPipeline        → Save to database
  ↓
Stage 4: MeilisearchPipeline    → Queue for search indexing
```

Items flow through all stages in order. Any stage can drop an item (e.g., validation fails) which prevents it from reaching later stages.

**File:** `apps/scraping/pipelines.py`

---

### Item (ProductItem)

The **structured data object** that a spider yields after scraping a product page. It's a dictionary-like container with predefined fields.

```python
ProductItem = {
    'marketplace_slug': 'amazon_in',
    'external_id':      'B0FCMJT7R7',
    'url':              'https://www.amazon.in/dp/B0FCMJT7R7',
    'title':            'OnePlus Nord CE5 | MediaTek Dimensity | 128GB 8GB',
    'brand':            'OnePlus',
    'price':            Decimal('2499800'),     # ₹24,998 in paisa
    'mrp':              Decimal('2899900'),     # ₹28,999 in paisa
    'images':           ['https://m.media-amazon.com/images/...', ...],
    'rating':           Decimal('4.4'),
    'review_count':     None,
    'specs':            {'OS': 'Android 15', 'Battery': '7100mAh', ...},
    'seller_name':      'Darshita Electronics',
    'in_stock':         True,
    'offer_details':    [],
    'about_bullets':    ['Flagship-class Performance with...', ...],
}
```

A spider yields items. The pipeline consumes items.

**File:** `apps/scraping/items.py`

---

### Index / Indexing

**Adding product data to Meilisearch** (the search engine) so users can search for products on the website. "Indexing" means converting a database record into a searchable document.

```
Database (PostgreSQL)              Search Engine (Meilisearch)
┌─────────────────────┐            ┌─────────────────────┐
│ Product table       │  ──sync──▶ │ "products" index    │
│ 425 rows            │            │ 425 documents       │
│ Full relational data│            │ Optimized for search│
└─────────────────────┘            └─────────────────────┘

User searches "samsung phone under 30000"
  → Meilisearch searches its index (fast, typo-tolerant)
  → Returns matching product IDs
  → Django fetches full details from PostgreSQL
```

**Two sync modes:**
- **Incremental:** After each scrape, only re-index products that were touched
- **Full reindex:** Nightly at 01:00 UTC, rebuild the entire index

**Command:** `python manage.py sync_meilisearch`

---

### Selector (CSS Selector / XPath)

The **rules used to find specific elements** on a web page. Like an address that tells the spider exactly where to find the price, title, or images in the HTML.

```html
<!-- Amazon product page HTML -->
<span id="productTitle" class="a-size-large">
  Samsung Galaxy S24 FE 5G (Mint, 8GB, 256GB)
</span>

<span class="a-price-whole">42,994</span>
```

```python
# CSS Selectors to extract data
title = response.css('#productTitle::text').get()           # "Samsung Galaxy S24 FE 5G..."
price = response.css('.a-price-whole::text').get()           # "42,994"

# XPath (alternative syntax, same purpose)
title = response.xpath('//span[@id="productTitle"]/text()').get()
```

Amazon and Flipkart frequently change their HTML structure, so our spiders have **multiple fallback selectors** — if the first one fails, try the next.

---

### Playwright / JS Rendering

**A headless browser** that renders JavaScript before the spider extracts data. Many modern websites (including Amazon and Flipkart) load prices, availability, and images via JavaScript after the initial HTML loads. Plain HTTP requests would get incomplete pages.

```
Without Playwright (plain HTTP):
  GET amazon.in/dp/B0FCMJT7R7
  → HTML arrives, but price div is empty (JS hasn't run yet)
  → Spider sees: price = None ❌

With Playwright (headless Chromium):
  GET amazon.in/dp/B0FCMJT7R7
  → HTML arrives
  → Playwright runs JavaScript in a real browser
  → Waits for price to appear in the DOM
  → Spider sees: price = ₹24,998 ✅
```

**Trade-off:** Playwright is slower (5-15 seconds per page vs <1 second for plain HTTP) and uses more RAM (headless Chromium). But it's necessary for accurate data extraction.

---

### Robots.txt

A file at the root of every website (`amazon.in/robots.txt`) that tells crawlers which pages they're **allowed or disallowed** from visiting. Our spiders obey robots.txt (`ROBOTSTXT_OBEY = True`).

```
# Example robots.txt
User-agent: *
Disallow: /gp/cart/
Disallow: /ap/signin
Allow: /s?k=
Allow: /dp/
```

This means: don't crawl cart or sign-in pages, but search results and product pages are fine.

---

### User-Agent

A **string that identifies the browser/client** making the request. Websites use it to detect bots. Our spiders rotate through 10 realistic User-Agent strings to avoid being blocked.

```
# What a real browser sends:
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0

# What a bot sends (gets blocked):
User-Agent: Scrapy/2.14.1

# Our spider sends (rotated randomly):
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) ... Firefox/126.0
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) ... Edg/125.0.0.0
# ... 10 total, picked randomly per request
```

---

### Download Delay

A **pause between requests** to avoid overloading the target website (and getting IP-banned). Our spiders wait 2-5 seconds between each page load.

```
Settings:
  DOWNLOAD_DELAY = 2                      # Base: 2 seconds
  RANDOMIZE_DOWNLOAD_DELAY = True         # Adds 0-1s random jitter
  CONCURRENT_REQUESTS_PER_DOMAIN = 2      # Max 2 pages loading at once

Result: 2-5 seconds between requests, 2 in parallel = ~24-60 pages per minute
```

This is "respectful crawling" — fast enough to be useful, slow enough to not be a burden.

---

### Timeout

The **maximum time to wait** for a page to load before giving up. Amazon product pages are heavy with JavaScript — sometimes they take forever.

```
DOWNLOAD_TIMEOUT = 30   # 30 seconds per page

What happens on timeout:
  Spider requests: amazon.in/dp/B0F1D9LCK3
  Playwright starts loading...
  ... 30 seconds pass, page still loading ...
  TimeoutError! Page dropped.
  Spider moves on to the next product.
  spider.items_failed += 1
```

From our test scrape: 114 out of ~280 product pages timed out. This is normal for Amazon — some pages are slow, some get rate-limited. The spider handles it gracefully and continues.

---

## Matching & Deduplication Terms

### Product Matching

The process of determining whether a newly scraped item is the **same real-world product** as something already in our database. This is how we avoid duplicates and link listings across marketplaces.

```
Spider scrapes from Amazon:
  "Samsung Galaxy S24 FE 5G (Mint, 8GB, 256GB)" — ASIN B0DJK3P7Y2

We already have from Flipkart:
  "SAMSUNG Galaxy S24 FE 5G (Mint, 8 GB RAM, 256 GB)" — FPID itm12345abc

Matching engine says: these are the same product (confidence 0.95)
  → Link Amazon listing to existing canonical product
  → DON'T create a duplicate
```

**File:** `apps/products/matching.py`

---

### Match Confidence

A **score from 0.0 to 1.0** indicating how certain the matching engine is that two items are the same product.

| Confidence | Meaning | Action |
|-----------|---------|--------|
| 1.00 | Exact EAN/barcode match | Auto-merge |
| 0.95 | Brand + model + storage + RAM + color all match | Auto-merge |
| 0.85 | Brand + model match, variant differs (different color/storage) | Auto-merge |
| 0.70 | Fuzzy title similarity ≥ 80% | Auto-merge (cautious) |
| < 0.60 | No good match found | Create new product |

---

### Match Method

**How the match was found.** Stored on the listing for debugging and analytics.

```
method="ean"                  → Barcode matched exactly
method="brand_model_variant"  → Brand + model + storage/RAM/color matched
method="brand_model"          → Brand + model matched (variant differs)
method="fuzzy_title"          → Title similarity was high enough
method=None                   → No match, created new product
```

Example from logs:
```
Matched 'Magnetic Shelf for Washing Machine...' → product magnetic-shelf-...
  (confidence=0.95, method=brand_model_variant)
```

---

### EAN / GTIN / UPC / Barcode

**Universal product identifiers** — standardized numbers printed on product barcodes worldwide. If two listings share the same EAN, they are guaranteed to be the same product.

```
EAN-13:  8901234567890     (European Article Number, 13 digits)
GTIN-14: 08901234567890    (Global Trade Item Number, 14 digits)
UPC-A:   012345678905      (Universal Product Code, 12 digits, US-focused)
```

Our matching engine checks specs for keys like `ean`, `ean13`, `gtin`, `upc`, `barcode`, `item model number`. If found and matched, confidence = 1.0 (highest possible).

---

### ASIN

**Amazon Standard Identification Number.** Amazon's proprietary product ID. 10 alphanumeric characters.

```
ASIN: B0FCMJT7R7

Found in URLs:
  https://www.amazon.in/dp/B0FCMJT7R7
  https://www.amazon.in/gp/product/B0FCMJT7R7

Extracted by regex:
  /(?:dp|gp/product)/([A-Z0-9]{10})
```

ASINs are unique within a marketplace (Amazon.in) but the same ASIN can mean different products on Amazon.com vs Amazon.in.

---

### FPID

**Flipkart Product ID.** Flipkart's proprietary product identifier. Starts with `itm` followed by alphanumeric characters.

```
FPID: itm7a3b5c9d2e

Found in URLs:
  https://www.flipkart.com/samsung-galaxy-s24/p/itm7a3b5c9d2e

Extracted by regex:
  /p/(itm[a-zA-Z0-9]+)
```

---

### Brand Alias

A mapping between **variant brand names** and the canonical brand. Manufacturers are referred to by different names on different marketplaces.

```
Brand aliases (stored in Brand.aliases JSONField):

Brand "Xiaomi":
  aliases: ["MI", "Mi", "Redmi by Xiaomi", "Poco by Xiaomi"]

Brand "Samsung":
  aliases: ["SAMSUNG", "Samsung Electronics"]

Brand "boAt":
  aliases: ["boat", "BOAT", "Boat Lifestyle"]
```

When the spider scrapes `brand: "MI"`, the pipeline's `resolve_or_create_brand()` checks aliases and maps it to the existing "Xiaomi" brand instead of creating a duplicate.

---

## Data Storage Terms

### Price Snapshot

A **point-in-time recording** of a product's price on a specific marketplace. Every time we scrape a product, we record a new snapshot — even if the price hasn't changed.

```
price_snapshots table (TimescaleDB hypertable):

time                  | listing_id | price    | mrp      | in_stock | seller_name
2026-02-27 00:15:00   | 42         | 2499800  | 2899900  | true     | Darshita Electronics
2026-02-27 06:15:00   | 42         | 2499800  | 2899900  | true     | Darshita Electronics
2026-02-27 12:15:00   | 42         | 2299900  | 2899900  | true     | Amazon.in    ← price dropped!
2026-02-27 18:15:00   | 42         | 2299900  | 2899900  | false    | Amazon.in    ← out of stock!
```

This enables price history charts, "lowest price ever" tracking, flash sale detection, and stock availability history.

---

### Hypertable

A **TimescaleDB concept** — a regular PostgreSQL table that's been converted into a time-series optimized table. Under the hood, TimescaleDB automatically partitions the data by time into "chunks" for fast queries.

```
Regular table:
  SELECT * FROM prices WHERE time > '2026-01-01'
  → Scans entire table (slow with millions of rows)

Hypertable:
  SELECT * FROM price_snapshots WHERE time > '2026-01-01'
  → Only scans recent chunks (fast, skips old data)
```

Our hypertables:
- `price_snapshots` — partitioned by `time`, compressed after 30 days
- `scoring.dudscore_history` — partitioned by `time`

---

### Continuous Aggregate

A **pre-computed summary** that TimescaleDB maintains automatically. Instead of calculating daily min/max/avg prices on every query, the database keeps a materialized view that refreshes hourly.

```
price_daily (continuous aggregate):

day        | product_id | marketplace_id | min_price | max_price | avg_price | open | close
2026-02-26 | 42         | 1              | 2299900   | 2499800   | 2399850   | ...  | ...
2026-02-27 | 42         | 1              | 2299900   | 2299900   | 2299900   | ...  | ...
```

Refreshed hourly via TimescaleDB policy. Used for price history charts without querying millions of raw snapshots.

---

### Paisa

The **subunit of the Indian Rupee (₹)**. 1 Rupee = 100 paisa. All prices in our database are stored in paisa to avoid floating-point precision issues.

```
Display:    ₹24,998.00
Storage:    2499800        (integer, in paisa)
Formula:    price_in_rupees = price_in_paisa / 100

Why not store ₹24,998.00 as a float?
  → 0.1 + 0.2 = 0.30000000000000004 in floating point
  → Financial math needs exact precision
  → Integer paisa: 10 + 20 = 30 (always exact)
```

---

## Scraping Infrastructure Terms

### Scrapy

The **Python web crawling framework** we use. It provides the foundation: request scheduling, download management, middleware chain, pipeline system, retry logic, robots.txt handling, and statistics.

Our code plugs into Scrapy's architecture:
- Spiders → define what to crawl and how to parse
- Pipelines → define what to do with scraped items
- Settings → configure behavior (delays, concurrency, etc.)
- Middlewares → modify requests/responses (User-Agent rotation, etc.)

---

### Celery

A **distributed task queue** for Python. It lets us run background jobs (like scraping) outside the web request cycle. Tasks are sent to Redis (the broker), and Celery workers pick them up and execute them.

```
Django app                Redis (broker)           Celery Worker
    │                         │                         │
    │ run_spider.delay()      │                         │
    ├────────────────────────▶│                         │
    │                         │  worker picks up task   │
    │                         ├────────────────────────▶│
    │                         │                         │ runs subprocess
    │                         │                         │ (Scrapy spider)
    │                         │                         │
    │                         │  task result            │
    │                         │◀────────────────────────┤
```

---

### Celery Beat

A **scheduler** that triggers Celery tasks on a cron-like schedule. It's the "alarm clock" that says "run Amazon spider at 00:00, 06:00, 12:00, 18:00 UTC."

```
Celery Beat process (always running)
  │
  ├── Every 6h (0,6,12,18 UTC): run_marketplace_spider("amazon-in")
  ├── Every 6h (3,9,15,21 UTC): run_marketplace_spider("flipkart")
  ├── Every 4h: check_price_alerts()
  ├── Every 2h: detect_deals()
  ├── Daily 01:00: full_reindex()
  └── Monthly 1st 03:00: recalculate_dudscores()
```

---

### Flower

A **web-based monitoring tool** for Celery. Shows active tasks, completed tasks, failed tasks, worker status, and task history.

```
http://localhost:5555 (dev)
https://whydud.com/flower/ (prod)

Shows:
  ┌─────────────────────────────────────────────┐
  │ Active Tasks                                 │
  │ run_marketplace_spider[amazon-in]  STARTED   │
  │                                              │
  │ Recent Tasks                                 │
  │ sync_products_to_meilisearch      SUCCESS    │
  │ check_price_alerts                SUCCESS    │
  └─────────────────────────────────────────────┘
```

**Limitation:** Flower only shows Celery tasks. The actual Scrapy spider runs as a subprocess inside the task, so the per-item scraping work is invisible to Flower.

---

### ScraperJob

A **database record** that tracks the status and results of a scraping run. Created by the Celery task wrapper, not by the CLI runner.

```
ScraperJob:
  id:             a7f3b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c
  spider_name:    amazon_in
  status:         COMPLETED       (QUEUED → RUNNING → COMPLETED)
  started_at:     2026-02-27 00:13:19
  finished_at:    2026-02-27 01:02:45
  items_scraped:  115
  items_failed:   17
  triggered_by:   scheduled
```

---

### Marketplace

A **source website** we scrape from. Each marketplace has its own spider, its own product IDs, and its own URL patterns.

```
Marketplace records in our DB:

| slug      | name       | base_url                    |
|-----------|------------|-----------------------------|
| amazon-in | Amazon.in  | https://www.amazon.in       |
| flipkart  | Flipkart   | https://www.flipkart.com    |
| croma     | Croma      | https://www.croma.com       |
```

---

### Seller

A **third-party or first-party seller** on a marketplace. Products on Amazon/Flipkart are often sold by multiple sellers at different prices.

```
Seller:
  name:           Darshita Electronics
  marketplace:    Amazon.in
  external_id:    A3EXAMPLE123         (Amazon's seller ID)
  rating:         4.2
```

The pipeline creates/updates Seller records during scraping. Used for seller trust analysis and DudScore calculation.

---

## Log Output Terms

### "Crawled X pages (at Y pages/min)"

Scrapy's periodic status line. Shows total pages visited and current crawling speed.

```
Crawled 87 pages (at 11 pages/min), scraped 68 items (at 11 items/min)
         │                                    │
         │ Total URLs visited                 │ Total ProductItems yielded
         │ (listing pages + product pages)    │ (successfully extracted)
```

The gap between crawled and scraped is normal:
- Listing pages are crawled but don't produce items
- Some product pages timeout or fail extraction

---

### "Created new canonical product: ..."

The matching engine found **no existing product** that matches this item. A brand new Product record was created.

```
Created new canonical product: oneplus-nord-ce5-mediatek-dimensity-...
                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                               This is the slug of the new product
```

---

### "Created listing: B0FCMJT7R7 on amazon_in"

A new **ProductListing** was created linking an external ID to a canonical product on a specific marketplace.

```
Created listing: B0FCMJT7R7 on amazon_in
                 ^^^^^^^^^^^    ^^^^^^^^^
                 ASIN           marketplace slug
```

---

### "Matched 'Title...' → product slug (confidence=X, method=Y)"

The matching engine found an **existing product** that matches this item. No new product created — the listing was linked to the existing one.

```
Matched 'Magnetic Shelf for Washing Machine...' → product magnetic-shelf-for-washing-machine-for-w
  (confidence=0.95, method=brand_model_variant)
   ^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   How certain       How the match was determined
```

---

### "Closing page due to failed request"

A Playwright **timeout or network error** occurred while loading a product page. The spider skips this product and moves on.

```
Closing page due to failed request:
  <GET https://www.amazon.in/dp/B0F1D9LCK3>
  exc_type=TimeoutError
  exc_msg=Page.goto: Timeout 30000ms exceeded.
```

This is expected — Amazon pages are heavy, and some don't load within 30 seconds. The spider handles it gracefully.

---

### "Found X results on URL"

The listing page parser successfully extracted **X product links** from a search results page.

```
Found 33 results on https://www.amazon.in/s?k=smartphones&rh=n%3A1805560031
      ^^
      33 product page URLs to follow
```

---

## Scrapy Stats (End of Run)

At the end of a spider run, Scrapy dumps a full statistics summary:

```
'downloader/request_count': 287,        # Total HTTP requests made
'downloader/response_count': 173,       # Successful responses received
'item_scraped_count': 115,              # ProductItems that passed all pipelines
'item_dropped_count': 3,               # Items dropped by ValidationPipeline
'finish_reason': 'finished',           # Why the spider stopped (finished = normal)
'elapsed_time_seconds': 2926.45,       # Total runtime
'scheduler/enqueued': 287,              # URLs queued for crawling
'scheduler/dequeued': 287,              # URLs actually crawled
'retry/count': 12,                      # Retried requests (5xx, 429, timeout)
'playwright/page_count': 173,           # Playwright pages opened
```
