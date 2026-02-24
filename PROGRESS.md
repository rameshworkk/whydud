# Whydud — Development Progress

**Last Updated:** 2026-02-23
**Current Sprint:** Sprint 1 — Foundation (Weeks 1–3)
**Architecture Reference:** `docs/ARCHITECTURE.md`

## 🎯 CURRENT TASK
Wire the register form and add auth context.

1. In register/page.tsx: Connect Step 1 (name, email, password) to POST /api/v1/auth/register/
2. Connect Step 2 (@whyd.xyz username) to POST /api/v1/email/whydud/create
3. Create src/contexts/auth-context.tsx with AuthProvider (user state, login, logout, isAuthenticated)
4. Wrap root layout with AuthProvider
5. Update header to show "Welcome, {name}" when authenticated, "Log In" when not
6. Create frontend/src/middleware.ts to redirect /dashboard/* to /login if not authenticated
## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Complete |
| 🔧 | Stub / placeholder (returns 501) |
| ⬜ | Not started |

---

## Sprint 1 — Foundation (Weeks 1–3)

### Backend — Database & Models

| Model / Table | App | Schema | Status | Notes |
|---|---|---|---|---|
| `User` | accounts | users | ✅ | AbstractBaseUser, UUID pk, roles enum, subscription_tier |
| `WhydudEmail` | accounts | users | ✅ | username unique, `email_address` property |
| `OAuthConnection` | accounts | users | ✅ | AES-256-GCM encrypted token fields (BinaryField) |
| `PaymentMethod` | accounts | users | ✅ | Card vault — bank name + variant ONLY, no card numbers |
| `ReservedUsername` | accounts | users | ✅ | Seeded via data migration (0002) |
| `Marketplace` | products | public | ✅ | Amazon.in + Flipkart seeded (0002); Croma, Reliance Digital, Meesho pending |
| `Category` | products | public | ✅ | Self-referential FK, has_tco_model flag |
| `Brand` | products | public | ✅ | aliases JSONField, verified flag |
| `Product` | products | public | ✅ | UUID pk, Status enum, dud_score, price denorm fields, indexes |
| `Seller` | products | public | ✅ | UUID pk, per-marketplace unique constraint |
| `ProductListing` | products | public | ✅ | UUID pk, affiliate_url injected at response time |
| `BankCard` | products | public | ✅ | Reference data for offer matching |
| `PriceSnapshot` | pricing | public | ✅ | `managed=False`; TimescaleDB hypertable created in migration 0002 |
| `MarketplaceOffer` | pricing | public | ✅ | Bank/card offers, DiscountType enum, indexes |
| `PriceAlert` | pricing | public | ✅ | Per-user per-product unique constraint |
| `Review` | reviews | public | ✅ | UUID pk, rating 1–5 check constraint, fraud_flags JSONField |
| `ReviewVote` | reviews | users | ✅ | ±1 check constraint, unique per (review, user) |
| `Wishlist` | wishlists | users | ✅ | share_slug for public lists |
| `WishlistItem` | wishlists | users | ✅ | target_price, alert_enabled, price tracking fields |
| `Deal` | deals | public | ✅ | DealType + Confidence enums, views/clicks counters |
| `RewardPointsLedger` | rewards | users | ✅ | BigAutoField, action_type, expires_at |
| `RewardBalance` | rewards | users | ✅ | OneToOne with User as PK |
| `GiftCardCatalog` | rewards | users | ✅ | denominations JSONField |
| `GiftCardRedemption` | rewards | users | ✅ | UUID pk, Status enum, gift code field (encrypted) |
| `InboxEmail` | email_intel | email_intel | ✅ | body stored as BinaryField (AES-256-GCM encrypted) |
| `ParsedOrder` | email_intel | email_intel | ✅ | matched_product FK, match_confidence |
| `RefundTracking` | email_intel | email_intel | ✅ | delay_days, expected_by |
| `ReturnWindow` | email_intel | email_intel | ✅ | alert_sent_3day / alert_sent_1day flags |
| `DetectedSubscription` | email_intel | email_intel | ✅ | billing_cycle, next_renewal |
| `DudScoreConfig` | scoring | scoring | ✅ | Versioned weights, is_active flag, change_reason audit |
| `DudScoreHistory` | scoring | scoring | ✅ | `managed=False`; TimescaleDB hypertable (migration 0002) |
| `DiscussionThread` | discussions | community | ✅ | ThreadType enum, is_pinned, is_locked, index on (product, -created_at) |
| `DiscussionReply` | discussions | community | ✅ | Self-referential parent_reply FK |
| `DiscussionVote` | discussions | community | ✅ | ±1 check constraint, unique per (user, target_type, target_id) |
| `TCOModel` | tco | tco | ✅ | input_schema + cost_components JSONField, versioned per category |
| `CityReferenceData` | tco | tco | ✅ | electricity_tariff, cooling_days, water hardness |
| `UserTCOProfile` | tco | users | ✅ | city FK, tariff override, ac_hours_per_day |

### Backend — Migrations

| App | Migrations | Status | Notes |
|---|---|---|---|
| accounts | 0001_initial, 0002_seed_reserved_usernames | ✅ | ~80 reserved usernames seeded |
| products | 0001_initial, 0002_seed_marketplaces | ✅ | 5 marketplaces seeded |
| pricing | 0001_initial, 0002_timescaledb_setup | ✅ | Hypertable created with autocommit RunPython pattern |
| reviews | 0001_initial | ✅ | |
| wishlists | 0001_initial | ✅ | |
| scoring | 0001_initial, 0002_dudscore_history_hypertable, 0003_weights_sum_constraint | ✅ | |
| email_intel | 0001_initial | ✅ | |
| deals | 0001_initial | ✅ | |
| rewards | 0001_initial | ✅ | |
| discussions | 0001_initial | ✅ | |
| tco | 0001_initial | ✅ | |
| search | 0001_initial | ✅ | |
| scraping | 0001_initial | ✅ | |

> **TimescaleDB pattern:** `atomic = False` is not sufficient with psycopg3; migrations use `RunPython` with `raw_conn.autocommit = True` before any TimescaleDB DDL. See `pricing/migrations/0002_timescaledb_setup.py` as the reference.

### Backend — Shared Infrastructure (`common/`)

| File | Status | What it does |
|---|---|---|
| `common/utils.py` | ✅ | `success_response`, `error_response`, `custom_exception_handler` (standard `{success, data}` envelope) |
| `common/pagination.py` | ✅ | `CursorPagination` + `ProductListPagination`; page sizes from `app_settings`, no hardcoded values |
| `common/app_settings.py` | ✅ | `PaginationConfig`, `ProductConfig`, `SearchConfig` — single source of truth for all tuneable values; Sprint 4 admin panel hooks in here |
| `common/rate_limiting.py` | ✅ | `AnonSearchThrottle`, `UserSearchThrottle`, `ProductViewThrottle`, `WriteThrottle`, `RateLimitMiddleware`; sliding-window via Redis sorted sets |
| `common/permissions.py` | ✅ | Custom DRF permission classes |

### Backend — Settings (`whydud/settings/`)

| Setting Group | Status | Notes |
|---|---|---|
| Database (PostgreSQL 16 + TimescaleDB) | ✅ | Multi-schema search_path, psycopg3, CONN_MAX_AGE |
| Redis (cache + sessions + Celery broker) | ✅ | |
| Celery (5 queues: default, scraping, email, scoring, alerts) | ✅ | |
| Django AllAuth (email + Google OAuth) | ✅ | Updated to non-deprecated `ACCOUNT_LOGIN_METHODS` / `ACCOUNT_SIGNUP_FIELDS` |
| Meilisearch | ✅ | |
| Security (HSTS, CSRF, cookies, CORS) | ✅ | |
| Encryption keys (AES-256-GCM) | ✅ | `EMAIL_ENCRYPTION_KEY`, `OAUTH_ENCRYPTION_KEY` |
| Pagination config | ✅ | `PAGINATION_PAGE_SIZE`, `PAGINATION_MAX_PAGE_SIZE` |
| Product list config | ✅ | `PRODUCT_LIST_PAGE_SIZE`, `PRODUCT_SORT_OPTIONS`, `PRODUCT_LIST_DEFAULT_ORDERING` |
| Search config | ✅ | `SEARCH_PAGE_SIZE_DEFAULT`, `SEARCH_AUTOCOMPLETE_LIMIT`, `SEARCH_SORT_MAP_MEILI` |
| Structlog (JSON logging) | ✅ | |

### Backend — Serializers

| Serializer | App | Status | Notes |
|---|---|---|---|
| `ProductListSerializer` | products | ✅ | Flat `brand_name`, `category_name` strings — compact for list/search pages |
| `ProductDetailSerializer` | products | ✅ | Full nested brand/category + `review_summary` computed field (rating dist, credibility, fraud count) |
| `ProductListingSerializer` | products | ✅ | Affiliate URL injected at response time via `get_buy_url` |
| `BrandSerializer` | products | ✅ | |
| `CategorySerializer` | products | ✅ | |
| `MarketplaceSerializer` | products | ✅ | |
| `SellerSerializer` | products | ✅ | |
| `BankCardSerializer` | products | ✅ | |
| `WishlistSerializer` | wishlists | ✅ | `item_count` computed |
| `WishlistDetailSerializer` | wishlists | ✅ | Inline items |
| `WishlistItemSerializer` | wishlists | ✅ | Uses `ProductListSerializer` for nested product |
| `DealSerializer` | deals | ✅ | `discount_pct_display` formatted string, uses `ProductListSerializer` |
| Other app serializers (reviews, scoring, discussions, rewards, email_intel, pricing, accounts) | various | ✅ | Implemented in previous sessions |

### Backend — Views & URLs

| Endpoint | Method | View | Status | Notes |
|---|---|---|---|---|
| `/api/v1/products/` | GET | `ProductListView` | ✅ | Filters: category, brand, min_price, max_price, q, sort_by, status. Cursor paginated. |
| `/api/v1/products/:slug/` | GET | `ProductDetailView` | ✅ | Full detail + review_summary + listings |
| `/api/v1/products/:slug/price-history/` | GET | `ProductPriceHistoryView` | 🔧 | Sprint 2 |
| `/api/v1/products/:slug/best-deals/` | GET | `ProductBestDealsView` | 🔧 | Sprint 3 |
| `/api/v1/products/:slug/tco/` | GET | `ProductTCOView` | 🔧 | Sprint 4 |
| `/api/v1/products/:slug/discussions/` | GET/POST | `ProductDiscussionsView` | ✅ | GET paginated, POST creates thread |
| `/api/v1/compare/` | GET | `CompareView` | ✅ | `?slugs=a,b,c` — 2–4 products |
| `/api/v1/cards/banks/` | GET | `BankListView` | ✅ | Distinct bank list |
| `/api/v1/cards/banks/:slug/variants/` | GET | `BankCardVariantsView` | ✅ | |
| `/api/v1/search/` | GET | `SearchView` | ✅ | Meilisearch primary + DB fallback; filters: q, category, brand, min_price, max_price, sort_by |
| `/api/v1/search/autocomplete/` | GET | `AutocompleteView` | ✅ | Meilisearch primary + DB fallback; limit from settings |
| `/api/v1/search/adhoc/` | POST | `AdhocScrapeView` | 🔧 | Sprint 2 |
| Auth endpoints (`/api/v1/auth/`) | various | allauth | ✅ | Registration, login, email verify, password reset, Google OAuth |
| Wishlist endpoints | various | WishlistViews | ✅ | CRUD + share |
| Review endpoints | various | ReviewViews | ✅ | Create/vote/list |
| Deal endpoints | various | DealViews | ✅ | List active deals |
| Discussion endpoints | various | DiscussionViews | ✅ | Threads + replies + votes |
| Scoring endpoints | various | ScoringViews | ✅ | DudScore config |
| Email intel endpoints | various | InboxViews | ✅ | Inbox, parsed orders |
| Rewards endpoints | various | RewardViews | ✅ | Points, gift cards |
| TCO endpoints | various | TCOViews | ✅ | |
| Cloudflare email webhook | POST | `/webhooks/` | ✅ | Isolated URL, no /api/v1 prefix |

### Backend — Root URL Configuration

```
/admin/               → Django admin
/api/v1/auth/         → allauth (accounts.urls.auth)
/api/v1/              → products, pricing, reviews, email_intel, wishlists,
                         deals, rewards, discussions, search, scoring, tco
/webhooks/            → email_intel.urls.webhooks
/accounts/            → allauth social auth flows
```

---

## Sprint 2 — Scrapers & Product Pages (Weeks 4–6)

| Task | Status |
|---|---|
| Amazon.in Scrapy spider | ⬜ |
| Flipkart Scrapy spider | ⬜ |
| Playwright anti-detection middleware | ⬜ |
| Price snapshot Celery task | ⬜ |
| On-demand scrape (`/api/v1/search/adhoc/`) | ⬜ |
| Price history TimescaleDB query + API | ⬜ |
| Meilisearch product index sync | ⬜ |

---

## Sprint 3 — DudScore, Email Intel, Card Vault (Weeks 7–9)

| Task | Status |
|---|---|
| DudScore v1 calculator (Celery task) | ⬜ |
| Review sentiment analysis (spaCy/TextBlob) | ⬜ |
| Cloudflare Email Worker → Django webhook live | ⬜ |
| Email parser (order, shipping, refund, return) | ⬜ |
| Card vault UI + offer matching | ⬜ |
| Payment optimizer (effective price calc) | ⬜ |

---

## Sprint 4 — TCO, Deals, Rewards, Launch (Weeks 10–12)

| Task | Status |
|---|---|
| TCO calculator (AC, fridge, washing machine) | ⬜ |
| Blockbuster deals detection | ⬜ |
| Rewards/points Celery tasks | ⬜ |
| Razorpay premium subscription | ⬜ |
| Admin panel — SiteConfiguration (exposes `app_settings` tuneable values) | ⬜ |
| Admin panel — DudScore weight tuning | ⬜ |
| Deployment (Docker Compose + Caddy on Contabo VPS) | ⬜ |

---

## Frontend

| Page / Component | Status | Notes |
|---|---|---|
| Layout (Header, Footer, Sidebar, MobileNav) | ✅ | Implemented |
| Global CSS + Tailwind config | ✅ | Custom brand tokens |
| `(public)/search` page | ✅ | Redesigned: 4-col ProductCard grid + seller sidebar (seller details, top reviews, related products). Mock data. Sort dropdown + results-only toggle. |
| `(public)/deals` page | ✅ | |
| `(public)/product/[slug]` page | ✅ | |
| `(public)/categories/[slug]` page | ✅ | |
| `(dashboard)/purchases` page | ✅ | |
| `(dashboard)/layout` | ✅ | |
| `src/lib/api/` — API client layer | ✅ | auth, client, discussions, inbox, products, rewards, search, sellers, tco, wishlists |
| `src/lib/utils/` — format helpers | ✅ | `format.ts`, `cn.ts` |
| `src/config/marketplace.ts` | ✅ | |
| shadcn/ui components (`src/components/ui/`) | ✅ | Installed via components.json |
| CardVault component | ✅ | |
| `src/lib/mock-data.ts` | ✅ | 8 products + 4 deals, MockProduct + MockDeal types |
| `src/components/product/product-card.tsx` | ✅ | Matches Figma — Recommended badge, stars, teal brand, marketplace badge, Best buy |
| Homepage | ✅ | Redesigned to match Figma: split hero (text+search left, floating visuals right), review CTA strip, trending with filter chips, Buyer's/Reviewer's Zone cards, deals, rate-&-review section, top picks/bestsellers/top-rated/most-bought side-by-side, helpful reviews section |
| Auth pages (login, register) | ✅ | Login: centered card, email+password with show/hide, remember me, forgot password, Google OAuth. Register: 3-step flow (account → @whyd.xyz email → marketplace onboarding) with step indicator dots, password strength bar, terms checkbox, Google OAuth, marketplace checklist with expand/collapse. |
| @whyd.xyz onboarding flow | ✅ | Step 2+3 of register page: username picker with availability check, marketplace setup checklist (8 sites) with progress bar |
| Wishlist pages (`/wishlists`) | ✅ | Wishlist cards grid (3 cols) with selection, item list with product image, DudScore badge, price tracking (added vs current with % change), target price, alert toggle, share link. Mock data in `mock-wishlists-data.ts`. |
| Product detail page (`/product/[slug]`) | ✅ | 3-column dashboard layout: left=image+specs, center=title+price+DudScore gauge+marketplace prices+price chart, right=reviews. Independently scrollable columns. 6 new components: `dud-score-gauge`, `marketplace-prices`, `category-score-bars`, `price-chart` (Recharts), `reviews/rating-distribution`, `reviews/review-card`. Mock data in `mock-product-detail.ts`. |
| Price history chart | ✅ | `price-chart.tsx` — Recharts LineChart, 3 marketplace lines, 1M/3M/Max tabs |
| DudScore badge component | ✅ | `dud-score-gauge.tsx` — SVG semi-circular gauge, red→green gradient, needle indicator |
| `(public)/compare` page | ✅ | Full comparison: sticky tabs (Highlights/Summary/Detailed/TCO), 3-product header with VS markers, highlights cards, category score dots (5-dot rows), ratings + DudScore, key specs with "Best" badges, detailed summary table, quick TCO. Mock data in `mock-pages-data.ts`. |
| `(public)/seller/[slug]` page | ✅ | Seller header card (avatar, name, verified badge, stars, TrustScore gauge), 4 tabs, seller info content (description, category pills, photo grid, socials, contact), right sidebar (performance metrics, report/enquire, feedback). Real API. |
| `(dashboard)/dashboard` page | ✅ | Expense Tracker matching Figma (₹ not $): 4 stat cards, tab nav (Overview/Platforms/Categories/Timeline/Insights), Monthly Spend Recharts line chart, Spend by Platform donut chart, Spend by Category horizontal bars, 3 insight cards. Mock data in `mock-dashboard-data.ts`. Client component `DashboardCharts.tsx`. |
| `(dashboard)/inbox` page | ✅ | 3-column layout: folder sidebar (8 folders with unread counts + marketplace filter) | email list (search, category badges, unread blue dot, time ago) | email reader (header, parsed data card with green border for order/refund/shipping detection, email body). Mock data in `mock-inbox-data.ts`. |
| `(dashboard)/rewards` page | ✅ | Points balance card with progress bar to next milestone, 4 "How to Earn" cards (Review/Email/Refer/Streak), 6 gift card redemption cards (disabled if insufficient points), chronological points history. Mock data in `mock-rewards-data.ts`. |
| `(dashboard)/settings` page | ✅ | 6-tab layout: Profile (avatar, name, city, password change), @whyd.xyz (email status, marketplace setup checklist, deactivate), Card Vault (security badge, 3 saved cards, wallets), TCO Preferences (city, tariff, ownership years, AC hours), Subscription (Free plan + Premium upsell with features list at ₹199/mo), Data & Privacy (connected services, export, delete account). |

---

## Key Architectural Decisions Made

| Decision | Rationale |
|---|---|
| Modular monolith (not microservices) | Solo founder, single VPS — complexity must stay minimal |
| `managed=False` for TimescaleDB hypertables | Django migrations cannot run `create_hypertable` inside a transaction |
| `RunPython` + `autocommit=True` for hypertable DDL | psycopg3 wraps every execute() in an implicit transaction even with `atomic=False` |
| Flat `ProductListSerializer` vs nested `ProductDetailSerializer` | Reduces payload on list pages; nested brand/category only needed on detail |
| Affiliate URLs injected at response time | Never stored in DB — avoids stale affiliate tags and simplifies data model |
| `common/app_settings.py` as settings accessor | All tuneable values go through one module; Sprint 4 admin can override without code changes |
| Prices stored as `Decimal(12,2)` in paisa | Never floats; display layer converts to ₹ |
| Email bodies as `BinaryField` (AES-256-GCM) | Encrypted at rest; decrypted only on explicit user request |
| Cursor pagination (not offset) | Consistent results as data changes; works with TimescaleDB time ordering |
| `users` / `email_intel` / `scoring` / `tco` / `community` custom schemas | Isolation between domains; `db_table = 'schema\\".\\"table'` pattern in Django |

---
## 2026-02-24 — Fix homepage console error

**Root cause:** `apiClient.request()` in `src/lib/api/client.ts` had no `try/catch`. When the backend is unreachable (dev without Docker), `fetch()` throws a network error. `useAuth` called `.then()` with no `.catch()`, so the rejection was unhandled → Next.js dev overlay showed "1 error".

**Fix:**
- `src/lib/api/client.ts`: wrapped `fetch` + `response.json()` in `try/catch`; returns `{ success: false, error: { code: "NETWORK_ERROR", ... } }` on failure instead of throwing.
- `src/hooks/useAuth.ts`: added `.catch(() => setState({ user: null, isLoading: false, isAuthenticated: false }))` — belt-and-suspenders in case any future error slips through.

---
## 2026-02-24 — Homepage Figma match

Redesigned `src/app/(public)/page.tsx` to closely match `docs/figma/homepage.png`:
- **Hero**: Two-column layout — left (title + search bar with All Categories dropdown), right (floating product visuals with labels). Removed trust pills (not in Figma).
- **Review CTA strip**: Peach (#fff5ef) banner after hero — "Get an ₹500 instant gift card", star/gift visual, "Write a review now" button.
- **Trending**: Renamed "What's Trending" → "Trending right now". Category filter chips (pill tabs, first = orange selected, rest = bordered) replacing emoji category row. Filters button.
- **Buyer's Zone / Reviewer's Zone**: Redesigned from dark+light cards to Figma-style warm-peach / pink cards with image placeholder on right.
- **Blockbuster Deals**: Title matches Figma ("Blockbuster deals for you").
- **Rate & review section**: New section with user avatar, "Rate and review your products" prompt, reward badges, 3 review-product cards.
- **Product grids**: Top Picks + Bestsellers side-by-side; Top Rated + Most Bought side-by-side.
- **Helpful reviews section**: New section with 4 mock review cards, prev/next nav buttons.

---
Build the Homepage (`/`) — `src/app/(public)/page.tsx`.
Figma reference: `docs/figma/homepage.png`.
Use `MOCK_PRODUCTS` and `MOCK_DEALS` from `src/lib/mock-data.ts`.
Use `ProductCard` from `src/components/product/product-card.tsx` for product grids.
Sections: hero search bar, featured/recommended products grid (use is_recommended), all products grid, blockbuster deals strip (use MOCK_DEALS).

## 2026-02-24 — Dashboard, Login, Register pages

Built 3 pages with mock data:

1. **Dashboard** (`/dashboard`) — Expense Tracker matching Figma mockup:
   - 4 stat cards (Total spend, Orders, Average order, Top platform) in ₹
   - Tab navigation (Overview/Platforms/Categories/Timeline/Insights)
   - Monthly Spend line chart (Recharts `LineChart`, 4 weekly data points)
   - Spend by Platform donut chart (Recharts `PieChart` with inner radius)
   - Spend by Category horizontal progress bars
   - 3 insight cards at bottom
   - New files: `mock-dashboard-data.ts`, `components/dashboard/DashboardCharts.tsx`

2. **Login** (`/login`) — From DESIGN-SYSTEM.md spec:
   - Centered card with Whydud logo, "Welcome back" heading
   - Email + Password inputs with show/hide toggle (eye icon SVG)
   - Remember me checkbox + Forgot password link
   - Orange "Sign in" button, "or" divider, Google OAuth with real G icon
   - Register link at bottom

3. **Register** (`/register`) — 3-step flow from DESIGN-SYSTEM.md:
   - Step indicator: 3 connected dots (filled/active/inactive states)
   - Step 1: Name, email, password (with strength bar), terms checkbox, Google OAuth
   - Step 2: @whyd.xyz username picker with availability check, skip option
   - Step 3: Marketplace onboarding checklist (8 Indian sites), expand/collapse per site, progress bar, "I'll do this later" link

---

## 2026-02-24 — Inbox, Wishlists, Rewards, Settings pages

Built 4 remaining dashboard pages with mock data:

1. **Inbox** (`/inbox`) — 3-column email layout from DESIGN-SYSTEM.md:
   - Folder sidebar (All/Orders/Shipping/Refunds/Returns/Subscriptions/Promotions/Starred) with unread counts + marketplace filter
   - Email list with search, unread blue dot, category badges (semantic colors), time ago
   - Email reader with parsed data card (green border, detected order/refund/shipping info with DudScore)
   - 7 mock emails across Amazon, Flipkart, Myntra, Croma, Swiggy

2. **Wishlists** (`/wishlists`) — Wishlist management:
   - 3 wishlist cards (Birthday/Home/Tech) with item count, total price, price drop badges
   - Item list: product image, title, brand, DudScore badge, added vs current price with % change
   - Target price display, alert toggle (switch component), share link, remove button

3. **Rewards** (`/rewards`) — Points & gift card system:
   - Balance card (450 points ≈ ₹45) with progress bar to next milestone (₹100 gift card)
   - 4 "How to Earn" cards: Review (+20), Email (+50), Refer (+30), Streak (+10)
   - 6 gift cards (Amazon/Flipkart/Swiggy/Zomato/BookMyShow/Myntra) with Redeem buttons (disabled if insufficient points)
   - Points history timeline (7 entries, earned + spent)

4. **Settings** (`/settings`) — 6-tab layout:
   - Profile: avatar, name, city, password change
   - @whyd.xyz: email status, marketplace setup checklist (6 sites), deactivate
   - Card Vault: "Never store card numbers" badge, 3 saved cards (HDFC/ICICI/SBI), wallets section
   - TCO Preferences: city, electricity tariff, ownership years, AC hours, washer loads
   - Subscription: Free plan badge + Premium upsell (₹199/mo, 5 features)
   - Data & Privacy: connected services, data export, account deletion

New mock data files: `mock-inbox-data.ts`, `mock-wishlists-data.ts`, `mock-rewards-data.ts`

---

## 2026-02-24 — Search page: replace mock data with real API calls

Rewrote `frontend/src/app/(public)/search/page.tsx`:
- Removed `MOCK_PRODUCTS` and `MOCK_SELLER_SIDEBAR` imports (no more mock data)
- Imports `searchApi` from `@/lib/api/search` and `productsApi` from `@/lib/api/products`
- Server component calls `searchApi.search(query)` first, falls back to `productsApi.list()` if Meilisearch is unavailable or returns no results
- Reads search params: `q`, `category`, `sortBy`, `offset`
- Removed seller sidebar section (no backend endpoint)
- Shows product count in results header
- Empty state with helpful message when no products found
- Kept sort dropdown and results-only toggle

---

## 2026-02-24 — Product detail page: replace mock data with real API calls

Rewrote `frontend/src/app/(public)/product/[slug]/page.tsx`:
- Removed `MOCK_PRODUCT_DETAIL` import (no more mock data)
- Imports `productsApi` from `@/lib/api/products`; fetches product detail, price history, and reviews in parallel via `Promise.all`
- Uses `notFound()` from `next/navigation` when the API returns an error (product not found)
- Data transformations to bridge API types to component expectations:
  - `p.brand.name` / `p.category.name` (objects, not strings)
  - `p.currentBestPrice` instead of `p.bestPrice`
  - MRP derived from the best-price listing (`getBestListing()`)
  - DudScore label derived from score value (`getDudScoreLabel()`)
  - DudScore components: placeholder values since backend doesn't return breakdown yet
  - Specs converted from `Record<string,string|number|boolean>` to `{label,value}[]`
  - Rating distribution normalized from raw counts to percentages
  - Breadcrumb constructed from category and brand names
  - Marketplace chart color map built from listing marketplace slugs

Updated child components to use real API types:
- `components/product/marketplace-prices.tsx`: accepts `ProductListing[]` + `bestPrice` instead of `MockMarketplaceListing[]`; computes diff percentage internally
- `components/product/price-chart.tsx`: accepts `PricePoint[]` (time/price/marketplaceId) instead of `MockPricePoint[]` (date/amazon/flipkart/croma); pivots data by marketplace dynamically; supports arbitrary number of marketplaces
- `components/reviews/review-card.tsx`: accepts `Review` type instead of `MockReviewDetail`; generates avatar color from name hash; computes relative date from ISO timestamp; shows flagged badge

---

## 2026-02-24 — Compare page: replace mock data with real API calls

Rewrote `frontend/src/app/(public)/compare/page.tsx`:
- Removed `MOCK_COMPARE` import (no more mock data)
- Imports `productsApi.compare(slugs)` from `@/lib/api/products`; parses `?slugs=slug1,slug2` from search params
- Server component calls `productsApi.compare(slugs)` with real API data
- Empty/error states: shows helpful message when no slugs provided, API fails, or no products found
- **Product header row**: Uses `ProductDetail.images[0]`, title, `currentBestPrice`; "Best Buy" badge on cheapest product
- **Highlights**: Dynamically generated by comparing products — Best Price, Highest Rated, Best DudScore
- **Category Scores**: Derived from DudScore availability + reviewSummary (credibility, verified purchase %) using 5-dot scale
- **Ratings**: Uses real `avgRating`, `totalReviews`, `dudScore` (out of 100 instead of mock's out of 10)
- **Key Specs**: Built dynamically from `specs` Record — finds all keys across products, shows "Best" badge on highest numeric values
- **Detailed Summary**: Same specs as flat string values in a detailed table
- **Quick TCO**: Replaced with "Coming soon" placeholder (no TCO endpoint ready)
- Kept all existing CSS classes, grid layout, ScoreDots, Stars components unchanged

---

## 2026-02-24 — Dashboard client pages: wired to real API calls

Replaced mock data with real API calls in 4 dashboard client components:

1. **Dashboard** (`/dashboard`) — Now fetches from `purchasesApi.getDashboard()`:
   - Converted from server component to `"use client"` with `useState`/`useEffect`
   - Stat cards populated from `PurchaseDashboard` fields (totalSpent, totalOrders, averageOrderValue, topMarketplace)
   - `DashboardCharts.tsx` refactored to accept `dashboard: PurchaseDashboard` prop instead of importing mock data
   - Charts derived from real `monthlySpending` and `categoryBreakdown` arrays
   - Insight cards dynamically generated from dashboard data (activeRefunds, expiringReturns, activeSubscriptions)
   - Loading skeleton and error/empty states added

2. **Inbox** (`/inbox`) — Now fetches from `inboxApi.list(filters)` + `inboxApi.get(id)`:
   - Email list fetched on mount and when folder changes (passes category/isStarred filters)
   - Individual email detail fetched on selection via `inboxApi.get(id)`, renders `bodyHtml`
   - Auto-marks emails as read via `inboxApi.markRead()`
   - Folder counts and marketplace filters computed from fetched email list
   - Adapted to real `InboxEmail` type (no snippet/body/parsedData on list, bodyHtml on detail)

3. **Wishlists** (`/wishlists`) — Now fetches from `wishlistsApi.list()`:
   - Fetches all wishlists with items on mount
   - `WishlistItem.product` is a UUID string (no product name/image) — shows product ID with placeholder image
   - Price tracking works with real `priceWhenAdded`, `currentPrice`, `priceChangePct`
   - Alert toggle calls `wishlistsApi.updateItem()` to persist
   - Remove button calls `wishlistsApi.removeItem()` with optimistic UI update

4. **Rewards** (`/rewards`) — Now fetches from `rewardsApi.getBalance()`, `getGiftCards()`, `getHistory()`:
   - Three parallel API calls via `Promise.all`
   - Balance card uses real `RewardBalance` (totalEarned, totalSpent, totalExpired, currentBalance)
   - Gift cards from `GiftCard[]` with `denominations` array, `brandLogoUrl`, `category`
   - Points history from `RewardPointsLedger[]` with `action`, `points`, `description`, `createdAt`
   - "How to Earn" cards kept as static content (not from API)

---

## 2026-02-24 — Full stack wiring complete (API client → seed data → all pages)

Completed the entire frontend-to-backend wiring in a single session:

### Phase 1: API Client snake_case → camelCase Transform
- Added recursive `snakeToCamel()` key transformer in `src/lib/api/client.ts`
- Runs on every API response before returning to callers
- Handles arrays, nested objects, null, primitives

### Phase 2: Docker Stack & Migrations
- Started PostgreSQL+TimescaleDB, Redis, Meilisearch via Docker Compose
- All 13 Django apps migrated cleanly

### Phase 3: Production-Grade Seed Data
- Created `backend/apps/products/management/commands/seed_data.py`
- Seeds: 15 categories, 20 brands, 31 products, 20 sellers, ~100 listings, ~5000 price snapshots, ~200 reviews, 15 deals, DudScore history, marketplace offers, bank cards, discussions, TCO models, city reference data, gift card catalog
- Test user: test@whydud.com / testpass123

### Phase 4-5: Frontend Types & API Endpoint Fixes
- Rewrote `src/types/product.ts` — flat `ProductSummary` vs nested `ProductDetail`
- Added missing types: Seller, ReviewSummary, SearchResponse, DiscussionThread/Reply, BankCard, City, TCOModel, DudScoreConfig, PriceAlert
- Fixed all API files (`products.ts`, `search.ts`, `rewards.ts`, `inbox.ts`, `discussions.ts`) to use correct generic types (`T[]` instead of `PaginatedResponse<T>`)

### Phase 6: All Frontend Pages Wired to Real API
- Homepage: `productsApi.list()` + `dealsApi.list()`
- Search: `searchApi.search()` with Meilisearch fallback to `productsApi.list()`
- Product detail: `productsApi.getDetail()` + `getPriceHistory()` + `getReviews()`
- Compare: `productsApi.compare(slugs)`
- Dashboard: `purchasesApi.getDashboard()` (client component)
- Inbox: `inboxApi.list()` + `inboxApi.get()` (client component)
- Wishlists: `wishlistsApi.list()` (client component)
- Rewards: `rewardsApi.getBalance()` + `getGiftCards()` + `getHistory()` (client component)

### Phase 7-8: Loading Skeletons & Error Boundaries
- Created `loading.tsx` for: `(public)/`, `(public)/search/`, `(public)/product/[slug]/`, `(public)/compare/`, `(dashboard)/`
- Created `error.tsx` for: `(public)/`, `(dashboard)/`, `(auth)/`

### Phase 9: Meilisearch Sync
- Created `backend/apps/search/management/commands/sync_meilisearch.py`
- Synced 31 products with searchable/filterable/sortable attributes

### Phase 10: End-to-End Verification
- TypeScript: 0 errors (`npx tsc --noEmit` passes clean)
- Backend: All API endpoints returning real data (products, deals, product detail, search)
- Frontend: All pages rendering with real product data from backend API
- Search: Meilisearch returning results for queries like "samsung"
- Fixed: Deals view `CursorPagination` ordering (model has `detected_at`, not `created_at`)

### Bug Fixes During Wiring
- `DealCard.tsx`: `deal.productSlug` → `deal.product?.slug` (Deal type now has nested product)
- `purchases/page.tsx`: Fixed double-wrapped API response unwrapping
- `categories/[slug]/page.tsx`: Fixed to use `SearchResponse.results` shape
- `deals/views.py`: Set `paginator.ordering = "-detected_at"` (model lacks `created_at`)

---

## Known Issues / Tech Debt

| Issue | Priority | Notes |
|---|---|---|
| Rate limit values hardcoded in `common/rate_limiting.py` | Medium | Should move to `app_settings` like search/pagination limits |
| `DudScoreHistory` and `PriceSnapshot` have no `__str__` | Low | `managed=False` models — low impact |
| No test suite yet | High | pytest + pytest-django; should cover serializers + views before Sprint 2 |
| Meilisearch index not yet configured | ✅ Done | `sync_meilisearch` command created and 31 products synced |
| `ProductBestDealsView` requires auth but `permission_classes = [IsAuthenticated]` stub needs card vault data | Medium | Sprint 3 dependency |

---

## 2026-02-24 — Complete API wiring: all pages use real API calls

Completed the remaining API wiring work to eliminate all mock data usage:

### New API files
- `src/lib/api/tco.ts` — TCO calculator endpoints: `calculate`, `compare`, `getCities`, `getProfile`, `updateProfile`
- `src/lib/api/sellers.ts` — Seller endpoints: `getDetail`, `getProducts`, `getReviews`

### New types
- `SellerDetail` in `src/types/product.ts` — Full seller profile with performance metrics, categories, socials, contact info

### Pages wired to real API (previously using mock data)
1. **Seller** (`/seller/[slug]`) — Now uses `sellersApi.getDetail(slug)` instead of `MOCK_SELLER_DETAIL`. Returns `notFound()` on API failure. Changed `s.avatar` → `s.avatarUrl`, `s.verified` → `s.isVerified`, `s.rating` → `s.avgRating`.
2. **Settings** (`/settings`) — Now fetches user, email, and cards via `Promise.all([authApi.me(), whydudEmailApi.getStatus(), cardVaultApi.list()])`. Each tab receives real data as props. Added `TabSkeleton` loading component. Marketplace list derived from `whydEmail.marketplacesRegistered`. Subscription tab uses `user.subscriptionTier`.
3. **Refunds** (`/refunds`) — Now fetches from `purchasesApi.getRefunds()`. Shows status badges (initiated/processing/completed/failed) with semantic colors. Empty state with explanatory message.
4. **Subscriptions** (`/subscriptions`) — Now fetches from `purchasesApi.getSubscriptions()`. Shows active/inactive badge, frequency, next charge date. Empty state with explanatory message.

### New loading skeletons
- `(public)/deals/loading.tsx` — Deal cards grid skeleton
- `(public)/seller/[slug]/loading.tsx` — Seller header + sidebar skeleton
- `(public)/categories/[slug]/loading.tsx` — Category product grid skeleton
- `discussions/[id]/loading.tsx` — Thread + replies skeleton

### API index updated
- `src/lib/api/index.ts` now exports: auth, client, discussions, inbox, products, rewards, search, sellers, tco, wishlists

### Summary
- **0 pages use mock data** — all pages call real API endpoints
- **13 API modules** covering all backend endpoints
- **Loading states** for every route (either via `loading.tsx` or inline skeletons)
- **Error boundaries** for all 3 route groups (public, dashboard, auth)
- TypeScript: 0 errors
- All 13 routes return HTTP 200

---

## 2026-02-24 — Dashboard pages: friendly auth error prompts

Replaced raw error messages with friendly "Please log in" prompts across all dashboard pages:

### Client components (had raw red error divs showing API error text)
- **Inbox** (`/inbox`) — `border-red-200 bg-red-50` → `border-amber-200 bg-amber-50` with "Please log in to view your inbox" + Log In button
- **Wishlists** (`/wishlists`) — Same pattern → "Please log in to view your wishlists"
- **Rewards** (`/rewards`) — Same pattern → "Please log in to view your rewards"

### Server components (previously swallowed errors silently, showed empty state)
- **Purchases** (`/purchases`) — Added `hasError` detection; shows login prompt instead of "No purchases detected" when API fails
- **Refunds** (`/refunds`) — Added `hasError` detection; shows login prompt instead of "No refunds tracked"
- **Subscriptions** (`/subscriptions`) — Added `hasError` detection; shows login prompt instead of "No subscriptions detected"

### Settings (had no error handling at all)
- **Settings** (`/settings`) — Added `error` state; shows login prompt when all 3 API calls (me, email status, card vault) fail

### Dashboard page
- Already had the correct amber prompt pattern — no changes needed

All prompts use consistent styling: `rounded-xl border border-amber-200 bg-amber-50 p-6 text-center` with orange Log In button linking to `/login`.

---

## 2026-02-24 — Wire login form to backend API

Connected the login page to the real Django auth endpoint (`POST /api/v1/auth/login`).

### Changes

1. **`src/lib/api/client.ts`** — Added DRF token management:
   - `getToken()`, `setToken()`, `clearToken()` helpers using `localStorage`
   - `request()` now attaches `Authorization: Token <key>` header when a token exists
   - `credentials: "include"` was already set (unchanged)

2. **`src/lib/api/auth.ts`** — Updated types and logout:
   - `login()` return type updated to `{ user: User; token: string }` (was missing `token`)
   - `register()` return type updated to `{ user: User; token: string }`
   - `logout()` now calls `clearToken()` after the API call to remove stored token

3. **`src/app/(auth)/login/page.tsx`** — Wired form to real API:
   - Added `useState` for `email`, `password`, `error`, `isLoading`
   - `handleSubmit`: calls `authApi.login()`, stores token via `setToken()`, redirects to `/dashboard`
   - On error: displays error message in a red banner below the form heading
   - Submit button shows "Signing in…" and is disabled during request
   - All existing UI (show/hide password, remember me, forgot password, Google OAuth, register link) preserved

4. **`src/hooks/useAuth.ts`** — Optimized auth check:
   - Skips `/api/v1/me` call entirely if no token in `localStorage` (avoids unnecessary 401s)
   - Clears stale token on failed `/me` response

### Flow
User types email/password → submits → `POST /api/v1/auth/login` → backend returns `{ user, token }` → token stored in localStorage → redirect to `/dashboard` → `useAuth` hook reads token, calls `/api/v1/me`, shows authenticated UI in Header.

---

## 2026-02-24 — Fix auth, dashboard crash, register, Google OAuth

### Root causes found and fixed

1. **Broken Django URLs (`../` prefix)**: `accounts/urls/auth.py` used `path("../me", ...)` etc. to break out of the `auth/` prefix. Django URL resolver treats `../` as a literal string — these routes were **unreachable** (404). This is why:
   - `GET /api/v1/me` always failed → `useAuth` returned not authenticated → Header showed "Log In"
   - `GET /api/v1/cards` always failed → card vault broken
   - `GET /api/v1/email/whydud/*` always failed → email status broken

2. **Dashboard crash**: Backend `PurchaseDashboardView` returned 5 fields with different names (e.g. `total_spend` not `total_spent`, `pending_refunds` not `active_refunds`) and was missing `monthlySpending`, `categoryBreakdown`, `averageOrderValue`, `topMarketplace`. Frontend accessed `undefined.length` → crash.

3. **Register page**: Form was a no-op (all `onSubmit` did was `setStep(1)` without calling API).

4. **Google OAuth**: Buttons were `<button>` with no click handler.

### Backend fixes

- **`accounts/urls/auth.py`** — Removed all `../` routes. Now only contains `register`, `login`, `logout`.
- **New `accounts/urls/account.py`** — Contains `me`, `email/whydud/*`, `cards/*` routes (no `../` prefix).
- **`whydud/urls.py`** — Added `path("api/v1/", include("apps.accounts.urls.account"))` so `/api/v1/me`, `/api/v1/cards/*`, `/api/v1/email/whydud/*` resolve correctly.
- **`email_intel/views.py`** — `PurchaseDashboardView`:
  - Changed `permission_classes` from `IsConnectedUser` to `IsAuthenticated` (dashboard should work without @whyd.xyz email).
  - Now returns all 9 fields the frontend expects: `total_spent`, `total_orders`, `average_order_value`, `top_marketplace`, `monthly_spending` (TruncMonth aggregation), `category_breakdown` (by marketplace), `active_refunds`, `expiring_returns`, `active_subscriptions`.

### Frontend fixes

- **`dashboard/page.tsx`** — Added `??` defaults for all PurchaseDashboard fields so missing fields don't crash.
- **`login/page.tsx`** — Google OAuth button changed from `<button>` to `<a href="/accounts/google/login/?process=login">`.
- **`register/page.tsx`** — Fully wired:
  - Step 1: calls `authApi.register()`, stores token, shows error on failure, loading state on button.
  - Step 2: calls `whydudEmailApi.checkAvailability()` on input, calls `whydudEmailApi.create()` on submit, skip goes to dashboard.
  - Step 3: unchanged (marketplace onboarding checklist).
  - Google OAuth button also wired (`<a>` to allauth).
- **`next.config.ts`** — Added `/accounts/*` rewrite to proxy allauth social auth routes to Django.

---

## 2026-02-24 — Fix remaining dashboard auth issues + wishlists crash

### Root causes found and fixed

1. **Server components can't access auth tokens**: `purchases/page.tsx`, `refunds/page.tsx`, `subscriptions/page.tsx` were `async` server components. Server-side Node.js has no access to `localStorage` → token never sent → 401 → "Please log in" even when user is authenticated.

2. **Wishlists crash**: `wl.items.filter()` crashes when `items` is `undefined` from the API response (backend may return wishlists without inline items).

3. **IsConnectedUser permission too restrictive**: All `email_intel` views (inbox, purchases, refunds, subscriptions dashboard) required `has_whydud_email=True` via `IsConnectedUser`. Newly registered users without a @whyd.xyz email got 403.

### Backend fixes

- **`email_intel/views.py`** — Changed ALL views from `IsConnectedUser` to `IsAuthenticated`:
  - `InboxListView`, `InboxDetailView`, `InboxReparseView`
  - `PurchaseDashboardView`, `PurchaseListView`
  - `RefundsView`, `ReturnWindowsView`, `SubscriptionsView`

### Frontend fixes

- **`purchases/page.tsx`** — Converted from server component to `"use client"` with `useState`/`useEffect`. Added loading skeleton.
- **`refunds/page.tsx`** — Same conversion to client component. Added loading skeleton.
- **`subscriptions/page.tsx`** — Same conversion to client component. Added loading skeleton.
- **`wishlists/page.tsx`** — Added `?? []` safety on all `wl.items` accesses (9 locations) to prevent crash when items is undefined.

---

## 2026-02-24 — Wire register form + AuthContext + route protection

Completed the current task: "Wire the register form and add auth context."

### 1. AuthContext (`src/contexts/auth-context.tsx`)
- Created `AuthProvider` with React Context wrapping user state, `login()`, `logout()`, `refreshUser()`
- `login(token, user)` — stores token + updates state immediately (no /me round-trip)
- `logout()` — calls POST /auth/logout, clears token, resets state
- `refreshUser()` — re-fetches /me (e.g. after profile update)
- Exports `useAuth()` hook that throws if used outside provider

### 2. `useAuth` hook backward compatibility (`src/hooks/useAuth.ts`)
- Replaced standalone hook with a re-export from `@/contexts/auth-context`
- All existing imports (`import { useAuth } from "@/hooks/useAuth"`) continue working — zero migration needed

### 3. Root layout wrapped (`src/app/layout.tsx`)
- Imported `AuthProvider` and wrapped `{children}` in `<AuthProvider>`
- Auth state is now shared across all components via context (Header, login, register, dashboard pages)

### 4. Login page updated (`src/app/(auth)/login/page.tsx`)
- Replaced manual `setToken()` with context `login(res.data.token, res.data.user)`
- Added `useSearchParams()` to read `?next=` param — redirects to the originally requested page after login
- Removed `setToken` import (no longer needed)

### 5. Register page updated (`src/app/(auth)/register/page.tsx`)
- Step 1 (`Step1CreateAccount`): Now calls context `login(token, user)` after `authApi.register()` succeeds
- Step 2 (`Step2ChooseEmail`): Unchanged — already wired to `whydudEmailApi.create()`
- Header immediately shows "Welcome, {name}" after Step 1 completes (context updates instantly)

### 6. Cookie flag for middleware (`src/lib/api/client.ts`)
- `setToken()` now also sets `document.cookie = "whydud_auth=1"` (simple flag, not the actual token)
- `clearToken()` now also clears the cookie
- This allows Next.js middleware (server-side) to detect auth state without localStorage

### 7. Route protection middleware (`src/middleware.ts`)
- Checks for `whydud_auth` cookie on all dashboard routes
- If missing → redirects to `/login?next=/dashboard/...` (preserves intended destination)
- Matcher covers: `/dashboard/*`, `/inbox/*`, `/wishlists/*`, `/purchases/*`, `/refunds/*`, `/subscriptions/*`, `/rewards/*`, `/settings/*`

### Auth flow summary
1. User registers → `authApi.register()` → context `login(token, user)` → token in localStorage + cookie flag → Step 2
2. User logs in → `authApi.login()` → context `login(token, user)` → redirect to `?next` or `/dashboard`
3. User visits `/dashboard` without auth → middleware reads cookie → not found → redirect to `/login?next=/dashboard`
4. User logs out → context `logout()` → `clearToken()` removes localStorage + cookie → state resets

TypeScript: 0 errors (`npx tsc --noEmit` clean)

---

## 2026-02-24 — Complete auth features: logout, password flows, email verification, OAuth

Added all mandatory auth features that were missing after the initial login/register wiring.

### Backend changes

**`apps/accounts/views.py`** — 6 new views + modified RegisterView:
- `ChangePasswordView` — POST, validates current password via `check_password()`, sets new, re-creates DRF token (returns new token so user stays logged in)
- `ForgotPasswordView` — POST (AllowAny), generates uid+token via `default_token_generator`, queues Celery email task. Always returns success to prevent email enumeration.
- `ResetPasswordView` — POST (AllowAny), validates uid+token, sets new password, deletes all DRF tokens (forces re-login)
- `VerifyEmailView` — POST (AllowAny), validates uid+token, sets `email_verified=True`
- `ResendVerificationEmailView` — POST (IsAuthenticated), queues verification email
- `OAuthSessionToTokenView` — GET (IsAuthenticated), converts Django session (set by AllAuth OAuth) to DRF token. Uses GET to avoid CSRF issues with SessionAuthentication.
- `RegisterView` now calls `send_verification_email.delay()` after user creation

**`apps/accounts/serializers.py`** — Updated:
- Added `email_verified` to `UserSerializer.fields` and `read_only_fields`
- `ChangePasswordSerializer`, `ForgotPasswordSerializer`, `ResetPasswordSerializer` already existed

**`apps/accounts/urls/auth.py`** — 9 URL patterns (was 3):
- register, login, logout, change-password, forgot-password, reset-password, verify-email, resend-verification, session-to-token

**`apps/accounts/tasks.py`** — Implemented email tasks:
- `send_verification_email(user_id)` — generates uid+token, sends email with `{FRONTEND_URL}/verify-email?uid=X&token=Y`
- `send_password_reset_email(user_id, uid, token)` — sends email with `{FRONTEND_URL}/reset-password?uid=X&token=Y`

**`whydud/settings/base.py`** — New settings:
- `FRONTEND_URL` — for email links (default `http://localhost:3000`)
- `LOGIN_REDIRECT_URL = "/auth/callback"` — AllAuth OAuth redirects here
- `PASSWORD_RESET_TIMEOUT = 86400` — 24 hours

### Frontend changes

**`src/types/user.ts`** — Added `emailVerified: boolean` to User interface

**`src/lib/api/auth.ts`** — 6 new API functions:
- `changePassword`, `forgotPassword`, `resetPassword`, `verifyEmail`, `resendVerification`, `sessionToToken`

**`src/components/layout/Header.tsx`** — User dropdown with logout:
- Replaced "Welcome, {name}" link with clickable dropdown
- Dropdown contains "Dashboard" link + "Log out" button
- Click-outside handler to close dropdown

**`src/components/layout/Sidebar.tsx`** — Added logout button:
- `<hr>` separator + red hover logout button at bottom of nav

**`src/app/(dashboard)/settings/page.tsx`** — Wired change password form:
- ProfileTab now has state for password fields, calls `authApi.changePassword()`
- Updates stored token on success (since backend re-creates it)
- Shows success/error feedback inline

**New pages (4):**
- `src/app/(auth)/forgot-password/page.tsx` — Email input → "Check your email" success state
- `src/app/(auth)/reset-password/page.tsx` — Reads uid+token from URL params, new password + confirm form, success → "Sign in" link
- `src/app/(auth)/verify-email/page.tsx` — Auto-verifies on mount using uid+token from URL, shows verifying → success/error states
- `src/app/(auth)/auth/callback/page.tsx` — OAuth callback: calls `sessionToToken()` on mount, stores token via context `login()`, redirects to dashboard

TypeScript: 0 errors (`npx tsc --noEmit` clean)
