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
| DudScore calculation | Celery task is a stub, no sentiment/rating/fraud scoring | Sprint 3 |
| Price history collection | No actual price snapshots being taken | Sprint 2 |
| Razorpay payments | Returns 501 | Sprint 4 |
| Fake review detection | Model exists, no detection rules | Sprint 3 |
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
| Click tracking (affiliate attribution) | ❌ NOT BUILT (model exists, no tracking logic) |
| Purchase search (cross-platform) | ❌ NOT BUILT |
| Admin audit log | ❌ NOT BUILT |
| Admin as independent system | ❌ NOT BUILT |
| Compare tray (floating) | ❌ NOT BUILT |
| Cross-platform price comparison panel | ❌ NOT BUILT |
| Back-in-stock alerts | ❌ NOT BUILT (model exists, no alert logic) |
| Share product/comparison | ❌ NOT BUILT |
| Similar/alternative products | ❌ NOT BUILT |
| Product matching engine | ❌ NOT BUILT |
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
- Dev `.env` exists with all required keys (encryption keys empty — need generation before prod)
- Google OAuth credentials configured for dev
- Meilisearch master key set
- `POSTGRES_PASSWORD=whydud_dev`

### Deployment Readiness
- Multi-stage Dockerfiles ✅
- Health checks on all services ✅
- Caddy reverse proxy + security headers ✅
- Non-root container users ✅
- Missing for prod: encryption keys, Sentry DSN, Resend API key, Razorpay keys

---

## Celery Queues & Tasks

| Queue | Real Tasks | Stub Tasks |
|---|---|---|
| `default` | — | moderate_discussion, flag_spam_reply |
| `scraping` | run_marketplace_spider, fetch_new_listings | — |
| `email` | send_verification_email, send_password_reset_email | process_inbound_email, check_return_window_alerts, detect_refund_delays |
| `scoring` | — | compute_dudscore, full_dudscore_recalculation, index_product, full_reindex |
| `alerts` | — | check_price_alerts, send_price_drop_notification |

---

## Priority Build Order (Updated)

```
Auth is DONE. Next priorities:

1. VISUAL POLISH — Match Figma references exactly:
   - Homepage → docs/figma/homepage.png
   - Search → docs/figma/Search_result_page-1.png
   - Product Detail → docs/figma/Product_detail_page.png
   - Comparison → docs/figma/Comparison_results.png
   - Dashboard → docs/figma/expense_tracker_mockup.png
   - Seller → docs/figma/Seller_detail_page-1.png

2. COMPLETE DASHBOARD PAGES (purchases, rewards, refunds, subscriptions)

3. DATABASE MIGRATIONS for v2.2 (see docs/TASKS.md Phase 1, prompts 1.1-1.10)

4. API ENDPOINTS (see docs/TASKS.md Phase 2, prompts 2.1-2.10)

5. FRONTEND TYPES + API CLIENT (see docs/TASKS.md Phase 3)

6. FRONTEND COMPONENTS + PAGES (see docs/TASKS.md Phase 4)

7. TCO + LEADERBOARD + TRENDING (see docs/TASKS.md Phase 5)

8. SEED DATA (see docs/TASKS.md Phase 6)

9. CELERY TASKS (see docs/TASKS.md Phase 7)

10. INTEGRATION (see docs/TASKS.md Phase 8)

11. EMAIL SYSTEM — webhook handler, send service, categorization, order parsers

12. SCRAPING — Amazon.in spider, Flipkart spider, product matching, price snapshots

13. INTELLIGENCE — DudScore calc, fake review detection, deal detection, dynamic TCO
```

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
  DJANGO_SECRET_KEY         — dev-secret-key (CHANGE FOR PROD)
  DATABASE_URL              — PostgreSQL (password: whydud_dev)
  REDIS_URL                 — redis://localhost:6379/0
  MEILISEARCH_URL           — http://localhost:7700
  MEILISEARCH_MASTER_KEY    — masterKey
  GOOGLE_CLIENT_ID          — Set (OAuth working)
  GOOGLE_CLIENT_SECRET      — Set (OAuth working)

Not configured yet:
  EMAIL_ENCRYPTION_KEY      — Empty (needs 64-char hex for AES-256-GCM)
  OAUTH_ENCRYPTION_KEY      — Empty (needs 64-char hex)
  RESEND_API_KEY            — For email sending
  RAZORPAY_KEY_ID           — Payment processing
  RAZORPAY_KEY_SECRET       — Payment processing
  CLOUDFLARE_EMAIL_SECRET   — Email webhook verification
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
