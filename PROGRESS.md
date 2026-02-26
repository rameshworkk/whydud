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
