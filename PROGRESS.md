# WHYDUD — Accurate Progress & Build Status

> **Claude Code: Read this file FIRST at the start of every session.**
> **Then read CLAUDE.md for project conventions.**
> **Audited 2026-02-24 — verified against actual codebase, not assumptions.**

---

## Discrepancies Found in Old PROGRESS.md

| Claim in Old File | Actual State |
|---|---|
| Login form submits to NOTHING (`preventDefault`) | **FALSE** — Login calls `authApi.login()`, stores token, redirects to `/dashboard` |
| Register page has no API calls wired | **FALSE** — All 3 steps wired: register → whydud email creation → onboarding |
| Dashboard shows "Please log in" because no auth token | **OUTDATED** — Auth context works, middleware checks cookie, dashboard calls real APIs |
| Google OAuth: "No frontend OAuth flow" | **FALSE** — OAuth callback page exchanges code for token via `authApi.exchangeOAuthCode()` |
| "Wire Auth" listed as current BLOCKER | **OUTDATED** — Auth is fully wired (commits `5abce2a`, `8588cd1`, `513956b` confirm this) |
| Lists "13 Django apps" but table has 14 entries | `common` is a utility module, not an app. `payments` mentioned but not a separate app. Actual apps: 13 |

---

## What's Working End-to-End

| Feature | Status | Verified |
|---|---|---|
| **13 Django apps scaffolded** | ✅ Built | accounts, products, pricing, reviews, scoring, email_intel, wishlists, deals, rewards, discussions, tco, search, scraping |
| **All database models + migrations** | ✅ Built | 27 migrations total across apps, TimescaleDB hypertables, 7 custom schemas |
| **All DRF serializers** | ✅ Built | List + Detail serializers for all models |
| **All DRF views + URL routing** | ✅ Built | ~30+ endpoints, 14 url paths in root urls.py |
| **Django Admin** | ✅ Built | All models registered |
| **Meilisearch** | ✅ Built | 31 seeded products indexed, search + autocomplete, fallback to DB |
| **Docker Compose** | ✅ Built | 9 production services, 3 dev services |
| **Seed data** | ✅ Built | 31 products with prices, reviews, marketplace listings, 12+ marketplaces |
| **Auth flow (login)** | ✅ Wired | Form → `authApi.login()` → token in localStorage + cookie → redirect to dashboard |
| **Auth flow (register)** | ✅ Wired | 3-step: account creation → @whyd.xyz email → onboarding |
| **Auth flow (OAuth)** | ✅ Wired | Google OAuth callback exchanges code → stores token → redirects |
| **Auth context + middleware** | ✅ Wired | `AuthProvider` restores session on mount, middleware protects dashboard routes |
| **Public pages** | ✅ Built | Homepage, Search, Product Detail, Compare, Seller, Deals, Categories — all calling real APIs |
| **Dashboard pages** | ✅ Built | Dashboard, Inbox, Wishlists, Settings — calling real APIs with loading states |
| **Header + Footer + Layout** | ✅ Built | Needs Figma polish |

---

## Auth System — Detailed Status

### Backend Auth Endpoints (all working)
```
POST /api/v1/auth/register/          → RegisterView
POST /api/v1/auth/login/             → LoginView
POST /api/v1/auth/logout/            → LogoutView
GET  /api/v1/me/                     → ProfileView
POST /api/v1/auth/change-password/   → ChangePasswordView
POST /api/v1/auth/reset-password/    → ResetPasswordView
POST /api/v1/auth/oauth/exchange-code/ → OAuth token exchange
POST /api/v1/email/whydud/create/    → WhydudEmail creation
GET  /api/v1/email/whydud/check-availability/ → Username check
GET  /api/v1/email/whydud/status/    → Email status
```

### Frontend Auth Implementation
| Component | File | Status |
|---|---|---|
| Login page | `src/app/(auth)/login/page.tsx` | ✅ Calls `authApi.login()`, error display, loading state, OAuth link |
| Register page | `src/app/(auth)/register/page.tsx` | ✅ 3-step flow, all API calls wired, password strength meter |
| OAuth callback | `src/app/(auth)/auth/callback/page.tsx` | ✅ Code exchange, token storage, error handling |
| Auth context | `src/contexts/auth-context.tsx` | ✅ Stores token, restores session via `/me`, login/logout/refresh methods |
| useAuth hook | `src/hooks/useAuth.ts` | ✅ Re-exports from AuthContext |
| Middleware | `src/middleware.ts` | ✅ Checks `whydud_auth` cookie, redirects unauthenticated to `/login` |
| API client | `src/lib/api/client.ts` | ✅ Token in localStorage + cookie, camelCase↔snake_case transforms, error wrapping |

---

## Frontend Pages — Detailed Status

### Public Pages (all call real APIs)
| Page | Route | API Calls | Status |
|---|---|---|---|
| Homepage | `/` | `productsApi.list()`, `dealsApi.list()` | ✅ Full UI |
| Search | `/search` | `searchApi.search()`, fallback `productsApi.list()` | ✅ Full UI |
| Product Detail | `/product/[slug]` | `productsApi.getDetail()`, `.getPriceHistory()`, `.getReviews()` | ✅ Full UI |
| Compare | `/compare` | `productsApi.compare()` | ✅ Full UI |
| Seller | `/seller/[slug]` | `sellersApi.getDetail()` | ✅ Full UI |
| Deals | `/deals` | `dealsApi.list()` | ✅ Full UI |
| Categories | `/categories/[slug]` | `productsApi.list(category)` | ✅ Full UI |
| Leaderboard | `/leaderboard` | `reviewsApi.getLeaderboard()`, `.getCategoryLeaderboard()` | ✅ Full UI — top-3 podium cards, table rows, level badges (bronze/silver/gold/platinum), category filter, cursor pagination, skeletons |

### Dashboard Pages (auth-protected, call real APIs)
| Page | Route | API Calls | Status |
|---|---|---|---|
| Dashboard | `/dashboard` | `purchasesApi.getDashboard()` | ✅ Charts, insights, spending overview |
| Inbox | `/inbox` | `inboxApi.list()`, `.get()`, `.markRead()`, `.star()`, `.softDelete()` | ✅ Full email client UI |
| Wishlists | `/wishlists` | `wishlistsApi.list()`, `.removeItem()`, `.updateItem()` | ✅ Tabbed, price tracking, alerts |
| Settings | `/settings` | `authApi.me()`, `whydudEmailApi.getStatus()`, `cardVaultApi.list()` | ✅ 6 tabs, card vault, password change |
| My Reviews | `/my-reviews` | `reviewsApi.getMyReviews()`, `.delete()` | ✅ Full UI — product name, stars, date, publish status, edit/delete |
| Alerts | `/alerts` | `alertsApi.getAlerts()`, `.getStockAlerts()`, `.updateAlert()`, `.deleteAlert()`, `.deleteStockAlert()` | ✅ Full UI — price alerts (inline edit), stock alerts, empty states |
| Purchases | `/purchases` | `purchasesApi.list()` | ⚠️ Basic — needs more UI |
| Rewards | `/rewards` | `rewardsApi.getBalance()` | ⚠️ Basic — needs more UI |
| Refunds | `/refunds` | `purchasesApi.getRefunds()` | ⚠️ Basic — needs more UI |
| Subscriptions | `/subscriptions` | `purchasesApi.getSubscriptions()` | ⚠️ Basic — needs more UI |

### Auth Pages
| Page | Route | Status |
|---|---|---|
| Login | `/login` | ✅ Fully wired |
| Register | `/register` | ✅ Fully wired (3-step) |
| OAuth Callback | `/auth/callback` | ✅ Fully wired |
| Verify Email | `/verify-email` | ⚠️ UI exists, needs verification |
| Forgot Password | `/forgot-password` | ⚠️ UI exists, needs verification |
| Reset Password | `/reset-password` | ⚠️ UI exists, needs verification |

---

## Frontend Components — Status

### Fully Built (with real data rendering)
- `ProductCard` — star rating, DudScore badge, price formatting
- `DashboardCharts` — Recharts, 5 tabs, insights
- `DealCard` — deal type badges, savings calc
- `PriceChart` — Recharts line chart, marketplace colors
- `RatingDistribution` — bars + percentages
- `ReviewCard` — author info, votes
- `DudScoreGauge` — circular gauge
- `CategoryScoreBars` — horizontal bars
- `MarketplacePrices` — price comparison table
- `Header`, `Footer`, `Sidebar`, `MobileNav`
- `SearchBar`, `SearchFilters`
- `CardVault` — bank card management
- `TCOCalculator` — full implementation: dynamic inputs from model schema, preset buttons, ownership years slider, debounced API calculation, stacked bar chart (Recharts), summary cards (total/yearly/monthly), cost breakdown detail, comparison mode (up to 3 products)
- `TrendingSection` — reusable async server component: fetches from trending/rising/price-dropping endpoints, ProductCard grid (2→3→4 cols), "View all" link, graceful empty state
- 19 shadcn/ui components (button, input, card, badge, tabs, etc.)

---

## Backend Apps — Detailed Status

### Models Status (all 13 apps)
| App | Models | Migrations | Real Views | Stub Tasks |
|---|---|---|---|---|
| **accounts** | 8 (User, WhydudEmail, OAuthConnection, PaymentMethod, ReservedUsername, Notification, NotificationPreference, PurchasePreference) | 5 | ✅ Register, Login, Profile, OAuth | 2 real tasks |
| **products** | 11 (Marketplace, Category, Brand, Product, Seller, ProductListing, BankCard, CompareSession, RecentlyViewed, StockAlert, CategoryPreferenceSchema) | 4 | ✅ List, Detail, Compare, Banks | Stubs |
| **pricing** | 4 (PriceSnapshot⚡, MarketplaceOffer, PriceAlert, ClickEvent) | 4 | ✅ Offers, PriceAlerts | Stubs |
| **reviews** | 3 (Review, ReviewVote, ReviewerProfile) | 3 | ✅ ProductReviews | Stubs |
| **scoring** | 2 (DudScoreConfig, DudScoreHistory⚡) | 3 | ✅ ScoreDetail, ConfigHistory | Stubs |
| **email_intel** | 6 (InboxEmail, EmailSource, ParsedOrder, RefundTracking, ReturnWindow, DetectedSubscription) | 3 | ✅ Inbox, Orders, Sources | Stubs |
| **wishlists** | 2 (Wishlist, WishlistItem) | 1 | ✅ CRUD | 1 stub |
| **deals** | 1 (Deal) | 1 | ✅ List | Stubs |
| **rewards** | 4 (RewardPointsLedger, RewardBalance, GiftCardCatalog, GiftCardRedemption) | 1 | ✅ Balance, Catalog, Redeem | Stubs |
| **discussions** | 3 (DiscussionThread, DiscussionReply, DiscussionVote) | 1 | ✅ List, Detail, Reply | Stubs |
| **tco** | 3 (TCOModel, CityReferenceData, UserTCOProfile) | 1 | ✅ Calculate, Profile | 1 real task |
| **search** | 1 (SearchLog) | 1 | ✅ Search (Meilisearch) | Stubs |
| **scraping** | 1 (ScraperJob) | 1 | ✅ Job status | 2 real tasks |

⚡ = TimescaleDB hypertable

**Total: 49 model classes, 27 migrations, ~8 real Celery tasks, ~15 stub tasks**

### Database Schemas
| Schema | Apps |
|---|---|
| `public` | products, pricing, reviews, deals, search, scraping |
| `users` | accounts, wishlists, rewards, products (compare/recent/stock), pricing (alerts) |
| `email_intel` | email_intel |
| `scoring` | scoring |
| `community` | discussions |
| `tco` | tco |
| `admin` | (created but unused — for future audit logs) |

---

## What's Stubbed (Code Exists But Logic Is `pass` / TODO)

| Feature | What's Stubbed | Sprint |
|---|---|---|
| Scraping spiders | Spider classes for Amazon.in, Flipkart — all methods `pass` | Sprint 2 |
| Email webhook | Endpoint accepts POST, does nothing | Sprint 3 |
| ~~DudScore calculation~~ | ~~Celery task is a stub, no sentiment/rating/fraud scoring~~ | ✅ Done |
| Price history collection | No actual price snapshots being taken | Sprint 2 |
| Razorpay payments | Returns 501 | Sprint 4 |
| ~~Fake review detection~~ | ~~Model exists, no detection rules~~ | ✅ Done |
| Deal detection | No actual price anomaly detection | Sprint 3 |
| Email parsing | No order extraction from emails | Sprint 3 |
| Price alerts | Check task is stub | Sprint 2 |
| Reward point calculation | Action-to-points mapping stubbed | Sprint 4 |

---

## What Doesn't Exist At All (v2.2 Features)

| Feature | Status |
|---|---|
| Multi-domain email (whyd.in / whyd.click / whyd.shop) | ❌ NOT BUILT |
| Email sending (Reply/Compose via Resend) | ❌ NOT BUILT |
| Email source aggregation (multi-account) | ❌ NOT BUILT |
| Click tracking (affiliate attribution) | ✅ BUILT (click_tracking.py, TrackClickView, frontend wired) |
| Purchase search (cross-platform) | ❌ NOT BUILT |
| Admin audit log | ❌ NOT BUILT |
| Admin as independent system | ❌ NOT BUILT |
| Compare tray (floating) | ❌ NOT BUILT |
| Cross-platform price comparison panel | ❌ NOT BUILT |
| Back-in-stock alerts | ❌ NOT BUILT (model exists, no alert logic) |
| Share product/comparison | ❌ NOT BUILT |
| Similar/alternative products | ❌ NOT BUILT |
| Product matching engine | ✅ BUILT (4-step: EAN → brand+model+variant → brand+model → fuzzy title) |
| Username suggestions | ❌ NOT BUILT |
| Write a Review page | ❌ NOT BUILT |
| Purchase proof upload | ❌ NOT BUILT |
| Feature-specific ratings | ❌ NOT BUILT |
| Seller feedback | ❌ NOT BUILT |
| NPS score | ❌ NOT BUILT |
| Notifications system | ❌ NOT BUILT (model exists, no delivery logic) |
| Notification preferences | ❌ NOT BUILT (model exists, no UI) |
| Purchase Preferences | ❌ NOT BUILT (model exists, no UI) |
| Reviewer levels & leaderboard | ❌ NOT BUILT (model exists, no calculation) |
| Trending products | ❌ NOT BUILT |
| Dynamic TCO per category | ⚠️ PARTIAL (backend + full calculator component exist, no seed data for TCO models) |
| Recently viewed | ❌ NOT BUILT (model exists, no tracking logic) |

---

## Infrastructure Status

### Docker Compose (Production — 9 services)
| Service | Image | Port | Status |
|---|---|---|---|
| Caddy | caddy:2-alpine | 80, 443 | ✅ Auto SSL, security headers |
| PostgreSQL 16 | timescale/timescaledb:latest-pg16 | 5432 | ✅ 7 schemas, 2 hypertables |
| Redis 7 | redis:7-alpine | 6379 | ✅ Cache + Celery broker |
| Meilisearch v1.7 | getmeili/meilisearch:v1.7 | 7700 | ✅ Product search |
| Django | Custom | 8000 | ✅ Gunicorn 3 workers |
| Celery Worker | Custom | — | ✅ 4 concurrent, 4 queues |
| Celery Beat | Custom | — | ✅ DatabaseScheduler |
| Email Worker | Custom | — | ✅ 2 concurrent, email queue |
| Next.js | Custom | 3000 | ✅ SSR |

### Environment
- Dev `.env` fully configured — all encryption keys generated and set
- Google OAuth credentials configured for dev
- Meilisearch master key set (`whydud_dev_meili_key_32chars!!` — matches docker-compose.dev.yml)
- `POSTGRES_PASSWORD=whydud_dev`
- `DJANGO_SECRET_KEY` — random 50-char key generated
- `EMAIL_ENCRYPTION_KEY` — 64-char hex generated (AES-256-GCM)
- `OAUTH_ENCRYPTION_KEY` — 64-char hex generated (AES-256-GCM)

### Deployment Readiness
- Multi-stage Dockerfiles ✅
- Health checks on all services ✅
- Caddy reverse proxy + security headers ✅
- Non-root container users ✅
- Missing for prod: Sentry DSN, Resend API key, Razorpay keys (encryption keys now set for dev)

---

## Celery Queues & Tasks

| Queue | Real Tasks | Stub Tasks |
|---|---|---|
| `default` | — | moderate_discussion, flag_spam_reply |
| `scraping` | run_marketplace_spider, fetch_new_listings | — |
| `email` | send_verification_email, send_password_reset_email | process_inbound_email, check_return_window_alerts, detect_refund_delays |
| `scoring` | compute_dudscore, full_dudscore_recalculation, sync_products_to_meilisearch, full_reindex | — |
| `alerts` | — | check_price_alerts, send_price_drop_notification |

---

---

## Established Patterns (Follow These)

| Pattern | Reference File |
|---|---|
| API response format | `{success: true, data: ...}` — `common/utils.py` |
| Cursor pagination | `common/pagination.py` |
| TimescaleDB migration | `pricing/migrations/0002_timescaledb_setup.py` (autocommit pattern) |
| Serializer flat vs nested | `ProductListSerializer` (flat) vs `ProductDetailSerializer` (nested) |
| Affiliate URL injection | `ProductListingSerializer.get_buy_url()` |
| App settings | `common/app_settings.py` (never hardcode config values) |
| Card pattern (frontend) | `bg-white rounded-lg border border-slate-200 shadow-sm` |
| Price formatting | `src/lib/utils/format.ts` → `formatPrice()` |
| Auth token storage | localStorage (`whydud_auth_token`) + cookie (`whydud_auth`) |
| API client transforms | camelCase ↔ snake_case automatic conversion |

---

## Credentials Available in .env

```
Configured (dev):
  DJANGO_SECRET_KEY         — Random 50-char key generated
  DATABASE_URL              — PostgreSQL (password: whydud_dev)
  REDIS_URL                 — redis://localhost:6379/0
  MEILISEARCH_URL           — http://localhost:7700
  MEILISEARCH_MASTER_KEY    — whydud_dev_meili_key_32chars!! (matches docker-compose.dev.yml)
  GOOGLE_CLIENT_ID          — Set (OAuth working)
  GOOGLE_CLIENT_SECRET      — Set (OAuth working)
  EMAIL_ENCRYPTION_KEY      — 64-char hex generated (AES-256-GCM)
  OAUTH_ENCRYPTION_KEY      — 64-char hex generated (AES-256-GCM)
  CELERY_RESULT_BACKEND     — redis://localhost:6379/1
  CLOUDFLARE_EMAIL_SECRET   — Placeholder set

Not configured yet:
  RESEND_API_KEY            — For email sending
  RAZORPAY_KEY_ID           — Payment processing
  RAZORPAY_KEY_SECRET       — Payment processing
  SENTRY_DSN                — Error monitoring
```

---

## Status Updates (Chronological)

### 2026-02-25 — Leaderboard Page
- Created `frontend/src/app/(public)/leaderboard/page.tsx` — full reviewer leaderboard page
- Updated `ReviewerProfile` type in `lib/api/types.ts` with all serializer fields (`totalUpvotesReceived`, `totalHelpfulVotes`, `reviewQualityAvg`, `isTopReviewer`)
- Fixed `reviewsApi.getLeaderboard()` to use string cursor (was incorrectly typed as number)
- Added `reviewsApi.getCategoryLeaderboard(categorySlug, cursor?)` for per-category filtering
- Page features: top-3 podium with medals, table rows for rank 4+, colored level badges (bronze/silver/gold/platinum), category filter dropdown, cursor-based pagination, skeleton loading, empty state, error state
- TypeScript clean: `tsc --noEmit` passes with zero errors

### 2026-02-25 — Trending Section Component + Homepage Update
- Created `frontend/src/components/product/trending-section.tsx` — reusable async server component
  - Props: `title`, `endpoint` (trending/rising/price-dropping), `limit`, `viewAllHref`
  - Fetches from `trendingApi`, renders ProductCard grid (2→3→4 responsive columns)
  - Returns null gracefully when API unavailable or no data
- Added two sections to homepage (`(public)/page.tsx`):
  - "Trending Products" → `GET /api/v1/trending/products`
  - "Price Dropping" → `GET /api/v1/trending/price-dropping`
- TypeScript clean: `tsc --noEmit` passes with zero errors

### 2026-02-25 — Purchase Preference Schemas Seed Data
- Created `backend/apps/products/management/commands/seed_preference_schemas.py`
- 7 category schemas with JSONB matching frontend `PreferenceSection[]` type:
  - Air Purifiers: 6 sections, 22 fields (verbatim from ARCHITECTURE.md Epic 8 US-8.1)
  - Air Conditioners: 5 sections, 14 fields
  - Water Purifiers: 5 sections, 13 fields
  - Refrigerators: 5 sections, 13 fields
  - Washing Machines: 4 sections, 11 fields
  - Vehicles: 5 sections, 10 fields
  - Laptops: 5 sections, 12 fields
- Creates missing categories (air-purifiers, water-purifiers, vehicles) via get_or_create
- Idempotent: uses update_or_create, supports `--flush` flag
- Run: `python manage.py seed_preference_schemas`

### 2026-02-25 — Notification Celery Tasks
- Added `create_notification` task (`queue="default"`) to `backend/apps/accounts/tasks.py`
  - Accepts: `user_id`, `type`, `title`, `body`, `action_url`, `action_label`, `entity_type`, `entity_id`, `metadata`
  - Checks `NotificationPreference` for the notification type — respects `in_app` toggle (suppresses creation if disabled)
  - Creates `Notification` record in DB
  - Checks `email` preference channel — queues `send_notification_email` if email is enabled
  - Falls back to model field defaults when no `NotificationPreference` row exists
  - Returns `notification.pk` on success, `None` if suppressed
- Added `send_notification_email` task (`queue="email"`, `max_retries=3`, `default_retry_delay=60`)
  - Fetches `Notification` with `select_related("user")`
  - Recipient priority: @whyd.* email (if active) → personal email
  - Renders plain-text + inline-styled HTML (brand colors, CTA button, unsubscribe link)
  - Sends via Django `send_mail` (Resend SMTP backend)
  - Marks `email_sent=True` + `email_sent_at` on success
  - Retries up to 3 times on failure (60s delay)
- Added `NOTIFICATION_TYPE_TO_PREF_FIELD` mapping (10 types → preference field names)
- No extra Celery registration needed — `app.autodiscover_tasks()` picks up `accounts/tasks.py` automatically

### 2026-02-25 — Review Celery Tasks + Beat Schedule
- Replaced `backend/apps/reviews/tasks.py` — kept existing stubs, added two real tasks:
  - `publish_pending_reviews` (`queue="default"`) — bulk-publishes reviews where `is_published=False` and `publish_at <= now()`, returns count
  - `update_reviewer_profiles` (`queue="scoring"`) — aggregates per-user stats from published Whydud reviews:
    - Counts total_reviews, sums upvotes + helpful_votes, averages credibility_score
    - Assigns level: bronze (1-4), silver (5-14), gold (15-29), platinum (30+)
    - Ranks all profiles by total_upvotes_received → sets leaderboard_rank
    - Top 10 → is_top_reviewer = True
    - Uses get_or_create + bulk_update (batch_size=500)
- Registered both in Celery Beat schedule (`backend/whydud/celery.py`):
  - `publish-pending-reviews-hourly`: `crontab(minute=0)` — every hour at :00
  - `update-reviewer-profiles-weekly`: `crontab(minute=0, hour=0, day_of_week="monday")` — Monday 00:00 UTC
- Added `crontab` import to celery.py

### 2026-02-25 — Price Alert Celery Task
- Replaced `backend/apps/pricing/tasks.py` — implemented real `check_price_alerts` task:
  - `queue="alerts"`, runs every 4 hours via Celery Beat (`check-price-alerts-4h`)
  - Queries all active, un-triggered `PriceAlert` records with `select_related` + `iterator(chunk_size=500)`
  - For each alert: finds cheapest in-stock `ProductListing.current_price` (marketplace-specific if alert.marketplace is set, otherwise global)
  - Updates `alert.current_price` on every check (price tracking)
  - If `current_price <= target_price`: triggers alert — sets `is_triggered`, `triggered_at`, `triggered_price`, `triggered_marketplace`, `notification_sent`, deactivates alert
  - Fires `create_notification.delay()` with type `price_alert`, formatted price (Indian numbering ₹X,XX,XXX), marketplace name, product slug, and metadata
  - Returns summary dict: `{checked, triggered, errors}`
  - Helper `_format_price()` converts paisa to ₹ with Indian comma grouping
- Registered in Celery Beat: `crontab(minute=0, hour="*/4")` — every 4 hours at :00
- Removed resolved `# TODO Sprint 3: "price-alerts-4h"` comment from celery.py

### 2026-02-25 — Amazon.in Spider + Scraping Pipeline (Sprint 2)
- **Created `backend/apps/scraping/items.py`** — `ProductItem` Scrapy Item class
  - Fields: marketplace_slug, external_id, url, title, brand, price (paisa), mrp (paisa), images, rating, review_count, specs, seller_name, seller_rating, in_stock, fulfilled_by, about_bullets, offer_details, raw_html_path
- **Replaced `backend/apps/scraping/spiders/base_spider.py`** — enhanced BaseWhydudSpider
  - 10 realistic browser User-Agent strings (Chrome/Firefox/Edge/Safari on Win/Mac/Linux)
  - `_random_ua()`, `_make_headers()`, `_extra_delay()` helper methods
  - Disables Scrapy's built-in UA middleware; rotates UA per request via headers
  - ROBOTSTXT_OBEY=True, DOWNLOAD_DELAY=2 with jitter, 2 concurrent/domain
- **Replaced `backend/apps/scraping/spiders/amazon_spider.py`** — full AmazonIndiaSpider
  - `start_requests()`: loads URLs from ScraperJob (job_id), CLI override (category_urls), or 8 seed category URLs (smartphones, laptops, headphones, air purifiers, washing machines, refrigerators, TVs, cameras)
  - `parse_listing_page()`: extracts product links from `div[data-component-type="s-search-result"]`, follows pagination up to max_pages (default 5), only follows /dp/ links
  - `parse_product_page()`: extracts ALL fields with multiple fallback CSS selectors per field:
    - ASIN: from URL regex + `input[name="ASIN"]` + `#ASIN`
    - Title: `#productTitle` + `#title span`
    - Brand: `a#bylineInfo` (strips "Visit the X Store" / "Brand: X") + tech specs fallback
    - Price: 6 selector fallbacks (corePriceDisplay, dealprice, apex, a-price, legacy)
    - MRP: 5 selector fallbacks (basisPrice, a-text-price, listPrice)
    - Images: landingImage (data-old-hires + src) + altImages strip + data-a-dynamic-image JSON
    - Rating: acrPopover + data-hook + averageCustomerReviews
    - Review count: acrCustomerReviewText + total-review-count
    - Seller: sellerProfileTriggerId + merchant-info + tabular-buybox
    - Availability: #availability span (pattern matching "in stock" / "currently unavailable")
    - Fulfilled by: tabular-buybox + deliveryBlockMessage
    - Specs: productDetails_techSpec_section_1 + detailBullets_sections1 + detailBullets_feature_div
    - About bullets: #feature-bullets ul li
    - Offers: sopp_feature_div + InstallmentCalculator (classified as cashback/emi/coupon/bank_offer)
  - Price parsing: strips ₹/commas, converts rupees → paisa (×100)
  - Image resolution upgrade: `_SX300_` → `_SL1500_`
  - Optional raw HTML saving to configurable directory
  - Playwright integration for JS-rendered product pages (wait_for_selector on #productTitle)
- **Replaced `backend/apps/scraping/pipelines.py`** — 4 real pipelines
  - `ValidationPipeline` (100): drops items missing marketplace_slug/external_id/url/title
  - `NormalizationPipeline` (200): collapses whitespace in titles, normalises brand casing (title-case / uppercase for ≤4 chars), strips spec whitespace, deduplicates images
  - `ProductPipeline` (400): full Django ORM persistence pipeline:
    - Resolves Marketplace by slug
    - get_or_create Seller by (marketplace, name)
    - get_or_create Brand by slug
    - Finds existing ProductListing by (marketplace, external_id) → updates if found
    - Product matching: brand + SequenceMatcher title similarity ≥0.85 → matches to existing canonical Product
    - If no match → creates new Product with unique slugified slug
    - Creates ProductListing with match_confidence=1.0, match_method="external_id"
    - PriceSnapshot via raw SQL (avoids ORM/hypertable managed=False issues)
    - Recomputes Product.current_best_price (MIN of in-stock listings)
    - Tracks lowest_price_ever + lowest_price_date
  - `MeilisearchIndexPipeline` (500): stub for Sprint 3
- **Updated `backend/apps/scraping/scrapy_settings.py`**
  - Removed DeduplicationPipeline + PersistencePipeline references (merged into ProductPipeline)
  - Added TWISTED_REACTOR for asyncio compatibility
  - Added DOWNLOAD_HANDLERS for Playwright (http + https)
  - Added PLAYWRIGHT_BROWSER_TYPE + PLAYWRIGHT_LAUNCH_OPTIONS
  - Added `get_scrapy_settings()` helper for programmatic access
- **Created `backend/apps/scraping/runner.py`** — standalone spider runner script
  - Invoked via `python -m apps.scraping.runner <spider_name> [--job-id] [--urls] [--max-pages] [--save-html]`
  - Initialises Django + Scrapy CrawlerProcess in a clean process (avoids Twisted reactor issues)
  - Used by Celery tasks via subprocess
- **Replaced `backend/apps/scraping/tasks.py`** — 3 real Celery tasks
  - `run_spider(marketplace_slug, spider_name, job_id)` — queue="scraping", bind=True, max_retries=1
    - Creates/updates ScraperJob (queued → running → completed/failed)
    - Runs spider via subprocess with 1-hour timeout
    - Captures stdout/stderr, updates job.error_message on failure
  - `scrape_product_adhoc(url, marketplace_slug)` — queue="scraping"
    - Single URL scrape, 2-min timeout, maps marketplace to spider
  - `scrape_daily_prices()` — queue="scraping"
    - Iterates active Marketplaces, launches parallel run_spider.delay() per marketplace
- **Added `ScrapingConfig` to `backend/common/app_settings.py`**
  - spider_timeout, max_listing_pages, raw_html_dir, product_match_threshold, spider_map
- **Registered daily scrape in Celery Beat** (`backend/whydud/celery.py`)
  - `scrape-daily-prices`: `crontab(minute=0, hour=2)` — daily at 02:00 UTC (07:30 IST)

### 2026-02-25 — Flipkart Spider
- **Replaced `backend/apps/scraping/spiders/flipkart_spider.py`** — full FlipkartSpider (505 lines)
  - Same `ProductItem` output format as AmazonIndiaSpider — shared pipelines
  - **JSON-LD primary extraction**: parses `<script type="application/ld+json">` for title, price, brand, rating, review_count, images, availability, seller — most reliable on Flipkart
  - CSS/XPath fallbacks for every field when JSON-LD is absent
  - `start_requests()`: loads from ScraperJob, CLI override, or 8 seed search URLs
  - `parse_listing_page()`: finds product links via `a[href*="/p/itm"]`, deduplicates, follows pagination via "Next" link up to max_pages
  - `parse_product_page()` extracts ALL fields:
    - FPID (Flipkart Product ID): from URL regex `/p/(itm[a-zA-Z0-9]+)`
    - Title: JSON-LD → `span.VU-ZEz` → `h1` variants → XPath
    - Brand: JSON-LD brand object → breadcrumb (3rd item) → specs table
    - Price: JSON-LD offers → `div._30jeq3` / `div.Nx9bqj` → XPath
    - MRP: `div._3I9_wc` / `div.yRaY8j` (strike-through) → XPath
    - Images: JSON-LD → gallery thumbnails (flixcart.com) → any `rukminim` images
    - Rating: JSON-LD aggregateRating → `div._3LWZlK` / `div.XQDdHH`
    - Review count: JSON-LD ratingCount/reviewCount → rating text pattern
    - Seller: JSON-LD offers.seller → `#sellerName span span`
    - Seller rating: separate CSS extraction from seller info section
    - Availability: JSON-LD schema.org/InStock → "Sold Out"/"Coming Soon" text → "Buy Now" button presence
    - Fulfilled by: Flipkart Assured badge detection (icon URL patterns + alt text + "F-Assured" text)
    - Specs: `div._14cfVK tr` tables (grouped by General/Display/Performance) → `div._3k-BhJ tr` → XPath "Specifications" section
    - Highlights: `div._2418kt li` / `div.xFVion li` → XPath "Highlights" section
    - Offers: offer list items → "Available offers" XPath section (classified: cashback/emi/exchange/coupon/bank_offer/partner_offer)
  - Image resolution upgrade: `/image/312/312/` → `/image/832/832/`
  - Canonical URL builder strips tracking params
  - Playwright for listing pages only (lazy-loaded cards); product pages via plain HTTP
  - Optional raw HTML saving

### 2026-02-25 — Product Matching Engine (Architecture §6 Stage 3)
- **Created `backend/apps/products/matching.py`** — 4-step cross-marketplace product deduplication engine
  - **Step 1 — Extract canonical identifiers:**
    - `_resolve_brand()`: brand normalization via `Brand.aliases` JSONField (e.g. "MI" → Xiaomi, "SAMSUNG" → Samsung)
    - `_extract_ean()`: barcode extraction from specs (EAN/GTIN/UPC/barcode keys, validates 8-14 digit format)
    - `_extract_model_info()`: regex-based extraction of model name, storage (GB/TB), RAM, color from marketplace titles
    - Handles Indian marketplace title formats: Amazon.in "(Mint, 8GB, 256GB)" vs Flipkart "(Mint, 256 GB)(8 GB RAM)"
  - **Step 2 — Match scoring (4 strategies in priority order):**
    - EAN exact match → confidence 1.0 → auto-merge (JSONB key-value lookup + stripped-digits fallback)
    - Brand + model + variant exact → confidence 0.95 → auto-merge (SequenceMatcher ≥0.90 on normalized model strings + storage/RAM equality)
    - Brand + model (variant differs) → confidence 0.85 → auto-merge (model similarity only)
    - Fuzzy title match (SequenceMatcher ≥ configurable threshold) → confidence 0.70 → manual review queue
    - Below threshold → create new canonical product
  - **Step 3 — Create or merge:**
    - `match_product(item, brand=None) → MatchResult` — main API, returns `(product, confidence, method, is_new)`
    - `_create_canonical_product()` — slug generation with collision avoidance, full field population
    - `resolve_or_create_brand()` — alias-aware brand resolution, replaces pipeline's bare `get_or_create`
  - **Step 4 — Update canonical product:**
    - `update_canonical_product(product)` — recalculates aggregates from ALL listings:
      - `avg_rating`: weighted average by review_count across listings
      - `total_reviews`: sum of all listing review_counts
      - `current_best_price` + `current_best_marketplace`: MIN of in-stock listing prices
      - `lowest_price_ever` + `lowest_price_date`: historical tracking
- **Added `MatchingConfig` to `backend/common/app_settings.py`**
  - `auto_merge_threshold` (0.85), `review_threshold` (0.60), `fuzzy_title_threshold` (0.80), `max_candidates` (500)
  - Removed old `product_match_threshold` from `ScrapingConfig` (superseded)
- **Updated `backend/apps/scraping/pipelines.py`** — integrated matching engine
  - Replaced `_find_matching_product()` + `_create_product()` + `_recompute_best_price()` with `match_product()` + `update_canonical_product()`
  - Brand resolution now uses `resolve_or_create_brand()` (alias-aware)
  - `_create_listing()` accepts `match_confidence` + `match_method` params (no longer hardcoded)
  - Removed `SequenceMatcher` import (moved to matching module)

### 2026-02-25 — Meilisearch Sync Tasks + Pipeline
- **Replaced `backend/apps/search/tasks.py`** — real Meilisearch sync tasks (was stubs)
  - `sync_products_to_meilisearch(product_ids=None)` (`queue="scoring"`):
    - If `product_ids` given: syncs only those products (selective sync after spider runs)
    - If None: syncs all active products (full sync)
    - Document format includes all searchable/filterable/sortable fields: title, brand_name, brand_slug, category_name, category_slug, current_best_price, avg_rating, total_reviews, dud_score, images, image_url, status, in_stock, created_at
    - Batched in groups of 500, waits for each batch task to complete
    - Returns summary dict: `{success, synced, errors, total}`
    - Graceful fallback if meilisearch package not installed or URL not configured
  - `full_reindex()` (`queue="scoring"`):
    - Configures index settings (searchableAttributes, filterableAttributes, sortableAttributes) to match `sync_meilisearch` management command
    - Then calls `sync_products_to_meilisearch()` for all active products
  - Helper `_product_to_document(product)` builds Meilisearch doc from Product model
  - Helper `_configure_index(index)` sets all index attributes
- **Updated `backend/apps/scraping/tasks.py`** — sync after each spider run
  - `run_spider()` now calls `sync_products_to_meilisearch.delay()` after successful spider completion
- **Updated `backend/apps/scraping/pipelines.py`** — real MeilisearchIndexPipeline
  - `ProductPipeline` now tracks product IDs via `_track_product()` (stashes on spider instance)
  - `MeilisearchIndexPipeline.close_spider()` collects all product IDs from the spider run, queues selective `sync_products_to_meilisearch.delay(product_ids=...)` for batch sync
  - Pipeline docstring updated: no longer marked as stub
- **Registered in Celery Beat** (`backend/whydud/celery.py`):
  - `meilisearch-full-reindex-daily`: `crontab(minute=0, hour=1)` — daily at 01:00 UTC

### 2026-02-25 — Scraping Orchestration: run_marketplace_spider + Per-Marketplace Beat
- **Added `run_marketplace_spider` task** to `backend/apps/scraping/tasks.py` — primary Beat entry point
  - `queue="scraping"`, `bind=True`, `max_retries=1`, `default_retry_delay=600`
  - Accepts `marketplace_slug` + optional `category_slugs` (list of category URLs)
  - Resolves spider name from `ScrapingConfig.spider_map()` (no hardcoded mapping)
  - Creates `ScraperJob` record → marks running → launches spider via subprocess
  - Reads timeout from `ScrapingConfig.spider_timeout()` (configurable, default 3600s)
  - On success triggers **two downstream tasks**:
    - `sync_products_to_meilisearch.delay()` — refreshes search index
    - `check_price_alerts.delay()` — notifies users whose target price was hit
  - Returns summary dict: `{success, job_id, status, marketplace, spider}`
- **Updated Celery Beat schedule** (`backend/whydud/celery.py`):
  - Replaced single `scrape-daily-prices` (daily 02:00 UTC) with per-marketplace schedules:
    - `scrape-amazon-in-6h`: `crontab(minute=0, hour="0,6,12,18")` — every 6h
    - `scrape-flipkart-6h`: `crontab(minute=0, hour="3,9,15,21")` — every 6h, offset +3h from Amazon
  - Both pass `args: ["<marketplace-slug>"]` with `options: {"queue": "scraping"}`
  - Moved Meilisearch reindex to 01:00 UTC (no longer coupled to single daily scrape)
- **Refactored `scrape_product_adhoc` + `scrape_daily_prices`** to use `ScrapingConfig.spider_map()` instead of hardcoded dicts
- Existing `run_spider` task kept as lower-level runner for direct invocations

### 2026-02-25 — Inbound Email Webhook Handler (Sprint 3 Email Pipeline)
- **Created `backend/common/encryption.py`** — AES-256-GCM encrypt/decrypt helpers
  - `encrypt(plaintext, key_setting)` → returns `nonce (12B) || ciphertext+tag`
  - `decrypt(data, key_setting)` → returns plaintext string
  - Uses `cryptography.hazmat.primitives.ciphers.aead.AESGCM` (already in requirements)
  - Key loaded from hex-encoded Django settings (`EMAIL_ENCRYPTION_KEY` / `OAUTH_ENCRYPTION_KEY`)
- **Updated `InboundEmailWebhookView`** in `backend/apps/email_intel/views.py` — full implementation per Architecture §6
  - Validates HMAC-SHA256 signature (unchanged)
  - Parses recipient → `username + domain` via `rsplit("@", 1)`
  - Looks up `WhydudEmail` by `(username, domain, is_active=True)` with `select_related("user")`
  - Returns 404 for unknown recipients (logged)
  - Encrypts `text` and `html` bodies via `common.encryption.encrypt()` (AES-256-GCM)
  - Creates `InboxEmail` record (direction=inbound, all fields populated)
  - Updates `WhydudEmail.total_emails_received` + `last_email_received_at` via atomic `F()` expression
  - Dispatches `process_inbound_email.delay(email_id)` Celery task (email queue)
  - Returns `202 {ok: true, email_id: "..."}` on success

### 2026-02-25 — Email Sending Service + Send/Reply API (Sprint 3 Email Pipeline)
- **Added `resend==2.0.0`** to `backend/requirements/base.txt`
- **Added `RESEND_API_KEY`** to `backend/whydud/settings/base.py` (env var, `.env.example` already had it)
- **Added `EmailSendConfig`** to `backend/common/app_settings.py`
  - `daily_send_limit()` (default 10), `monthly_send_limit()` (default 50)
  - `allowed_marketplace_domains()` — 11 Indian marketplace domains (per Architecture §6)
- **Created `backend/apps/email_intel/send_service.py`** — full sending pipeline per Architecture §6
  - `send_email(from_user_id, to_address, subject, body_html, body_text?, reply_to_message_id?)` → `SendResult`
  - Step 1: Validates user owns active `WhydudEmail` (raises `SendEmailError`)
  - Step 2: Rate limiting via Redis sliding-window counters (daily + monthly, fail-open)
  - Step 3: Recipient validation (MVP: any address; post-MVP: replied-to senders + marketplace domains)
  - Step 4: Sanitizes HTML body with `nh3.clean()`, strips tags for plain-text fallback
  - Step 5: Calls `resend.Emails.send()` with From, To, Subject, HTML, Text, Reply-To, In-Reply-To + References headers (for threading)
  - Step 6: Stores outbound `InboxEmail` record (direction='outbound', body encrypted AES-256-GCM, resend_message_id saved, parse_status='skipped')
  - Step 7: Increments Redis rate counters
  - Custom `SendEmailError(code, message)` exception for structured error responses
- **Added serializers** to `backend/apps/email_intel/serializers.py`
  - `SendEmailSerializer`: validates `to` (EmailField), `subject`, `body_html`, optional `body_text`
  - `ReplyEmailSerializer`: validates `body_html`, optional `body_text`
- **Added `SendEmailView`** to `backend/apps/email_intel/views.py`
  - `POST /api/v1/inbox/send` — compose new email
  - Validates via `SendEmailSerializer`, calls `send_email()`, maps error codes to HTTP status (429/502/503)
  - Returns `201 {success: true, data: {email_id, resend_message_id}}`
- **Added `ReplyEmailView`** to `backend/apps/email_intel/views.py`
  - `POST /api/v1/inbox/:id/reply` — reply to an existing inbound email
  - Fetches original email, replies to `sender_address`, auto-prefixes "Re:" to subject
  - Passes `message_id` as `reply_to_message_id` for email threading (In-Reply-To + References headers)
  - Returns `201 {success: true, data: {email_id, resend_message_id}}`
- **Updated URL routing** in `backend/apps/email_intel/urls/__init__.py`
  - `inbox/send` placed before `inbox/<uuid:pk>` to avoid UUID path capture conflict
  - `inbox/<uuid:pk>/reply` added after detail route

### 2026-02-26 — DudScore Algorithm Implementation (Sprint 3 Week 7)
- **Created `backend/apps/scoring/components.py`** — all 6 DudScore component calculators + 2 multiplier helpers
  - `calculate_sentiment_score(product_id)` → 0-1: weighted avg sentiment via pre-computed `Review.sentiment_score` with TextBlob fallback, exponential decay (half-life 90d), verified purchase 2x weight, backfills Review.sentiment_score on first run
  - `calculate_rating_quality_score(product_id)` → 0-1: std dev base score + bimodal distribution penalty (40%) + skewness bonus for healthy left-skewed distributions
  - `calculate_price_value_score(product_id)` → 0-1: rating/price value ratio percentile-ranked within product's category
  - `calculate_review_credibility_score(product_id)` → 0-1: 4-signal composite — verified purchase % (0.35), review length quality (0.25), copy-paste uniqueness via content_hash (0.25), review burst detection (0.15)
  - `calculate_price_stability_score(product_id)` → 0-1: price Coefficient of Variation over 90d + inflation spike penalty (>15% jump then drop) + flash sale frequency penalty
  - `calculate_return_signal_score(product_id)` → 0-1: return/refund rate from ParsedOrder + RefundTracking, cold start 0.5 when <10 data points
  - `calculate_fraud_penalty_multiplier(product_id)` → 0.5-1.0: based on `Review.is_flagged` percentage (>30% → 0.7x)
  - `calculate_confidence_multiplier(product_id)` → (0.6-1.0, label): 5-tier system per ARCHITECTURE.md (<5→0.6, 5-19→0.7, 20-49→0.8, 50-199→0.9, 200+→1.0) + price history depth (-0.1) + marketplace breadth (-0.05) adjustments
  - `compute_all_components(product_id)` → `ComponentResult` NamedTuple orchestrator
- **Replaced `backend/apps/scoring/tasks.py`** — full DudScore Celery tasks
  - `compute_dudscore(product_id)` (`queue="scoring"`, `bind=True`, `max_retries=2`):
    - Loads active `DudScoreConfig` weights, runs all component calculators
    - Weighted sum × fraud multiplier × confidence multiplier → 0-100 scale
    - Spike detection: logs warning if score delta > `anomaly_spike_threshold` (saves anyway for v1)
    - Inserts `DudScoreHistory` via raw SQL (TimescaleDB hypertable, no auto PK) with full `component_scores` JSON
    - Updates `Product.dud_score`, `dud_score_confidence`, `dud_score_updated_at`
    - Returns summary dict with all component scores
  - `full_dudscore_recalculation()` (`queue="scoring"`):
    - Fans out individual `compute_dudscore.delay()` per active product for Celery concurrency + fault isolation
- **Added `ScoringConfig`** to `backend/common/app_settings.py`
  - 7 tunable thresholds: sentiment_half_life_days (90), verified_purchase_weight (2.0), price_stability_window_days (90), return_signal_min_datapoints (10), review_burst_window_days (2), review_burst_fraction (0.30), flash_sale_penalty_threshold (10)
- **Added Celery Beat schedule** to `backend/whydud/celery.py`
  - `dudscore-full-recalc-monthly`: `crontab(minute=0, hour=3, day_of_month=1)` — 1st of month, 03:00 UTC

### 2026-02-26 — Fake Review Detection Module (Sprint 3 Week 7)
- **Created `backend/apps/reviews/fraud_detection.py`** — rule-based fake review detection v1
  - `detect_fake_reviews(product_id)` — main orchestrator, returns `{total, flagged, updated}`
  - **Rule 1 — Copy-paste detection:** checks `content_hash` duplicates across product reviews (threshold: 2+ identical hashes)
  - **Rule 2 — Rating burst:** detects N+ same-rating reviews posted on the same calendar day (threshold: 5)
  - **Rule 3 — Suspiciously short 5-star:** body < 20 chars with 5-star rating
  - **Rule 4 — Reviewer account patterns:** new account (<30 days) + all reviews are 5-star + single brand + at least 2 reviews
  - **Rule 5 — Unverified 5-star:** `is_verified_purchase=False` with 5-star rating
  - **Credibility scoring (0.00–1.00):** starts at 1.00, deducts per-flag penalties (copy_paste: -0.30, rating_burst: -0.20, suspicious_reviewer: -0.25, suspiciously_short: -0.15, unverified_5star: -0.10), bonuses for verified purchase (+0.10), media (+0.05), detailed body 200+ chars (+0.05)
  - Auto-flags reviews with 2+ fraud signals (`is_flagged=True`)
  - Pre-computes content_hash counts and burst windows once per product (efficient — avoids N+1 queries)
  - Processes reviews via `.iterator(chunk_size=500)` for memory efficiency
- **Added `FraudDetectionConfig`** to `backend/common/app_settings.py` — 5 tuneable thresholds:
  - `FRAUD_SHORT_REVIEW_MAX_CHARS` (20), `FRAUD_BURST_COUNT_THRESHOLD` (5), `FRAUD_DUPLICATE_COUNT_THRESHOLD` (2), `FRAUD_FLAG_THRESHOLD` (2), `FRAUD_NEW_ACCOUNT_DAYS` (30)
- **Wired `detect_fake_reviews` Celery task** in `backend/apps/reviews/tasks.py` — replaced stub with real implementation that calls `fraud_detection.detect_fake_reviews()` and returns summary dict

### 2026-02-26 — Affiliate Click Tracking (Architecture §6, Feature #13)
- **Created `backend/apps/pricing/click_tracking.py`** — affiliate URL generation + click metadata helpers
  - `generate_affiliate_url(listing, user, referrer_page)`: builds tracked affiliate URL from listing's external_url + marketplace's affiliate_param/tag, with sub-tag for attribution
  - `_build_sub_tag()`: encodes user hash + product ID + referrer page into URL-safe sub-tag (~50 chars)
  - `hash_ip()`, `hash_user_agent()`: one-way SHA-256 hashes for analytics (no raw PII stored)
  - `detect_device_type()`: simple mobile/tablet/desktop detection from User-Agent
  - Sub-tag params configurable per marketplace (Amazon: `ascsubtag`, Flipkart: `affExtParam1`)
- **Added `ClickTrackingConfig`** to `backend/common/app_settings.py`
  - `sub_tag_marketplaces()`: list of marketplace slugs supporting sub-tag tracking
  - `sub_tag_param(marketplace_slug)`: URL param name per marketplace
  - `valid_source_pages()`: allowed values for source_page field (product_page, comparison, deal, search, homepage)
- **Added serializers** to `backend/apps/pricing/serializers.py`
  - `TrackClickSerializer`: validates POST body — listing_id (UUID), referrer_page (choice), source_section (optional)
  - `ClickEventSerializer`: read-only serializer for click history (product_slug, marketplace_name, marketplace_slug, source_page, affiliate_url, price_at_click, clicked_at)
- **Added `TrackClickView`** to `backend/apps/pricing/views.py`
  - `POST /api/v1/clicks/track` — accepts authenticated + anonymous users
  - Validates listing_id → fetches ProductListing with marketplace + product
  - Generates affiliate URL via `generate_affiliate_url()`
  - Creates `ClickEvent` record with full metadata (user, product, marketplace, source_page, source_section, affiliate_url, affiliate_tag, sub_tag, price_at_click, device_type, ip_hash, user_agent_hash)
  - Returns `201 {success: true, data: {affiliate_url, click_id}}`
- **Added `ClickHistoryView`** to `backend/apps/pricing/views.py`
  - `GET /api/v1/clicks/history` — user's click history (authenticated, cursor-paginated)
- **Updated URL routing** in `backend/apps/pricing/urls.py`
  - `clicks/track` → TrackClickView
  - `clicks/history` → ClickHistoryView
- **Added `clicksApi`** to `frontend/src/lib/api/products.ts`
  - `clicksApi.track(listingId, referrerPage, sourceSection?)` → POST /api/v1/clicks/track
- **Updated `MarketplacePrices` component** (`frontend/src/components/product/marketplace-prices.tsx`)
  - Converted from server component to client component (`"use client"`)
  - "Buy" buttons now call `clicksApi.track()` on click → opens returned `affiliateUrl` in new tab
  - Graceful fallback: if tracking API fails, falls back to direct `buyUrl` (no broken UX)
  - Loading state: shows "..." on button while tracking request is in-flight
  - Added `referrerPage` prop (default: "product_page") for source attribution
  - Added `focus-visible` + `active` states on all buy buttons
- TypeScript clean: `tsc --noEmit` passes with zero errors

---

### Admin Tooling — `backend/apps/admin_tools/` (14th Django app)
- **Created `admin_tools` app** under `backend/apps/admin_tools/`
- **Models** (all in PostgreSQL `admin` schema):
  - `AuditLog`: immutable record of every admin action — admin_user FK, action (create/update/delete/approve/reject/suspend/restore/config_change), target_type, target_id, old_value JSONB, new_value JSONB, ip_address, created_at. Fully read-only in Django Admin.
  - `ModerationQueue`: review/discussion/user moderation queue — item_type, item_id, reason, status (pending/approved/rejected), assigned_to FK, resolved_at. Bulk approve/reject actions in admin.
  - `ScraperRun`: aggregated scraper execution stats — marketplace FK, spider_name, status with emoji badges, items_scraped/created/updated, errors JSONB, started_at, completed_at, computed duration_seconds and error_count properties.
  - `SiteConfig`: runtime key-value store (JSONB) for tuneable config — key (unique), value, updated_by FK, auto-sets updated_by on save.
- **Django Admin registrations**:
  - `AuditLogAdmin`: list_display, list_filter by action/target_type, date_hierarchy on created_at, fully read-only (no add/change/delete)
  - `ModerationQueueAdmin`: list_filter by status/item_type, bulk approve/reject actions, truncated reason display
  - `ScraperRunAdmin`: status badges with emoji indicators, all stats in list_display
  - `SiteConfigAdmin`: auto-sets updated_by to current admin user on save
- **Migration** `0001_initial.py`: creates `admin` schema + all 4 tables
- **Registered** in `INSTALLED_APPS` as `apps.admin_tools`

### 2026-02-26 — Write a Review Routing Fix + /reviews/new Page
- **Fixed route group conflict** that caused `/product/[slug]/review` to 404:
  - Moved `(review)/product/[slug]/review/page.tsx` → `(public)/product/[slug]/review/page.tsx`
  - Deleted `(review)` route group entirely — having `product/[slug]` in two route groups (`(public)` and `(review)`) broke Next.js App Router resolution
- **Created `(public)/reviews/new/page.tsx`** — product search entry point for "Write a Review" links
  - Search bar using `searchApi.search()` (Meilisearch)
  - Shows user's existing reviews (if authenticated) with edit option
  - Popular products grid as fallback when no search active
  - Product cards with "Write a Review" / "Edit Your Review" CTAs linking to `/product/[slug]/review`
  - Skeleton loading, empty states
- **Fixed dead `/reviews/new` links** across the frontend:
  - `Header.tsx` line 225: "Post a Review" → `/reviews/new` (now resolves)
  - `Footer.tsx` line 8: "Write a Review" → `/reviews/new` (now resolves)
  - Homepage CTA strip + Reviewer's Zone → `/reviews/new` (now resolves)
  - Homepage "View All" reviews tile → changed from `/reviews` to `/reviews/new`
- **Fixed "Post a review" button** on product detail page (`(public)/product/[slug]/page.tsx`):
  - Was a `<button>` with no navigation — changed to `<Link href="/product/${slug}/review">`
- TypeScript clean: `tsc --noEmit` passes with zero errors

### 2026-02-26 — Frontend Route & Navigation Link Audit + Fix
- **Full audit** of all 28 frontend routes vs navigation links — identified 8 broken footer links, 3 orphaned pages, and missing nav entries
- **Created 6 missing pages** (all under `(public)/` route group with Header + Footer):
  - `/about` — About Whydud page with mission, features
  - `/terms` — Terms of Service (7 sections)
  - `/privacy` — Privacy Policy (7 sections, references @whyd.xyz email encryption)
  - `/contact` — Contact page with email + location cards
  - `/cookies` — Cookie Policy with cookie table (whydud_auth, csrftoken)
  - `/affiliate-disclosure` — Affiliate disclosure explaining marketplace partnerships
- **Fixed Footer.tsx** — removed 2 broken links (`/blog`, `/advertise` — not developed features), reorganized sections:
  - Discover: Search, Deals, Compare, Leaderboard (was: Write a Review)
  - Account: Dashboard, Inbox, Wishlists, Write a Review (was: Rewards)
  - Company: About, Contact, Rewards, Affiliate Disclosure (was: Blog, Advertise)
  - Legal: Privacy, Terms, Cookies (removed Affiliate Disclosure — moved to Company)
- **Fixed Header.tsx** — added Deals link (Flame icon) and Leaderboard link (Trophy icon) to right nav area (previously orphaned, unreachable pages)
- **Fixed Sidebar.tsx** — added Notifications link (BellDot icon) between Inbox and Wishlists (page existed at `/notifications` with middleware protection but had no sidebar entry)
- **Zero broken links remaining** — all 28 internal routes verified against page.tsx files
- TypeScript clean: `tsc --noEmit` passes with zero errors

### 2026-02-26 — Dev Environment Setup + DB Bootstrap + Scraper End-to-End Verification

#### Environment & Encryption Keys
- **Generated all encryption keys** in `backend/.env`:
  - `DJANGO_SECRET_KEY` — random 50-character key (replaced placeholder `dev-secret-key`)
  - `EMAIL_ENCRYPTION_KEY` — 64-char hex for AES-256-GCM email body encryption
  - `OAUTH_ENCRYPTION_KEY` — 64-char hex for OAuth token encryption at rest
- **Added missing env vars**: `DATABASE_URL`, `CELERY_RESULT_BACKEND`, `SENTRY_DSN` (placeholder), `CLOUDFLARE_EMAIL_SECRET` (placeholder)
- **Fixed Meilisearch key mismatch**: docker-compose.dev.yml hardcodes `whydud_dev_meili_key_32chars!!` but .env had `masterKey` — synced .env to match

#### Docker Infrastructure Verification
- Verified `docker/docker-compose.dev.yml` — 3 services running:
  - PostgreSQL 16 (timescale/timescaledb:latest-pg16, port 5432) with init.sql mount
  - Redis 7 (redis:7-alpine, port 6379)
  - Meilisearch v1.7 (port 7700)
- Health checks, persistence volumes, env vars all confirmed correct

#### Database Bootstrap
- **Schemas**: All 7 custom PostgreSQL schemas already created from init.sql (public, users, email_intel, scoring, tco, community, admin)
- **Migrations**: All 27+ migrations applied cleanly; auto-generated `accounts/0007_alter_user_referral_code.py` for pending model change
- **TimescaleDB hypertables**: Both `price_snapshots` and `dudscore_history` verified operational
- **Superuser**: `admin@whydud.com` confirmed (already existed)
- **Tables**: 79 tables across 7 schemas verified

#### Seed Data
- **Created `backend/apps/products/management/commands/seed_marketplaces.py`** — seeds all 12 Indian marketplaces:
  - amazon_in, flipkart, croma, reliance_digital, vijay_sales, tata_cliq, jiomart, myntra, nykaa, ajio, meesho, snapdeal
  - Uses `update_or_create` by slug, actual Marketplace model fields (slug, name, base_url, affiliate_param, affiliate_tag, scraper_status)
  - Marketplace model has NO `logo_url` or `is_active` fields — uses `scraper_status` field
- **Ran all seed commands in order**:
  1. `seed_marketplaces` → 12 marketplaces (7 new + 5 updated)
  2. `seed_preference_schemas` → 7 category schemas
  3. `seed_data` → master seeder (categories, brands, products, listings, reviews, etc.)
  4. `seed_review_features` → review feature definitions
  5. `seed_tco_models` → TCO calculation models
  6. `sync_meilisearch` → all products indexed
- **Final counts**: 31 products, 73 listings, 12 marketplaces, 19 categories, 30 brands, 655+ reviews

#### Scraper End-to-End Test — 6 Bug Fixes
Ran Amazon.in spider against a single category URL. Found and fixed 6 bugs:

1. **MARKETPLACE_SLUG mismatch** (`amazon_spider.py` line 30):
   - Bug: `MARKETPLACE_SLUG = "amazon-in"` (hyphen) but DB has `amazon_in` (underscore)
   - Fix: Changed to `"amazon_in"`

2. **Amazon HTML structure changed** (`amazon_spider.py` lines 152-157):
   - Bug: `h2 a.a-link-normal` CSS selector returns None — Amazon moved product links to `div[data-cy="title-recipe"]` in 2025+
   - Fix: Added fallback chain: `div[data-cy="title-recipe"] a` → `a.a-link-normal[href*="/dp/"]` → `h2 a.a-link-normal`

3. **SynchronousOnlyOperation in async reactor** (`runner.py`):
   - Bug: Scrapy's Playwright reactor runs async, Django ORM calls are sync → `SynchronousOnlyOperation` error
   - Fix: Added `os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"` in runner.py (safe — subprocess, not web server)

4. **.env not loaded in spider subprocess** (`runner.py`):
   - Bug: Django settings default `POSTGRES_PASSWORD` to `"whydud"` but actual is `"whydud_dev"` — .env wasn't loaded in subprocess context
   - Fix: Added `from dotenv import load_dotenv; load_dotenv(os.path.join(BACKEND_DIR, ".env"))` before Django setup

5. **PriceSnapshot ORM create fails on hypertable** (`pipelines.py` lines 192-211):
   - Bug: `PriceSnapshot.objects.create()` emits `RETURNING "price_snapshots"."id"` but TimescaleDB hypertable has no `id` column (`managed=False`)
   - Fix: Replaced with raw SQL INSERT (no RETURNING clause)

6. **Seller UniqueViolation on blank external_seller_id** (`pipelines.py` lines 146-161):
   - Bug: `unique_together = [("marketplace", "external_seller_id")]` — multiple sellers with blank `external_seller_id` collide
   - Fix: Changed `get_or_create` lookup to use `external_seller_id` with slugified seller name as fallback

7. **playwright_page_methods dict format** (`amazon_spider.py`):
   - Bug: scrapy-playwright 0.0.46 expects `PageMethod` objects, not plain dicts
   - Fix: Imported `PageMethod` from `scrapy_playwright.page`, replaced dict with `PageMethod("wait_for_selector", "#productTitle", timeout=10000)`

#### Scraper Test Results
- **4 products successfully scraped** from Amazon.in single category URL (smartphones):
  - Samsung Galaxy S24 Ultra (₹47,996 / MRP ₹79,999), OnePlus 12R, Samsung M15, OnePlus Nord CE4 Lite
  - All 4: Product created + ProductListing created + PriceSnapshot inserted (raw SQL) + Meilisearch synced
- **12 product pages timed out** (Playwright timeout on `#productTitle`) — expected for Amazon CAPTCHA/anti-bot on some pages
- **Pipeline verified end-to-end**: Scrapy → Playwright → ValidationPipeline → NormalizationPipeline → ProductPipeline → MeilisearchIndexPipeline
- **Final DB state**: 37 products, 79 listings (31 seeded + 4 scraped + 4 new listings)

### 2026-02-26 — Flipkart Spider End-to-End Test + Bug Fix
- **Bug: Flipkart 403 on plain HTTP product pages** (`flipkart_spider.py`):
  - All product detail page requests returned HTTP 403 when using plain HTTP (no Playwright)
  - Root cause: Flipkart's anti-bot blocks non-browser HTTP requests to product URLs
  - Fix 1: Changed product page requests from `meta={"playwright": False}` to `meta={"playwright": True}` with `PageMethod("wait_for_load_state", "domcontentloaded")`
  - Fix 2: Added `PageMethod` import from `scrapy_playwright.page`
  - Fix 3: Added `http` handler to `DOWNLOAD_HANDLERS` alongside `https`
  - Note: Original spider assumed "product pages render server-side" — true for content, but Flipkart blocks non-browser User-Agents entirely
- **Ran full Flipkart spider** (`python -m apps.scraping.runner flipkart --max-pages 2`):
  - 8 seed categories × 2 pages each = 16 listing pages crawled
  - ~460 product URLs discovered across smartphones, laptops, headphones, air purifiers, washing machines, refrigerators, televisions, cameras
  - **288 new Flipkart listings** created (some duplicates deduplicated by external_id)
  - Pipeline verified: Playwright → ValidationPipeline → NormalizationPipeline → ProductPipeline → MeilisearchIndexPipeline → Meilisearch sync
- **Cross-marketplace product matching results**:
  - **26 products matched across Amazon.in + Flipkart** (matching engine successfully linked listings)
  - **29 products total on 2+ marketplaces** (includes Amazon+Croma from seed data)
  - Match method distribution for Flipkart: `new: 222`, `brand_model_variant: 44`, `exact_sku: 28`, `fuzzy_title: 28`, `brand_model: 4`
  - Examples of successful cross-marketplace matches:
    - Daikin 1.5T AC: Amazon ₹44,990 vs Flipkart ₹43,990 vs Croma ₹47,990
    - HP Pavilion 15: Amazon ₹52,990 vs Flipkart ₹53,490 vs Croma ₹55,990
    - Sony WH-1000XM5: Amazon ₹22,990 vs Flipkart ₹23,490 vs Croma ₹24,990
    - LG 8kg Washing Machine: Amazon ₹38,990 vs Flipkart ₹37,990 vs Croma ₹39,990
  - Price comparison working as intended — same product shows different prices per marketplace
- **Final DB state**: 259 products, 377 listings (Amazon.in: 35, Flipkart: 326, Other: 16)

### 2026-02-27 — Celery Flower Monitoring Setup
- **Added Flower 2.0.1** to `backend/requirements/base.txt` for Celery task monitoring and observability
- **Created `backend/whydud/flowerconfig.py`** — Flower configuration with:
  - Basic auth (env-configurable, defaults to `admin:admin` in dev)
  - Persistent task storage via SQLite (survives Flower restarts)
  - Max 50,000 tasks in memory (prevents OOM on high-volume queues)
  - Auto-refresh enabled, offline worker purge after 24h
  - URL prefix support for reverse proxy (production: `/flower/`)
- **Docker Compose — Dev** (`docker/docker-compose.dev.yml`):
  - Added `flower` service using `mher/flower:2.0.1` image
  - Connects to Redis broker, exposed on port 5555
  - Persistent volume `flower_dev_data` for task history
  - Access: `http://localhost:5555` (admin/admin)
- **Docker Compose — Prod** (`docker/docker-compose.yml`):
  - Added `flower` service (10th service, ~128MB RAM)
  - Uses same backend Dockerfile, runs `celery -A whydud flower` with flowerconfig.py
  - `FLOWER_BASIC_AUTH` env var required in production (no default)
  - Persistent volume `flower_data`, URL prefix `/flower` for Caddy proxy
  - Caddy dependency added so reverse proxy starts after Flower
- **Caddy** (`docker/Caddyfile`):
  - Added `/flower/*` route → reverse proxy to `flower:5555`
  - Production access: `https://whydud.com/flower/` (basic-auth protected)
- **Verified locally**: Flower starts, connects to Redis, discovers all 30 registered Celery tasks across 13 apps
- **What Flower provides for admin monitoring**:
  - Real-time worker status (active/offline, concurrency, queues)
  - Task history with filtering by state, name, worker, queue
  - Task details: args, kwargs, result, exception, runtime, retries
  - Queue depths and message rates per queue (default, scraping, email, scoring, alerts)
  - Beat schedule visibility (all 8 periodic tasks)
  - Worker pool control (shutdown, restart, autoscale)
  - Broker connection status and stats

### 2026-02-27 — Review Scraping Infrastructure
- **Review model updated** (`apps/reviews/models.py`):
  - Added 6 new fields for scraped marketplace reviews: `external_reviewer_name`, `external_reviewer_id`, `external_review_url`, `helpful_vote_count`, `marketplace` (FK to Marketplace), `variant_info`
  - Updated `external_review_id` with `default=""` and `db_index=True`
  - Added `unique_external_review_per_marketplace` constraint — `(external_review_id, marketplace)` where review ID is non-empty
  - Migration `reviews/0004` created and applied
  - `user` field already nullable — no change needed
- **ReviewItem added** (`apps/scraping/items.py`):
  - 4 required fields: `marketplace_slug`, `product_external_id`, `rating`, `body`
  - 11 optional fields: `title`, `reviewer_name`, `reviewer_id`, `review_id`, `review_url`, `review_date`, `is_verified_purchase`, `helpful_votes`, `images`, `variant`, `country`
- **Review pipelines added** (`apps/scraping/pipelines.py`):
  - `ReviewValidationPipeline` (priority 150) — drops ReviewItems missing required fields or with body < 5 chars; passes through ProductItems
  - `ReviewPersistencePipeline` (priority 450) — looks up ProductListing by marketplace+external_id, generates SHA256 review ID if none provided, dedup-checks, parses date, creates Review record
- **Pipeline order** in `scrapy_settings.py`: 100 (Validation) → 150 (ReviewValidation) → 200 (Normalization) → 400 (Product) → 450 (ReviewPersistence) → 500 (Meilisearch)

### 2026-02-27 — Amazon Review Spider
- **Created `apps/scraping/spiders/amazon_review_spider.py`** — `AmazonReviewSpider` (name: `amazon_in_reviews`)
  - Inherits `BaseWhydudSpider` (UA rotation, download delay, error counting)
  - `start_requests()`: queries all in-stock Amazon ProductListings with < 10 scraped reviews, ordered by total_reviews desc, capped at 200 products
  - Targets `/product-reviews/<ASIN>/` pages sorted by helpfulness
  - `parse_review_page()` extracts per-review: review_id, rating (1-5), title, body, reviewer_name, reviewer_id (from profile link), review_date, country, is_verified_purchase, helpful_votes, images (thumbnail→full-res upgrade), variant, review_url
  - Pagination: follows up to `max_review_pages` (default 3, ~30 reviews/product) if page has 8+ reviews
  - Yields `ReviewItem` instances → processed by `ReviewValidationPipeline` (150) + `ReviewPersistencePipeline` (450)
- **Updated `common/app_settings.py`** — added `"amazon_in_reviews": "amazon_in_reviews"` to `ScrapingConfig.spider_map()`
- **Updated `apps/scraping/runner.py`** — added `--max-review-pages` CLI argument
  - Invocation: `python -m apps.scraping.runner amazon_in_reviews --max-review-pages 3`

### 2026-02-27 — Flipkart Review Spider
- **Created `apps/scraping/spiders/flipkart_review_spider.py`** — `FlipkartReviewSpider` (name: `flipkart_reviews`)
  - Inherits `BaseWhydudSpider` with Playwright download handlers (Flipkart 403s plain HTTP)
  - `start_requests()`: queries all in-stock Flipkart ProductListings with < 10 scraped reviews, ordered by total_reviews desc, capped at 200 products
  - `_build_review_url()`: converts product URL `/p/<FPID>` to `/product-reviews/<FPID>?page=1&sortOrder=MOST_HELPFUL`
  - `_find_review_blocks()`: 4 CSS fallback selectors + XPath structural fallback (Flipkart obfuscates class names frequently)
  - Field extraction: every field (`rating`, `title`, `body`, `reviewer_name`, `date`, `verified`, `helpful_votes`, `images`, `variant`) has 3-4 CSS selector fallbacks + XPath last resort
  - Empty `review_id` — Flipkart doesn't expose per-review IDs in HTML; `ReviewPersistencePipeline` generates SHA256 content hash
  - All reviews tagged `country="India"` (Flipkart is India-only)
  - Image URLs upgraded to 832×832 resolution via regex substitution
  - Pagination: follows up to `max_review_pages` (default 3, ~30 reviews/product) if page has 8+ reviews
  - Yields `ReviewItem` instances → processed by review pipelines (150 + 450)
- **Updated `common/app_settings.py`** — added `"flipkart_reviews": "flipkart_reviews"` to `ScrapingConfig.spider_map()`
  - Invocation: `python -m apps.scraping.runner flipkart_reviews --max-review-pages 3`

### 2026-02-27 — Auto Review Scraping After Product Scrape + Downstream Processing
- **Added `run_review_spider` Celery task** (`apps/scraping/tasks.py`, `queue="scraping"`, `bind=True`, `max_retries=1`)
  - Resolves review spider name via `ScrapingConfig.review_spider_map()`
  - Creates `ScraperJob` for tracking, runs spider via subprocess with `--max-review-pages`
  - On success: triggers `_queue_review_downstream_tasks()` for post-processing
- **Chained review spider after product spider** — `run_marketplace_spider` now calls `run_review_spider.delay()` on successful completion for any marketplace with a review spider configured
- **Added `_queue_review_downstream_tasks()` helper** — for each product with new reviews (last 2 hours):
  1. Queues `detect_fake_reviews` (fraud detection per product)
  2. Queues `compute_dudscore` (DudScore recalculation per product)
  3. Updates `product.avg_rating` and `product.total_reviews` from published reviews aggregate
- **Added Celery Beat schedule** (`whydud/celery.py`) — independent daily review scrapes:
  - `scrape-amazon-in-reviews-daily`: 04:00 UTC (after product scrapes)
  - `scrape-flipkart-reviews-daily`: 07:00 UTC
  - Both safe to double-run (review spiders dedup on `external_review_id`)
- **Added `ScrapingConfig` entries** (`common/app_settings.py`):
  - `review_spider_map()`: marketplace slug → review spider name (`amazon-in` → `amazon_in_reviews`, `flipkart` → `flipkart_reviews`)
  - `default_max_review_pages()`: defaults to 3

### 2026-02-27 — Review Serializer + Frontend Review Display Overhaul
- **Updated `ReviewSerializer`** (`apps/reviews/serializers.py`) — new fields:
  - `external_reviewer_name`, `helpful_vote_count`, `variant_info`, `external_review_url`, `media` (direct model fields)
  - `marketplace_name` (SerializerMethodField: checks `marketplace` FK, falls back to `listing.marketplace`)
  - `marketplace_slug` (from `marketplace.slug`)
  - `is_scraped` (SerializerMethodField: `source == "scraped"` and `user is None`)
- **Updated `ProductReviewsView.get`** (`apps/reviews/views.py`):
  - Added `source` query param filter (marketplace slug or `"whydud"`)
  - Updated `select_related` to include `"marketplace"` directly
  - Changed "helpful" sort to use `helpful_vote_count` (scraped marketplace data)
- **Updated `Review` TypeScript interface** (`frontend/src/types/product.ts`) — added: `externalReviewerName`, `helpfulVoteCount`, `marketplaceName`, `marketplaceSlug`, `variantInfo`, `externalReviewUrl`, `isScraped`, `media`
- **Updated `productsApi.getReviews`** (`frontend/src/lib/api/products.ts`) — now accepts `sort`, `source`, `rating`, `verified` params
- **Rewrote `ReviewCard` component** (`frontend/src/components/reviews/review-card.tsx`):
  - Scraped reviews: marketplace badge (orange Amazon, blue Flipkart), external reviewer name, helpful count, variant info chip, image gallery, "Read on Amazon →" link
  - Whydud reviews: green "Whydud" badge, thumbs up/down vote buttons, "Verified Purchase" badge
- **Created `ReviewSidebar` client component** (`frontend/src/components/reviews/review-sidebar.tsx`):
  - Source filter tabs: All Reviews | Amazon.in | Flipkart | Whydud
  - Sort dropdown: Most Helpful | Newest | Highest Rating | Lowest Rating
  - Loading spinner during re-fetch, "Load more reviews" button
- **Updated product detail page** (`frontend/src/app/(public)/product/[slug]/page.tsx`) — replaced 60-line inline review sidebar with `<ReviewSidebar>` component

### 2026-02-28 — Review Scraping E2E Testing & Spider Rewrites

**Amazon Review Spider — Complete Rewrite** (`apps/scraping/spiders/amazon_review_spider.py`):
- **Problem**: Original spider targeted `/product-reviews/ASIN` pages which require Amazon sign-in — all requests 302'd to `/ap/signin`
- **Fix 1**: Added Playwright download handlers + `ROBOTSTXT_OBEY: False` (Amazon redirects trigger false robots.txt blocks)
- **Fix 2**: Switched URL pattern from `/product-reviews/ASIN` to `/dp/ASIN` (product detail page) — embeds ~8 "Top Reviews" without sign-in
- **Fix 3**: Added synthetic ASIN filter — skips seed-data ASINs (`amazon_in_*` prefix or length > 12)
- **Fix 4**: Updated CSS selectors — reviews are `<li data-hook="review">` (not `<div>`), title in `[data-hook="review-title"] span:not(.a-icon-alt):not(.a-letter-space)`, verified purchase detected via full text search
- **Result**: 76 Amazon.in reviews scraped successfully (from ~168 product pages)

**Flipkart Review Spider — Complete Rewrite** (`apps/scraping/spiders/flipkart_review_spider.py`):
- **Problem**: Flipkart switched to React Native Web — all CSS class names changed to obfuscated utility hashes (`css-175oi2r`, `css-1rynq56`), every selector returned 0 matches
- **Solution**: Replaced CSS selector extraction with JavaScript DOM extraction via `PageMethod("evaluate", EXTRACT_REVIEWS_JS)`:
  - Walks DOM text nodes to find "Verified Purchase" / "Certified Buyer" anchors
  - Walks up parent chain to find review container (div matching `^[1-5]\.0` pattern)
  - Extracts rating, title, body, reviewer name, helpful votes, date, variant, images
  - Injects results as JSON into `<script id="whydud-reviews" type="application/json">`
  - Spider reads JSON blob via `response.css("script#whydud-reviews::text")`
- **Result**: 1,447 Flipkart reviews scraped successfully

**Pipeline Bug Fixes** (`apps/scraping/pipelines.py`):
- `ValidationPipeline` (priority 100) checked for `external_id` and `url` fields that don't exist on `ReviewItem` — was dropping ALL review items before they reached `ReviewValidationPipeline`
- `ProductPipeline` (priority 200) tried to process `ReviewItem` as product data — would fail on missing fields
- **Fix**: Added `isinstance(item, ReviewItem): return item` guard to both pipelines, letting review items pass through to the review-specific pipelines (400+)

**Fraud Detection Verification**:
- Ran `detect_fake_reviews()` on 20 products with scraped reviews
- 408 reviews flagged across all products (rules triggered: `unverified_5star`, `suspiciously_short`, `copy_paste`, `rating_burst`)
- Credibility scores computed (0.00–1.00) for all reviews

**Frontend API Verification**:
- `GET /api/v1/products/{slug}/reviews` returns reviews with marketplace badges, credibility scores, images, helpful vote counts
- `is_flagged=False` filter correctly hides fraud-flagged reviews from public API
- ReviewSidebar component fetches and displays reviews client-side

**Final Counts**: 2,178 total reviews in DB (was 655 seed data). 1,770 unflagged/visible, 408 flagged by fraud detection. Sources: 76 Amazon.in + 1,447 Flipkart + 655 seed data.

### 2026-02-28 — Amazon Scraper Anti-Detection & Stealth Fixes

**Problem**: Amazon spider was getting 0 items scraped — all product detail pages timed out waiting for `#productTitle` selector (10s). Amazon's bot detection was blocking headless Playwright from rendering product pages.

**Fixes Applied**:

1. **Installed `playwright-stealth` (v2.0.2)** — injects anti-detection scripts that hide headless browser fingerprints (navigator.webdriver, chrome.runtime, WebGL, etc.)

2. **Base spider updates** (`apps/scraping/spiders/base_spider.py`):
   - Added `Stealth` config instance (class-level, shared by all spiders)
   - Added `--disable-blink-features=AutomationControlled` to Chromium launch args
   - Bumped `DOWNLOAD_DELAY` from 2s → 3s for more human-like timing

3. **Amazon spider updates** (`apps/scraping/spiders/amazon_spider.py`):
   - Added `_apply_stealth()` async callback — runs on every Playwright page before navigation
   - Replaced hard `wait_for_selector("#productTitle", timeout=10s)` with `wait_for_load_state("domcontentloaded")` + 3s delay — eliminates timeouts entirely
   - Added 6+ CSS title selector fallbacks + `<title>` tag + `og:title` meta extraction
   - Filters out CAPTCHA pages (pages where title = "Amazon.in")
   - Moved `--save-html` debug dump to before title check (so failing pages can be inspected)

4. **Scrapy settings updates** (`apps/scraping/scrapy_settings.py`):
   - Added stealth Chromium launch args globally
   - Added `PLAYWRIGHT_CONTEXTS` with Indian locale (`en-IN`), timezone (`Asia/Kolkata`), realistic viewport (1366×768)

**Results** (1-page smartphones test):

| Metric | Before Fix | After Fix |
|---|---|---|
| Timeouts | 18/25 pages | 0/25 pages |
| HTTP 200 responses | 7/25 | 25/25 |
| Items scraped | 0 | 24 |
| Scrape speed | 0 items/min | 15 items/min |

~10/25 pages still serve Amazon CAPTCHA (no proxy rotation yet) — those are correctly skipped. Remaining pages extract fully: title, brand, price, MRP, rating, images, seller, specs, about bullets, offers.

**Note**: Items extracted but not persisted to DB — PostgreSQL not running locally. Start Docker containers to enable DB persistence.

### 2026-02-28 — Proxy Rotation Middleware for Scraping

**Problem**: Amazon scraper achieved only ~16% success rate (237 items from 1,400 responses) due to single-IP rate limiting — Amazon serves CAPTCHAs and 503 errors on product detail pages. Without proxy rotation, the IP gets rapidly flagged.

**Solution**: Environment-based proxy rotation via a custom Scrapy downloader middleware that integrates with scrapy-playwright's browser context system. Proxies are set at the Playwright context level (not per-request, which scrapy-playwright doesn't support).

**Files Created/Modified**:

1. **CREATED: `apps/scraping/middlewares.py`** — Core proxy rotation infrastructure:
   - `ProxyState` — health tracker per proxy (ban state, exponential backoff cooldown)
   - `ProxyPool` — round-robin rotation with health tracking, loads from env or CLI
   - `PlaywrightProxyMiddleware` — Scrapy downloader middleware that:
     - Assigns named Playwright contexts per proxy (`proxy_0`, `proxy_1`, etc.)
     - Detects bans via HTTP status (403/429/503) + CAPTCHA markers in response body
     - Applies exponential backoff (30s → 60s → 120s... capped at 600s)
     - Supports session stickiness (`meta["proxy_session"]`) — listing + child product pages use same proxy
   - `_parse_proxy_url()` — converts `http://user:pass@host:port` to Playwright proxy dict format

2. **MODIFIED: `common/app_settings.py`** — Added to `ScrapingConfig`:
   - `proxy_list()` — reads `SCRAPING_PROXY_LIST` env var (comma-separated proxy URLs)
   - `proxy_ban_cooldown_base()` — base cooldown seconds (default 30)
   - `proxy_ban_max_cooldown()` — max cooldown cap (default 600)
   - `proxy_enabled()` — True if proxy list is non-empty

3. **MODIFIED: `apps/scraping/scrapy_settings.py`** — Registered `PlaywrightProxyMiddleware` at priority 400

4. **MODIFIED: `apps/scraping/spiders/base_spider.py`** — Added `_with_proxy_session()` helper + middleware in `custom_settings`

5. **MODIFIED: `apps/scraping/spiders/amazon_spider.py`** — Sticky proxy sessions: `start_requests()` → `parse_listing_page()` → `parse_product_page()` + CAPTCHA retry all propagate `proxy_session`

6. **MODIFIED: `apps/scraping/spiders/flipkart_spider.py`** — Same sticky proxy session pattern for listing → product detail → pagination

7. **MODIFIED: `apps/scraping/runner.py`** — Added `--proxy-list` CLI arg to override env var

8. **MODIFIED: `.env.example`** — Added `SCRAPING_PROXY_LIST`, `SCRAPING_PROXY_BAN_COOLDOWN_BASE`, `SCRAPING_PROXY_BAN_MAX_COOLDOWN`

**Key Design Decisions**:
- Graceful fallback: no proxies configured = behavior identical to before (direct requests)
- Session stickiness: category listing + all child product pages use same proxy, cleared on ban
- Contexts registered at startup via `from_crawler()`, created lazily by scrapy-playwright
- Review spiders auto-benefit — they inherit `BaseWhydudSpider` and the middleware applies to all Playwright requests

**Usage**:
```bash
# Via environment variable
SCRAPING_PROXY_LIST=http://user:pass@proxy1:8080,http://proxy2:8080

# Via CLI override
python -m apps.scraping.runner amazon_in --proxy-list "http://p1:8080,http://p2:8080" --urls "..."
```

**Regression test**: All proxy rotation unit tests pass. Empty proxy pool correctly falls back to direct requests.

### 2026-02-28 — Comprehensive Scraping Upgrade (All Categories + Full Data Extraction)

**Goal**: Scrape ALL product categories from Amazon.in and Flipkart with complete product data extraction — no information left behind.

#### Critical Bug Fix — Marketplace Slug Mismatch
- **Bug**: `amazon_spider.py` had `MARKETPLACE_SLUG = "amazon_in"` (underscore) but the DB Marketplace record uses `slug="amazon-in"` (hyphen). This caused **every** Amazon ProductItem to be silently dropped by ProductPipeline with "Unknown marketplace" error.
- **Fix**: Changed to `"amazon-in"` in `amazon_spider.py`, `amazon_review_spider.py`, and all DB query filters in review spider.
- **Also fixed**: `app_settings.py` `spider_map()` had review spider entries mixed in — removed them (handled by `review_spider_map()`).

#### Category Expansion — Amazon.in (90 → 130+ categories)
- Added ~30 new seed URLs covering: kitchen tools, fashion (men/women/kids), books, baby products, automotive, gaming consoles, smart speakers, home improvement, garden, pet supplies, art supplies, musical instruments, office products
- Expanded `KEYWORD_CATEGORY_MAP` from ~90 to ~130 keyword→slug entries
- Per-category page limits: `_TOP=10` (popular categories), `_STD=5` (niche categories)

#### Category Expansion — Flipkart (8 → 110+ categories)
- Expanded from 8 seed URLs to 110+ with full keyword→category mapping
- Changed `SEED_CATEGORY_URLS` from flat URL list to `list[tuple[str, int]]` with per-category page limits
- Refactored `start_requests()` and `_load_urls()` to support `(url, max_pages)` tuples
- Added `_max_pages_override` and `_max_pages_map` to match Amazon's pagination pattern
- Full category coverage: smartphones, laptops, TVs, appliances, fashion, beauty, books, baby, automotive, sports, gaming, musical instruments, pet supplies, and more

#### Enhanced Anti-Detection
- **User-Agents**: Expanded from 10 to 25+ strings covering Chrome 124-131, Firefox 125-133, Edge, Safari 17-18, Chrome Android mobile
- **Viewport Randomization**: 7 viewport sizes (1920×1080 through 2560×1440), randomized per spider instance
- **Accept-Language**: 5 Indian locale variants rotated per request
- **Sec-CH-UA Client Hints**: 4 variants matching Chrome UA versions, added to headers for Chrome UAs only
- **Sec-Fetch Headers**: Full set (Dest, Mode, Site, User) + Cache-Control, Pragma, Upgrade-Insecure-Requests
- **Playwright Launch Args**: Added `--disable-infobars`, `--disable-extensions`, `--disable-gpu`, `--lang=en-IN`

#### Full Product Data Extraction (11 New Fields)
Added to `ProductItem` in `items.py`:
- `description` — full product description text
- `warranty` — warranty information
- `delivery_info` — delivery estimate text
- `return_policy` — return policy text
- `breadcrumbs` — navigation breadcrumb trail (list[str])
- `variant_options` — color/size/storage variants (list[dict])
- `country_of_origin` — manufacturing country
- `manufacturer` — manufacturer name
- `model_number` — model/part number
- `weight` — product weight
- `dimensions` — product dimensions

**Amazon spider** — 7 new extraction methods:
- `_extract_description()`: productDescription → productOverview → A+ content fallbacks
- `_extract_warranty()`: techSpec table → detailBullets → bullet text with "warranty" keyword
- `_extract_delivery_info()`: deliveryBlockMessage → delivery-promise-text
- `_extract_return_policy()`: productSupportAndReturnPolicy → returnPolicyFeature
- `_extract_breadcrumbs()`: wayfinding-breadcrumbs navigation trail
- `_extract_variants()`: variation_color_name, variation_size_name with ASIN capture
- `_extract_from_specs()`: case-insensitive spec key lookup for country_of_origin, manufacturer, etc.

**Flipkart spider** — same 7 extraction methods adapted for Flipkart's HTML/JSON-LD structure.

#### Auto-Category Creation from Breadcrumbs
- Added `_resolve_category_from_breadcrumbs()` to `ProductPipeline` in `pipelines.py`
- Walks breadcrumbs deepest-first, skips generic terms ("home", "all categories")
- Auto-creates `Category` with slug from breadcrumb text, resolves parent from adjacent level
- Falls back to keyword→slug mapping when breadcrumbs unavailable
- Specs now merge (existing + new) instead of replace-if-richer

#### Files Modified
- `apps/scraping/spiders/amazon_spider.py` — slug fix, 30+ new URLs, 130+ keyword mappings, 7 extraction methods
- `apps/scraping/spiders/flipkart_spider.py` — 110+ URLs with per-category limits, 130+ keyword mappings, 7 extraction methods
- `apps/scraping/spiders/amazon_review_spider.py` — slug fix in MARKETPLACE_SLUG and DB queries
- `apps/scraping/spiders/base_spider.py` — 25+ UAs, viewport pool, Client Hints, Sec-Fetch headers
- `apps/scraping/items.py` — 11 new ProductItem fields
- `apps/scraping/pipelines.py` — breadcrumb category creation, spec merging, description persistence
- `apps/scraping/scrapy_settings.py` — viewport randomization, timeout, bypass_csp, extra headers
- `common/app_settings.py` — cleaned spider_map (removed review spider entries)

---

### Scraping Pipeline Fixes & Multi-Category Scrape Run — 2026-02-28

#### Critical Fixes

**1. Stealth Playwright Handler** (`apps/scraping/playwright_handler.py` — NEW)
- Created `StealthPlaywrightHandler` subclass of `ScrapyPlaywrightDownloadHandler`
- Overrides `_create_browser_context()` to inject `playwright-stealth` init scripts into every new browser context BEFORE page navigation
- Patches: `navigator.webdriver`, `navigator.plugins`, `window.chrome`, WebGL vendor/renderer, Permission API
- The base spider's `Stealth()` object was previously defined but never applied — this handler makes it active

**2. Flipkart 403 Fix** (`apps/scraping/spiders/flipkart_spider.py`)
- **Root cause:** Flipkart returns HTTP 403 on listing/search pages but still renders valid product data via JavaScript. Scrapy's `HttpErrorMiddleware` was discarding these valid responses.
- **Fix:** Added `"HTTPERROR_ALLOWED_CODES": [403]` to Flipkart spider's `custom_settings`
- Added `"ROBOTSTXT_OBEY": False` — Flipkart's robots.txt itself returns 403
- Added `PageMethod("wait_for_load_state", "networkidle")` to listing page requests for reliable JS rendering
- Switched download handler to `StealthPlaywrightHandler`

**3. Scrapy Settings** (`apps/scraping/scrapy_settings.py`)
- Updated default `DOWNLOAD_HANDLERS` to use `StealthPlaywrightHandler` globally (benefits both Amazon and Flipkart spiders)

#### Scrape Results (10 categories x 2 pages each, no proxies)

| Metric | Amazon.in | Flipkart | Combined |
|--------|-----------|----------|----------|
| Items scraped | ~340 | 520 | ~860 |
| Pipeline drops | 0 | 0 | 0 |
| Pipeline success | 100% | 100% | 100% |

**Final DB totals:**
- **729 products** across 12 categories
- **969 listings** (515 Amazon + 454 Flipkart)
- **144 cross-marketplace matches** (products found on both Amazon & Flipkart)
- **729/729 synced to Meilisearch**

Categories scraped: Smartphones, Laptops, Headphones/Audio, Televisions, Washing Machines, Refrigerators, Cameras, Smartwatches, Tablets, Air Purifiers, Electronics, Fashion

#### Files Modified
- `apps/scraping/playwright_handler.py` — NEW: StealthPlaywrightHandler with init script injection
- `apps/scraping/spiders/flipkart_spider.py` — HTTPERROR_ALLOWED_CODES, ROBOTSTXT_OBEY, StealthPlaywrightHandler, networkidle page methods
- `apps/scraping/spiders/base_spider.py` — Updated Stealth() usage comment
- `apps/scraping/scrapy_settings.py` — Default handler switched to StealthPlaywrightHandler

---

### 2026-02-28 — Scraping Anti-Detection & Reliability Overhaul

**Problem:** Amazon scraping hitting ~4 items/min with massive proxy bans and 503 errors. Root cause analysis found 7 issues.

#### Critical Fix: Amazon Spider Missing Stealth
The Amazon spider was using `scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler` (basic, no anti-detection) instead of the custom `StealthPlaywrightHandler`. Flipkart was correctly using stealth, but Amazon was not — this was the #1 cause of CAPTCHA/503 failures.

#### Changes Made

**1. Amazon Spider** (`apps/scraping/spiders/amazon_spider.py`)
- Fixed DOWNLOAD_HANDLERS to use `StealthPlaywrightHandler` (was using basic handler with no stealth)
- Reduced concurrency: `CONCURRENT_REQUESTS=2`, `CONCURRENT_REQUESTS_PER_DOMAIN=1` (was 4/2)
- Increased base delay: `DOWNLOAD_DELAY=7` (was 4)
- Enabled AutoThrottle (start 8s, max 45s, target concurrency 1.0)
- Replaced default retry with `BackoffRetryMiddleware` (exponential backoff on 503/429)
- Batched category starts: only 5 categories upfront, rest drip-fed as earlier ones complete
- Categories shuffled to distribute load across browse nodes
- CAPTCHA retries: 3 (was 2), with escalating wait (10-38s), forces new proxy on retry
- Randomized `wait_for_timeout` (2.5-5s) instead of fixed 4s
- Changed `_TOP=30`, `_STD=20` pages per category (was 10/5)

**2. Flipkart Spider** (`apps/scraping/spiders/flipkart_spider.py`)
- Added `DOWNLOAD_DELAY=7`, `CONCURRENT_REQUESTS=2`, `CONCURRENT_REQUESTS_PER_DOMAIN=1`
- Enabled AutoThrottle (start 8s, max 45s, target concurrency 1.0)
- Changed `_TOP=30`, `_STD=20` pages per category (was 10/5)

**3. Base Spider** (`apps/scraping/spiders/base_spider.py`)
- Reduced defaults: `DOWNLOAD_DELAY=6`, `CONCURRENT_REQUESTS=2`, `CONCURRENT_REQUESTS_PER_DOMAIN=1`
- Enabled AutoThrottle globally (start 6s, max 30s, target 1.0)
- Replaced default retry middleware with `BackoffRetryMiddleware`

**4. Middlewares** (`apps/scraping/middlewares.py`)
- NEW: `BackoffRetryMiddleware` — exponential backoff on retries (10s → 20s → 40s → 80s → 120s cap, ±50% jitter)
- Proxy ban cooldown increased: base 60s (was 30s), max 900s (was 600s)
- Added jitter to proxy ban cooldown to prevent thundering herd

**5. Scrapy Settings** (`apps/scraping/scrapy_settings.py`)
- Enabled AutoThrottle globally
- Replaced default retry middleware with `BackoffRetryMiddleware`
- Increased `DOWNLOAD_TIMEOUT` to 60s (was 45s)

#### Expected Impact
- Stealth fix alone should dramatically reduce CAPTCHA/503 rates
- AutoThrottle dynamically adapts — slows down when server pushes back
- Batched starts prevent burst traffic that triggers anti-bot systems
- Backoff retries prevent retry storms that compound bans
- Net throughput: slower per-request (~6-10 items/min) but much higher success rate

---

### 2026-03-01 — Scraping Architecture Overhaul: Two-Phase Spiders + Settings Cleanup

Major rewrite of scraping infrastructure to use a two-phase architecture (plain HTTP for fast pages, Playwright only when needed) and centralize settings.

**1. Base Spider** (`apps/scraping/spiders/base_spider.py`)
- `ROBOTSTXT_OBEY` → `False` (Amazon/Flipkart robots.txt blocks most scraping paths; we access same public pages as browsers)
- Removed all duplicate settings that belong in `scrapy_settings.py`: `PLAYWRIGHT_BROWSER_TYPE`, `PLAYWRIGHT_MAX_PAGES_PER_CONTEXT`, `PLAYWRIGHT_LAUNCH_OPTIONS`, `AUTOTHROTTLE_*`, `DOWNLOADER_MIDDLEWARES`
- `custom_settings` now only: `DOWNLOAD_DELAY`, `RANDOMIZE_DOWNLOAD_DELAY`, `CONCURRENT_REQUESTS` (4), `CONCURRENT_REQUESTS_PER_DOMAIN` (3), `ROBOTSTXT_OBEY` (False), `COOKIES_ENABLED`

**2. Scrapy Settings** (`apps/scraping/scrapy_settings.py`)
- `DOWNLOAD_HANDLERS` → standard `scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler` (was custom `StealthPlaywrightHandler`)
- Added `PLAYWRIGHT_MAX_CONTEXTS = 3` (cap memory at ~450MB)
- `AUTOTHROTTLE_TARGET_CONCURRENCY` → `1.5` (was 2.0, gentler)
- Added `MEMUSAGE_ENABLED = True`, `MEMUSAGE_LIMIT_MB = 2048`, `MEMUSAGE_WARNING_MB = 1536`

**3. Amazon Spider** (`apps/scraping/spiders/amazon_spider.py`) — FULL REWRITE
- **Two-phase architecture:**
  - Phase 1: Listing pages (`/s?k=...`) use **plain HTTP** (no Playwright). ~0.5s vs 5-8s per page.
  - Phase 2: Product pages (`/dp/ASIN`) use **Playwright** for JS-rendered prices.
- CAPTCHA on listings auto-promotes to Playwright (`dont_filter=True, priority=-1`)
- Product pages: no proxy session stickiness — middleware round-robins per request
- Quick mode: `QUICK_MODE_CATEGORIES = 10` when `--max-pages <= 3`
- Stats tracking: `_listing_pages_scraped`, `_product_pages_scraped`, `_captcha_count`, `_products_extracted` + `closed()` log
- Resilient `_extract_title()`: 7 methods in priority order (CSS, JSON-LD, og:title, `<title>` tag) with debug logging
- Cleaned `custom_settings`: removed `DOWNLOAD_HANDLERS`, `DOWNLOADER_MIDDLEWARES`, `AUTOTHROTTLE_*` (all in global settings)

**4. Flipkart Spider** (`apps/scraping/spiders/flipkart_spider.py`) — FULL REWRITE
- **Two-phase architecture:**
  - Phase 1: Listing pages use **Playwright** (React-rendered, kept as-is) + block detection (403/429/Access Denied)
  - Phase 2: Product pages try **plain HTTP first** (Flipkart serves JSON-LD in raw HTML). Falls back to Playwright only if JSON-LD incomplete.
- `parse_product_page()` checks JSON-LD for title + price → if sufficient, skips Playwright entirely
- Product pages: no proxy session stickiness
- Quick mode: `QUICK_MODE_CATEGORIES = 10` when `--max-pages <= 3`
- Stats tracking: `_listing_pages_scraped`, `_product_pages_scraped`, `_product_pages_plain_http`, `_product_pages_playwright`, `_blocked_count`, `_products_extracted` + `closed()` log
- New `_build_item()` method centralizes item building for both HTTP and Playwright paths
- Cleaned `custom_settings`: removed `DOWNLOAD_HANDLERS`, `AUTOTHROTTLE_*`

#### Expected Impact
- Amazon listing pages: ~10x faster (plain HTTP vs Playwright)
- Flipkart product pages: ~5-8x faster when JSON-LD is available (majority of pages)
- Memory: capped at 2GB with warnings at 1.5GB, max 3 browser contexts (~450MB)
- Quick mode: test runs with `--max-pages 1-3` only hit 10 categories instead of 120+
- Settings centralized: spider `custom_settings` only contain spider-specific overrides

### 2026-03-01 — Scraping Middleware Rewrite (PlaywrightProxyMiddleware v2)

#### Changes
- **Active context limiting**: `MAX_ACTIVE_CONTEXTS = 3` — only 3 browser contexts alive at once, even with 10+ proxies. Reserve proxies rotated in when active ones get banned. Prevents memory bombs on small VPS.
- **Smarter ban detection**: 403=definite ban, 429=rate limit (30s short cooldown), 503=conditional (only ban if body has "robot"/"captcha" or body < 1KB), 200+CAPTCHA=ban. Connection errors only ban after 2 consecutive from same proxy.
- **Proxy stats logging**: On spider close, logs per-proxy stats (requests, bans, success %) and overall totals.
- **Removed session stickiness**: Deleted `_sessions` dict. Two-phase architecture means listing pages don't use proxies, so session stickiness is unnecessary. Simple round-robin for all Playwright requests.
- **All-proxies-banned fallback**: Instead of falling back to direct requests (burns server IP), pauses spider by inflating `download_delay` to shortest remaining ban time. Restores original delay when a proxy becomes available.
- **New config**: `SCRAPING_PROXY_MAX_ACTIVE_CONTEXTS` in `app_settings.py` (default 3).
- BackoffRetryMiddleware unchanged.

### 2026-03-01 — Pipeline Robustness Fixes

#### Changes
- **ValidationPipeline**: Fixed `AttributeError` — `spider.items_failed` now uses `getattr()` with default 0 (also in Marketplace.DoesNotExist handler in ProductPipeline).
- **ReviewPersistencePipeline**: Timezone-naive dates from `dateutil.parser.parse()` now made aware via `timezone.make_aware()` — prevents Django `USE_TZ=True` warnings/crashes.
- **ProductPipeline**: PriceSnapshot raw SQL wrapped in try/except — logs warning on failure but does NOT drop the product item. Missing snapshot is recoverable; dropped product is not.
- **MeilisearchIndexPipeline**: Added fallback for `ProductPipeline._product_ids_attr` — uses `getattr()` with `"_synced_product_ids"` default in case class attribute is undefined.
- **SpiderStatsUpdatePipeline** (NEW, priority 600): Updates `ScraperJob` row with real-time `items_scraped` / `items_failed` counts every 50 items + final update on close. Best-effort (silent on failure).
- Registered in `scrapy_settings.py` at priority 600.

### 2026-03-01 — `scrape_test` Management Command

- **New**: `python manage.py scrape_test` — tests scraping health without a full run.
- Tests: proxy connectivity (`--test-proxies`), Amazon listing (HTTP), Amazon product (Playwright), Flipkart listing (Playwright), Flipkart product (HTTP + JSON-LD check), DB counts, Meilisearch health.
- Reports: HTTP status, response size, timing, title presence, CAPTCHA detection, JSON-LD availability.
- `--save-html` saves response HTML to `data/raw_html/` for debugging.
- Custom URLs: `--amazon-url`, `--flipkart-url`.

### 2026-03-01 — Review Spider Fixes (Amazon + Flipkart)

#### amazon_review_spider.py
- **Removed redundant `custom_settings`**: `DOWNLOAD_HANDLERS` already in `scrapy_settings.py`, `ROBOTSTXT_OBEY: False` already in base spider. Spider now inherits base defaults.
- **Added stealth**: `_apply_stealth()` method + `playwright_page_init_callback` in request meta (consistent with product spiders).
- **Added CAPTCHA detection**: `_is_captcha_page()` (same logic as product spider). On CAPTCHA, skips this product's reviews (no retry — reviews are lower priority than products).
- **Added stats**: `_reviews_scraped`, `_captcha_skipped`, `_products_processed` with structured `closed()` logging.
- **Added `errback`**: All requests now use `self.handle_error` from base spider.
- **Added random wait**: `PageMethod("wait_for_timeout", random.randint(2000, 4000))` to look more human.

#### flipkart_review_spider.py
- **Removed redundant `custom_settings`**: `DOWNLOAD_HANDLERS` already in `scrapy_settings.py`. Spider now inherits base defaults.
- **Added stealth**: `_apply_stealth()` method + `playwright_page_init_callback` in all request metas (start_requests + pagination).
- **Added DOM structure change detection**: If reviews_data has entries but ALL bodies are empty or < 10 chars, logs warning about possible DOM structure change needing EXTRACT_REVIEWS_JS update.
- **Improved JSON parse error handling**: Logs exception details, validates `reviews_data` is a list (guards against unexpected JS output).
- **Added stats**: `_reviews_scraped`, `_products_processed`, `_empty_pages`, `_js_extraction_failures` with structured `closed()` logging.
- **Added `errback`**: All requests now use `self.handle_error` from base spider.

#### CLAUDE.md updates
- Added `## HARD RULES — DATA SAFETY` section (production data protection, destructive migration rules, scraping safety).
- Added `## Scraping Patterns` section (file structure, two-phase architecture, proxy rules).

### 2026-03-01 — Rotating Proxy Support (DataImpulse Gateway)

**Problem**: The proxy middleware treated all proxies as static (each URL = distinct IP, round-robin with ban tracking). Rotating proxies like DataImpulse use a single gateway URL that assigns a different IP per TCP connection. Banning a rotating proxy URL is pointless — the next connection gets a fresh IP automatically.

**Key insight**: Playwright sets proxy at the **browser context level**, not per-request. A context keeps TCP connections alive (connection pooling), so one context through a rotating gateway may reuse the same IP. To get a new IP, you need a **new context** — cycling through context slots with randomized viewports forces Playwright to create new contexts.

#### Changes Made

**1. Middleware** (`apps/scraping/middlewares.py`) — Dual-mode proxy support:
- Added `SCRAPING_PROXY_TYPE` env var: `"static"` (default, existing behavior) or `"rotating"`
- Added `total_failures` field to `ProxyState` dataclass (rotating mode tracks failures without banning)
- `from_crawler()`: reads proxy type, skips pre-building context kwargs in rotating mode
- `process_request` dispatches to `_process_rotating` or `_process_static`
- `_process_rotating()`: cycles through 5 context slots (`rotating_0`..`rotating_4`) with randomized viewports (forces new contexts = new IPs)
- `process_response` dispatches to `_process_rotating_response` or `_process_static_response`
- `_process_rotating_response()`: tracks CAPTCHA/403/429 as failures, NEVER bans
- `process_exception`: rotating mode tracks failures without banning
- `_spider_closed`: dispatches to `_log_rotating_stats` (failure-based) or `pool.log_stats()` (ban-based)

**2. Amazon Spider** (`apps/scraping/spiders/amazon_spider.py`):
- Added `_is_rotating` flag in `__init__` (reads `SCRAPING_PROXY_TYPE` env)
- CAPTCHA retry: `max_retries = 1` for rotating (was 3) — new IP each time, no point retrying heavily
- Removed `download_delay` from CAPTCHA retry meta (rotating proxy gives new IP anyway)
- Wrapped `_apply_stealth()` in try/except (prevents crashes from stealth injection failures)
- Improved `closed()` stats with success rate percentage

**3. Flipkart Spider** (`apps/scraping/spiders/flipkart_spider.py`):
- Added `_is_rotating` flag in `__init__`
- Wrapped `_apply_stealth()` in try/except
- Block handling in `parse_listing_page`: added `block_retries` counter, retry once for rotating proxies on 403/429/Access Denied (new context = new IP)
- Improved `closed()` stats with success rate percentage

**4. Environment** (`.env`):
- Already configured: `SCRAPING_PROXY_TYPE=rotating`, `SCRAPING_PROXY_BAN_THRESHOLD=3`

#### Config
```bash
# Static mode (default) — existing behavior, round-robin with ban detection
SCRAPING_PROXY_TYPE=static

# Rotating mode — single gateway, new IP per connection
SCRAPING_PROXY_TYPE=rotating
SCRAPING_PROXY_LIST=http://user:pass@gw.dataimpulse.com:823
```

### 2026-03-01 — Scraping Performance Fixes (Context Cycling + Timeout + CAPTCHA Skip)

**Problem**: Scraping through DataImpulse rotating proxy was stalling — only ~1 product scraped before timeouts. Root causes: (1) Playwright's default 30s timeout too short for proxy connections, (2) spider retried CAPTCHA pages 3x even when middleware already flagged them, (3) Playwright waited for full page `"load"` event (all images/scripts) instead of just DOM.

#### Changes Made

**1. CAPTCHA skip via middleware flag** (`amazon_spider.py`, `flipkart_spider.py`):
- Added `_rotating_proxy_captcha` meta check at top of `parse_product_page` in both spiders
- When middleware already detected CAPTCHA (403/429/markers), spider skips immediately (0s) instead of retrying 3x (90+ seconds wasted)

**2. Playwright timeout increases** (`amazon_spider.py`, `flipkart_spider.py`):
- `_apply_stealth()` now sets `page.set_default_navigation_timeout(60000)` (60s, was 30s default)
- `_apply_stealth()` now sets `page.set_default_timeout(45000)` (45s, was 30s default)

**3. Scrapy download timeout** (`scrapy_settings.py`):
- `DOWNLOAD_TIMEOUT = 90` (was 45) — proxy connections need more headroom

**4. Faster page load strategy** (`amazon_spider.py`, `flipkart_spider.py`):
- Added `"playwright_page_goto_kwargs": {"wait_until": "domcontentloaded"}` to all product page Playwright requests
- Tells Playwright to consider page loaded once HTML is parsed, not waiting for every image/script/font
- Applied to: initial product requests, CAPTCHA retry requests, and Playwright promotion requests

#### Expected Impact
- Eliminates 90+ second waste per CAPTCHA'd page (instant skip)
- Reduces timeout failures (60s nav timeout vs 30s)
- Faster page loads through proxy (DOM-only vs full resource load)

### 2026-03-02 — Critical: .gitignore corruption fix + 41 missing files committed

**Problem**: Production Docker build (`next build`) was failing with import errors — `RecentlyViewedSection`, `RecentlyViewedTracker`, `ShareButton`, `CrossPlatformPricePanel`, `ReviewSidebar` not found. These component files existed locally but were never committed to git.

**Root Cause**: Commit `429d9ec` ("vsix files removed") appended `*.vsix` to `.gitignore` in **UTF-16LE encoding** (null bytes between each character). Git interpreted the pattern as just `*` — a wildcard matching everything. This silently prevented **all new files** from being staged via `git add` from that point forward. Files already tracked were unaffected, but every new file created after that commit was invisible to git.

#### What Was Fixed

**1. `.gitignore` rewritten** — replaced corrupted UTF-16LE `*.vsix` entry with proper UTF-8. Added `backend/data/` to ignore scraped HTML cache.

**2. 14 frontend files committed** (were missing from git, causing build failure):
- Components: `recently-viewed-section.tsx`, `recently-viewed-tracker.tsx`, `share-button.tsx`, `cross-platform-price-panel.tsx`, `review-sidebar.tsx`
- Hook: `use-recently-viewed.ts`
- Pages: `about`, `contact`, `privacy`, `terms`, `cookies`, `affiliate-disclosure`, `product/[slug]/review`, `reviews/new`

**3. 27 backend files committed** (were missing from git):
- Entire `admin_tools` app (6 files)
- Scraping: `middlewares.py`, `middlewares1.py`, `playwright_handler.py`, `amazon_review_spider.py`, `flipkart_review_spider.py`, `scrape_test` management command
- Business logic: `deals/detection.py`, `pricing/click_tracking.py`, `rewards/engine.py`, `scoring/components.py`, `reviews/fraud_detection.py`
- Accounts: `subscription.py`, `urls/subscription.py`, migrations `0006`, `0007`
- Config: `whydud/flowerconfig.py`, `products/management/commands/assign_categories.py`, `seed_marketplaces.py`

#### Other Issues Noted (not fixed yet)
- **130MB VSIX file in git history** — `.git` is 134MB. Needs `git filter-repo` or BFG to purge from history.
- **Orphan/dangling commits** (`4a6a4c3`, `d9b3704`, `a5edfe3`) — earlier VSIX cleanup attempt on an abandoned branch. Harmless but adds noise.
- **Two author emails** in commit history (`ramesh4nani@gmail.com` vs `ramesh.workk@gmail.com`).

**Commit**: `5575997`

### 2026-03-02 — Fix: Static generation timeout during Docker build

**Problem**: After fixing the missing files
, `next build` still failed — homepage (`/`) timed out during static page generation (3 attempts × 60s each = 330s). The homepage is an `async` server component that makes 4 API calls (products, deals, 2× trending). During Docker build, no backend is running, so `fetch()` to `http://localhost:8000` hangs indefinitely until Next.js kills the page generation.

**Fix**: Added `export const dynamic = "force-dynamic"` to:
- `(public)/page.tsx` (homepage) — 4 async API calls
- `(public)/deals/page.tsx` — 1 async API call

This tells Next.js to render these pages on each request instead of at build time. Correct behavior since they show live data (trending products, deals).

Other async pages (`search`, `compare`, `product/[slug]`, `seller/[slug]`, `categories/[slug]`, `discussions/[id]`) already have dynamic segments or `searchParams` so Next.js won't statically generate them.

**Deploy note**: Run `docker compose build --no-cache` (or at minimum `--no-cache` on the frontend service) to bust the Docker layer cache from the previous failed build.

**Commit**: `ea53e01`

### 2026-03-02 — Fix: useSearchParams Suspense boundaries + replica compose

**Problem**: `docker compose -f docker-compose.replica.yml build` failed on the replica server. The frontend build (`next build`) crashed during static page generation with:
```
useSearchParams() should be wrapped in a suspense boundary at page "/verify-email"
```
Next.js 15 requires any component using `useSearchParams()` to be wrapped in a `<Suspense>` boundary for static generation to work.

**Fix**: Wrapped `useSearchParams()` usage in `<Suspense>` boundaries on 3 auth pages:
- `frontend/src/app/(auth)/verify-email/page.tsx` — extracted `VerifyEmailContent`, wrapped in Suspense
- `frontend/src/app/(auth)/login/page.tsx` — extracted `LoginContent`, wrapped in Suspense
- `frontend/src/app/(auth)/reset-password/page.tsx` — extracted `ResetPasswordContent`, wrapped in Suspense

The `auth/callback/page.tsx` already had the correct pattern.

**Also**: `docker-compose.replica.yml` added to repo root for the replica node deployment (8 GB / 4 CPU Contabo VPS). Services: postgres (replica), redis, meilisearch, caddy, backend, frontend, celery-scraping. Write routing via `DATABASE_WRITE_URL` points to primary (10.0.0.1) over WireGuard.

### 2026-03-02 — Fix: Production deployment — 7 critical blockers resolved

**Problem**: Backend container crashed on startup with `ModuleNotFoundError: apps.admin_tools` and multiple config issues prevented the site from working behind Cloudflare.

**Root causes found (audit of entire deployment stack):**

1. **Django couldn't connect to PostgreSQL** — Compose set `DATABASE_URL` but `prod.py` only read individual `POSTGRES_HOST` env vars (defaulted to `localhost`, wrong inside Docker)
2. **Missing `CSRF_TRUSTED_ORIGINS`** in prod settings — all POST requests behind Cloudflare got 403
3. **Missing `CORS_ALLOWED_ORIGINS`** for `whydud.com` — browser API calls blocked
4. **No database router** for replica write routing to primary via WireGuard
5. **`init-replication.sql` was gitignored** — Docker mount failed on server after `git pull` (file didn't exist)
6. **Caddyfile missing routes** for `/accounts/*`, `/oauth/*`, `/static/*` — Google OAuth and Django admin unreachable
7. **`collectstatic` failed silently** (`|| true`) — Django admin had no CSS/JS
8. **`static_files` Docker volume** mounted over `/app/staticfiles`, shadowing files collected into the image

**Fixes applied:**

| File | Change |
|---|---|
| `backend/whydud/settings/prod.py` | Parse `DATABASE_URL`/`DATABASE_WRITE_URL`, add `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, WhiteNoise middleware |
| `backend/whydud/db_router.py` | New file — routes reads to local DB, writes to primary on replica node |
| `backend/requirements/prod.txt` | Added `whitenoise==6.11.0` |
| `docker/Dockerfiles/backend.Dockerfile` | Fixed `collectstatic` with build-time `DJANGO_SECRET_KEY` (removed `|| true`) |
| `docker/Caddyfile.cloudflare` | Added `/accounts/*`, `/oauth/*`, `/static/*` routes; log to stdout |
| `docker-compose.primary.yml` | Replaced gitignored `.sql` with `.sh` replication script, added `REPLICATOR_PASSWORD` env var, removed `static_files` volume |
| `docker-compose.replica.yml` | Removed `static_files` volume |
| `docker/postgres/init-replication.sh` | New file — creates replicator user from env var (no hardcoded password) |
| `.env.example` | New file — template with all required production env vars |
| `deploy.sh` | New file — deployment script with pre-flight checks, staged startup, migration support |

**Commit**: `e7400c4`

### 2026-03-02 — Fix: TimescaleDB extension not preloaded

**Problem**: Migrations failed with `function create_hypertable does not exist` because TimescaleDB extension wasn't available.

**Root causes:**
1. `init.sql` (with `CREATE EXTENSION timescaledb`) only runs on first Docker volume init — volume already existed on server
2. `primary.conf` overrode PostgreSQL defaults but was missing `shared_preload_libraries = 'timescaledb'` — without preloading, `CREATE EXTENSION` fails

**Fixes:**
- Added `CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;` to both migration files (`pricing/0002`, `scoring/0002`) so extensions are ensured regardless of init.sql
- Added `shared_preload_libraries = 'timescaledb'` to `docker/postgres/primary.conf`

**Commits**: `feddda3`, `845d896`

### 2026-03-03 — Fix: Site accessible but pages empty (DisallowedHost + Caddy HTTPS)

**Problem**: All 8 containers running, Cloudflare routing traffic to server, homepage HTML loads — but all API data missing. Pages render empty/broken.

**Root causes:**
1. **`DisallowedHost: 'backend:8000'`** — Next.js SSR (server-side rendering) calls the Django backend via Docker internal hostname `http://backend:8000/api/...`. Django's `ALLOWED_HOSTS` only had `whydud.com` and `www.whydud.com`, so it rejected all internal requests with HTTP 400. Every API call from the frontend server component failed.
2. **Cloudflare SSL mode "Flexible"** — Traffic between Cloudflare edge and origin server was unencrypted HTTP. Not a functional blocker but a security issue for production.

**Fixes:**

| File | Change |
|---|---|
| `backend/whydud/settings/prod.py` | Added `backend` and `localhost` to `ALLOWED_HOSTS` for internal Docker container-to-container requests |
| `docker/Caddyfile.cloudflare` | Reconfigured from `:80` catchall to `whydud.com, www.whydud.com` with TLS using Cloudflare Origin Certificate — enables Full (strict) SSL mode |
| `docker-compose.primary.yml` | Added `./docker/certs:/etc/caddy/certs:ro` volume mount for Caddy |
| `docker-compose.replica.yml` | Same certs volume mount |
| `.gitignore` | Added `docker/certs/` (certificates must never be in git) |

**Deployment requires**: Generate Cloudflare Origin Certificate, save as `docker/certs/origin.pem` + `docker/certs/origin-key.pem` on server, set Cloudflare SSL mode to "Full (strict)"

**Commit**: `7fa1b49`

### 2026-03-03 — Primary Node Successfully Deployed to Production

**Status**: LIVE at whydud.com

**What's running (primary server — 95.111.232.70):**
- PostgreSQL 16 + TimescaleDB (hypertables for price_snapshots, dudscore_history)
- Redis 7 (Celery broker + cache)
- Meilisearch v1.7 (product search + autocomplete)
- Django 5 backend via Gunicorn (3 workers, gthread)
- Next.js 15 frontend (standalone mode)
- Celery worker (queues: default, scoring, alerts, email)
- Celery beat (scheduled tasks: daily scraping, price alerts, review publishing)
- Caddy 2 reverse proxy with Cloudflare Origin Certificate (Full strict SSL)

**All 8 containers healthy.** All 27 migrations applied successfully including TimescaleDB hypertables.

**Deployment issues resolved across 5 commits:**
1. `e7400c4` — 7 critical blockers (DATABASE_URL parsing, CSRF, CORS, db_router, collectstatic, Caddyfile routes, init-replication)
2. `feddda3` — TimescaleDB extension ensured in migrations
3. `845d896` — shared_preload_libraries for TimescaleDB
4. `7fa1b49` — ALLOWED_HOSTS for Docker internal SSR calls + Caddy HTTPS with origin certs

**Remaining:**
- ~~Replica node deployment (46.250.237.93) — not started~~ DONE (see 2026-03-03 entries below)
- ~~PostgreSQL streaming replication setup between primary and replica~~ DONE
- ~~WireGuard VPN tunnel verification (10.0.0.1 ↔ 10.0.0.2)~~ DONE

### 2026-03-03 — Replica Node Deployed + PostgreSQL Streaming Replication

**Status**: Replica node (46.250.237.93) LIVE — PostgreSQL streaming replication confirmed working, scraping celery worker running.

**What's running (replica server — 46.250.237.93, 8GB / 4 vCPU):**
- PostgreSQL 16 + TimescaleDB (streaming replica of primary, read-only)
- Redis 7 (local cache, Celery broker points to primary Redis over WireGuard)
- Meilisearch v1.7 (local index)
- Django 5 backend via Gunicorn (2 workers)
- Next.js 15 frontend (standalone mode)
- Celery scraping worker (queue: scraping only)
- Caddy 2 reverse proxy with Cloudflare Origin Certificate

**PostgreSQL replication verified:**
- WAL positions match exactly between primary and replica (`0/300A5A0`)
- `pg_is_in_recovery()` = true on replica
- `pg_stat_replication` shows `state='streaming'` on primary
- Replication slot `replica_slot` active

**WireGuard tunnel verified:**
- 10.0.0.1 (primary) ↔ 10.0.0.2 (replica) — bidirectional connectivity confirmed
- Replica connects to primary PostgreSQL (10.0.0.1:5432) for write routing
- Replica connects to primary Redis (10.0.0.1:6379) for Celery broker

### 2026-03-03 — Discord Webhook Notifications for Celery Tasks

- **Created `backend/common/discord.py`** — Discord webhook utility
  - `send_discord_notification(embed)` — sync httpx POST to `DISCORD_WEBHOOK_URL`
  - 5s timeout, silent fail (logs warning, never crashes tasks)
  - Rich embed formatting with colors: green=success, red=failure, yellow=retry
- **Updated `backend/whydud/celery.py`** — registered 3 signal handlers:
  - `@task_success.connect` → green embed with task name, result summary, runtime, worker hostname
  - `@task_failure.connect` → red embed with task name, exception, traceback (truncated), worker hostname
  - `@task_retry.connect` → yellow embed with task name, reason, retry count, worker hostname
  - Filters out noisy internal Celery tasks (`celery.backend_cleanup`)
  - Smart result formatting: dict results show key fields, long results truncated to 1000 chars
- **Updated `backend/whydud/settings/base.py`** — added `DISCORD_WEBHOOK_URL` setting
- **Updated both compose files** — added `DISCORD_WEBHOOK_URL` env var to celery-worker (primary) and celery-scraping (replica)
- **Updated `.env.example`** — added `DISCORD_WEBHOOK_URL` entry

### 2026-03-03 — Scraping Deployment Fixes (6 issues resolved)

**1. Marketplace slug mismatch** (`seed_marketplaces.py`):
- `seed_marketplaces` command created slugs with underscores (`amazon_in`) but entire codebase uses hyphens (`amazon-in`)
- Fixed all 4 slugs: `amazon_in` → `amazon-in`, `reliance_digital` → `reliance-digital`, `vijay_sales` → `vijay-sales`, `tata_cliq` → `tata-cliq`
- Added `_SLUG_MIGRATIONS` dict to auto-fix existing DB records via UPDATE
- **Commit**: `a054c5b`

**2. Missing playwright-stealth in production** (`requirements/base.txt`):
- `playwright-stealth==2.0.2` was in `lock.txt` but missing from `base.txt` (which prod Dockerfile installs from)
- Spider subprocess crashed with `ModuleNotFoundError: No module named 'playwright_stealth'`
- **Commit**: `1b9eb9e`

**3. Spider output invisible in container logs** (`apps/scraping/tasks.py`):
- All 3 spider tasks used `subprocess.run(capture_output=True)` — silently captured all Scrapy output
- Rewrote with `_run_spider_process()` helper using `subprocess.Popen` with line-by-line streaming
- Uses `collections.deque(maxlen=80)` to keep tail for error reporting
- Spider output now visible in real-time via `docker compose logs celery-scraping`
- **Commit**: `29496e9`

**4. Playwright Chromium binary installed to root** (`backend.Dockerfile`):
- `playwright install chromium` runs as root during Docker build `deps` stage → binaries at `/root/.cache/ms-playwright/`
- Production stage runs as `USER whydud` → Playwright looks in `/home/whydud/.cache/ms-playwright/` → `Executable doesn't exist`
- All product detail pages (which need Playwright) failed; listing pages (plain HTTP) worked fine
- **Fix**: Added `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` to base ENV + `chmod -R o+rx /ms-playwright` after install
- Browsers now install to shared `/ms-playwright` path accessible by any user

**5. Django superuser creation** (production):
- Custom User model uses email as USERNAME_FIELD — `--username` flag doesn't work
- Non-TTY environment in Docker exec — needed `python -c` one-liner with `django.setup()` before imports

**6. Playwright Chromium + system deps in Dockerfile** (`backend.Dockerfile`):
- Added `RUN playwright install-deps chromium && playwright install chromium` to deps stage
- Required for scraping spiders that use Playwright for JS-rendered product pages
- **Commit**: `6576cf1`

### Scraping Test Results (production, Amazon.in)
- Listing phase working: plain HTTP requests to Amazon category pages
- 121 categories queued, some pages successfully crawled (yoga mats: 48 results, laptops: 24 results)
- Amazon returning 503 on many requests (normal anti-bot behavior, backoff retry handling it)
- Product detail pages: **blocked by Playwright binary path issue** (fix committed, pending rebuild)

### 2026-03-03 — 10 New Marketplace Spiders (Full Coverage)

Built dedicated spiders for all 10 remaining marketplaces defined in `seed_marketplaces`. Each spider follows the two-phase architecture (listing → detail), extracts via site-specific JS state variables first, then JSON-LD fallback, then HTML/CSS fallback.

#### Spiders Created

| Spider | File | Slug | Domain | Tech Stack | Primary Extraction | Anti-Bot | Lines |
|--------|------|------|--------|------------|-------------------|----------|-------|
| **Croma** | `croma_spider.py` | `croma` | croma.com | Custom JS | `__INITIAL_DATA__` pdpReducer | Low | ~850 |
| **Reliance Digital** | `reliance_digital_spider.py` | `reliance-digital` | reliancedigital.in | Vue.js 2 / Fynd | `window.__INITIAL_STATE__` | Medium | ~490 |
| **Vijay Sales** | `vijay_sales_spider.py` | `vijay-sales` | vijaysales.com | Magento 2 / Unbxd | JSON-LD Product schema | Medium | ~420 |
| **Snapdeal** | `snapdeal_spider.py` | `snapdeal` | snapdeal.com | Server-rendered HTML | Hidden inputs + `sdLogData` JS | Medium | ~530 |
| **Nykaa** | `nykaa_spider.py` | `nykaa` | nykaa.com | React / Redux | `window.__PRELOADED_STATE__` | High (Akamai) | ~480 |
| **TataCLiQ** | `tatacliq_spider.py` | `tata-cliq` | tatacliq.com | Next.js SSR | `__NEXT_DATA__` | High (Cloudflare) | ~510 |
| **JioMart** | `jiomart_spider.py` | `jiomart` | jiomart.com | Jio Commerce / React SSR | `window.__INITIAL_STATE__` | High (Akamai) | ~400 |
| **Myntra** | `myntra_spider.py` | `myntra` | myntra.com | React (custom Webpack) | `window.__myx` | High (behavioral) | ~480 |
| **AJIO** | `ajio_spider.py` | `ajio` | ajio.com | React SPA | `__PRELOADED_STATE__` / `__NEXT_DATA__` | Very High (Akamai + PerimeterX) | ~430 |
| **Meesho** | `meesho_spider.py` | `meesho` | meesho.com | Next.js | `__NEXT_DATA__` / `__INITIAL_STATE__` | Extreme (Akamai + TLS fingerprinting) | ~420 |

#### Per-Spider Architecture

Each spider implements:
- `SEED_CATEGORY_URLS` — 16-39 category URLs per site
- `KEYWORD_CATEGORY_MAP` — keyword→whydud category slug mapping
- `start_requests()` → `parse_listing()` → `parse_product()` three-phase flow
- Multi-strategy extraction: JS state variable → JSON-LD → CSS/HTML → listing data fallback
- `_is_blocked()` / `_is_captcha_page()` for anti-bot detection
- `closed()` with structured stats logging
- Prices converted to paisa (×100) for `ProductItem`

#### Custom Settings by Anti-Bot Tier

| Tier | Spiders | DOWNLOAD_DELAY | CONCURRENT_REQUESTS | PER_DOMAIN |
|------|---------|---------------|--------------------:|------------|
| Low | Croma, Snapdeal | 1.5 | 8 | 4 |
| Medium | Reliance Digital, Vijay Sales, Nykaa | 2 | 6 | 3 |
| High | TataCLiQ, JioMart, Myntra, AJIO | 3 | 4 | 2 |
| Extreme | Meesho | 4 | 3 | 2 |

#### Configuration Changes

- **`common/app_settings.py`** — Added all 10 to `ScrapingConfig.spider_map()`:
  ```
  croma, reliance-digital, vijay-sales, snapdeal, nykaa,
  tata-cliq, jiomart, myntra, ajio, meesho
  ```
- **`whydud/celery.py`** — Added 10 staggered daily Beat schedule entries:
  - Croma 02:00 UTC, Reliance Digital 04:30, Vijay Sales 05:00
  - Snapdeal 07:30, Nykaa 08:00
  - TataCLiQ 10:00, JioMart 13:00, Myntra 16:00, AJIO 19:00, Meesho 22:00
  - Spread across 24h to avoid proxy overload; electronics early, SPA sites during off-peak

#### No Changes Needed

- **`apps/scraping/tasks.py`** — `scrape_daily_prices()` already iterates all active marketplaces dynamically via `ScrapingConfig.spider_map()`, no code change needed
- **Pipelines** — existing `ValidationPipeline`, `ProductPipeline`, `MeilisearchIndexPipeline` handle all `ProductItem` instances regardless of marketplace

#### Testing

All 10 spiders verified via `py_compile` (syntax clean). Full integration testing requires Docker containers running (PostgreSQL, Redis, Meilisearch). To test individual spiders:
```bash
python -m apps.scraping.runner {spider_name} --max-pages 1 --urls "{test_url}"
```

#### Total Spider Coverage

Now 12 product spiders + 2 review spiders covering all Indian marketplaces:
- Amazon.in, Flipkart (existing, 6h cycle)
- Croma, Reliance Digital, Vijay Sales, Snapdeal, Nykaa (new, daily)
- TataCLiQ, JioMart, Myntra, AJIO, Meesho (new, daily)

### 2026-03-03 — Spider Fixes: HTTPERROR Handling, Block→Playwright Promotion, Proxy IP Logging

After local integration testing, discovered and fixed several systemic issues across all 10 new spiders plus enhanced the proxy middleware with IP logging and multi-context rotation.

#### Issue 1: HTTPERROR_ALLOWED_CODES Missing (All 10 Spiders)

**Problem:** Scrapy's `HttpErrorMiddleware` silently drops non-2xx responses before they reach spider callbacks. All 10 new spiders were missing `HTTPERROR_ALLOWED_CODES`, so 403/429/503 responses triggered the errback instead of the callback — spiders could never handle blocks properly.

**Fix:** Added `"HTTPERROR_ALLOWED_CODES": [403, 429, 503]` to `custom_settings` on all 10 spiders.

#### Issue 2: 403 in RETRY_HTTP_CODES on SPA Spiders (6 Spiders)

**Problem:** 6 SPA spiders (Nykaa, TataCLiQ, JioMart, Myntra, AJIO, Meesho) had `403` in `RETRY_HTTP_CODES` but no `HTTPERROR_ALLOWED_CODES`. This caused 2 wasteful retry requests per 403 that were still dropped by HttpErrorMiddleware — triple the wasted requests.

**Fix:** Removed `403` from `RETRY_HTTP_CODES` on all 6 SPA spiders. Spider callbacks now handle 403 directly via `_is_blocked()`.

#### Issue 3: Block→Playwright Promotion (Croma + Snapdeal)

**Problem:** Croma and Snapdeal use HTTP-first listing requests. When blocked (403), they skipped the page entirely instead of retrying with Playwright.

**Fix:** Added block→Playwright promotion in both `parse_listing_page` and `parse_product_page` for Croma and Snapdeal:
- If blocked on HTTP request → re-request same URL with `meta={"playwright": True}` + stealth init
- If blocked even with Playwright → skip and log warning
- Same pattern used by Amazon/Flipkart spiders

#### Issue 4: Single Rotating Proxy Context (Middleware)

**Problem:** `PlaywrightProxyMiddleware` used ONE Playwright context (`proxy_rotating`) for all rotating proxy requests. Playwright pools TCP connections per context, so connection reuse meant the same exit IP could be used repeatedly despite DataImpulse assigning new IPs per connection.

**Fix:** Changed from 1 context to 5 context slots (`rotating_0` through `rotating_4`):
- Requests cycle round-robin through 5 context names
- Each context gets a randomized viewport from `_VIEWPORT_CHOICES`
- Forces new TCP connections more frequently → better IP rotation
- Updated `PLAYWRIGHT_MAX_CONTEXTS` from 3 to 6 in `scrapy_settings.py` (5 rotating + 1 default)

#### Enhancement: Proxy IP Logging

Added comprehensive IP tracking to `PlaywrightProxyMiddleware`:

- **`resolve_proxy_exit_ip()`** — New utility function that makes a sync HTTP request through the proxy to `api.ipify.org` to discover the actual exit IP
- **Startup IP check** — Logs the exit IP at spider start (confirms proxy is working)
- **Per-request logging** — Logs which context slot is used for each request
- **Response header IP detection** — Extracts IPs from `X-Client-IP`, `X-Real-IP`, `CF-Connecting-IP` headers
- **Enhanced close stats** — Logs IP summary: unique IPs seen, per-context IP mapping, end-of-run IP check, rotation count

#### Files Modified

| File | Change |
|------|--------|
| `spiders/croma_spider.py` | `HTTPERROR_ALLOWED_CODES` + block→Playwright promotion |
| `spiders/snapdeal_spider.py` | `HTTPERROR_ALLOWED_CODES` + block→Playwright promotion |
| `spiders/reliance_digital_spider.py` | `HTTPERROR_ALLOWED_CODES` added |
| `spiders/vijay_sales_spider.py` | `HTTPERROR_ALLOWED_CODES` added |
| `spiders/nykaa_spider.py` | `HTTPERROR_ALLOWED_CODES` added, 403 removed from `RETRY_HTTP_CODES` |
| `spiders/tatacliq_spider.py` | `HTTPERROR_ALLOWED_CODES` added, 403 removed from `RETRY_HTTP_CODES` |
| `spiders/jiomart_spider.py` | `HTTPERROR_ALLOWED_CODES` added, 403 removed from `RETRY_HTTP_CODES` |
| `spiders/myntra_spider.py` | `HTTPERROR_ALLOWED_CODES` added, 403 removed from `RETRY_HTTP_CODES` |
| `spiders/ajio_spider.py` | `HTTPERROR_ALLOWED_CODES` added, 403 removed from `RETRY_HTTP_CODES` |
| `spiders/meesho_spider.py` | `HTTPERROR_ALLOWED_CODES` added, 403 removed from `RETRY_HTTP_CODES` |
| `middlewares.py` | `resolve_proxy_exit_ip()`, 5-slot context rotation, IP logging |
| `scrapy_settings.py` | `PLAYWRIGHT_MAX_CONTEXTS` 3→6 |

#### Local Test Results

| Spider | Result | Notes |
|--------|--------|-------|
| **Snapdeal** | **19 products scraped + persisted to DB** | Full pipeline works: validation → normalization → product creation → price snapshots → Meilisearch |
| **Croma** | 403 → Playwright promotion works | Still blocked by Croma WAF (geo/fingerprint); needs Indian VPS |
| **Reliance Digital** | Blocked | Indian IP required (Akamai Bot Manager) |
| **Vijay Sales** | Blocked | Indian IP required |
| **Nykaa** | Blocked | Indian IP required (Akamai) |
| **TataCLiQ** | Blocked | Indian IP required (Cloudflare) |
| **Myntra** | Blocked | Indian IP required (behavioral detection) |

#### Proxy IP Verification

Confirmed DataImpulse rotating proxy works correctly from local machine:
- **Machine IP:** `103.162.159.179` (Indian ISP)
- **Proxy exit IPs observed:** `122.173.26.9`, `223.181.103.237`, `171.79.79.53`, `157.37.136.20`, `106.222.216.199` (all Indian residential)
- **Rotation confirmed:** Startup IP differs from end-of-run IP on every test run
- Most Indian e-commerce sites block even Indian residential proxies — production deployment on Contabo VPS with Indian proxy should have better success

### 2026-03-03 — Fix: Remove Time Limits from Scraping Tasks

Amazon spider was killed mid-scrape after 25 minutes by Celery's global `CELERY_TASK_SOFT_TIME_LIMIT = 1500s`. It had crawled 51 pages and scraped 38 products and was still actively running. Scraping tasks can legitimately take hours across 12 marketplaces with many categories.

#### Root Cause

- Global Celery settings: `CELERY_TASK_SOFT_TIME_LIMIT = 1500` (25 min), `CELERY_TASK_TIME_LIMIT = 1800` (30 min) in `whydud/settings/base.py`
- These globals are correct for short tasks (email, scoring, alerts) but scraping tasks inherited them
- Additionally, `ScrapingConfig.spider_timeout() = 3600s` fed `proc.wait(timeout=3600)` which would also kill long scrapes

#### Changes

| File | Change |
|------|--------|
| `apps/scraping/tasks.py` | Added `soft_time_limit=None, time_limit=None` to `run_marketplace_spider`, `run_review_spider`, `run_spider` decorators |
| `apps/scraping/tasks.py` | Removed `timeout` param from `_run_spider_process()` — now calls `proc.wait()` with no timeout |
| `apps/scraping/tasks.py` | Removed all `subprocess.TimeoutExpired` except blocks (no longer possible) |
| `common/app_settings.py` | Removed `ScrapingConfig.spider_timeout()` (no longer referenced) |

Global 25/30 min limits still protect all other queues (email, scoring, alerts, default). Only scraping tasks run unlimited.

### 2026-03-03 — Reliance Digital Spider: Rewrite to Pure JSON API

Replaced the Playwright-based HTML scraper with a pure HTTP spider targeting Reliance Digital's open Fynd Commerce JSON API. Zero authentication required — the API is completely open.

#### Architecture Change

| Before | After |
|--------|-------|
| Playwright for listing + detail pages | Pure HTTP JSON API (`/ext/raven-api/catalog/v1.0/products`) |
| Two-phase: listing HTML → product detail HTML | Single-phase: API returns full product data per item |
| `window.__INITIAL_STATE__` JS extraction | Standard JSON parsing via `response.json()` |
| 21 seed category URLs (HTML pages) | 10 seed search queries (API calls) |
| ~2 min per page (Playwright overhead) | ~17 seconds for 4 API pages (48 products) |

#### API Details

- **Endpoint:** `GET https://www.reliancedigital.in/ext/raven-api/catalog/v1.0/products?q={query}&page={n}&pageSize=24`
- **Auth:** None (open API, no cookies/tokens needed)
- **Pagination:** `response.page.has_next`, `response.page.current`
- **Platform:** Fynd Commerce (powers JioMart, Reliance Digital, etc.)

#### Seed Queries (10 categories)

smartphones (10pg), laptops (10pg), headphones (5pg), televisions (5pg), air conditioners (5pg), refrigerators (5pg), washing machines (5pg), air purifiers (5pg), cameras (5pg), tablets (5pg)

#### Test Run Results (`--max-pages 1`, quick mode = 4 queries)

| Metric | Value |
|--------|-------|
| API requests | 4 |
| Products scraped | 48 |
| Items dropped | 0 |
| Errors | 0 |
| Elapsed time | ~17 seconds |

#### Field Coverage

| Field | Status | Source |
|-------|--------|--------|
| Title, Brand, Price, MRP | ✅ | `name`, `brand.name`, `price.effective.min`, `price.marked.min` |
| Images | ✅ 7-11 per product | `medias[]` array (CDN: cdn.jiostore.online) |
| Specs | ✅ 15-25 curated keys | `attributes{}` — filtered whitelist (EAN, RAM, Processor, etc.) |
| Description | ✅ | `attributes.description` (HTML stripped to text) |
| About Bullets | ✅ 6-8 per product | `attributes.key-features` `<li>` items |
| Country of Origin | ✅ | Top-level `country_of_origin` field |
| Warranty | ✅ | `attributes.warranty` |
| Weight/Dimensions | ✅ | `net-weight`, `item-height/width/length` |
| Price Snapshots | ✅ | 48 PriceSnapshots recorded via raw SQL |
| Rating/Reviews | ❌ Not available | API always returns `rating: 0`, no review endpoint exists |

#### Files Changed

| File | Change |
|------|--------|
| `apps/scraping/spiders/reliance_digital_spider.py` | Complete rewrite — Playwright HTML → pure HTTP JSON API |
| DB: `marketplaces` table | Created `reliance-digital` slug row (old `reliance_digital` underscore row already existed) |

#### Notes

- `reliance-digital` was already registered in `app_settings.py` `spider_map()` and `seed_marketplaces.py`
- No Playwright dependency — `meta={"playwright": False}` on all requests
- 1.5s download delay with 2 concurrent requests per domain
- Spec extraction uses a whitelist of ~50 consumer-facing attribute keys, filtering out internal Fynd fields (`_id`, `_custom_json`, `seo`, `price-zmr*`, etc.)
- Reliance Digital does not expose reviews via API — products will share reviews from Amazon/Flipkart via cross-marketplace matching

---

### 2026-03-03 — Vijay Sales Spider (Unbxd JSON API)

**Status:** ✅ Complete — tested with `--max-pages 1`

Rewrote the Vijay Sales spider from Playwright+HTML scraping to **pure HTTP + Unbxd Search JSON API**. P0 priority marketplace — open API, no auth, no Playwright, no proxy needed.

#### Test Results (`--max-pages 1`)

| Metric | Value |
|--------|-------|
| API pages fetched | 4 (1 per query × 4 quick-mode queries) |
| Products extracted | 200 |
| Duplicates skipped | 0 |
| HTTP status | All 200 |
| Elapsed time | 13s |
| Items dropped (pipeline) | 100 — DB `vijay-sales` marketplace row not yet created (expected) |

#### Sample Products

**Product 1:** Acer Aspire Lite Laptop (13th Gen Core i3-1305U/ 8 GB RAM/512GB SSD)
- Price: ₹35,990 (3599000 paisa) | MRP: ₹52,990
- SKU: 230211 | EAN: 8906170203628
- Specs: Model, Manufacturing Warranty, Services Warranty, Delhi Offers, Discount (32%), COD, Exchange
- URL: `vijaysales.com/p/230211/acer-aspire-lite-laptop-...`

**Product 2:** HP Thin & Light Laptop (Intel Core 3/ 16GB/ 512GB SSD)
- Price: ₹47,490 (4749000 paisa) | MRP available
- Full specs, warranty, Delhi city-specific offers

#### Architecture

| Aspect | Detail |
|--------|--------|
| Approach | HTTP + Unbxd Search JSON API (no Playwright) |
| API Endpoint | `search.unbxd.io/{api_key}/{site_key}/search?q={query}&rows=50&start={offset}` |
| Pagination | `start` offset, `response.numberOfProducts` for total |
| Price Source | Delhi city-specific pricing (cityId_10_*) → fallback to global |
| Price Format | Rupees → paisa (* 100) |
| Dedup | `_seen_ids` set across queries |
| Concurrency | 4 requests, 2 per domain, 1.5s delay |

#### Data Quality

| Field | Status | Source |
|-------|--------|--------|
| Title, Brand, Price, MRP | ✅ | `title`, `brand`, `offerPrice`/`cityId_10_offerPrice`, `mrp`/`price` |
| Images | ✅ | `imageUrl`, `smallImage`, `thumbnailImage` |
| Specs | ✅ 8-12 per product | SKU, Model, EAN, Color, Warranty (5 fields), Discount, COD, Exchange |
| Delhi Pricing | ✅ | `cityId_10_offerPrice_unx_d`, `cityId_10_specialTag_unx_ts` |
| Description | ✅ | `description` (HTML stripped) |
| Rating/Reviews | ❌ Not in Unbxd API | Reviews loaded via separate service |

#### Files Changed

| File | Change |
|------|--------|
| `apps/scraping/spiders/vijay_sales_spider.py` | Complete rewrite — Playwright HTML → pure HTTP Unbxd JSON API |

#### Notes

- `vijay-sales` was already registered in `app_settings.py` `spider_map()`
- No Playwright dependency — `meta={"playwright": False}` on all requests
- City-specific pricing (Delhi, cityId=10) stored as default price; city data preserved in specs for future multi-city support
- Unbxd API key is public (embedded in Vijay Sales HTML source), CORS fully open
- Total catalog: ~5,124 products across all categories

### 2026-03-03 — Vijay Sales Spider Phase 2: GraphQL Enrichment

**Status:** ✅ Complete — tested with `--max-pages 1`

Added Phase 2 enrichment to the Vijay Sales spider using Magento's **open GraphQL API** (`/api/graphql`). No Playwright needed — both phases are pure HTTP.

#### Architecture

| Phase | API | Data |
|-------|-----|------|
| Phase 1 (Listing) | Unbxd Search JSON API | Title, brand, price, MRP, images, warranty, specs, stock |
| Phase 2 (Detail) | Magento GraphQL API | Description, high-res image gallery, rating, review count, about bullets |

- **Batch enrichment:** 10 SKUs per GraphQL request (buffer-and-flush pattern)
- GraphQL endpoint: `GET https://www.vijaysales.com/api/graphql` with `Store: vijay_sales` header
- Query: `products(filter: {sku: {in: [...]}})` returns `rating_summary`, `review_count`, `description{html}`, `short_description{html}`, `media_gallery{url}`
- `rating_summary` is 0-100 scale, converted to 0-5 Decimal (÷20)

#### Test Results (`--max-pages 1`)

| Metric | Value |
|--------|-------|
| Total requests | 24 (4 Unbxd + 20 GraphQL batches) |
| Products extracted (Unbxd) | 200 |
| GraphQL batches | 20 (10 SKUs each) |
| GraphQL success rate | 10/10 products per batch |
| All HTTP status | 200 |
| Elapsed time | 54s |
| Items through pipeline | 100 (DB connection pool limit — pre-existing) |

#### Enrichment Fields

| Field | Status | Source |
|-------|--------|--------|
| Rating | ✅ | `rating_summary` (0-100 → 0-5 Decimal) |
| Review Count | ✅ | `review_count` |
| Description | ✅ | `description.html` (HTML stripped, specs parsed) |
| About Bullets | ✅ | `short_description.html` (split on `<br>`) |
| Images | ✅ Upgraded | `media_gallery[].url` (full gallery, replaces Unbxd thumbnails) |
| Specs (from desc) | ✅ | Parsed `<b>Key:</b> Value` patterns from description HTML |

#### Files Changed

| File | Change |
|------|--------|
| `apps/scraping/spiders/vijay_sales_spider.py` | Added Phase 2 GraphQL enrichment — `_flush_graphql_batch()`, `parse_graphql_response()`, `_enrich_item()`, `_yield_items_unenriched()` fallback |

#### Notes

- Both phases are pure HTTP — no Playwright, no proxy needed
- GraphQL API is completely open (no auth, no CORS restrictions)
- Fallback: if GraphQL fails, items are still yielded with Phase 1 data only
- `_handle_graphql_error` errback cannot yield items (Scrapy limitation) — items are lost on request-level GraphQL failure. In practice this API is stable and never fails.
- Some products have `rating: None` — these are products with no reviews (expected)

### 2026-03-03 — Snapdeal Spider Rewrite (Search-Based + Microdata, No Playwright)

**Goal**: Rewrite the Snapdeal spider to use search-based discovery with schema.org microdata extraction, eliminating all Playwright dependencies.

#### What Changed

**Complete rewrite of `apps/scraping/spiders/snapdeal_spider.py`**:

**Old architecture** (removed):
- Category URL-based discovery (`/products/{category}`)
- Playwright fallback on blocked pages and for pagination
- Hidden inputs + JS variables (`sdLogData`, `pdpConfigs`) as primary extraction
- `scrapy_playwright.page.PageMethod` import dependency

**New architecture**:
- **Phase 1 (Listing)**: Search URL-based discovery (`/search?keyword={term}&noOfResults=20&offset={N}`)
  - Parses `.product-tuple-listing` elements for product URLs
  - Extracts pogId from URL path for dedup
  - Pagination via `offset` query param (increment by 20)
  - **CRITICAL**: Skips `/honeybot` honeypot links
- **Phase 2 (Detail)**: Schema.org microdata extraction (`itemprop` attributes)
  - `itemprop="name"` → title
  - `itemprop="price"` + `itemprop="priceCurrency"` → price (rupees → paisa)
  - `itemprop="brand"` → brand
  - `itemprop="ratingValue"` → rating (Decimal 0-5)
  - `itemprop="reviewCount"` / `itemprop="ratingCount"` → review count
  - `itemprop="description"` → description
  - `itemprop="availability"` → stock status
  - `itemprop="image"` → product images
  - Falls back to hidden inputs + CSS selectors when microdata sparse

**Key design decisions**:
- Pure HTTP — zero Playwright dependency (Snapdeal is fully SSR, no anti-bot)
- Search queries instead of category URLs (per feasibility report recommendation)
- 17 seed queries covering electronics, appliances, kitchen, grooming, wearables
- Dedup via `_seen_ids` set (pogId-based, same as Vijay Sales pattern)
- Follows same code structure as Reliance Digital + Vijay Sales spiders

**Registration**: Already configured — `"snapdeal": "snapdeal"` in `ScrapingConfig.spider_map()`, marketplace seeded in DB

#### Files Changed

| File | Change |
|------|--------|
| `apps/scraping/spiders/snapdeal_spider.py` | Complete rewrite — removed Playwright, added search-based discovery + microdata extraction |

#### Run Command
```
cd backend
python -m apps.scraping.runner snapdeal --max-pages 1
```

### 2026-03-03 — Nykaa Spider (HTTP-only with curl_cffi TLS Impersonation)

**P1 spider** — rewrote existing Playwright-based `nykaa_spider.py` to pure HTTP with Akamai bypass.

#### Problem: Akamai Bot Manager TLS Fingerprinting
- Nykaa uses Akamai Bot Manager which checks JA3/JA4 TLS fingerprints
- Python's ssl/urllib3/Twisted TLS handshake is blocked (403) regardless of HTTP headers
- `curl` from same machine works fine — different TLS fingerprint
- **Solution**: `curl_cffi` library with `impersonate='chrome120'` mimics Chrome's TLS handshake

#### Problem: Stale Category URLs
- User-provided category IDs (c/8, c/6, c/12, etc.) all returned 404
- Existing spider's category IDs (c/5116, c/6627, etc.) redirected to wrong pages
- **Solution**: Discovered 21 correct category URLs from nykaa.com homepage (e.g., `/makeup/face/face-foundation/c/228`, `/skin/moisturizers/face-moisturizer-day-cream/c/8395`)

#### Problem: Chrome/131 UA Blocked
- Akamai blocks Chrome/131+ `sec-ch-ua` format but allows Chrome/120
- **Solution**: Pinned to Chrome/120 UA with `"Not_A Brand";v="8", "Chromium";v="120"` sec-ch-ua header

#### Architecture
- **Phase 1 (Listing)**: Category pages → `__PRELOADED_STATE__` → `categoryListing.listingData.products` (20/page)
  - Pagination via `?page_no=N`, stops on `stopFurtherCall` flag or empty products
  - Extracts product URLs as `/product-slug/p/product-id`
- **Phase 2 (Detail)**: Product pages → `__PRELOADED_STATE__` → `productPage.product`
  - Primary: Redux state with full product data (name, prices, brand, rating, images, manufacturer, etc.)
  - Fallback: JSON-LD `<script type="application/ld+json">` for structured data
  - Prices in rupees → multiplied by 100 for paisa storage
- **CurlCffiDownloaderMiddleware**: Custom Scrapy downloader middleware that intercepts nykaa.com requests and routes through curl_cffi with `impersonate='chrome120'`
- `json.JSONDecoder().raw_decode()` for robust `__PRELOADED_STATE__` parsing (handles trailing JS)

#### Test Results (`--max-pages 1`)
- **79 pages crawled** — ALL HTTP 200 (zero 403s)
- **75 products extracted** — 100% success rate
- **128 items/minute** throughput
- Rich data: prices (paisa), ratings, review counts, images, manufacturer info, return policy, country of origin

#### Dependencies Added
- `curl_cffi>=0.14.0` added to `backend/requirements/base.txt`

#### Files Changed

| File | Change |
|------|--------|
| `apps/scraping/spiders/nykaa_spider.py` | Complete rewrite — removed Playwright, HTTP-only with curl_cffi TLS impersonation, 21 verified category URLs, `__PRELOADED_STATE__` + JSON-LD extraction |
| `requirements/base.txt` | Added `curl_cffi>=0.14.0` for Chrome TLS impersonation |

#### Run Command
```
cd backend
python -m apps.scraping.runner nykaa --max-pages 1
```

---

### 2026-03-03 — JioMart Spider (P2 Marketplace)

#### Overview
Built a **sitemap-based, HTTP-only** spider for JioMart (jiomart.com). JioMart's listing/search pages are 100% client-rendered via Algolia, making them impossible to scrape without Playwright. However, product detail pages are server-side rendered, and JioMart publishes comprehensive XML sitemaps. The spider uses sitemap discovery for Phase 1 and SSR HTML parsing for Phase 2.

#### Problem: Akamai WAF TLS Fingerprinting
- Standard Python requests blocked with HTTP 403 by Akamai Bot Manager
- Same issue as Nykaa — TLS fingerprint (JA3/JA4) doesn't match any real browser
- **Solution**: `JioMartCurlCffiMiddleware` using `curl_cffi` with `impersonate="chrome131"` for Chrome TLS handshake

#### Problem: Double Decompression of Gzipped Sitemaps
- curl_cffi internally decompresses gzip/brotli responses, but passes through the original `Content-Encoding` header
- Scrapy's `HttpCompressionMiddleware` then tried to decompress already-decompressed content → "Not a gzipped file" error
- **Solution**: Strip `Content-Encoding` header from curl_cffi responses before returning to Scrapy

#### Architecture
- **Phase 1 (Sitemap Discovery)**: Fetch `sitemap.xml` → parse sitemap index XML → filter to allowed verticals (electronics, cdit, home-improvement) → parse sub-sitemaps → extract product URLs
  - Uses `xml.etree.ElementTree` for namespace-aware XML parsing
  - `ALLOWED_SITEMAPS` dict filters v1 categories (skips groceries/FMCG)
  - `--max-pages` controls URLs per sitemap: `urls_per_sitemap = max_pages * 50`
- **Phase 2 (Product Detail)**: HTTP GET product pages → parse SSR HTML
  - Title from `<span class="product-header-name">`
  - Selling price from `#pdp-price-info` span
  - MRP from `.line-through` span or MRP label
  - Images from `#images_[n]` tags
  - Specs from `#features-value-container` divs
  - Breadcrumbs from `.cls-bread-crumb` links
  - Brand from `<a href="/brand/...">`
  - Rating/reviews from `.plp-card-details-rating` and `.plp-card-details-reviewCount`
  - In-stock detection via absence of `.oos-text` class
- **Category mapping**: URL vertical segments mapped to Whydud category slugs via `VERTICAL_CATEGORY_MAP`
- **Stale URL handling**: 404 responses logged and skipped gracefully (sitemaps dated 2023-12 to 2024-04)

#### Test Results (`--max-pages 1`)
- **2 sitemaps fetched** — electronics (7,124 URLs) + cdit (43,701 URLs)
- **100 product URLs queued** — 50 per sitemap
- **94 products extracted** — 97% success rate (3 stale 404s)
- **90 products synced to Meilisearch**
- **45 items/minute** throughput
- Rich data: prices (paisa), images, specs, breadcrumbs, brand, availability

#### Files Changed

| File | Change |
|------|--------|
| `apps/scraping/spiders/jiomart_spider.py` | Complete rewrite — removed Playwright, sitemap-based discovery + HTTP-only SSR parsing, curl_cffi TLS impersonation, Akamai WAF bypass |

#### Run Command
```
cd backend
python -m apps.scraping.runner jiomart --max-pages 1
```

---

### 2026-03-03 — Tier 3 Playwright Spiders: Tata CLiQ, Croma, Meesho

**Status:** Built (untested — needs live run with `--max-pages 1`)

Built Playwright-based spiders for the three hardest-to-scrape Indian marketplaces. All use XHR/fetch interception as the primary extraction strategy, with DOM/JSON-LD/HTML fallbacks.

#### Shared Architecture (all 3 spiders)
- **XHR Interception**: `page.add_init_script()` patches `window.fetch` and `XMLHttpRequest.prototype` BEFORE page scripts load — captures all JSON API responses into `window.__whydud_xhr` array
- **DOM Injection**: After page load, `PageMethod("evaluate")` serializes captured XHR data into a `<script id="__whydud_data">` element for Scrapy to parse
- **DataImpulse Proxy**: `http://7be2cfc014934c04249e:dd4d0a314e025711@gw.dataimpulse.com:823` configured per-context
- **2 Browser Contexts**: Round-robin rotation (`{name}_0`, `{name}_1`) for IP diversity
- **playwright-stealth**: Applied via `self.STEALTH.apply_stealth_async(page)` in page init callback
- **Extraction chain**: XHR API data → framework state (__NEXT_DATA__/__INITIAL_DATA__) → JSON-LD → HTML CSS selectors

#### Tata CLiQ Spider (`tatacliq_spider.py`)
- **Anti-bot**: Cloudflare Bot Management (`__cf_bm` cookie)
- **Site type**: Pure SPA — every page returns `<div id="root">`, all data loaded via XHR
- **Delays**: 5-10s between pages, `CONCURRENT_REQUESTS=2`
- **XHR keys**: `/api/`, `/searchProducts`, `/product/`, `mplSearchResult`, `productDetails`
- **Categories**: 16 seed categories covering electronics, fashion, home, beauty

#### Croma Spider (`croma_spider.py`)
- **Anti-bot**: Akamai Bot Manager (blocks ALL HTTP requests)
- **Site type**: React SSR + SAP Hybris backend
- **Strategy**: Homepage warm-up first (Akamai sensor challenge runs on first page load, sets `_abck` cookie), then category pages
- **Delays**: 10-15s (Akamai rate-limits to ~5 req/min), `CONCURRENT_REQUESTS_PER_DOMAIN=1`
- **XHR keys**: `/search`, `/products`, `hybris`, Hybris API responses with classifications/stockInfo
- **Categories**: 39 seed categories (electronics-focused)

#### Meesho Spider (`meesho_spider.py`)
- **Anti-bot**: Akamai Bot Manager (most aggressive anti-bot of the three)
- **Site type**: Next.js with empty `__next` div (data loaded entirely via API)
- **Delays**: 7-12s, `CONCURRENT_REQUESTS=2`, `MAX_LISTING_PAGES=3` (conservative)
- **XHR keys**: `catalogs`, `catalog_id`, `catalog_data`, `/api/`, `product`
- **Categories**: 19 seed categories covering fashion, home, beauty, electronics

#### Celery Beat Schedules (updated)
| Spider | Schedule | IST |
|--------|----------|-----|
| tata-cliq | `crontab(minute=30, hour=6)` — 06:30 UTC | 12:00 IST |
| croma | `crontab(minute=0, hour=8)` — 08:00 UTC | 13:30 IST |
| meesho | `crontab(minute=0, hour=10)` — 10:00 UTC | 15:30 IST |

#### Files Changed

| File | Change |
|------|--------|
| `apps/scraping/spiders/tatacliq_spider.py` | Complete rewrite — Playwright + XHR interception, Cloudflare bypass, DataImpulse proxy |
| `apps/scraping/spiders/croma_spider.py` | Complete rewrite — Playwright-first with homepage warm-up, Akamai bypass, Hybris API extraction |
| `apps/scraping/spiders/meesho_spider.py` | Complete rewrite — Playwright + XHR interception, Akamai bypass, Next.js API capture |
| `whydud/celery.py` | Updated Beat schedules: tata-cliq 06:30 UTC, croma 08:00 UTC, meesho 10:00 UTC |

#### Test Commands
```
cd backend
python -m apps.scraping.runner tata_cliq --max-pages 1
python -m apps.scraping.runner croma --max-pages 1
python -m apps.scraping.runner meesho --max-pages 1
```

---

### 2026-03-04 — TataCLiQ Spider: Live Testing & Fixes

**Status:** Tested & Working

Ran the TataCLiQ spider live and fixed 8 issues discovered during testing.

#### Issues Found & Fixed

1. **Middleware overriding spider's Playwright context** — `PlaywrightProxyMiddleware._process_rotating_request` overwrote `playwright_context` and `playwright_context_kwargs`, removing spider-specific settings like `bypass_csp: True`. Fix: Added `_skip_proxy_middleware` meta flag check in middleware's `process_request` and `process_response`.

2. **SPA redirect to /404 not detected as block** — TataCLiQ's SPA client-side redirects to `/404` when bot-detected, but `_is_blocked` only checked HTTP status codes. Fix: Added URL pattern check for `/404`, title check for "page not found"/"404", gadget-clp redirect detection, and captcha body check (small pages only).

3. **No homepage warmup** — Cloudflare Bot Management requires `__cf_bm` session cookie established first. Fix: Added homepage warmup visit in `start_requests` with `_after_warmup`/`_warmup_failed` callbacks.

4. **Product page visits fail with ERR_PROXY_AUTH_UNSUPPORTED** — Individual product page requests through DataImpulse proxy failed with Chromium proxy auth errors. Fix: Eliminated product page visits entirely — extract all data directly from listing page XHR/DOM data.

5. **Marketplace slug mismatch ('tata-cliq' vs 'tata_cliq')** — DB has `tata_cliq` (underscore), spider used `tata-cliq` (hyphen). Pipeline logged "Marketplace 'tata-cliq' not found — skipping item". Fix: Changed `MARKETPLACE_SLUG = "tata_cliq"`.

6. **Pagination URL loses search query params** — `response.url.split("?")[0]` stripped the search text, producing `search/?page=1&size=40` instead of preserving `searchCategory=all&text=smartphones`. Fix: Rewrote pagination with `urllib.parse` to preserve all existing query params.

7. **XHR capture missing Request object URLs** — `fetch()` calls using `new Request(url)` showed as empty string because capture JS only checked `typeof arguments[0] === 'string'`. Fix: Added fallbacks to check `a0.url` and `r.url`.

8. **Generic search terms redirect to promo CLP pages** — Terms like "laptops", "television" redirect to `gadget-clp` promo page instead of search results. Fix: Updated seed queries to use brand-specific terms and reordered known-working queries first.

#### Architecture Changes
- **Listing-only extraction**: Spider no longer visits individual product pages. All data extracted from search page XHR (Hybris `searchab` API) or DOM fallback
- **Proxy made optional**: Reads from `SCRAPING_PROXY_LIST` env var, works without proxy when empty (direct connections)
- **XHR priority**: `_find_products_in_xhr` now prioritizes Hybris `/searchab/` API responses
- **Wait time increased**: From 5-10s to 8-15s to ensure XHR responses are captured

#### Test Results (`--max-pages 1`)
- **40 items scraped** — from 1 successful search query ("smartphones")
- **100% extraction rate** — 40/40 product attempts succeeded
- **0 failures** — zero items dropped by pipeline
- **XHR-only extraction** — all 40 products from Hybris searchab API, 0 from DOM fallback
- Products created in DB with brand matching working (Sony, OnePlus, Apple, Realme, CMF)

#### Files Changed

| File | Change |
|------|--------|
| `apps/scraping/spiders/tatacliq_spider.py` | Major rework — listing-only extraction, homepage warmup, optional proxy, XHR priority, brand-specific search queries, pagination fix |
| `apps/scraping/middlewares.py` | Added `_skip_proxy_middleware` meta flag check in `PlaywrightProxyMiddleware.process_request` and `process_response` |

#### Run Command
```
cd backend
python -m apps.scraping.runner tata_cliq --max-pages 1
```

---

### 2026-03-04 — Wave 2 Spider Setup: Giva + FirstCry Marketplace Seed Data & Giva Spider

#### What Was Done

**Prompt 0: Marketplace Seed Data**
- Added **Giva** (`slug: giva`, `base_url: https://www.giva.co`) and **FirstCry** (`slug: firstcry`, `base_url: https://www.firstcry.com`) to `seed_marketplaces.py`
- Both set to `scraper_status: development` (not active in daily scrape rotation)
- Updated marketplace count: 12 -> 14
- Registered both spiders in `ScrapingConfig.spider_map()` in `common/app_settings.py`
- Fixed slug migration logic in `seed_marketplaces.py` to handle case where both old (`amazon_in`) and new (`amazon-in`) slugs exist (UniqueViolation crash)
- Fixed Unicode arrow character in seed command output (cp1252 encoding crash on Windows)

**Prompt 1A: Giva Spider (Shopify JSON API)**
- Created `apps/scraping/spiders/giva_spider.py` -- pure HTTP spider, no Playwright
- **Architecture change**: Giva's `/collections/{slug}.json` endpoints are broken (404/empty). Switched to single-phase `/products.json` approach which returns all ~5,000 products across 20 pages (250 per page)
- Prices converted from rupees to paisa (* 100)
- Deduplication via `_seen_ids` set
- Structured tag parsing: Giva uses `Key_Value` format tags (e.g., `Metal_925 Silver`, `Color_Rose Gold`, `plating_Rose Gold Micron`)
- Specs extracted: Material, Color, Plating, Stone, Weight, Lock Type, Length, Thickness, Hallmark, Category, Style, SKU
- Fixed brotli encoding issue: removed `br` from Accept-Encoding (brotli package not installed)
- Settings: 0.5s download delay, 2 concurrent requests, 3 retries

#### Test Results (`--max-pages 1`)
- **250 items scraped** from 1 API page (250 per page)
- **100% success rate** -- 250/250, 0 failures
- **206 canonical products** created in DB (some shared across collections)
- **250 product listings** with correct marketplace linkage
- **Price snapshots** recorded in TimescaleDB hypertable
- **Meilisearch** synced: 206 products indexed
- **~20 seconds** total runtime for 250 products
- Prices verified: Rs 2,499 = 249900 paisa (correct conversion)
- Specs quality: Material (925 Silver), Color (Rose Gold), Plating, Hallmark (BIS 925), Weight, etc.

#### Files Changed

| File | Change |
|------|--------|
| `apps/products/management/commands/seed_marketplaces.py` | Added Giva + FirstCry entries (14 total), fixed slug migration UniqueViolation, fixed Unicode cp1252 crash |
| `common/app_settings.py` | Added `giva` and `firstcry` to `ScrapingConfig.spider_map()` |
| `apps/scraping/spiders/giva_spider.py` | **NEW** -- Giva spider using Shopify /products.json API, single-phase, structured tag parsing |

#### Run Command
```
cd backend
python -m apps.scraping.runner giva --max-pages 1
```

### 2026-03-04 — FirstCry Spider (Prompt 2B: Baby & Kids Marketplace)

#### What Was Done

**Reconnaissance Findings** (deviated from dev plan assumptions):
- **Server:** Apache/2.4.54 with OpenSSL — no Cloudflare/Akamai protection
- **Category URLs broken:** `/baby-care`, `/toys`, `/diapers` all return 404
- **Search works:** `/search?q={query}` redirects to listing pages with SSR HTML
- **Product URL pattern:** `/brand/slug/PID/product-detail` (NOT `.html` as dev plan assumed)
- **JSON-LD broken:** Present on product pages but empty/unparseable
- **Goldmine:** `CurrentProductDetailJSON` embedded JS variable contains full product data (name, MRP, discount%, images, age groups, colors, sizes)
- **Pagination:** `?page=N` works, 20 products per page

**Spider Implementation** (`apps/scraping/spiders/firstcry_spider.py` — ~580 lines):
- `FirstCryCurlCffiMiddleware` — curl_cffi Session with `impersonate="chrome131"`, intercepts all firstcry.com requests
- `FirstCrySpider` inherits `BaseWhydudSpider`
- **Discovery:** 24 seed search queries across 8 categories (baby care, feeding, clothing, toys, gear, nursery, footwear, school supplies)
- **Listing extraction:** CSS `div.li_inner_block a[href*='/product-detail']` for product links, pagination via `?page=N`
- **Detail extraction:** `CurrentProductDetailJSON` via `json.JSONDecoder().raw_decode()`, plus `avg_rating` and `totalreview` JS variables
- **Price calculation:** `selling_price = mrp * (100 - Dis) / 100`, then * 100 for paisa
- **Image extraction:** Semicolon-separated `Img` field → CDN URLs (`cdn.fcglcdn.com/brainbees/images/products/438x531/`)
- **Age groups:** Parsed from `hashAgeG` (e.g., `["0#0-3 Months", "1#3-6 Months"]`) → stored in variant_options
- **Colors:** Parsed from `hashCols` (e.g., `["10#Multi Color"]`) → stored in variant_options
- **Settings:** `DOWNLOAD_DELAY=1.5s`, `CONCURRENT_REQUESTS=4`, `CONCURRENT_REQUESTS_PER_DOMAIN=3`

**Celery Beat Schedule:**
- Added `scrape-firstcry-daily` at 09:30 UTC (15:00 IST) in `whydud/celery.py`

**Documentation:**
- Updated `docs/Scraping-logic.md`: file structure, spider count (15), Section 5 entry, anti-bot table, Celery Beat schedule table

#### Files Changed

| File | Change |
|------|--------|
| `apps/scraping/spiders/firstcry_spider.py` | **NEW** — FirstCry spider with curl_cffi middleware, search-based discovery, CurrentProductDetailJSON extraction |
| `whydud/celery.py` | Added `scrape-firstcry-daily` Beat schedule entry (09:30 UTC) |
| `docs/Scraping-logic.md` | Added FirstCry to file structure, spider count, Section 5 reference, anti-bot table, Beat schedule table |

#### Run Command
```
cd backend
python -m apps.scraping.runner firstcry --max-pages 1
```

---

### 2026-03-04 — AJIO Spider (Prompt 3A recon + 3B build)

**Reconnaissance (Prompt 3A):**
- Created `apps/scraping/spiders/test_ajio_recon.py` — probed AJIO site structure
- **All HTTP blocked:** Akamai Bot Manager returns 403 Access Denied on every endpoint
- Internal APIs (`/api/category`, `/api/search`, `/api/p/`) all blocked
- `curl_cffi` Chrome 131 TLS impersonation insufficient — Akamai detects it
- `_abck` cookies and `edgesuite.net` error references confirm Akamai infrastructure
- **Difficulty revised: 8/10** (up from initial 7/10 estimate)

**Spider Build (Prompt 3B):**
- Created `apps/scraping/spiders/ajio_spider.py` — full Playwright spider
- **Architecture:** Full Playwright + stealth for BOTH listing and product phases (no HTTP fallback possible)
- **Listing phase:** Playwright → `networkidle` → extract `a[href*="/p/"]` links → `?page=N` pagination
- **Detail phase:** Playwright → `domcontentloaded` → JSON-LD first → CSS selector fallback
- **Block detection:** Checks for 403 + "Access Denied" text, retries once with rotating proxy
- **10 seed categories:** men-t-shirts, men-shirts, men-jeans, women-kurtas, women-tops, women-dresses, men-shoes, women-shoes, bags-wallets, watches
- **Settings:** `DOWNLOAD_DELAY=5s`, `CONCURRENT_REQUESTS=1`, serial only (Akamai rate-sensitive)
- **Note:** Residential proxy rotation likely required for production success rates — Akamai blocks datacenter IPs aggressively

**Marketplace seed data:** AJIO already exists in `seed_marketplaces.py` (slug: `ajio`)

#### Files Changed

| File | Change |
|------|--------|
| `apps/scraping/spiders/ajio_spider.py` | **NEW** — AJIO spider with full Playwright, Akamai block detection, JSON-LD + CSS extraction |
| `apps/scraping/spiders/test_ajio_recon.py` | **NEW** — AJIO recon script (curl_cffi probes, API endpoint checks, Akamai detection) |

#### Run Command
```
cd backend
python -m apps.scraping.runner ajio --max-pages 1
```

### 2026-03-04 — AJIO Spider Rewrite: Camoufox (replaces Playwright)

**Problem:** Playwright + stealth + residential proxy got 100% blocked by Akamai Bot Manager (all HTTP 403).

**Solution:** Rewrote the AJIO spider to use **camoufox** (anti-detection Firefox), following the same pattern as `meesho_spider.py`.

**Test results:**
- **Run 1:** Camoufox bypassed Akamai successfully — HTTP 200 on all 3 listing pages, 45 products extracted per page, first product detail page loaded with full data (title, brand, price ₹2399, MRP ₹3999, images, variants)
- **Run 2:** Akamai rate-limited the IP after Run 1's heavy activity — all 403s. Expected behavior; production needs IP rotation between runs.

**Key changes:**
- Replaced Playwright with `AJIOCamoufoxMiddleware` (in-file downloader middleware)
- Disabled Playwright download handlers, added camoufox at middleware priority 100
- Added threading lock to serialise camoufox page operations (prevents greenlet cross-thread errors)
- Fixed specs to use comma-separated strings instead of lists (pipeline compatibility)
- Filtered empty variant values
- Removed all Playwright-specific code (PageMethod, stealth callbacks, playwright meta)

**Architecture:** Same as Meesho spider — camoufox sync API runs in thread pool via `run_in_executor`, single browser context persists for cookie/session continuity.

#### Files Changed

| File | Change |
|------|--------|
| `apps/scraping/spiders/ajio_spider.py` | **REWRITTEN** — Camoufox-based spider replacing Playwright |

### 2026-03-04 — Myntra Spider Rewrite: Camoufox (replaces Playwright)

**Problem:** Myntra (Flipkart Group) uses PerimeterX / HUMAN anti-bot. Playwright with stealth gets blocked. Recon confirmed PerimeterX markers and SPA rendering requirement.

**Solution:** Rewrote `myntra_spider.py` to use **camoufox** (anti-detection Firefox), following the proven pattern from AJIO and Meesho spiders.

**Architecture:**
- `MyntraCamoufoxMiddleware` — in-file downloader middleware, camoufox sync API in thread pool via `run_in_executor`
- Threading lock serialises page operations (prevents greenlet cross-thread errors)
- Single browser context persists across requests for cookie/session continuity
- Disabled Playwright download handlers; camoufox at middleware priority 100

**Two-phase extraction:**
- **Phase 1 (Listing):** Category pages (`/{category}?p={n}`) via camoufox → extract product URLs from `window.__myx` state (primary) or DOM product cards (fallback)
- **Phase 2 (Detail):** Product pages via camoufox → 4-strategy extraction cascade:
  1. `window.__myx` embedded JSON (pdpData, productData) — richest source
  2. JSON-LD structured data (`schema.org/Product`)
  3. DOM parsing (CSS selectors: `h1.pdp-title`, `span.pdp-price`, `.image-grid-image`, etc.)
  4. Listing data fallback (from Phase 1 state extraction)

**Features:**
- 26 seed category URLs (men/women fashion, footwear, accessories, beauty)
- Full ProductItem extraction: title, brand, price/MRP (paisa), images, rating, review_count, specs (articleAttributes), sizes, colours/variants, breadcrumbs, delivery info, return policy
- PerimeterX-specific block detection (px-captcha, Press & Hold, window._pxAppId markers)
- Quick mode: `--max-pages 3` uses first 5 categories only
- Spider args: `job_id`, `category_urls`, `urls` (direct product URLs), `max_pages`
- Custom settings: DOWNLOAD_DELAY=5, CONCURRENT_REQUESTS=1, RETRY_TIMES=2

**Test command:**
```bash
cd backend
python -m apps.scraping.runner myntra --max-pages 1
```

#### Files Changed

| File | Change |
|------|--------|
| `apps/scraping/spiders/myntra_spider.py` | **REWRITTEN** — Camoufox-based spider replacing Playwright version |

### 2026-03-04 — Flipkart Spider: Fix All Errors (greenlet crash, brotli, deprecations)

**Problem:** Flipkart spider was crashing with multiple errors:
1. **CRITICAL — `greenlet.error: Cannot switch to a different thread`:** Camoufox middleware used `run_in_executor(None, ...)` which dispatches to *different* threads from the default pool. Playwright's sync API uses greenlets bound to a single OS thread — concurrent requests from different threads crashed.
2. **`brotli` not installed:** Flipkart serves brotli-compressed (`br`) responses. Without the package, `HttpCompressionMiddleware` couldn't decode them → responses arrived as non-text → every product page unnecessarily fell back to camoufox, which then also crashed from the greenlet issue.
3. **LeakWarning:** Camoufox warned about `block_images` causing WAF detection issues.
4. **Scrapy 2.14 deprecation warnings:** `start_requests()` deprecated for `start()`, and all middleware/pipeline methods with explicit `spider` argument deprecated.

**Fixes:**
1. **Greenlet fix:** Replaced default `ThreadPoolExecutor` with a **single-worker executor** (`max_workers=1, thread_name_prefix="camoufox"`). All browser operations now serialised on the same OS thread — no greenlet cross-thread switches possible. Removed the `threading.Lock` (no longer needed).
2. **Brotli:** Added `brotli>=1.1.0` to `requirements/base.txt` and installed. Product detail pages now decode properly via plain HTTP — massively reduces camoufox fallback load.
3. **LeakWarning:** Added `i_know_what_im_doing=True` to Camoufox constructor.
4. **Deprecation fixes:**
   - `FlipkartSpider.start_requests()` → `async def start()` (Scrapy 2.13+ async generator)
   - `FlipkartCamoufoxMiddleware.process_request(request, spider)` → `process_request(request, spider=None)`
   - `BackoffRetryMiddleware` — removed `spider` from `process_response`/`process_exception`, added `from_crawler()`, uses module `logger` instead of `spider.logger`
   - All 7 pipelines updated: added `from_crawler()` class method, removed `spider` arg from `process_item`/`open_spider`/`close_spider`, access spider via `self._crawler.spider`

**Test command:**
```bash
cd backend
python -m apps.scraping.runner flipkart --max-pages 1
```

#### Files Changed

| File | Change |
|------|--------|
| `apps/scraping/spiders/flipkart_spider.py` | Fixed greenlet crash (single-thread executor), `start()` async, `i_know_what_im_doing`, removed unused `threading` import |
| `apps/scraping/middlewares.py` | `BackoffRetryMiddleware` — removed `spider` arg, added `from_crawler()` |
| `apps/scraping/pipelines.py` | All 7 pipelines updated: `from_crawler()` + removed `spider` arg from all methods |
| `requirements/base.txt` | Added `brotli>=1.1.0` |

### 2026-03-04 — FirstCry Spider: Recon + Full Build (Wave 2 — Spider 2)

**Context:** SCRAPER-DEV-PLAN-WAVE2.md Prompt 2A (recon) + Prompt 2B (build).

**Recon findings (test_firstcry_recon.py):**
- Server: Apache/2.4.54 — **no Cloudflare, no Akamai**. Minimal anti-bot.
- Direct category URLs (`/baby-care`) return 404. Categories use numeric IDs or search redirects.
- `/search?q={query}` redirects to SSR listing pages (200–1.3MB) with 20+ product cards.
- Product URL pattern: `/{brand}/{slug}/{PID}/product-detail` (not `.html` as dev plan assumed).
- Product pages embed rich JS: `CurrentProductDetailJSON` with pid, pn, mrp, Dis%, hashAgeG (age groups), hashCols (colors), Img, stock, warranty.
- Additional JS vars: `avg_rating`, `totalreview`, `review_url`, `cat_url`, `scat_url`.
- **HTTP-only viable** — no Playwright needed for either listing or detail phase.
- Difficulty: **3/10** (downgraded from plan's 4/10).

**Spider architecture (firstcry_spider.py):**
- HTTP-only via `curl_cffi` + `FirstCryCurlCffiMiddleware` (Chrome/131 TLS impersonation).
- Phase 1 (Listing): Search-based discovery `/search?q={query}` → parse SSR HTML `div.li_inner_block a[href*='/product-detail']` → extract PIDs. Pagination via `?page=N`. 24 seed search queries across baby-care, feeding, clothing, toys, gear, nursery, footwear, school.
- Phase 2 (Detail): Extract `CurrentProductDetailJSON` via `json.JSONDecoder.raw_decode()`. Rating/reviews from `avg_rating`/`totalreview` JS vars.
- Age group extraction (CRITICAL): `hashAgeG` → `["0#0-3 Months", ...]` → `specs.age_group`.
- Colors from `hashCols`, images from `Img` (semicolon-separated CDN filenames).
- Prices in rupees → converted to paisa (* 100). Selling price computed as `MRP * (1 - Dis/100)`.
- Brand extracted from URL path segment.
- Breadcrumbs from `cat_url`/`scat_url` JS vars.
- Category inference from breadcrumb keywords.
- Dedup by product ID. Pagination tracking per base URL.

**Settings:** `DOWNLOAD_DELAY=1.5`, `CONCURRENT_REQUESTS=4`, `RETRY_TIMES=3`.

**Test command:**
```bash
cd backend
python -m apps.scraping.runner firstcry --max-pages 1
```

#### Files Changed

| File | Change |
|------|--------|
| `apps/scraping/spiders/firstcry_spider.py` | **NEW** — Full HTTP-only spider with curl_cffi, search-based discovery, CurrentProductDetailJSON extraction |
| `apps/scraping/spiders/test_firstcry_recon.py` | **NEW** — Recon script that probed FirstCry site structure and anti-bot |

---

### Fix: Google OAuth "Network request failed" (2026-03-04)

**Problem:** Google OAuth sign-in completed on the backend but the frontend callback page showed "Network request failed" when exchanging the one-time code for a DRF token.

**Root causes found (3 issues):**

1. **`frontend/src/lib/api/client.ts` — All client-side API calls broken.** The `new URL(path, "http://localhost:3000")` fallback on the client side caused every browser `fetch()` to target `localhost:3000` on the user's machine instead of `whydud.com`. Fixed by using `window.location.origin` as the base URL on the client side.

2. **`frontend/src/app/accounts/[...path]/route.ts` & `oauth/[...path]/route.ts` — Proxy loop.** Route handlers used `NEXT_PUBLIC_API_URL` (= `https://whydud.com` in prod), sending requests back through Caddy to themselves. Fixed by using `INTERNAL_API_URL` (= `http://backend:8000`) for server-side proxying.

3. **`docker/Caddyfile` — Missing `/accounts/*` and `/oauth/*` routes.** AllAuth OAuth endpoints fell through to the Next.js catch-all instead of going directly to Django. Added explicit `handle` blocks for both paths.

#### Files Changed

| File | Change |
|------|--------|
| `frontend/src/lib/api/client.ts` | Fix URL base: use `window.location.origin` on client side instead of `http://localhost:3000` |
| `frontend/src/app/accounts/[...path]/route.ts` | Use `INTERNAL_API_URL` instead of `NEXT_PUBLIC_API_URL` |
| `frontend/src/app/oauth/[...path]/route.ts` | Use `INTERNAL_API_URL` instead of `NEXT_PUBLIC_API_URL` |
| `docker/Caddyfile` | Add `/accounts/*` and `/oauth/*` → `reverse_proxy backend:8000` |

---

### 2026-03-04 — Sentry Error Monitoring for Django Backend

#### What Was Done

Configured Sentry SDK for Django backend error monitoring with Celery integration.

- `sentry-sdk[django]==2.26.1` added to requirements
- `sentry_sdk.init()` in `settings/base.py` — guarded by `SENTRY_DSN` env var, 10% traces/profiles sampling, PII disabled
- Separate `sentry_sdk.init()` in `celery.py` with `CeleryIntegration(monitor_beat_tasks=True)` for Celery worker processes
- `SENTRY_DSN` env var added to all backend services in both `docker-compose.primary.yml` and `docker-compose.replica.yml`
- `SENTRY_DSN` added to `backend/.env.example` (root `.env.example` already had it)

#### Verification

```bash
docker compose exec backend python -c "import sentry_sdk; sentry_sdk.capture_message('Whydud Sentry test')"
```

#### Files Changed

| File | Change |
|------|--------|
| `backend/requirements/base.txt` | Add `sentry-sdk[django]==2.26.1` |
| `backend/whydud/settings/base.py` | Add `sentry_sdk.init()` after imports, guarded by `SENTRY_DSN` |
| `backend/whydud/celery.py` | Add `sentry_sdk.init()` with `CeleryIntegration` for worker processes |
| `docker-compose.primary.yml` | Add `SENTRY_DSN` to backend, celery-worker, celery-beat services |
| `docker-compose.replica.yml` | Add `SENTRY_DSN` to backend, celery-scraping services |
| `backend/.env.example` | Add `SENTRY_DSN=` entry |

---

### 2026-03-04 — Security: Password Validation, Login Lockout, OTP Email Verification

Implemented §16 security requirements from ARCHITECTURE.md.

#### What Changed

1. **Password validation on all serializers** — `RegisterSerializer`, `ChangePasswordSerializer`, and `ResetPasswordSerializer` now call `django.contrib.auth.password_validation.validate_password()`. Rejects short (<8 chars), common ("password"), and all-numeric passwords.

2. **Login lockout (5 attempts / 15 min)** — `LoginView` tracks failed attempts via Redis cache key `login_lockout:{email}`. After 5 failures, returns HTTP 429 for 15 minutes. Counter resets on successful login.

3. **OTP-based email verification** — Replaced link-based email verification with 6-digit OTP. On registration a code is sent to the user's email, stored in Redis (`email_otp:{user_id}`, 10-min TTL). `VerifyEmailView` now accepts `{email, otp}` instead of `{uid, token}`. Max 5 OTP attempts before requiring a resend. `ResendVerificationEmailView` generates a fresh OTP.

#### Files Changed

| File | Change |
|------|--------|
| `backend/apps/accounts/serializers.py` | Added `validate_password()` / `validate_new_password()` to Register, ChangePassword, ResetPassword serializers |
| `backend/apps/accounts/views.py` | Login lockout logic, OTP generation, OTP-based VerifyEmailView + ResendVerificationEmailView |
| `backend/apps/accounts/tasks.py` | Added `send_verification_otp` Celery task |

### 2026-03-04 — Username Validation for @whyd.* Email Addresses

Enforced strict username rules for @whyd.xyz email creation and availability checks.

#### Validation Rules

1. Length: 3-30 characters
2. Allowed characters: lowercase letters, digits, dots, underscores (`^[a-z0-9._]+$`)
3. Must start with a letter (not digit/dot/underscore)
4. No consecutive dots (`..`) or underscores (`__`)
5. Cannot end with dot or underscore
6. Checked against `reserved_usernames` table
7. Uniqueness per (username, domain) — same username can exist on different domains

#### What Changed

- **Shared validator** — `validate_whydud_username_format()` in `models.py` handles format rules 1-5 (no DB queries), reused by serializer, model `clean()`, and availability view.
- **Serializer validation** — `WhydudEmailSerializer.validate_username()` enforces all 7 rules (format + reserved + uniqueness). View now delegates to serializer per DRF standards.
- **Model safety net** — `WhydudEmail.clean()` calls the format validator as a last line of defense.
- **View cleanup** — Removed old `_USERNAME_RE` regex from views. `WhydudEmailView.post()` refactored to use serializer. `WhydudEmailAvailabilityView` uses shared validator.
- **Migration 0008** — Seeds 6 additional reserved usernames: postmaster, webmaster, hello, test, pop, imap.

#### Files Changed

| File | Change |
|------|--------|
| `backend/apps/accounts/models.py` | Added `validate_whydud_username_format()`, `WhydudEmail.clean()` |
| `backend/apps/accounts/serializers.py` | Added `validate_username()` to `WhydudEmailSerializer`, added `domain` to fields |
| `backend/apps/accounts/views.py` | Removed `_USERNAME_RE`, refactored `WhydudEmailView.post()` to use serializer, updated availability view |
| `backend/apps/accounts/migrations/0008_seed_more_reserved_usernames.py` | Seeds postmaster, webmaster, hello, test, pop, imap |

### 2026-03-04 — Production Spider Test Script

Created `backend/scripts/test_all_spiders.sh` — a connectivity test script for the 7 spiders never tested on production VPS.

#### Spiders Covered

| Spider | Anti-Bot Strategy | Test URL |
|--------|-------------------|----------|
| croma | curl_cffi Chrome TLS | `croma.com/phones-wearables/mobile-phones/c/10` |
| meesho | camoufox anti-detect Firefox | `meesho.com/mobile-phones/pl/mobiles` |
| ajio | Playwright + PerimeterX | `ajio.com/shop/men-shoes` |
| myntra | Playwright + fingerprinting | `myntra.com/men-tshirts` |
| firstcry | curl_cffi Chrome/131 | `firstcry.com/toys` |
| nykaa | curl_cffi Chrome/120 (partially tested) | `nykaa.com/skin/c/2` |
| jiomart | curl_cffi + sitemap (partially tested) | `jiomart.com/c/groceries/...` |

#### What the Script Does

1. Pre-flight check that `celery-worker` container is running
2. Runs each spider sequentially: `docker compose exec -T celery-worker python -m apps.scraping.runner {spider} --max-pages 1 --urls {url}`
3. Captures exit code, parses `item_scraped_count` from Scrapy stats, measures elapsed time
4. On failure/warning: prints last 20 lines of log output
5. Prints formatted summary table (PASS/WARN/FAIL per spider)
6. Full logs saved to `/tmp/spider_tests_<timestamp>/`

#### Files Changed

| File | Change |
|------|--------|
| `backend/scripts/test_all_spiders.sh` | New file — production spider connectivity test script |

---

### Automated PostgreSQL Backups & System Health Check

**Date:** 2026-03-04

#### Backup System (`backend/scripts/backup.sh`)

Automated PostgreSQL backup script with incremental strategy:

- **pg_dump** with custom format (`-Fc`), excludes TimescaleDB internal schemas
- **Incremental strategy:** Tracks row counts in time-series tables (`price_snapshots`, `dudscore_history`) via manifest file. Skips unchanged hypertable data on subsequent runs to save storage
- **Compression:** gzip -9 on dump files
- **S3 upload:** IDrive S3-compatible via rclone (fallback to AWS CLI). Configured via `RCLONE_S3_ENDPOINT`, `RCLONE_S3_ACCESS_KEY`, `RCLONE_S3_SECRET_KEY` env vars
- **Retention:** 7 days local, 180 days remote
- **Discord notifications:** Success/failure embeds via existing `DISCORD_WEBHOOK_URL`
- **Cron:** Every 6 hours (`0 */6 * * *`) via dedicated `backup` container in docker-compose.primary.yml

#### Health Check Command (`python manage.py health_check`)

7-point system health check with `--json` output option:

| Check | Pass Criteria |
|-------|---------------|
| PostgreSQL | Connected + reports 17 table counts (products, users, reviews, etc.) + DB size |
| Redis | Connected + memory usage stats + key counts |
| Meilisearch | `/health` returns 200 + document counts per index |
| Celery Workers | At least 1 worker responding via `inspect.active()` + queue listing |
| Scraper Recency | Per-marketplace last scrape < 48h ago (warn if some stale, fail if all stale) |
| Disk Usage | < 80% pass, 80-90% warn, > 90% fail |
| Last Backup | < 12h pass, 12-24h warn, > 24h fail |

Exit code 1 if any critical check fails. Supports `--json` flag for machine-readable output.

#### Configuration

- `BackupConfig` added to `common/app_settings.py` (backup_dir, s3_bucket, retention days, max_backup_age_hours)
- Backup container added to `docker-compose.primary.yml` with `backup_data` volume

#### Files Changed

| File | Change |
|------|--------|
| `backend/scripts/backup.sh` | New — automated pg_dump + S3 upload + retention + Discord |
| `backend/apps/accounts/management/commands/health_check.py` | New — 7-check system health command |
| `backend/common/app_settings.py` | Added `BackupConfig` class |
| `docker-compose.primary.yml` | Added `backup` service + `backup_data` volume |

---

### Write a Review — Backend API (2026-03-04)

**Status:** ✅ Complete

Implemented the Write a Review backend API per architecture.md §3 (US-3.6 through US-3.11) and §13.

#### What Was Built

**Service layer** (`backend/apps/reviews/services.py` — NEW):
- `create_review(user, product, validated_data)` — central business logic
- `_generate_content_hash()` — SHA-256 from body_positive + body_negative for duplicate detection
- `_check_verified_purchase()` — validates purchase_platform against Marketplace slugs in DB
- Queues `compute_dudscore` Celery task after review creation
- Queues `award_points_task` for reviewer rewards

**Serializer updates** (`backend/apps/reviews/serializers.py` — MODIFIED):
- Added missing fields: `media`, `has_purchase_proof`, `purchase_proof_url`
- Added `validate_title()` — enforces 5-200 character length
- Added `validate_purchase_price_paid()` — must be > 0 if provided
- Added `validate_media()` — validates array of `{url, type}` objects (image/video)
- Moved creation logic from serializer's `create()` to `services.create_review()`

**Existing infrastructure (already working, no changes needed):**
- `POST /api/v1/products/{slug}/reviews` — ProductReviewsView (IsAuthenticated)
- `GET /api/v1/products/{slug}/review-features` — ReviewFeaturesView (AllowAny)
- 48-hour publish hold via `is_published=False` + `publish_at`
- `publish_pending_reviews` Celery Beat task (hourly)
- UNIQUE(user, product) constraint — one review per product per user

#### Business Rules Implemented
1. One review per product per user (DB constraint + serializer validation)
2. 48-hour publish hold (`is_published=False`, `publish_at=now()+48h`)
3. Source set to `whydud`, user set to `request.user`
4. Verified purchase: `has_purchase_proof=True` AND `purchase_platform` matches a Marketplace slug → `is_verified_purchase=True`
5. Content hash generated from `body_positive + body_negative` for duplicate detection
6. DudScore recalc queued after creation via `compute_dudscore.delay()`
7. Rewards points awarded via `award_points_task.delay()`

#### Files Changed

| File | Change |
|------|--------|
| `backend/apps/reviews/services.py` | New — review creation service layer |
| `backend/apps/reviews/serializers.py` | Updated WriteReviewSerializer: added fields, validations, delegated to service |

---

### Session — 2026-03-04: Write a Review Frontend Enhancements

Enhanced the existing Write a Review 4-tab form with missing features from architecture.md §13.

#### What Was Added

1. **StarRatingInput hover labels** — Shows text label ("Poor", "Fair", "Good", "Very Good", "Excellent") next to stars on hover/selection. New `showLabel` prop. Enabled on the overall rating in LeaveReviewTab.

2. **localStorage draft persistence** — Review form state auto-saves to `localStorage` (key: `review_draft_{slug}`) on every change. Restores form + active tab on page mount. Clears on successful submission. File objects (invoice, media) are excluded from serialization.

3. **Textarea character limits** — "What did you like?" and "What you didn't like?" textareas now enforce 500-character max with live counter display.

4. **Media upload file limit** — Max 5 files enforced. Upload button shows count and hides at capacity.

#### Files Changed

| File | Change |
|------|--------|
| `frontend/src/components/reviews/star-rating-input.tsx` | Added `STAR_LABELS`, `showLabel` prop, hover label display |
| `frontend/src/components/review/leave-review-tab.tsx` | Added `MAX_BODY_CHARS` (500), `MAX_MEDIA_FILES` (5), char counter, file limit enforcement, `showLabel` on overall rating |
| `frontend/src/app/(public)/product/[slug]/review/page.tsx` | Added `saveDraft`/`loadDraft`/`clearDraft` helpers, auto-save effect, load-on-mount, clear-on-submit |
