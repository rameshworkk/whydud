# WHYDUD — Backfill Pipeline: Complete Implementation Plan


> **This is the SINGLE SOURCE OF TRUTH for the price history backfill system.**
>
> **What it does:** Discovers 17M+ Indian e-commerce products from external price tracker
> platforms, harvests years of historical price data, creates functional product records
> immediately, enriches them with full marketplace details on a tiered priority system,
> and scrapes reviews + calculates DudScore for the top 100K products.
>
> **Current state:** 28,735 BackfillProduct records exist. 27,625 in Discovered status,
> 53 with PH Extended (price history fetched), 153 Done, 904 Failed. 72,570 price snapshots
> injected (34K from BuyHatke, 34K from PriceHistory.app, 4K from own scraper). 28,540
> products have scrape_status=pending (never scraped from marketplace).
>
> **What this plan covers:**
> 1. Scaling discovery+history to 50K+ products/day via async concurrency
> 2. Creating lightweight Product records directly from tracker data (no marketplace scrape)
> 3. Tiered enrichment: Playwright for high-priority, curl_cffi for rest
> 4. Priority assignment based on tracker signals
> 5. Pipeline hooks to close the enrichment loop
> 6. Review scraping + DudScore calculation for top 100K products
> 7. Multi-node worker setup with DataImpulse session routing
> 8. Proxy bandwidth optimization
>
> **18 Claude Code prompts across 8 sessions. ~7-9 hours total.**

---

## TABLE OF CONTENTS

```
PART 1: CONCEPTS (Read first — explains WHY before HOW)
  1.1  The Five-Phase Pipeline
  1.2  Why Lightweight Records Change Everything
  1.3  Tiered Enrichment Strategy
  1.4  Priority Scoring from Tracker Signals
  1.5  How Enrichment Status Gets Updated (Pipeline Hook)
  1.6  Review Scraping Chain (Top 100K Products)
  1.7  DataImpulse Session Routing for Multi-Worker
  1.8  Bandwidth Budget (Including Reviews)

PART 2: MODEL & SCHEMA CHANGES
  2.1  BackfillProduct additions (enrichment + review fields)
  2.2  Product model: is_lightweight flag
  2.3  price_snapshots: source column in existing pipeline

PART 3: CLAUDE CODE PROMPTS (BF-1 through BF-18)
  Session 1:  BF-1, BF-2   — Model changes + async source framework
  Session 2:  BF-3, BF-4   — Async runner + management command upgrades
  Session 3:  BF-5, BF-6   — Source implementations (post-recon)
  Session 4:  BF-7, BF-8   — Lightweight record creator + fast injection
  Session 5:  BF-9, BF-10  — Priority assigner + pipeline hook
  Session 6:  BF-11, BF-12 — Tiered enrichment worker + curl_cffi extractor
  Session 7:  BF-13, BF-14 — Review scraping chain + DudScore trigger
  Session 8:  BF-15, BF-16 — Multi-node proxy config + worker setup
  Session 9:  BF-17, BF-18 — Frontend handling + monitoring + utilities

PART 4: EXECUTION PLAYBOOK
  Phase A:  recon 
  Phase B:  Discovery + history at scale
  Phase C:  Lightweight records + injection
  Phase D:  Overnight enrichment runs
  Phase E:  Review scraping for top 100K
  Phase F:  Scale to 17M
```

---

# PART 1: CONCEPTS

## 1.1 The Five-Phase Pipeline

```
PHASE 1: DISCOVER                    PHASE 2: FETCH HISTORY
┌──────────────────────┐            ┌──────────────────────┐
│ Crawl tracker sites: │            │ For each discovered  │
│ - PriceHistory.app   │            │ product, call the    │
│ - BuyHatke           │            │ tracker's chart API  │
│ - PriceBefore.com    │            │ to get full price    │
│                      │───────────→│ timeseries.          │
│ Extract:             │            │                      │
│ - Product title      │            │ Store as JSONB in    │
│ - Amazon/FK URL      │            │ backfill_products    │
│ - ASIN / Flipkart PID│           │ .price_data column.  │
│ - Current price      │            │                      │
│ - Category, image    │            │ 200-500 data points  │
│                      │            │ per product typical. │
└──────────────────────┘            └──────────┬───────────┘
                                               │
PHASE 3: CREATE + INJECT                       │
┌──────────────────────┐                       │
│ From tracker data    │←──────────────────────┘
│ alone, create:       │
│                      │            PHASE 4: ENRICH (background)
│ 1. Product record    │            ┌──────────────────────┐
│ 2. ProductListing    │            │ Scrape Amazon/FK for │
│ 3. Bulk INSERT all   │            │ full details:        │
│    price_snapshots   │            │                      │
│                      │            │ P0-P1: Playwright    │
│ Product is LIVE on   │───────────→│   (full images,      │
│ site immediately     │            │    specs, variants)  │
│ with price chart.    │            │                      │
│                      │            │ P2-P3: curl_cffi     │
│ Missing: full images,│            │   (specs, rating,    │
│ specs, reviews,      │            │    MRP, 1 image)     │
│ DudScore             │            │                      │
└──────────────────────┘            └──────────┬───────────┘
                                               │
                                    PHASE 5: REVIEWS + DUDSCORE
                                    ┌──────────────────────┐
                                    │ For top 100K products│
                                    │ (after detail enrich):│
                                    │                      │
                                    │ 1. Run review spider │
                                    │    (existing amazon_ │
                                    │     in_reviews /     │
                                    │     flipkart_reviews)│
                                    │                      │
                                    │ 2. 10-30 reviews per │
                                    │    product scraped   │
                                    │                      │
                                    │ 3. Trigger DudScore  │
                                    │    recalculation     │
                                    │                      │
                                    │ Product is now FULLY │
                                    │ COMPLETE with trust  │
                                    │ signals              │
                                    └──────────────────────┘
```

**Phases 1-3 are the FAST PATH.** They run on asyncio, hit free tracker APIs,
cost zero in proxy bandwidth, and can process 50K+ products in 2-3 hours.
After Phase 3, products are usable on the site with price history charts.

**Phase 4 is the SLOW PATH.** It scrapes actual marketplaces (Amazon, Flipkart),
costs proxy bandwidth, and runs at whatever speed your budget supports. It fills
in the gaps: full image galleries, specs tables, seller info.

**Phase 5 is the TRUST PATH.** It scrapes reviews and triggers DudScore for
the top 100K products. Without reviews, there's no DudScore (Whydud's core
differentiator). Reviews can ONLY be scraped after Phase 4 because the
review spiders need a valid ProductListing with an external_id (ASIN/PID).

---

## 1.2 Why Lightweight Records Change Everything

The original pipeline required scraping Amazon/Flipkart BEFORE injecting price
history. At 3-5 seconds per Playwright page load, 50K products = 42-70 hours.
With residential proxies at $0.70/GB, that's ~$220 just for the scraping.

Lightweight records flip this: create Product records from tracker data (free,
instant), inject price history immediately, then scrape marketplace details later.

**What a lightweight record contains (from tracker data, zero scraping):**

```
Product:
  title               "Apple iPhone 16 (Pink, 128 GB)"     ← from tracker
  slug                "apple-iphone-16-pink-128gb-a3f8"     ← generated
  current_best_price  6499900 (₹64,999 in paisa)           ← from tracker
  mrp                 7990000 (₹79,900)                     ← from tracker
  category            "Smartphones" (matched from tracker)  ← from tracker
  images              ["https://tracker/thumb.jpg"]         ← 1 thumbnail
  brand               "Apple" (parsed from title)           ← extracted
  avg_rating          NULL                                  ← needs enrichment
  dud_score           NULL                                  ← needs reviews
  total_reviews       0                                     ← needs reviews
  specs               {}                                    ← needs enrichment

ProductListing:
  marketplace         Amazon India                          ← from tracker URL
  external_id         "B0CX23GFMV"                         ← parsed from URL
  external_url        "https://www.amazon.in/dp/B0CX..."   ← from tracker
  current_price       6499900                               ← from tracker
  in_stock            true                                  ← from tracker

price_snapshots:
  200-500 rows of historical price data                     ← from tracker API
  Spanning months to years                                  ← the treasure
```

**What's missing until detail enrichment (Phase 4):**
```
  Full image gallery (6-8 high-res images)
  Specs / technical details JSON
  About / description bullets
  Seller name + rating + fulfilled_by
  Review count + average rating
  Variant options (color, storage)
  Bank offers / coupons
```

**What's missing until review enrichment (Phase 5):**
```
  Individual review text, ratings, dates
  Review credibility signals (verified purchase, helpful votes)
  DudScore (needs reviews for sentiment, rating quality, credibility)
  Fake review detection flags
```

**A product page with a title, price, one image, a marketplace link, and a 2-year
price history chart is already useful.** Users can see if now is a good time to buy
and click through to purchase. The rest is progressive enhancement.

---

## 1.3 Tiered Enrichment Strategy

Not all 17M products deserve a Playwright browser session. The enrichment worker
routes each product to the cheapest extraction method that gets enough data:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENRICHMENT ROUTING                            │
│                                                                  │
│  Priority 0 (on-demand):  User visited product page              │
│  Priority 1 (first night): Top categories + brands               │
│      │                                                           │
│      ├──→ PLAYWRIGHT (full scrape)                               │
│      │    - Launches headless Chrome via scrapy-playwright        │
│      │    - Gets: everything (images, specs, seller, offers)     │
│      │    - Cost: ~500KB bandwidth, 3-5 seconds                  │
│      │    - Uses existing Amazon/Flipkart spider infrastructure  │
│      │    - THEN: chains to review scraping if top 100K          │
│      │    - THEN: triggers DudScore calculation after reviews    │
│      │                                                           │
│  Priority 2 (second night): Mid-value products                   │
│  Priority 3 (background): Long tail                              │
│      │                                                           │
│      ├──→ CURL_CFFI (HTTP only, no browser)                      │
│      │    - Chrome TLS fingerprint impersonation                 │
│      │    - Gets: title, brand, price, MRP, specs, about,       │
│      │            rating, review count, seller, 1 image          │
│      │    - MISSES: full image gallery, variants, bank offers    │
│      │    - Cost: ~50KB bandwidth, 0.3 seconds                   │
│      │    - 10x cheaper and faster than Playwright               │
│      │    - NO review scraping (not in top 100K)                 │
│      │                                                           │
│  Not enriched: Products nobody has viewed                        │
│      │                                                           │
│      └──→ SKIP (enrich on-demand when visited)                   │
│           - Stays as lightweight record with price chart         │
│           - Gets enriched via P0 trigger if user visits          │
└─────────────────────────────────────────────────────────────────┘
```

**What Amazon.in serves in JSON-LD (available via curl_cffi without JS):**
  - Product name, brand, 1 image, price, currency, stock status
  - Rating value + review count (sometimes)
  - Seller name (sometimes)

**What Amazon.in serves in HTML body (also available via curl_cffi):**
  - MRP (strikethrough price element)
  - Specs table (#productDetails rows)
  - About bullets (#feature-bullets)
  - Seller name + fulfilled_by (#merchant-info)
  - ASIN (hidden input)

**What ONLY Playwright can get (requires JavaScript execution):**
  - Full image gallery (colorImages JS object)
  - Variant matrix (twister JS data)
  - Bank offers/coupons (JS-rendered widget)
  - Delivery estimates (AJAX post-load)
  - EMI options (lazy-loaded)

**Why curl_cffi sometimes fails:**
  Amazon's bot detection has 4 layers: TLS fingerprint, JS execution, browser
  fingerprint, and IP reputation. curl_cffi passes TLS (layer 1) but fails JS
  (layer 2). When Amazon doesn't require JS challenge (depends on IP reputation
  and time of day), curl_cffi gets the full page. Success rate ~55% through
  residential proxy, higher during off-peak hours (IST midnight-6am).

---

## 1.4 Priority Scoring from Tracker Signals

Before enrichment, every product gets a priority (0-3) based on signals available
from the tracker data — no marketplace scraping needed.

**Signal 1: price_data_points (strongest proxy for popularity)**
Trackers track popular products longer. 500+ data points = bestseller tracked daily
for 1.5+ years. 50 data points = niche or recently added.

**Signal 2: Category (from tracker's categorization)**
Electronics categories drive 80% of price tracking traffic in India.
  Tier 1: Smartphones, Laptops, Headphones, TVs, Tablets, Smartwatches
  Tier 2: Refrigerators, Washing Machines, ACs, Air Purifiers, Cameras
  Tier 3: Kitchen, Fashion, Books, Groceries — low price tracking intent

**Signal 3: Brand (parsed from title string)**
Apple, Samsung, OnePlus products get viewed 10x more than unknown brands.
Simple regex on title: if title starts with a top-20 brand name, bump priority.

**Signal 4: Price bracket**
₹10K-₹2L = highest research intent (phones, laptops, appliances).
<₹2K = nobody researches a ₹500 cable. >₹2L = niche/premium.

**Signal 5: Post-launch behavioral (available after products go live)**
Page views, search impressions, wishlist adds, price alert creation, affiliate
click-throughs. Any user interaction bumps the product to P0/P1.

**Assignment:**
```
P1 (~10-15%):  price_data_points >= 200
            OR category is Tier 1
            OR brand is top-10 AND price > ₹10,000
            OR has any user interaction (post-launch)

P2 (~25-30%):  price_data_points >= 50
            OR price between ₹5,000 and ₹2,00,000
            OR marketplace is Amazon (higher traffic than Flipkart)

P3 (rest):     everything else
```

**Review targeting (separate from enrichment priority):**
```
Top 100K products get reviews. Selection criteria:
  1. All P1 products (typically 50-70K)
  2. Top P2 products by price_data_points (fill to 100K)
```

---

## 1.5 How Enrichment Status Gets Updated (Pipeline Hook)

The backfill system and the scraping pipeline are separate codebases. When an
enrichment task calls `scrape_product_adhoc()`, the existing Amazon/Flipkart
spider runs, the ProductPipeline creates/updates a ProductListing, but nobody
tells the BackfillProduct record that enrichment is done.

**Solution:** Add one method to ProductPipeline.process_item() that checks if the
just-scraped listing matches a BackfillProduct and updates its scrape_status.
If the product is also marked for review scraping, it chains the review spider.

```
Spider finishes scraping ASIN B0CX23GFMV
  → ProductPipeline.process_item() runs
    → Creates/updates ProductListing (existing behavior)
    → NEW: _close_backfill_loop() runs
      → Queries: BackfillProduct WHERE external_id='B0CX23GFMV'
                 AND scrape_status IN ('pending', 'enriching')
      → Updates: scrape_status = 'scraped', product_listing = listing
      → If review_status = 'pending': chains queue_review_scraping task
      → Single indexed query, <1ms, no impact on normal scraping
```

This is the ONLY mechanism that closes the enrichment loop. Without it,
BackfillProduct records stay in 'enriching' forever.

The try/except wrapper ensures that if the backfill module doesn't exist or the
table hasn't been migrated, normal scraping is completely unaffected.

---

## 1.6 Review Scraping Chain (Top 100K Products)

Reviews can only be scraped AFTER detail enrichment because:
  1. Review spiders need the ASIN/PID (from ProductListing.external_id)
  2. Reviews are linked to ProductListing via listing_id
  3. DudScore needs both product details AND reviews

**The chain:**
```
Detail enrichment completes (scrape_status = 'scraped')
    │
    ├─ Is review_status = 'pending'?
    │      │
    │     yes → queue_review_scraping.delay(listing_id, marketplace_slug, external_id)
    │              │
    │              ├─ amazon-in → run existing amazon_in_reviews spider
    │              │               (scrapes /product-reviews/{ASIN}/ pages)
    │              │               (gets 10-30 reviews per product, 3 pages)
    │              │
    │              └─ flipkart → run existing flipkart_reviews spider
    │                             (Playwright + scroll for review section)
    │              │
    │              ↓
    │         ReviewPersistencePipeline saves reviews
    │              │
    │              ↓
    │         post_review_enrichment.delay(product_id)
    │              │
    │              ├─ Update Product.total_reviews, avg_rating
    │              ├─ Update BackfillProduct.review_status = 'scraped'
    │              ├─ Run detect_fake_reviews(product_id)
    │              └─ Run recalculate_dudscore(product_id)
    │              │
    │              ↓
    │         Product is FULLY COMPLETE ✅
    │         (price chart + images + specs + reviews + DudScore)
    │
    └─ no → Product is done without reviews
            (still has price chart, images, specs from enrichment)
```

**Bandwidth for reviews:**
  Per product: 3 review pages × ~200KB = ~600KB
  With 80% success rate: ~750KB per product
  100K products × 750KB = 75 GB
  At $0.70/GB = ~$53 (₹4,400)

---

## 1.7 DataImpulse Session Routing for Multi-Worker

DataImpulse is a rotating residential proxy. Single gateway endpoint,
every request gets a random IP. For session stickiness (listing
page + product pages use same IP), you append a session ID to the username:

```
Regular (rotating every request):
  username: customer_abc
  password: xyz123

Sticky session (same IP for ~10-30 minutes):
  username: customer_abc-session-{worker_id}_{listing_hash}
  password: xyz123
```

Each Celery worker gets a unique CELERY_WORKER_ID env var:
  Oracle worker 1:  CELERY_WORKER_ID=oracle-w1
  Oracle worker 2:  CELERY_WORKER_ID=oracle-w2
  OCI free node:    CELERY_WORKER_ID=oci-w1
  GCP free node:    CELERY_WORKER_ID=gcp-w1

At runtime:
  oracle-w1 scraping iPhone listing → session: oracle-w1_a3f8b2c1 → IP 103.42.x.x
  oracle-w2 scraping Samsung listing → session: oracle-w2_7d2e9f4a → IP 49.207.x.x
  oci-w1 scraping Laptop listing → session: oci-w1_e5c1d8b3 → IP 182.73.x.x

Three simultaneous scrapes, three different residential IPs, each with
internal consistency (listing + child pages through same IP).

---

## 1.8 Bandwidth Budget (Including Reviews)

**Scenario C (recommended): 2.5M enriched, 100K with reviews, 14.5M lightweight**

```
                           Products     Bandwidth     Cost ($0.70/GB)
Detail (Playwright P1):    500K         312 GB        $219
Detail (curl_cffi P2):     2M           100 GB        $70
Reviews (top 100K):        100K         75 GB         $53
Skip (14.5M):              14.5M        0             $0
─────────────────────────────────────────────────────────────
Total one-time:                         487 GB        $342 (₹28,700)

Ongoing (new products):    ~1K-5K/day   ~1-2 GB/day   ~$1-2/day
Monthly ongoing:                                       ~$45 (₹3,800)
```

---

# PART 2: MODEL & SCHEMA CHANGES

## 2.1 BackfillProduct Additions

The model already exists with these status-tracking fields:
  - `status`: Discovered → PH Extended → Done → Failed (backfill lifecycle)
  - `scrape_status`: pending → scraped → failed (marketplace enrichment lifecycle)

**New fields needed:**

```python
# Enrichment routing
enrichment_priority = models.SmallIntegerField(
    default=3,
    db_index=True,
    help_text="0=on-demand, 1=high(Playwright), 2=mid(curl_cffi), 3=low(curl_cffi)"
)
enrichment_method = models.CharField(
    max_length=20, default='pending',
    choices=[('pending','Pending'), ('playwright','Playwright'),
             ('curl_cffi','curl_cffi'), ('skipped','Skipped')],
    help_text="Which extraction method was used"
)
enrichment_queued_at = models.DateTimeField(null=True, blank=True)

# Review tracking
review_status = models.CharField(
    max_length=20, default='skip',
    choices=[
        ('skip', 'Skip'),           # Not eligible for review scraping
        ('pending', 'Pending'),      # Eligible, waiting for detail enrichment first
        ('scraping', 'Scraping'),    # Review spider currently running
        ('scraped', 'Scraped'),      # Reviews fetched + DudScore calculated
        ('failed', 'Failed'),        # Review scrape failed
    ],
    help_text="Review scraping status (only top 100K products)"
)
review_count_scraped = models.IntegerField(default=0)

# New scrape_status choice: add 'enriching' to existing choices
```

**New indexes:**
```python
models.Index(
    fields=['scrape_status', 'enrichment_priority', 'created_at'],
    name='idx_backfill_enrich_queue',
),
models.Index(
    fields=['review_status', 'scrape_status'],
    name='idx_backfill_review_queue',
),
```

## 2.2 Product Model: Lightweight Flag

```python
# Add to apps/products/models.py — Product model
is_lightweight = models.BooleanField(
    default=False,
    db_index=True,
    help_text="True = created from tracker data only, missing full details"
)
```

This flag is used by:
  - Frontend: show "Limited info" banner, hide empty specs/reviews sections
  - Search: deprioritize lightweight products in Meilisearch ranking
  - Enrichment: know which products still need marketplace scraping
  - API serializer: include is_lightweight in response

## 2.3 price_snapshots source column

The BF-1 migration added: `source VARCHAR(50) DEFAULT 'scraper'`
Values: 'scraper', 'pricehistory_app', 'buyhatke', 'pricebefore', 'keepa'

The existing ProductPipeline INSERT statement must be updated to explicitly
include `source = 'scraper'` in the column list. Currently it omits the column
and relies on the DEFAULT, which works but should be explicit.

---

# PART 3: CLAUDE CODE PROMPTS

## Session 1: Model Changes + Async Source Framework

### Prompt BF-1: Model Additions + Migrations

```
Read CLAUDE.md for project rules.
Read apps/pricing/models.py — find the BackfillProduct model.
Read apps/products/models.py — find the Product model.
Read PROGRESS.md for current state.

=== CONTEXT ===

We have 28,735 BackfillProduct records. The model already has:
  - status field: Discovered, PH Extended, Done, Failed
  - scrape_status field: pending, scraped, failed
  - source, source_product_id, marketplace_slug, external_id, marketplace_url
  - title, current_price, lowest_price, highest_price, average_price, mrp
  - price_data (JSONB), price_data_points, history_from, history_to
  - product_listing FK (nullable)

We're scaling to 17M products with:
  - Tiered enrichment: P0-P1 → Playwright, P2-P3 → curl_cffi
  - Review scraping for top 100K products after detail enrichment
  - DudScore calculation after reviews

=== TASK: Add enrichment + review fields to BackfillProduct + lightweight flag to Product ===

Step 1: Add fields to BackfillProduct in apps/pricing/models.py:

  # Enrichment routing
  enrichment_priority = models.SmallIntegerField(
      default=3,
      db_index=True,
      help_text="0=on-demand, 1=Playwright, 2=curl_cffi, 3=curl_cffi-low"
  )
  enrichment_method = models.CharField(
      max_length=20, default='pending',
      choices=[
          ('pending', 'Pending'),
          ('playwright', 'Playwright'),
          ('curl_cffi', 'curl_cffi'),
          ('skipped', 'Skipped'),
      ],
  )
  enrichment_queued_at = models.DateTimeField(null=True, blank=True)

  # Review tracking (only for top 100K products)
  review_status = models.CharField(
      max_length=20, default='skip',
      choices=[
          ('skip', 'Skip'),
          ('pending', 'Pending'),
          ('scraping', 'Scraping'),
          ('scraped', 'Scraped'),
          ('failed', 'Failed'),
      ],
      help_text="Review scraping status — only top 100K get reviews"
  )
  review_count_scraped = models.IntegerField(default=0)

  Also add 'enriching' to the scrape_status choices if it's a CharField with choices.
  If scrape_status is a plain CharField without choices, just document that
  'enriching' is now a valid value.

  Add indexes to Meta:
  class Meta:
      # Keep ALL existing indexes/constraints
      # ADD these new indexes:
      indexes = [
          # ... existing indexes ...
          models.Index(
              fields=['scrape_status', 'enrichment_priority', 'created_at'],
              name='idx_backfill_enrich_queue',
          ),
          models.Index(
              fields=['review_status', 'scrape_status'],
              name='idx_backfill_review_queue',
          ),
      ]

Step 2: Add is_lightweight to Product in apps/products/models.py:

  is_lightweight = models.BooleanField(
      default=False,
      db_index=True,
      help_text="True if created from tracker data only (no marketplace scrape yet)"
  )

Step 3: Create migrations:

  python manage.py makemigrations pricing --name add_enrichment_review_fields
  python manage.py makemigrations products --name add_is_lightweight

Step 4: If the source column on price_snapshots doesn't exist yet, add it:

  Create a migration in apps/pricing/migrations/:
  class Migration(migrations.Migration):
      dependencies = [('pricing', '<latest>')]
      operations = [
          migrations.RunSQL(
              "ALTER TABLE price_snapshots ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'scraper';",
              "ALTER TABLE price_snapshots DROP COLUMN IF EXISTS source;",
          ),
      ]

Step 5: Update the BackfillProduct admin to show new fields:

  In the BackfillProductAdmin (apps/pricing/admin.py), add to list_display:
    'enrichment_priority', 'enrichment_method', 'scrape_status', 'review_status'
  Add to list_filter:
    'enrichment_priority', 'enrichment_method', 'scrape_status', 'review_status'
  Add admin actions:
    @admin.action(description="Mark for review scraping")
    def mark_for_reviews(self, request, queryset):
        queryset.filter(scrape_status='scraped').update(review_status='pending')

Step 6: Run migrations:
  python manage.py migrate

Step 7: Verify:
  python manage.py shell -c "
  from apps.pricing.models import BackfillProduct
  bp = BackfillProduct.objects.first()
  print(f'enrichment_priority={bp.enrichment_priority}')
  print(f'enrichment_method={bp.enrichment_method}')
  print(f'review_status={bp.review_status}')
  from apps.products.models import Product
  p = Product.objects.first()
  print(f'is_lightweight={p.is_lightweight}')
  "

Commit: "feat: add enrichment + review fields to BackfillProduct, is_lightweight to Product"
```

---

### Prompt BF-2: Async Source Framework with Connection Pooling

```
Read CLAUDE.md for project rules.
Read apps/pricing/backfill/ directory to see existing source modules.
Read apps/pricing/backfill/sources/base.py for the current BackfillSourceBase class.
Read apps/pricing/backfill/config.py for source configurations.

=== CONTEXT ===

The current source base class uses sync httpx. For 50K+/day throughput,
we need async httpx with connection pooling and controlled concurrency.

The key difference: instead of making 1 request at a time (86,400/day max),
we make 10-20 concurrent requests via asyncio.Semaphore (500K+/day capacity).

=== TASK: Upgrade source framework to async with connection pooling ===

Step 1: Update apps/pricing/backfill/sources/base.py:

  Replace the existing BackfillSourceBase with an async version.

  Key changes:
  - __aenter__ creates httpx.AsyncClient with connection pooling:
      self.client = httpx.AsyncClient(
          headers=self.config.headers,
          timeout=30.0,
          follow_redirects=True,
          limits=httpx.Limits(
              max_connections=50,
              max_keepalive_connections=20,
              keepalive_expiry=30,
          ),
      )
  - _request() method is async, uses asyncio.sleep() for rate limiting
    (NOT time.sleep() which blocks the event loop)
  - Add _request_count tracker for monitoring
  - Retry logic: exponential backoff on 429/5xx, max 3 retries
  - discover_products() is an async generator (async for)
  - fetch_price_history() is async

  The rate limiting should use a per-source semaphore:
    self._semaphore = asyncio.Semaphore(config.max_concurrency)

  Add max_concurrency to SourceConfig dataclass:
    max_concurrency: int = 10  # concurrent requests to this source

  The _detect_marketplace() helper should handle all Indian marketplaces:
    amazon.in → 'amazon-in' + ASIN extraction
    flipkart.com → 'flipkart' + PID extraction (from pid= param or /p/itm... path)
    myntra.com → 'myntra' + ID extraction
    croma.com → 'croma'
    ajio.com → 'ajio'
    tatacliq.com → 'tatacliq'
    jiomart.com → 'jiomart'
    meesho.com → 'meesho'
    snapdeal.com → 'snapdeal'
    nykaa.com → 'nykaa'
    firstcry.com → 'firstcry'
    reliancedigital.in → 'reliance-digital'
    vijaysales.com → 'vijay-sales'

  The _parse_price_rupees() helper converts rupee amounts to paisa (int):
    "64,999" → 6499900
    "₹64,999.00" → 6499900

Step 2: Add a source registry:

  Create apps/pricing/backfill/sources/__init__.py:

  def get_source(name: str) -> BackfillSourceBase:
      """Factory function to get a source instance by name."""
      from apps.pricing.backfill.sources.pricehistory_app import PriceHistoryAppSource
      from apps.pricing.backfill.sources.buyhatke import BuyHatkeSource
      from apps.pricing.backfill.sources.pricebefore import PriceBeforeSource

      sources = {
          'pricehistory_app': PriceHistoryAppSource,
          'buyhatke': BuyHatkeSource,
          'pricebefore': PriceBeforeSource,
      }
      if name not in sources:
          raise ValueError(f"Unknown source: {name}. Available: {list(sources.keys())}")
      return sources[name]()

Step 3: Update config.py — add max_concurrency to SourceConfig:

  @dataclass
  class SourceConfig:
      name: str
      base_url: str
      chart_endpoint: str = ''
      search_endpoint: str = ''
      browse_endpoint: str = ''
      sitemap_url: str = ''
      headers: dict = field(default_factory=dict)
      rate_limit: float = 0.5        # seconds between requests per connection
      max_concurrency: int = 10      # concurrent connections
      max_retries: int = 3
      enabled: bool = True

Step 4: Update source stubs (pricehistory_app.py, buyhatke.py, pricebefore.py)
  to use the new async base class. Keep the TODO placeholders for endpoints
  that need recon data, but make sure they inherit correctly and the method
  signatures match the async base.

Step 5: Verify async works:
  python -c "
  import asyncio, os, django
  os.environ['DJANGO_SETTINGS_MODULE'] = 'whydud.settings.dev'
  django.setup()
  from apps.pricing.backfill.sources import get_source
  source = get_source('pricehistory_app')
  print(f'Source: {source.config.name}, concurrency: {source.config.max_concurrency}')
  "

Commit: "feat: async source framework with connection pooling + source registry"
```

---

## Session 2: Async Runner + Management Command

### Prompt BF-3: High-Throughput Async Runner

```
Read apps/pricing/backfill/sources/base.py (the async base class from BF-2).
Read apps/pricing/models.py for BackfillProduct model.

=== CONTEXT ===

This is the core engine that achieves 50K+/day throughput. It replaces the
sync Celery tasks for discovery and history fetching. It uses:
  - asyncio.Semaphore for concurrency control
  - httpx.AsyncClient connection pooling (reuses TCP connections)
  - Batch DB writes via bulk_create (flush every 500 items)
  - sync_to_async for Django ORM calls (ORM is not async-safe)
  - Progress callback for real-time monitoring
  - Resume support (picks up where it left off via status filtering)

THROUGHPUT MATH:
  Sync (1 req/sec):     86,400/day
  Async (20 concurrent): 20 × 2 req/sec = 40/sec = 3,456,000/day
  That's a 40x improvement.

=== TASK: Create the async backfill runner ===

Create backend/apps/pricing/backfill/async_runner.py:

  """
  High-throughput async backfill runner.

  Usage:
    python manage.py backfill_prices async-discover --source pricehistory_app --concurrency 20 --max 50000
    python manage.py backfill_prices async-history --source pricehistory_app --concurrency 10 --batch 5000

    python -m apps.pricing.backfill.async_runner --source pricehistory_app --phase discover --concurrency 20
  """
  import asyncio
  import logging
  import time
  from asgiref.sync import sync_to_async

  logger = logging.getLogger(__name__)


  class AsyncBackfillRunner:

      def __init__(self, source_name, concurrency=10, rate_limit=0.5,
                   batch_db_size=500, on_progress=None):
          self.source_name = source_name
          self.concurrency = concurrency
          self.rate_limit = rate_limit
          self.batch_db_size = batch_db_size
          self.on_progress = on_progress or (lambda *a: None)
          self._discovered = 0
          self._history_fetched = 0
          self._errors = 0
          self._db_buffer = []
          self._start_time = None

      async def run_discovery(self, max_products=None, category=None):
          """
          Phase 1: Discover products from source platform.
          Creates BackfillProduct records via bulk_create with ignore_conflicts=True.
          Re-running is safe — duplicates are silently skipped.
          """
          from apps.pricing.backfill.sources import get_source
          source = get_source(self.source_name)
          self._start_time = time.time()

          logger.info(f"Discovery starting: source={self.source_name}, "
                      f"concurrency={self.concurrency}, max={max_products}")

          async with source:
              async for product_dict in source.discover_products(
                  category=category, max_products=max_products
              ):
                  if not product_dict.get('external_id'):
                      continue
                  self._db_buffer.append(product_dict)
                  self._discovered += 1
                  if len(self._db_buffer) >= self.batch_db_size:
                      await self._flush_discovered()
                  if self._discovered % 500 == 0:
                      elapsed = time.time() - self._start_time
                      rate = self._discovered / elapsed if elapsed > 0 else 0
                      self.on_progress('discover', self._discovered,
                                       max_products or 0, rate)
                      logger.info(f"Discovered {self._discovered} ({rate:.0f}/sec)")

          if self._db_buffer:
              await self._flush_discovered()

          elapsed = time.time() - self._start_time
          rate = self._discovered / elapsed if elapsed > 0 else 0
          logger.info(f"Discovery complete: {self._discovered} in {elapsed:.0f}s ({rate:.0f}/sec)")
          return self._discovered

      async def run_history_fetch(self, batch_size=5000):
          """
          Phase 2: Fetch price history for discovered products.
          Uses semaphore for concurrency control.
          IMPORTANT: status values must match YOUR ACTUAL model.
          Check if it's 'Discovered' or 'discovered' — case matters.
          """
          from apps.pricing.backfill.sources import get_source
          from apps.pricing.models import BackfillProduct

          source = get_source(self.source_name)
          self._start_time = time.time()
          semaphore = asyncio.Semaphore(self.concurrency)

          products = await sync_to_async(list)(
              BackfillProduct.objects.filter(
                  source=self.source_name,
                  status='Discovered',  # VERIFY: check your actual status value
              ).order_by('created_at')[:batch_size].values('id', 'source_product_id')
          )

          total = len(products)
          logger.info(f"Fetching history for {total} products (concurrency={self.concurrency})")

          async with source:
              tasks = [self._fetch_one(source, p, semaphore) for p in products]
              await asyncio.gather(*tasks, return_exceptions=True)

          elapsed = time.time() - self._start_time
          logger.info(f"History complete: {self._history_fetched}/{total} "
                      f"in {elapsed:.0f}s, {self._errors} errors")
          return self._history_fetched

      async def _fetch_one(self, source, product_dict, semaphore):
          """Fetch history for one product, respecting semaphore."""
          async with semaphore:
              await asyncio.sleep(self.rate_limit)
              try:
                  data_points = await source.fetch_price_history(
                      product_dict['source_product_id']
                  )
                  if not data_points:
                      return

                  from apps.pricing.models import BackfillProduct
                  updates = {
                      'price_data': data_points,
                      'price_data_points': len(data_points),
                      'status': 'PH Extended',  # VERIFY: match your actual status value
                  }
                  times = [dp['time'] for dp in data_points if dp.get('time')]
                  if times:
                      updates['history_from'] = min(times)
                      updates['history_to'] = max(times)

                  await sync_to_async(
                      BackfillProduct.objects.filter(id=product_dict['id']).update
                  )(**updates)
                  self._history_fetched += 1

                  if self._history_fetched % 100 == 0:
                      elapsed = time.time() - self._start_time
                      rate = self._history_fetched / elapsed
                      self.on_progress('history', self._history_fetched, 0, rate)

              except Exception as e:
                  self._errors += 1
                  logger.warning(f"History failed for {product_dict['source_product_id']}: {e}")
                  try:
                      await sync_to_async(
                          BackfillProduct.objects.filter(id=product_dict['id']).update
                      )(status='Failed', error_message=str(e)[:500])
                  except Exception:
                      pass

      async def _flush_discovered(self):
          """Bulk insert discovered products."""
          from apps.pricing.models import BackfillProduct

          objects = []
          for pd in self._db_buffer:
              objects.append(BackfillProduct(
                  source=self.source_name,
                  source_product_id=pd.get('source_product_id', ''),
                  source_url=pd.get('source_url', ''),
                  marketplace_slug=pd.get('marketplace_slug', ''),
                  external_id=pd.get('external_id', ''),
                  marketplace_url=pd.get('marketplace_url', ''),
                  title=(pd.get('title', '') or '')[:1000],
                  current_price=pd.get('current_price'),
                  lowest_price=pd.get('lowest_price'),
                  highest_price=pd.get('highest_price'),
                  average_price=pd.get('average_price'),
                  mrp=pd.get('mrp'),
                  category_name=pd.get('category_name', ''),
                  brand_name=pd.get('brand_name', ''),
                  image_url=pd.get('image_url', ''),
                  status='Discovered',
              ))

          if objects:
              await sync_to_async(BackfillProduct.objects.bulk_create)(
                  objects, ignore_conflicts=True, batch_size=500
              )
          self._db_buffer.clear()


  # CLI entry point
  if __name__ == '__main__':
      import argparse, os, django
      os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whydud.settings.dev')
      django.setup()

      parser = argparse.ArgumentParser(description='Async Backfill Runner')
      parser.add_argument('--source', required=True)
      parser.add_argument('--phase', required=True, choices=['discover', 'history'])
      parser.add_argument('--concurrency', type=int, default=10)
      parser.add_argument('--max', type=int, default=None)
      parser.add_argument('--batch', type=int, default=5000)
      parser.add_argument('--category', default=None)
      args = parser.parse_args()

      def progress(phase, current, total, rate):
          print(f"\r  [{phase}] {current:,}" +
                (f"/{total:,}" if total else "") +
                f" ({rate:.0f}/sec)", end='', flush=True)

      runner = AsyncBackfillRunner(
          source_name=args.source, concurrency=args.concurrency, on_progress=progress,
      )

      if args.phase == 'discover':
          count = asyncio.run(runner.run_discovery(max_products=args.max, category=args.category))
          print(f"\nDiscovered {count:,} products")
      elif args.phase == 'history':
          count = asyncio.run(runner.run_history_fetch(batch_size=args.batch))
          print(f"\nFetched history for {count:,} products")


IMPORTANT NOTES:
  - Use asyncio.sleep() NOT time.sleep() — time.sleep blocks the event loop
  - Use sync_to_async for ALL Django ORM operations
  - The 'status' field values must match YOUR ACTUAL model choices exactly
  - asyncio.gather with return_exceptions=True prevents one failure from killing all tasks

Commit: "feat: high-throughput async backfill runner (50K+/day)"
```

---

### Prompt BF-4: Management Command Upgrades

```
Read apps/pricing/management/commands/backfill_prices.py (existing command).
Read apps/pricing/backfill/async_runner.py (from BF-3).

=== TASK: Add async subcommands + lightweight + enrichment + review subcommands ===

Add these new subcommands to the existing backfill_prices command:

  1. async-discover
     python manage.py backfill_prices async-discover \
       --source pricehistory_app --concurrency 20 --max 50000

  2. async-history
     python manage.py backfill_prices async-history \
       --source pricehistory_app --concurrency 10 --batch 5000

  3. create-lightweight
     python manage.py backfill_prices create-lightweight --batch 5000

  4. assign-priorities
     python manage.py backfill_prices assign-priorities

  5. enrich
     python manage.py backfill_prices enrich --priority 1 --batch 100 --method playwright
     python manage.py backfill_prices enrich --priority 2 --batch 500 --method curl_cffi

  6. scrape-reviews
     python manage.py backfill_prices scrape-reviews --batch 100
     (Processes products with review_status='pending' and scrape_status='scraped')

  7. Update existing 'status' subcommand to show:
     - Enrichment priority distribution
     - scrape_status breakdown
     - review_status breakdown
     - Enrichment method usage
     - Products by is_lightweight
     - Estimated bandwidth + time remaining

Implementation for status display:

  BY STATUS:
    Discovered       27,625
    PH Extended          53
    Done                153
    Failed              904

  BY SCRAPE STATUS:
    pending          28,540  (ready for enrichment)
    enriching            12
    scraped             153
    failed               30

  BY ENRICHMENT PRIORITY:
    P0 (on-demand)        0
    P1 (Playwright)   4,832  → ~3 GB proxy
    P2 (curl_cffi)   10,215  → ~0.5 GB proxy
    P3 (curl_cffi)   13,493  → ~0.7 GB proxy

  BY REVIEW STATUS:
    skip             28,235
    pending             350  (waiting for detail enrichment first)
    scraping             15
    scraped             100
    failed                5

  PRODUCTS:
    Total:             184 (seed + enriched)
    Lightweight:         0
    With reviews:      100
    With DudScore:     100

Commit: "feat: management command upgrades for full pipeline + review tracking"
```

---

## Session 3: Source Implementations (Post-Recon)

### Prompt BF-5: PriceHistory.app Source (Fill After Recon)

```
Read RECON-RESULTS.md 
Read apps/pricing/backfill/config.py for PRICEHISTORY_APP config.
Read apps/pricing/backfill/sources/pricehistory_app.py for the stub.
Read apps/pricing/backfill/sources/base.py for the async base class.

=== CONTEXT ===

You've done manual Chrome DevTools recon on pricehistory.app and recorded
the actual API endpoints in RECON-RESULTS.md. Now fill in the implementation.

=== TASK: Implement PriceHistory.app source with real endpoints ===

Step 1: Update config.py with endpoints from RECON-RESULTS.md:
  PRICEHISTORY_APP = SourceConfig(
      name='pricehistory_app',
      base_url='https://pricehistory.app',
      chart_endpoint='FILL_FROM_RECON',
      browse_endpoint='FILL_FROM_RECON',
      sitemap_url='FILL_FROM_RECON',
      headers={FILL_FROM_RECON},
      rate_limit=0.5,
      max_concurrency=15,
  )

Step 2: Implement discover_products():
  Strategy order:
  a) Sitemap (fastest — one XML fetch gives all product URLs)
  b) Category browse API (if sitemap doesn't list products)
  c) HTML scraping of category pages (fallback)

  For sitemap, create apps/pricing/backfill/sitemap_parser.py:
  - Parse sitemap.xml and sitemap index files
  - Handle gzipped sitemaps
  - Filter by path (e.g., /p/ for product pages)
  - Return list of product URLs

Step 3: Implement fetch_price_history():
  - Call the chart endpoint discovered in recon
  - Parse response based on actual JSON format
  - Transform to: [{'time': 'ISO8601', 'price': int(paisa), 'mrp': int|None, 'in_stock': bool}]
  - IMPORTANT: multiply rupee values by 100 to get paisa

Step 4: Test:
  python -c "
  import asyncio, os, django
  os.environ['DJANGO_SETTINGS_MODULE'] = 'whydud.settings.dev'
  django.setup()
  from apps.pricing.backfill.sources.pricehistory_app import PriceHistoryAppSource
  async def test():
      async with PriceHistoryAppSource() as source:
          count = 0
          async for p in source.discover_products(max_products=5):
              print(f'Found: {p[\"title\"][:50]} | {p[\"marketplace_slug\"]} | {p[\"external_id\"]}')
              count += 1
          print(f'Discovered {count}')
          if count:
              history = await source.fetch_price_history(p['source_product_id'])
              print(f'History: {len(history)} points')
  asyncio.run(test())
  "

Commit: "feat: PriceHistory.app source with real endpoints"
```

---

### Prompt BF-6: BuyHatke Source (Fill After Recon)

```
Read RECON-RESULTS.md for BuyHatke API details.
Read apps/pricing/backfill/sources/base.py for async base class.
Read apps/pricing/backfill/sources/pricehistory_app.py for the pattern.

=== TASK: Implement BuyHatke source ===

Same pattern as BF-5 but for BuyHatke. Key differences:
  - API requires parameters mimicking Chrome extension (specific headers)
  - Covers MORE marketplaces (Myntra, Ajio, Croma, Meesho, etc.)
  - Only ~3 months of history (less deep than PriceHistory.app)
  - Primarily useful for fetch_price_history() on products already discovered

Include same test function pattern as BF-5.

Commit: "feat: BuyHatke source with real endpoints"
```

---

## Session 4: Lightweight Records + Fast Injection

### Prompt BF-7: Lightweight Record Creator

```
Read apps/products/models.py for Product, ProductListing, Marketplace, Category, Brand.
Read apps/pricing/models.py for BackfillProduct.
Read apps/scraping/pipelines.py to understand how existing ProductPipeline creates products.

=== CONTEXT ===

This is the critical innovation. Instead of waiting for marketplace scraping,
we create Product + ProductListing records directly from tracker data.
The product is immediately usable on the site with price history chart.

Runs AFTER Phase 2 (history fetch). Processes BackfillProduct records that
have price history data and scrape_status='pending'.

IMPORTANT patterns to follow (match existing ProductPipeline):
  - Slug must be unique (append UUID suffix on collision)
  - Marketplace lookup by slug (cache in dict for performance)
  - Category matching by slug (best-effort from tracker category name)
  - Brand extraction from title (simple prefix matching)
  - Use existing Marketplace records (don't create new ones)

PRICE CONVERSION:
  Tracker data: price_data[].price = integer in PAISA (6499900 = ₹64,999)
  price_snapshots table: DECIMAL(12,2) in RUPEES (64999.00)
  Product.current_best_price: DECIMAL(12,2) — VERIFY if paisa or rupees by checking:
    SELECT current_best_price FROM products LIMIT 5;

=== TASK: Create lightweight record creator ===

Create backend/apps/pricing/backfill/lightweight_creator.py:

  TOP_BRANDS = ['apple','samsung','oneplus','xiaomi','realme','vivo',
                'oppo','hp','dell','lenovo','asus','acer','sony','lg',
                'boat','jbl','bose','whirlpool','haier','google',
                'nothing','motorola','nokia','mi ','redmi']

  def extract_brand(title: str) -> str | None:
      title_lower = title.lower()
      for brand in TOP_BRANDS:
          if title_lower.startswith(brand):
              return brand.strip().title()
      return None

  def create_lightweight_records(batch_size=1000) -> dict:
      """
      Convert BackfillProduct records into real Product + ProductListing.
      Then inject their price_data into price_snapshots.
      Returns: {created, linked, skipped, errors, snapshots_injected}
      """
      Implementation:
      1. Query BackfillProduct with price history ready + scrape_status='pending'
         + product_listing__isnull=True
         VERIFY your actual status for "price history fetched" — might be
         'PH Extended' or 'Done'. Check:
         BackfillProduct.objects.values('status').annotate(c=Count('id'))

      2. For each BackfillProduct:
         a) Get/cache Marketplace by slug
         b) Check if ProductListing already exists for (marketplace, external_id)
            → If yes: link it, skip creation, still inject history
         c) Guess category from tracker category_name (slugify → match)
         d) Extract brand from title using extract_brand()
         e) Generate unique slug (slugify title + UUID if collision)
         f) Create Product(is_lightweight=True, ...)
         g) Create ProductListing
         h) Inject price history via _inject_history()
         i) Update BackfillProduct.product_listing = listing

      3. _inject_history() uses psycopg2.extras.execute_values:
         - Convert price_data JSONB → list of tuples
         - price in paisa ÷ 100 for DB (VERIFY price unit in your price_snapshots)
         - Include source column = bp.source
         - page_size=2000

      4. Wrap each product in try/except — one failure shouldn't stop batch
      5. After batch, queue Meilisearch sync:
         from apps.search.tasks import sync_products_to_meilisearch
         sync_products_to_meilisearch.delay()

Commit: "feat: lightweight record creator — Product+Listing from tracker data"
```

---

### Prompt BF-8: Fast Price History Injection

```
Read apps/pricing/backfill/lightweight_creator.py (from BF-7).

=== CONTEXT ===

For 17M products with ~200 data points each = 3.4 BILLION rows,
we need PostgreSQL COPY protocol which is 5-10x faster than INSERT.

=== TASK: Create COPY-based fast injection + Meilisearch lightweight field ===

Step 1: Create backend/apps/pricing/backfill/fast_inject.py:

  import io, csv, logging
  from django.db import connection

  def copy_inject_snapshots(rows: list[tuple]) -> int:
      """
      Insert price snapshots using PostgreSQL COPY protocol.
      5-10x faster than INSERT for bulk loads.
      rows: list of (time, listing_id, product_id, marketplace_id,
                      price, mrp, discount_pct, in_stock, seller_name, source)
      """
      if not rows:
          return 0
      buf = io.StringIO()
      writer = csv.writer(buf, delimiter='\t')
      for row in rows:
          writer.writerow([str(v) if v is not None else '\\N' for v in row])
      buf.seek(0)
      with connection.cursor() as cur:
          cur.copy_from(buf, 'price_snapshots',
              columns=('time','listing_id','product_id','marketplace_id',
                       'price','mrp','discount_pct','in_stock','seller_name','source'),
              sep='\t', null='\\N')
      return len(rows)

  def batch_inject_from_backfill(batch_size=5000) -> dict:
      # Gather rows from batch_size BackfillProduct records, call copy_inject_snapshots

Step 2: Add is_lightweight to Meilisearch index:
  Find where Meilisearch documents are built in apps/search/.
  Add: 'is_lightweight': product.is_lightweight
  In ranking rules, sort enriched above lightweight when scores equal.

Commit: "feat: COPY-based fast injection + Meilisearch lightweight field"
```

---

## Session 5: Priority Assigner + Pipeline Hook

### Prompt BF-9: Enrichment Priority Assigner + Review Target Assignment

```
Read apps/pricing/models.py for BackfillProduct with enrichment_priority + review_status.

=== CONTEXT ===

After lightweight records are created, we assign:
1. Enrichment priorities (which products get Playwright vs curl_cffi)
2. Review targets (which 100K products get review scraping after enrichment)

Both run as UPDATE queries — ~2 seconds on 50K rows.

=== TASK: Create priority + review target assigner ===

Create backend/apps/pricing/backfill/prioritizer.py:

  TOP_BRANDS_PATTERN = (
      r'^(apple|samsung|oneplus|xiaomi|realme|vivo|oppo|'
      r'hp |dell |lenovo|asus|acer|sony|lg |boat |jbl |bose|'
      r'whirlpool|haier|google|nothing|motorola|nokia)'
  )
  TIER1_CATEGORIES_PATTERN = (
      r'(mobile|phone|smartphone|laptop|notebook|headphone|earphone|earbud|'
      r'television|tv|tablet|smartwatch|watch|iphone|galaxy|macbook|ipad|airpod)'
  )
  TIER2_CATEGORIES_PATTERN = (
      r'(refrigerator|washing.machine|air.conditioner|air.purifier|'
      r'camera|gaming|playstation|xbox|printer|monitor|speaker|soundbar|'
      r'router|hard.drive|ssd|power.bank|trimmer|iron)'
  )

  def assign_enrichment_priorities():
      """Assign P1/P2/P3 based on tracker signals."""
      base_qs = BackfillProduct.objects.filter(
          scrape_status='pending', enrichment_priority=3,
      )
      # P1: Playwright targets
      p1_count = base_qs.filter(
          Q(price_data_points__gte=200) |
          Q(category_name__iregex=TIER1_CATEGORIES_PATTERN) |
          Q(title__iregex=TOP_BRANDS_PATTERN, current_price__gte=1000000)
      ).filter(current_price__gt=0).update(enrichment_priority=1)

      # P2: curl_cffi targets
      p2_count = base_qs.filter(enrichment_priority=3).filter(
          Q(price_data_points__gte=50) |
          Q(current_price__gte=500000, current_price__lte=20000000) |
          Q(marketplace_slug='amazon-in', price_data_points__gte=30) |
          Q(category_name__iregex=TIER2_CATEGORIES_PATTERN)
      ).filter(current_price__gt=0).update(enrichment_priority=2)

      # Log distribution
      dist = BackfillProduct.objects.filter(scrape_status='pending').values(
          'enrichment_priority'
      ).annotate(count=Count('id')).order_by('enrichment_priority')
      for row in dist:
          logger.info(f"  P{row['enrichment_priority']}: {row['count']:,}")
      return {'p1': p1_count, 'p2': p2_count}


  def assign_review_targets(max_review_products=100_000):
      """
      Mark top 100K products for review scraping.
      Run AFTER assign_enrichment_priorities.
      """
      # All P1 products get reviews
      p1_count = BackfillProduct.objects.filter(
          enrichment_priority=1,
          review_status='skip',
      ).update(review_status='pending')

      remaining = max_review_products - p1_count
      if remaining > 0:
          # Fill from P2, ordered by popularity (price_data_points desc)
          p2_ids = list(
              BackfillProduct.objects.filter(
                  enrichment_priority=2,
                  review_status='skip',
              ).order_by('-price_data_points')
              .values_list('id', flat=True)[:remaining]
          )
          BackfillProduct.objects.filter(id__in=p2_ids).update(review_status='pending')

      total = BackfillProduct.objects.filter(review_status='pending').count()
      logger.info(f"Review targets: {total:,} products marked for review scraping")
      return total


  def bump_priority_for_viewed_products():
      """Post-launch: bump lightweight products with user interactions to P1."""
      from apps.products.models import Product
      viewed_ids = Product.objects.filter(
          is_lightweight=True,
          # view_count__gt=0  # Add this field later
      ).values_list('id', flat=True)
      BackfillProduct.objects.filter(
          product_listing__product_id__in=viewed_ids,
          scrape_status='pending',
          enrichment_priority__gt=1,
      ).update(enrichment_priority=1)


Commit: "feat: enrichment priority + review target assigner"
```

---

### Prompt BF-10: Pipeline Hook for Enrichment + Review Chaining

```
Read apps/scraping/pipelines.py — find ProductPipeline class and process_item().
Read apps/pricing/models.py for BackfillProduct.

=== CONTEXT ===

This is the CRITICAL connection. When enrichment triggers scrape_product_adhoc(),
the spider runs and ProductPipeline saves a ProductListing. We need:
1. Update BackfillProduct.scrape_status to 'scraped'
2. Upgrade Product.is_lightweight to False
3. If review_status='pending', chain the review scraping task

DESIGN PRINCIPLES:
  - Must NEVER crash the main scraping pipeline (wrap in try/except)
  - Runs on EVERY scrape, not just enrichment (finds 0 matches for normal scrapes)
  - Query hits composite index on (marketplace_slug, external_id) — sub-millisecond
  - If backfill tables don't exist, nothing breaks (ImportError → pass)

=== TASK: Add _close_backfill_loop + review chaining to ProductPipeline ===

In apps/scraping/pipelines.py, at the END of ProductPipeline.process_item(),
after the listing is saved:

  if listing:
      self._close_backfill_loop(listing)

  def _close_backfill_loop(self, listing):
      """
      If this listing was scraped as part of backfill enrichment,
      close the loop and optionally chain review scraping.
      """
      try:
          from apps.pricing.models import BackfillProduct

          # Find matching backfill records
          matching = BackfillProduct.objects.filter(
              marketplace_slug=listing.marketplace.slug,
              external_id=listing.external_id,
              scrape_status__in=('pending', 'enriching'),
          )

          # Check if any need reviews BEFORE updating
          needs_reviews = list(
              matching.filter(review_status='pending')
              .values_list('id', flat=True)
          )

          # Mark enrichment complete
          updated = matching.update(
              scrape_status='scraped',
              product_listing=listing,
          )

          if updated > 0:
              self._upgrade_lightweight_product(listing)
              logger.info(f"Backfill enrichment complete: {listing.external_id}")

              # Chain review scraping for eligible products
              if needs_reviews:
                  from apps.pricing.backfill.enrichment import queue_review_scraping
                  queue_review_scraping.delay(
                      listing_id=str(listing.id),
                      marketplace_slug=listing.marketplace.slug,
                      external_id=listing.external_id,
                  )
                  logger.info(f"Chained review scraping for {listing.external_id}")

      except ImportError:
          pass
      except Exception as e:
          logger.debug(f"Backfill loop skipped: {e}")

  def _upgrade_lightweight_product(self, listing):
      """Update Product from lightweight to full."""
      try:
          from apps.products.models import Product
          product = listing.product
          if not product or not product.is_lightweight:
              return
          updates = {'is_lightweight': False}
          if listing.rating and not product.avg_rating:
              updates['avg_rating'] = listing.rating
          if listing.review_count and (not product.total_reviews or product.total_reviews == 0):
              updates['total_reviews'] = listing.review_count
          Product.objects.filter(id=product.id).update(**updates)
      except Exception as e:
          logger.debug(f"Lightweight upgrade skipped: {e}")


ALSO: Update the existing INSERT for price_snapshots in ProductPipeline to
include the source column:

  Before:
    INSERT INTO price_snapshots (time, listing_id, product_id, marketplace_id,
                                 price, mrp, in_stock, seller_name)
    VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s)
  After:
    INSERT INTO price_snapshots (time, listing_id, product_id, marketplace_id,
                                 price, mrp, in_stock, seller_name, source)
    VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, 'scraper')

Commit: "feat: pipeline hook — enrichment status + review chaining + source column"
```

---

## Session 6: Tiered Enrichment Worker + curl_cffi Extractor

### Prompt BF-11: Tiered Enrichment Worker

```
Read apps/scraping/tasks.py for scrape_product_adhoc.
Read apps/pricing/models.py for BackfillProduct.
Read apps/pricing/backfill/prioritizer.py (from BF-9).

=== CONTEXT ===

The enrichment worker routes each product to the right method:
  P0-P1 → Playwright (existing scrape_product_adhoc)
  P2-P3 → curl_cffi (new enrich_via_http, see BF-12)

Three modes:
  1. Batch (Celery Beat every 15 min): processes N products by priority
  2. On-demand (user visits lightweight page): immediate P0 trigger
  3. Overnight (management command): processes all pending by priority

=== TASK: Create tiered enrichment worker ===

Create backend/apps/pricing/backfill/enrichment.py:

  @shared_task(queue='scraping', rate_limit='30/m')
  def enrich_single_product(backfill_product_id):
      bp = BackfillProduct.objects.get(id=backfill_product_id)
      if bp.scrape_status not in ('pending', 'enriching'):
          return
      bp.scrape_status = 'enriching'
      bp.enrichment_queued_at = timezone.now()
      bp.save(update_fields=['scrape_status', 'enrichment_queued_at'])

      if bp.enrichment_priority <= 1:
          bp.enrichment_method = 'playwright'
          bp.save(update_fields=['enrichment_method'])
          scrape_product_adhoc.delay(bp.marketplace_url, bp.marketplace_slug)
          # Status updated by _close_backfill_loop in ProductPipeline
      else:
          bp.enrichment_method = 'curl_cffi'
          bp.save(update_fields=['enrichment_method'])
          enrich_via_http.delay(str(bp.id))


  @shared_task(queue='scraping', rate_limit='60/m')
  def enrich_via_http(backfill_product_id):
      """Lightweight enrichment via curl_cffi — no browser."""
      from apps.pricing.backfill.curlffi_extractor import extract_product_data
      bp = BackfillProduct.objects.select_related('product_listing').get(id=backfill_product_id)
      data = extract_product_data(bp.marketplace_url, bp.marketplace_slug)

      if not data or not data.get('title'):
          bp.retry_count = (bp.retry_count or 0) + 1
          bp.scrape_status = 'failed' if bp.retry_count >= 3 else 'pending'
          bp.error_message = 'curl_cffi failed' if bp.retry_count >= 3 else ''
          bp.save()
          return

      # Update ProductListing + Product with extracted data
      listing = bp.product_listing
      if listing:
          listing_updates = {}
          for field in ('title','current_price','mrp','rating','review_count','in_stock'):
              if data.get(field if field != 'current_price' else 'price'):
                  listing_updates[field] = data.get(field if field != 'current_price' else 'price')
          listing_updates['last_scraped_at'] = timezone.now()
          ProductListing.objects.filter(id=listing.id).update(**listing_updates)

      product = listing.product if listing else None
      if product:
          product_updates = {'is_lightweight': False}
          if data.get('rating') and not product.avg_rating:
              product_updates['avg_rating'] = data['rating']
          if data.get('review_count') and not product.total_reviews:
              product_updates['total_reviews'] = data['review_count']
          Product.objects.filter(id=product.id).update(**product_updates)

      bp.scrape_status = 'scraped'
      bp.save(update_fields=['scrape_status'])

      # Check if this product needs reviews (curl_cffi enriched products
      # in top 100K still get reviews)
      if bp.review_status == 'pending':
          queue_review_scraping.delay(
              listing_id=str(listing.id),
              marketplace_slug=bp.marketplace_slug,
              external_id=bp.external_id,
          )


  @shared_task(queue='scraping')
  def enrich_batch(batch_size=100):
      """Celery Beat: process batch by priority."""
      products = BackfillProduct.objects.filter(
          scrape_status='pending',
      ).order_by('enrichment_priority', 'created_at')[:batch_size]
      for bp in products:
          enrich_single_product.delay(str(bp.id))
      return len(products)


  def trigger_on_demand_enrichment(external_id, marketplace_slug):
      """Called from ProductDetailView when user visits lightweight product."""
      bp = BackfillProduct.objects.filter(
          external_id=external_id, marketplace_slug=marketplace_slug,
          scrape_status='pending',
      ).first()
      if bp:
          bp.enrichment_priority = 0
          bp.save(update_fields=['enrichment_priority'])
          enrich_single_product.apply_async(args=[str(bp.id)], priority=9)
          return True
      return False


  @shared_task(queue='scraping', rate_limit='20/m')
  def queue_review_scraping(listing_id, marketplace_slug, external_id):
      """
      Chain review scraping after detail enrichment.
      Uses existing review spider infrastructure.
      """
      BackfillProduct.objects.filter(
          marketplace_slug=marketplace_slug, external_id=external_id,
          review_status='pending',
      ).update(review_status='scraping')

      if marketplace_slug in ('amazon-in', 'amazon_in'):
          from apps.scraping.tasks import run_review_spider
          run_review_spider.delay('amazon-in', product_external_ids=[external_id])
      elif marketplace_slug == 'flipkart':
          from apps.scraping.tasks import run_review_spider
          run_review_spider.delay('flipkart', product_external_ids=[external_id])
      else:
          BackfillProduct.objects.filter(
              marketplace_slug=marketplace_slug, external_id=external_id,
          ).update(review_status='skip')


  @shared_task(queue='default')
  def cleanup_stale_enrichments():
      """Reset stuck enrichments. Run hourly."""
      from django.db.models import F
      from datetime import timedelta
      cutoff = timezone.now() - timedelta(hours=2)
      BackfillProduct.objects.filter(
          scrape_status='enriching', enrichment_queued_at__lt=cutoff, retry_count__lt=3,
      ).update(scrape_status='pending', retry_count=F('retry_count') + 1)
      BackfillProduct.objects.filter(
          scrape_status='enriching', enrichment_queued_at__lt=cutoff, retry_count__gte=3,
      ).update(scrape_status='failed', error_message='Enrichment timed out')


  Add Celery Beat schedules in whydud/celery.py:
    'backfill-enrich-batch': {
        'task': 'apps.pricing.backfill.enrichment.enrich_batch',
        'schedule': crontab(minute='*/15'),
        'kwargs': {'batch_size': 100},
    },
    'backfill-cleanup-stale': {
        'task': 'apps.pricing.backfill.enrichment.cleanup_stale_enrichments',
        'schedule': crontab(minute=30, hour='*/1'),
    },


  Wire on-demand enrichment into product detail view:
    In apps/products/views.py ProductDetailView:
    if product.is_lightweight:
        from apps.pricing.backfill.enrichment import trigger_on_demand_enrichment
        listing = product.listings.first()
        if listing:
            trigger_on_demand_enrichment(listing.external_id, listing.marketplace.slug)


Commit: "feat: tiered enrichment worker — Playwright/curl_cffi routing + review chaining"
```

---

### Prompt BF-12: curl_cffi Product Extractor

```
Read Scraping-logic.md for anti-bot patterns (curl_cffi for Croma/Nykaa).
Read apps/scraping/spiders/amazon_spider.py for Amazon CSS selectors.
Read apps/scraping/spiders/flipkart_spider.py for Flipkart CSS selectors.

=== CONTEXT ===

curl_cffi impersonates Chrome TLS fingerprint without launching a browser.
Amazon serves full HTML (with JSON-LD + product data) ~55% of the time
through residential proxy. 10x cheaper and faster than Playwright.

JSON-LD gives: title, brand, 1 image, price, stock, rating, review count, seller.
HTML parsing adds: MRP, specs table, about bullets, seller, ASIN.
NOT available without JS: full image gallery, variants, bank offers.

IMPORTANT: Read the ACTUAL CSS selectors from your spider files, not the
ones below. Amazon and Flipkart change selectors periodically. The selectors
below are examples — use whatever is working in your current spiders.

=== TASK: Create curl_cffi product data extractor ===

Step 1: Add to requirements/scraping.txt:  curl_cffi>=0.7

Step 2: Create backend/apps/pricing/backfill/curlffi_extractor.py:

  def extract_product_data(url, marketplace_slug, proxy_url=None) -> dict | None:
      """
      Fetch product page via HTTP (no browser) and extract data.
      Returns: {title, brand, price(paisa), mrp(paisa), rating, review_count,
                images, in_stock, specs, about_bullets, seller_name, external_id}
      Returns None if blocked/CAPTCHA.
      """

  For Amazon:
    1. Try JSON-LD first: parse <script type="application/ld+json"> for Product
    2. HTML fallback for fields not in JSON-LD:
       - MRP: look for strikethrough price (a-text-price class or basisPrice)
       - Specs: #productDetails_techSpec_section_1 table rows
       - About: #feature-bullets ul li spans
       - ASIN: /dp/ASIN from URL or input[name="ASIN"]
       - Brand: #bylineInfo (clean "Visit the X Store" → "X")

  For Flipkart:
    - Try window.__INITIAL_STATE__ JSON in script tag
    - HTML fallback with Flipkart selectors from your spider

  Block detection: check for 'captcha', 'robot', 'automated access',
    '<title>Amazon.in</title>' (empty challenge page)

  Price helper: _rupees_to_paisa("₹64,999") → 6499900

Step 3: Test:
  python -c "
  from apps.pricing.backfill.curlffi_extractor import extract_product_data
  data = extract_product_data('https://www.amazon.in/dp/B0CX23GFMV', 'amazon-in')
  if data: print(f'Title: {data[\"title\"][:50]}')
  else: print('Blocked')
  "

Commit: "feat: curl_cffi product extractor — Amazon + Flipkart"
```

---

## Session 7: Review Completion + DudScore Trigger

### Prompt BF-13: Review Completion Hook + DudScore Chain

```
Read apps/scraping/pipelines.py — find ReviewPersistencePipeline.
Read apps/reviews/models.py for Review model.
Read apps/scoring/tasks.py for recalculate_dudscore.
Read apps/reviews/tasks.py for detect_fake_reviews (if it exists).

=== CONTEXT ===

After queue_review_scraping fires the review spider, reviews get saved by
the existing ReviewPersistencePipeline. But nobody tells BackfillProduct
that reviews are done, and nobody triggers DudScore calculation.

We need a task that runs after reviews are saved for a product:
1. Update BackfillProduct.review_status = 'scraped'
2. Update Product.total_reviews and avg_rating
3. Run detect_fake_reviews (if available)
4. Run recalculate_dudscore
5. Product is now FULLY COMPLETE

TWO OPTIONS for triggering this:
a) Hook into ReviewPersistencePipeline.close_spider()
b) Run as a periodic task that checks for products with reviews but review_status='scraping'

Option (b) is simpler and doesn't require modifying the review pipeline:

=== TASK: Create review completion handler + DudScore trigger ===

Create a task in apps/pricing/backfill/enrichment.py (add to existing file):

  @shared_task(queue='scoring')
  def post_review_enrichment(product_id: str):
      """
      Finalize review enrichment for a backfill product.
      Called after review spider finishes for this product.
      
      1. Count reviews, update Product aggregate fields
      2. Update BackfillProduct.review_status
      3. Run fake review detection
      4. Trigger DudScore recalculation
      """
      from apps.products.models import Product, ProductListing
      from apps.reviews.models import Review
      from apps.pricing.models import BackfillProduct
      from django.db.models import Avg

      product = Product.objects.get(id=product_id)

      # Count and aggregate reviews
      review_stats = Review.objects.filter(product_id=product_id).aggregate(
          count=Count('id'),
          avg_rating=Avg('rating'),
      )

      # Update Product
      Product.objects.filter(id=product_id).update(
          total_reviews=review_stats['count'] or 0,
          avg_rating=review_stats['avg_rating'],
      )

      # Update BackfillProduct
      listing = product.listings.first()
      if listing:
          BackfillProduct.objects.filter(
              marketplace_slug=listing.marketplace.slug,
              external_id=listing.external_id,
              review_status='scraping',
          ).update(
              review_status='scraped',
              review_count_scraped=review_stats['count'] or 0,
          )

      # Fake review detection
      try:
          from apps.reviews.tasks import detect_fake_reviews
          detect_fake_reviews.delay(str(product_id))
      except ImportError:
          try:
              from apps.scoring.tasks import detect_fake_reviews
              detect_fake_reviews.delay(str(product_id))
          except ImportError:
              logger.debug("No fake review detection task found")

      # DudScore calculation (this is the big one — Whydud's core differentiator)
      try:
          from apps.scoring.tasks import recalculate_dudscore
          recalculate_dudscore.delay(str(product_id))
          logger.info(f"DudScore triggered for product {product_id} "
                      f"({review_stats['count']} reviews)")
      except ImportError:
          logger.warning("recalculate_dudscore task not found")


  Create a periodic checker that links completed review scrapes:

  @shared_task(queue='default')
  def check_review_completion():
      """
      Find products where review spider has finished (reviews exist in DB)
      but review_status is still 'scraping'. Trigger post_review_enrichment.

      Run every 15 minutes via Celery Beat.
      """
      from apps.pricing.models import BackfillProduct
      from apps.reviews.models import Review

      scraping = BackfillProduct.objects.filter(
          review_status='scraping',
      ).select_related('product_listing')

      completed = 0
      for bp in scraping:
          if not bp.product_listing:
              continue
          product_id = bp.product_listing.product_id
          review_count = Review.objects.filter(product_id=product_id).count()

          if review_count > 0:
              # Reviews exist — trigger completion
              post_review_enrichment.delay(str(product_id))
              completed += 1
          elif bp.enrichment_queued_at:
              # Check if review scraping has been running too long
              from django.utils import timezone
              from datetime import timedelta
              if timezone.now() - bp.enrichment_queued_at > timedelta(hours=3):
                  bp.review_status = 'failed'
                  bp.error_message = 'Review scraping timed out'
                  bp.save(update_fields=['review_status', 'error_message'])

      if completed:
          logger.info(f"Review completion: {completed} products finalized")


  Add Celery Beat:
    'backfill-check-reviews': {
        'task': 'apps.pricing.backfill.enrichment.check_review_completion',
        'schedule': crontab(minute='*/15'),
    },


Commit: "feat: review completion hook + DudScore trigger chain"
```

---

### Prompt BF-14: Hook Review Spider to Support External ID Filtering

```
Read apps/scraping/spiders/amazon_review_spider.py for existing review spider.
Read apps/scraping/spiders/flipkart_review_spider.py.
Read apps/scraping/tasks.py for run_review_spider.

=== CONTEXT ===

The queue_review_scraping task calls:
  run_review_spider.delay('amazon-in', product_external_ids=['B0CX23GFMV'])

But the existing review spiders might not support filtering by specific
external_ids. They typically query ALL products needing reviews.

We need the review spider to accept an optional list of external_ids
and only scrape reviews for those specific products.

=== TASK: Add external_id filtering to review spiders ===

Step 1: Check how the existing review spider's start_requests() gets products:
  - If it queries ProductListing to find products needing reviews,
    add support for an external_ids kwarg that filters the queryset
  - If it takes URLs directly, build the review URLs from external_ids

Step 2: Update run_review_spider task (or create a variant):

  @shared_task(queue='scraping')
  def run_review_spider_for_products(marketplace_slug, external_ids):
      """
      Run review spider for specific products (used by backfill enrichment).
      """
      # Build the spider command with the specific product filter
      # This depends on how your runner.py works
      # Option A: Pass external_ids as spider argument
      # Option B: Create a temporary ScraperJob with the product list
      # Check your actual runner.py and spider implementation

Step 3: If the review spiders use start_requests() that queries the DB:

  In AmazonReviewSpider.start_requests():
    # Add support for external_id filtering
    external_ids = getattr(self, 'external_ids', None)
    queryset = ProductListing.objects.filter(marketplace__slug='amazon-in', ...)
    if external_ids:
        queryset = queryset.filter(external_id__in=external_ids)
    for listing in queryset:
        yield scrapy.Request(f'https://www.amazon.in/product-reviews/{listing.external_id}/', ...)

  Same for FlipkartReviewSpider.

Step 4: Update the runner to pass external_ids:
  In apps/scraping/runner.py, add --external-ids argument
  Or in the Celery task, pass it as a spider kwarg

IMPORTANT: Read the ACTUAL spider files before implementing.
The spider architecture may be different from what's described here.
Match whatever pattern your existing review spiders use.

Commit: "feat: review spider external_id filtering for targeted backfill reviews"
```

---

## Session 8: Multi-Node Proxy Config + Worker Setup

### Prompt BF-15: DataImpulse Session Routing

```
Read apps/scraping/middlewares.py — find ProxyPool and PlaywrightProxyMiddleware.
Read common/app_settings.py for ScrapingConfig.

=== CONTEXT ===

DataImpulse sticky session format:
  username: customer_abc-session-{worker_id}_{listing_hash}
Same session string = same residential IP for ~10-30 minutes.

Each Celery worker needs unique CELERY_WORKER_ID env var.

=== TASK: Add DataImpulse session routing ===

Step 1: Add to common/app_settings.py ScrapingConfig:
  @staticmethod
  def worker_id():
      import os, uuid
      return os.environ.get('CELERY_WORKER_ID', f'worker-{uuid.uuid4().hex[:6]}')

Step 2: Add get_sticky_proxy() to ProxyPool in middlewares.py:
  def get_sticky_proxy(self, session_key):
      worker_id = ScrapingConfig.worker_id()
      parsed = urlparse(self.proxy_urls[0])
      sticky_username = f"{parsed.username}-session-{worker_id}_{session_key}"
      return {
          'server': f'{parsed.scheme}://{parsed.hostname}:{parsed.port}',
          'username': sticky_username,
          'password': parsed.password,
      }

Step 3: Add SessionManager for rotation every N products.

Step 4: Add curl_cffi proxy helper:
  def get_curlffi_proxy_url(session_key=None):
      proxy_list = ScrapingConfig.proxy_list()
      if not proxy_list: return None
      base = proxy_list[0]
      if not session_key: return base
      parsed = urlparse(base)
      worker_id = ScrapingConfig.worker_id()
      sticky = f"{parsed.username}-session-{worker_id}_{session_key}"
      return f"{parsed.scheme}://{sticky}:{parsed.password}@{parsed.hostname}:{parsed.port}"

Commit: "feat: DataImpulse session routing for multi-worker"
```

---

### Prompt BF-16: Worker-Only Node Docker Config

```
Read docker-compose.primary.yml and docker-compose.replica.yml for patterns.
Read DEPLOYMENT.md for Celery worker config.

=== TASK: Create worker-only Docker Compose for remote nodes ===

Create docker/docker-compose.worker.yml:
  - Single service: celery-enrichment
  - Connects to Oracle Redis + PostgreSQL via WireGuard (10.0.0.x)
  - Unique WORKER_ID and WORKER_HOSTNAME per node
  - 1GB memory limit for free-tier VMs
  - No database, no Redis, no web server on this node

Create scripts/setup-worker-node.sh:
  - Installs Docker on fresh VM
  - Creates .env.worker template
  - Instructions for WireGuard setup

Commit: "infra: worker-only Docker config for remote enrichment nodes"
```

---

## Session 9: Frontend + Monitoring + Utilities

### Prompt BF-17: Frontend Lightweight Products + Monitoring Dashboard

```
Read frontend/src/lib/api/types.ts for Product type.
Read frontend/src/app/(public)/product/[slug]/page.tsx.
Read apps/products/serializers.py.

=== TASK: Handle lightweight products in frontend + upgrade status dashboard ===

Step 1: Add is_lightweight to serializers + frontend types.

Step 2: Product detail page: if isLightweight:
  - Info banner: "Price history available. Full details being fetched."
  - Show: title, price, marketplace link, price chart
  - Hide: empty specs, empty reviews, null DudScore
  - Still show marketplace links and "View on Amazon" button

Step 3: Search results: subtle "Price tracked" badge on lightweight cards.

Step 4: Update management command 'status' to show full pipeline:
  BY STATUS, BY SCRAPE STATUS, BY ENRICHMENT PRIORITY,
  BY REVIEW STATUS (skip/pending/scraping/scraped/failed),
  PRODUCTS (total, lightweight, with reviews, with DudScore),
  ESTIMATED TIMES + BANDWIDTH

Step 5: Add --watch flag for overnight monitoring (refresh every 30s).

Commit: "feat: frontend lightweight handling + comprehensive status dashboard"
```

---

### Prompt BF-18: Utility Commands + Overnight Runner

```
=== TASK: Create utility commands for pipeline operations ===

Add to backfill_prices management command:

  1. retry-failed
     --scrape (retry failed enrichments)
     --reviews (retry failed review scrapes)
     --history (retry failed history fetches)

  2. skip-products
     --price-below 10000  (skip under ₹100)
     --category "grocery"

  3. run-overnight
     All-in-one overnight command:
     a) assign-priorities (if not done)
     b) Enrich P1 with Playwright
     c) Enrich P2-P3 with curl_cffi
     d) Progress every 5 minutes
     e) Stop at --stop-at time (default 6 AM IST)
     f) Print summary when done

  4. verify-data
     Data quality checks:
     - is_lightweight=True but has full data
     - scrape_status=scraped but product_listing is NULL
     - review_status=scraped but 0 reviews in DB
     - Duplicate (marketplace, external_id)
     - Products with price=0
     - Orphaned BackfillProducts

Commit: "feat: utility commands + overnight runner + data verification"
```

---

# PART 4: EXECUTION PLAYBOOK

## Phase A:Recon

```
Done by you files are saved -
docs\BuyHatke Chrome Extension API Recon Re.md
docs\RECON-RESULTS.md

```

## Phase B: Build Infrastructure (Sessions 1-2, no recon needed)

```
[ ] BF-1:  Model additions (enrichment + review fields + is_lightweight)
[ ] BF-2:  Async source framework with connection pooling
[ ] BF-3:  Async runner (50K/day throughput)
[ ] BF-4:  Management command upgrades
```

## Phase C: Source Implementations (Session 3, needs recon)

```
[ ] BF-5:  PriceHistory.app source (real endpoints)
[ ] BF-6:  BuyHatke source (real endpoints)
```

## Phase D: Lightweight Pipeline (Session 4)

```
[ ] BF-7:  Lightweight record creator
[ ] BF-8:  Fast injection + Meilisearch indexing
```

## Phase E: Enrichment System (Sessions 5-6)

```
[ ] BF-9:  Priority + review target assigner
[ ] BF-10: Pipeline hook (_close_backfill_loop + review chain)
[ ] BF-11: Tiered enrichment worker (Playwright + curl_cffi routing)
[ ] BF-12: curl_cffi product extractor
```

## Phase F: Review + DudScore Chain (Session 7)

```
[ ] BF-13: Review completion hook + DudScore trigger
[ ] BF-14: Review spider external_id filtering
```

## Phase G: Scaling Infrastructure (Session 8)

```
[ ] BF-15: DataImpulse session routing
[ ] BF-16: Worker-only Docker config
```

## Phase H: Frontend + Monitoring (Session 9)

```
[ ] BF-17: Frontend lightweight handling + status dashboard
[ ] BF-18: Utility commands + overnight runner + verification
```

## First Run Playbook

```
# 1. Process existing 28,735 products through lightweight pipeline
python manage.py backfill_prices create-lightweight --batch 2000
# Run in loop until all products with price history have Product records

# 2. Assign priorities + review targets
python manage.py backfill_prices assign-priorities
python manage.py backfill_prices status

# 3. Start enrichment (first night)
python manage.py backfill_prices run-overnight

# 4. Next morning
python manage.py backfill_prices status
python manage.py backfill_prices verify-data

# 5. Scale discovery to 50K+
python manage.py backfill_prices async-discover \
  --source pricehistory_app --concurrency 20 --max 50000
python manage.py backfill_prices async-history \
  --source pricehistory_app --concurrency 10 --batch 10000
python manage.py backfill_prices create-lightweight --batch 5000
python manage.py backfill_prices assign-priorities
python manage.py backfill_prices run-overnight
```

## Complete Product Lifecycle

```
Discovered → History Fetched → Lightweight Record Created
    (usable on site: title, price, marketplace link, price chart)
         │
         ├─ P0-P1 → Playwright → scrape_status='scraped'
         │                           │
         │                    review_status='pending'?
         │                           │ yes
         │                           ↓
         │                    Review spider → 10-30 reviews
         │                           │
         │                    detect_fake_reviews()
         │                           │
         │                    recalculate_dudscore()
         │                           │
         │                    FULLY COMPLETE ✅
         │                    (chart + images + specs + reviews + DudScore)
         │
         ├─ P2-P3 → curl_cffi → scrape_status='scraped'
         │                           │
         │                    review_status='pending'?
         │                           │ yes (if top 100K)
         │                           ↓
         │                    Same review chain as above
         │
         └─ Unscored → stays lightweight until user visits
                         → on-demand P0 trigger → Playwright
```

## Scaling to 17M Timeline

```
Week 1:  500K discovered + history injected
         50K P1 enriched overnight
         Site has 500K products with price charts

Week 2:  2M total products
         200K P1 + 500K P2 enriched
         100K with reviews + DudScore
         Deploy 3 free worker nodes

Week 3:  5M products (add BuyHatke source)
         1M enriched via curl_cffi
         Users see rich product pages for top categories

Week 4+: Scale to 17M discovered
         2.5M enriched, 100K with reviews
         Background enrichment drip for the rest
         On-demand enrichment handles user traffic
```

## HOW TO USE THIS FILE

Add to your project root:
  cp BACKFILL.md /opt/whydud/BACKFILL.md

Add to CLAUDE.md read order:
  6. BACKFILL.md — backfill pipeline, enrichment, review scraping

Use short triggers with Claude Code:
  "Execute BF-1 and BF-2 from BACKFILL.md"
  "Read BACKFILL.md Part 1, then execute BF-7 and BF-8"

Batch 2 prompts per session (3 max for small ones).
Verify between sessions before proceeding.
If context is lost: "Read BACKFILL.md Part 1 to restore context"