# Whydud — Development Progress

**Last Updated:** 2026-02-23
**Current Sprint:** Sprint 1 — Foundation (Weeks 1–3)
**Architecture Reference:** `docs/ARCHITECTURE.md`

## 🎯 CURRENT TASK
Build remaining pages with mock data:

1. src/app/(dashboard)/inbox/page.tsx — 3-column layout (folder sidebar | email list | reader). Use docs/DESIGN-SYSTEM.md "Screen: Inbox" wireframe.
2. src/app/(dashboard)/wishlists/page.tsx — wishlist cards grid + item list with price tracking
3. src/app/(dashboard)/rewards/page.tsx — points balance + earn cards + gift card catalog
4. src/app/(dashboard)/settings/page.tsx — tabbed: Profile | @whyd.xyz | Cards | TCO | Subscription | Privacy

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
| `src/lib/api/` — API client layer | ✅ | `inbox.ts`, `index.ts`, `types.ts` |
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
| `(public)/seller/[slug]` page | ✅ | Seller header card (avatar, name, verified badge, stars, TrustScore gauge), 4 tabs, seller info content (description, category pills, photo grid, socials, contact), right sidebar (performance metrics, report/enquire, feedback). Mock data. |
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

## Known Issues / Tech Debt

| Issue | Priority | Notes |
|---|---|---|
| Rate limit values hardcoded in `common/rate_limiting.py` | Medium | Should move to `app_settings` like search/pagination limits |
| `DudScoreHistory` and `PriceSnapshot` have no `__str__` | Low | `managed=False` models — low impact |
| No test suite yet | High | pytest + pytest-django; should cover serializers + views before Sprint 2 |
| Meilisearch index not yet configured | High | Product sync task needed before search is live |
| `ProductBestDealsView` requires auth but `permission_classes = [IsAuthenticated]` stub needs card vault data | Medium | Sprint 3 dependency |
