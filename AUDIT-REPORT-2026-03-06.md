# WHYDUD Audit Report — 2026-03-06

## Summary
- Total checks run: **98**
- PASS: **78**
- PARTIAL: **10**
- STUB: **6** (Celery tasks only)
- FAIL: **4**
- SKIP: **0**

---

## Phase 1: Backend Models & Migrations

| App | Models | Migrations | Status |
|-----|--------|------------|--------|
| accounts | 9 (User, WhydudEmail, OAuthConnection, PaymentMethod, ReservedUsername, Notification, NotificationPreference, MarketplacePreference, PurchasePreference) | 11 | **PASS** |
| products | 11 (Marketplace, Category, Brand, Product, Seller, ProductListing, BankCard, CompareSession, RecentlyViewed, StockAlert, CategoryPreferenceSchema) | 4 | **PASS** |
| pricing | 5 (PriceSnapshot, MarketplaceOffer, PriceAlert, ClickEvent, BackfillProduct) | 6 | **PASS** |
| reviews | 3 (Review, ReviewVote, ReviewerProfile) | 4 | **PASS** |
| scoring | 3 (DudScoreConfig, DudScoreHistory, BrandTrustScore) | 4 | **PASS** |
| email_intel | 6 (InboxEmail, EmailSource, ParsedOrder, RefundTracking, ReturnWindow, DetectedSubscription) | 4 | **PASS** |
| wishlists | 2 (Wishlist, WishlistItem) | 1 | **PASS** |
| deals | 1 (Deal) | 1 | **PASS** |
| rewards | 4 (RewardPointsLedger, RewardBalance, GiftCardCatalog, GiftCardRedemption) | 1 | **PASS** |
| discussions | 3 (DiscussionThread, DiscussionReply, DiscussionVote) | 1 | **PASS** |
| tco | 3 (TCOModel, CityReferenceData, UserTCOProfile) | 1 | **PASS** |
| search | 1 (SearchLog) | 1 | **PASS** |
| scraping | 1 (ScraperJob) | 1 | **PASS** |
| admin_tools | 4 (AuditLog, ModerationQueue, ScraperRun, SiteConfig) | 1 | **PASS** (undocumented 14th app) |

**Totals:** 56 models across 14 apps (PROGRESS.md claims 49 across 13). Delta: +7 models from growth + undocumented `admin_tools` app. 41 migrations (expected 27+). 2 TimescaleDB hypertables confirmed (price_snapshots, dudscore_history).

**Verdict:** **PASS** — All models import cleanly. More models than documented (growth, not deficit).

---

## Phase 2: API Endpoints (Serializers & Views)

| Check | Count | Status |
|-------|-------|--------|
| Serializer classes | 62 across 13 apps | **PASS** — all import cleanly |
| View classes | 118 APIView across 13 apps | **PASS** — all import cleanly |
| URL patterns | ~131 endpoint paths | **PASS** |
| Scraping views | 0 (correct — operates via Celery only) | **PASS** |

---

## Phase 3: API Response Format

| Check | Status | Notes |
|-------|--------|-------|
| `success_response` / `error_response` helpers | **PASS** | Exist in `common/utils.py`, import cleanly |
| Custom exception handler wired | **PASS** | `custom_exception_handler` in DRF settings |
| Consistent usage | **PARTIAL** | 307/309 response calls use helpers. 2 webhook views (`email_intel/views.py` lines 382, 402) return `{"ok": true}` instead of standard envelope |

---

## Phase 4: Auth System

| Component | Status | Notes |
|-----------|--------|-------|
| RegisterView | **PASS** | Full implementation with password validation |
| LoginView | **PASS** | Token creation, cookie flag set |
| LogoutView | **PASS** | Token deletion |
| ChangePasswordView | **PASS** | Validates new password, reissues token |
| ForgotPasswordView | **PASS** | Dispatches `send_password_reset_email` Celery task |
| ResetPasswordView | **PASS** | Token validation + password reset |
| VerifyEmailView | **PASS** | OTP + link verification |
| MeView (Profile) | **PASS** | GET `/api/v1/me` |
| OAuth (Google) | **PASS** | AllAuth + one-time code exchange via Redis |
| Token auth (DRF) | **PASS** | `TokenAuthentication` as default |
| Frontend login page | **PASS** | 224 lines, API wired, error display, OAuth link |
| Frontend register page | **PASS** | 612 lines, 3-step flow |
| Frontend OAuth callback | **PASS** | 107 lines, code exchange |
| Auth context | **PASS** | login/logout/refreshUser + auto-init + 401 listener |
| useAuth hook | **PASS** | Re-exports from AuthContext |
| Middleware | **PASS** | `whydud_auth` cookie check, 12 protected route groups |
| DeleteAccountView | **PASS** | DPDP soft-delete + hard-delete task |
| ExportDataView | **PASS** | DPDP data portability |
| Remember Me checkbox | **STUB** | UI present but non-functional (always remembers via localStorage) |
| Password hashing | **PARTIAL** | PBKDF2 (Django default), NOT bcrypt cost 12 as CLAUDE.md claims |

**BUG FOUND:** `apiClient.put` method does not exist in `client.ts`. `auth.ts:65` calls `apiClient.put()` for marketplace preferences update — will crash at runtime.

---

## Phase 5: Frontend Pages

### Public Pages
| Page | Route | Lines | API Wired | Status |
|------|-------|-------|-----------|--------|
| Homepage | `/` | 663 | Yes (4) | **PASS** |
| Search | `/search` | 129 | Yes (4) | **PASS** |
| Product Detail | `/product/[slug]` | 581 | Yes (10) | **PASS** |
| Compare | `/compare` | 677 | Yes (2) | **PASS** |
| Deals | `/deals` | 51 | Yes (2) | **PARTIAL** — Functional but shows "Deal detection launching Sprint 4" |
| Categories index | `/categories` | — | — | **FAIL** — Page does not exist. Only `/categories/[slug]` exists |
| Category Detail | `/categories/[slug]` | 36 | Yes (2) | **PARTIAL** — Thin, no loading/empty state |
| Leaderboard | `/leaderboard` | 570 | Yes (14) | **PASS** |
| Seller | `/seller/[slug]` | 316 | Yes | **PASS** (note: route is `[slug]` not `[id]`) |

### Dashboard Pages
| Page | Route | Lines | API Wired | Status |
|------|-------|-------|-----------|--------|
| Dashboard | `/dashboard` | 132 | Yes (6) | **PASS** |
| Inbox | `/inbox` | 391 | Yes (8) | **PASS** |
| Wishlists | `/wishlists` | 352 | Yes (8) | **PASS** |
| Settings | `/settings` | 1002 | Yes (16) | **PASS** |
| My Reviews | `/my-reviews` | 244 | Yes (7) | **PASS** |
| Alerts | `/alerts` | 433 | Yes (11) | **PASS** |
| Purchases | `/purchases` | 102 | Yes (6) | **PASS** |
| Refunds | `/refunds` | 118 | Yes (6) | **PASS** |
| Subscriptions | `/subscriptions` | 116 | Yes (6) | **PASS** |
| Rewards | `/rewards` | 322 | Yes (9) | **PASS** |
| Notifications | `/notifications` | 11 | Delegated | **PARTIAL** — Thin wrapper, logic in `NotificationList` component (247 lines) |

### Auth Pages
| Page | Route | Lines | Status |
|------|-------|-------|--------|
| Login | `/login` | 224 | **PASS** |
| Register | `/register` | 612 | **PASS** |
| Forgot Password | `/forgot-password` | 113 | **PASS** |
| Reset Password | `/reset-password` | 177 | **PASS** |
| Verify Email | `/verify-email` | 127 | **PASS** |
| OAuth Callback | `/auth/callback` | 107 | **PASS** |

---

## Phase 6: API Client & Type Safety

| Check | Status | Notes |
|-------|--------|-------|
| API client (`client.ts`) | **PASS** | 179 lines, token auth, camelCase↔snake_case, 401 handling, env-aware URLs |
| Types (`types.ts` + `@/types/`) | **PASS** | ~790 lines of type definitions |
| TypeScript strict mode | **PASS** | `strict: true` + `noUncheckedIndexedAccess: true` |
| Zero `any` usage | **PASS** | 0 occurrences across all .ts/.tsx |
| Zero raw `fetch` in components | **PASS** | 0 violations (2 server-side proxy routes are acceptable) |
| API modules | **PASS** | 16 modules covering all domains |
| Missing `put` method | **FAIL** | `client.ts` exports get/post/patch/delete but no `put`. `auth.ts:65` calls `apiClient.put()` |

---

## Phase 7: Celery Tasks

| Task | App | Real/Stub | Queue | Status |
|------|-----|-----------|-------|--------|
| send_verification_email | accounts | Real | email | **PASS** |
| send_verification_otp | accounts | Real | email | **PASS** |
| send_password_reset_email | accounts | Real | email | **PASS** |
| hard_delete_user | accounts | Real (~130 lines) | default | **PASS** |
| send_deletion_confirmation_email | accounts | Real | email | **PASS** |
| generate_data_export | accounts | Real (~100 lines) | default | **PASS** |
| sync_gmail_account | accounts | **Stub** | email | **STUB** |
| create_notification | accounts | Real (~90 lines) | default | **PASS** |
| send_notification_email | accounts | Real (~100 lines) | email | **PASS** |
| compute_dudscore | scoring | Real (~125 lines) | scoring | **PASS** |
| full_dudscore_recalculation | scoring | Real | scoring | **PASS** |
| recompute_brand_trust_scores | scoring | Real (~110 lines) | scoring | **PASS** |
| run_sentiment_analysis | reviews | **Stub** | scoring | **STUB** |
| detect_fake_reviews | reviews | Real | scoring | **PASS** |
| aggregate_review_sentiment | reviews | **Stub** | scoring | **STUB** |
| publish_pending_reviews | reviews | Real | default | **PASS** |
| update_reviewer_profiles | reviews | Real (~80 lines) | scoring | **PASS** |
| run_marketplace_spider | scraping | Real (~110 lines) | scraping | **PASS** |
| run_review_spider | scraping | Real (~90 lines) | scraping | **PASS** |
| run_spider | scraping | Real (~80 lines) | scraping | **PASS** |
| scrape_product_adhoc | scraping | Real (~45 lines) | scraping | **PASS** |
| scrape_daily_prices | scraping | Real (~30 lines) | scraping | **PASS** |
| sync_products_to_meilisearch | search | Real (~55 lines) | scoring | **PASS** |
| full_reindex | search | Real | scoring | **PASS** |
| check_price_alerts | pricing | Real (~115 lines) | alerts | **PASS** |
| snapshot_product_prices | pricing | **Stub** | scraping | **STUB** |
| backfill_existing_listings | pricing | Real | scraping | **PASS** |
| run_phase1_discover | pricing | Real | scraping | **PASS** |
| run_phase2_buyhatke | pricing | Real | scraping | **PASS** |
| run_phase3_extend | pricing | Real | scraping | **PASS** |
| refresh_price_daily_aggregate | pricing | Real | default | **PASS** |
| process_inbound_email | email_intel | Real (~45 lines) | email | **PASS** |
| send_return_window_alert | email_intel | Real (~40 lines) | email | **PASS** |
| check_return_window_alerts | email_intel | Real | email | **PASS** |
| detect_refund_delays | email_intel | Real (~35 lines) | email | **PASS** |
| detect_blockbuster_deals | deals | Real | scoring | **PASS** |
| award_points_task | rewards | Real | default | **PASS** |
| expire_points | rewards | Real (~40 lines) | default | **PASS** |
| fulfill_gift_card | rewards | Partial (~25 lines) | default | **PARTIAL** — logs for manual fulfillment, TODO for API integration |
| clawback_review_points_task | rewards | Real | default | **PASS** |
| reindex_product_in_meilisearch | products | **Stub** | scoring | **STUB** — superseded by `search.sync_products_to_meilisearch` |
| update_product_aggregate_stats | products | **Stub** | default | **STUB** |
| update_wishlist_prices | wishlists | **Stub** (unused) | alerts | **STUB** |

**Summary:** 37 tasks total — 30 real (81%), 1 partial (3%), 6 stubs (16%).

**Beat Schedule:** 21 scheduled entries covering scraping (14 marketplaces staggered across 24h), reviews, scoring, alerts, search reindex, deal detection.

**Issues:**
- 4 tasks documented as periodic are NOT in Beat schedule: `expire_points`, `check_return_window_alerts`, `detect_refund_delays`, `recompute_brand_trust_scores`
- Beat collision: `scrape-croma-daily` and `scrape-nykaa-daily` both at 08:00 UTC
- `discussions/tasks.py` is empty (imports `shared_task` but defines nothing)

---

## Phase 8: DudScore & Fraud Detection

| Component | Status | Notes |
|-----------|--------|-------|
| `compute_dudscore` task | **PASS** | 125 lines, 6 weighted components, fraud/confidence multipliers, spike detection, hypertable write |
| `DudScoreConfig` model | **PASS** | Versioned, 6 weights, is_active flag, all tuning fields |
| Component calculators (`components.py`) | **PASS** | 504 lines: sentiment (time-decay, VP weighting), rating quality (bimodal detection), price value (percentile), review credibility (4 sub-signals), price stability (CoV + inflation), return signal |
| Fraud multiplier | **PASS** | 0.7x if >30% flagged reviews |
| Confidence multiplier | **PASS** | 5-tier system (0.6-1.0) |
| `detect_fake_reviews` (`fraud_detection.py`) | **PASS** | 249 lines, 5 heuristic rules (copy-paste, burst, short, suspicious reviewer, unverified 5-star), credibility scoring, configurable thresholds via `FraudDetectionConfig` |
| Brand trust scores | **PASS** | Full aggregation with 5 trust tiers, stale cleanup |
| Deal detection engine | **PASS** | 340 lines, 4 deal types (error pricing, lowest ever, flash sale, genuine discount), stale deactivation |

---

## Phase 9: Scraping Spiders

| Spider | Lines | Real/Stub | Playwright | Status |
|--------|-------|-----------|------------|--------|
| amazon_spider | 1274 | Real | Yes (17 refs) | **PASS** |
| flipkart_spider | 1784 | Real | Yes (11 refs) | **PASS** |
| amazon_review_spider | 290 | Real | Yes (7 refs) | **PASS** |
| flipkart_review_spider | 373 | Real | Yes (14 refs) | **PASS** |
| myntra_spider | 1412 | Real | Yes (6 refs) | **PASS** |
| nykaa_spider | 1161 | Real | Yes (7 refs) | **PASS** |
| tatacliq_spider | 1056 | Real | Yes (10 refs) | **PASS** |
| ajio_spider | 948 | Real | Yes (7 refs) | **PASS** |
| jiomart_spider | 925 | Real | Yes (7 refs) | **PASS** |
| firstcry_spider | 912 | Real | Yes (4 refs) | **PASS** |
| meesho_spider | 818 | Real | Yes (7 refs) | **PASS** |
| croma_spider | 803 | Real | Yes (1 ref) | **PASS** |
| vijay_sales_spider | 784 | Real | Yes (3 refs) | **PASS** |
| snapdeal_spider | 707 | Real | Yes (3 refs) | **PASS** |
| reliance_digital_spider | 585 | Real | Yes (2 refs) | **PASS** |
| giva_spider | 455 | Real | Yes (2 refs) | **PASS** |
| base_spider | 176 | Real | N/A | **PASS** — 25 UAs, viewport randomization, stealth |

**Total:** 16 spiders (15 marketplace + 1 base), all fully implemented. Zero stubs.

| Infrastructure | Status | Notes |
|----------------|--------|-------|
| Pipeline chain (6 pipelines) | **PASS with BUG** | All functional but incorrect method signatures (`process_item(self, item)` missing `spider` param) — will crash at runtime |
| Middlewares | **PASS** | ProxyPool, PlaywrightProxy (dual-mode), BackoffRetry |
| Scrapy settings | **PASS** | Memory limits, AutoThrottle, Playwright config |
| Product matching | **PASS** | 522-line 4-step engine (EAN → brand+model+variant → brand+model → fuzzy title) |

**BUG:** Pipeline `process_item`, `open_spider`, `close_spider` methods all missing required `spider` parameter. Tests pass because they call methods directly without it, but Scrapy always passes spider as positional arg → `TypeError` in production.

---

## Phase 10: Frontend Components

| Category | Components | Status |
|----------|------------|--------|
| Layout | Header, Footer, Sidebar, MobileNav | **PASS** |
| Product | ProductCard (x2), PriceChart, MarketplacePrices, DudScoreGauge, DudScoreDisplay, ShareButton, PriceAlertButton, AddToCompareButton, RecentlyViewedSection, TrendingSection, BrandLeaderboard, BrandTrustBadge, BrandTrustGauge, CrossPlatformPricePanel | **PASS** (note: duplicate ProductCard files) |
| Dashboard | DashboardCharts (11KB), SpendOverview, CardVault | **PASS** |
| Reviews | ReviewCard, ReviewSidebar, RatingDistribution, StarRatingInput | **PASS** |
| Discussions | ThreadCard, ThreadDetail, DiscussionSection, CreateThreadForm, ReplyForm, VoteButtons | **PASS** |
| Notifications | NotificationBell, NotificationCard, NotificationList | **PASS** |
| TCO | TCOCalculator (21KB) | **PASS** |
| Search | SearchBar, SearchFilters | **PASS** |
| Inbox | EmailList, InboxSidebar | **PASS** |
| Compare | CompareTray | **PASS** |
| shadcn/ui | 19 components installed | **PASS** |

**Issues:**
- Duplicate `ProductCard`: `ProductCard.tsx` (79 lines, older) and `product-card.tsx` (155+ lines, newer). Import ambiguity risk.
- Empty component directories: `wishlists/`, `seller/` — logic inlined in page files.

---

## Phase 11: Infrastructure

| Check | Status | Notes |
|-------|--------|-------|
| Docker Compose (production) | **PASS** | 10 services, healthchecks, `restart: unless-stopped` |
| Docker Compose (dev) | **PASS** | 4 infra services (postgres, redis, meilisearch, flower) |
| Docker Compose (primary/replica) | **PASS** | 2-node topology with WireGuard, resource limits |
| Caddy configuration | **PASS** | 2 variants (Let's Encrypt + Cloudflare origin), security headers, marketplace redirects |
| Multi-stage Dockerfiles | **PASS** | Non-root users, layer caching, build-time secrets |
| DB config (PostgreSQL + TimescaleDB) | **PASS** | Schemas, replication, pg_hba scram-sha-256, DB router |
| Backup system | **PASS** | pg_dump every 6h, S3 upload, incremental, Discord alerts |
| Celery config | **PASS** | 5 queues, 21 beat entries, Discord + Sentry monitoring |
| `common/app_settings.py` | **PASS** | 14 config classes, zero hardcoded tuneable values |
| Cursor pagination | **PASS** | Reads from app_settings, correct response format |
| `.env.example` (root) | **FAIL** | Contains real secrets committed to git history (Django secret key, DB passwords, encryption keys, proxy credentials) |
| Requirements | **PARTIAL** | sentry-sdk version conflict (base 2.26.1 vs prod 2.12.0), scraping deps in base.txt, lock.txt divergence |

---

## Phase 12: Security

| Check | Status | Notes |
|-------|--------|-------|
| Password validators | **PASS** | 4 validators, min_length=8 |
| Password hashing | **PARTIAL** | PBKDF2 (Django default), NOT bcrypt cost 12 as documented |
| Session cookies | **PASS** | HttpOnly, Secure, SameSite=Strict |
| CSRF cookies | **PASS** | HttpOnly, Secure, SameSite=Strict |
| AES-256-GCM encryption | **PASS** | Email + OAuth tokens encrypted at rest, separate keys |
| nh3 HTML sanitization | **PASS** | Used on all email body processing paths |
| Rate limiting (per-view) | **PASS** | Auth (10/min), Search (60/min), Reviews (5/hr), Email (10/day) |
| Rate limiting (global) | **PARTIAL** | `RateLimitMiddleware` defined but NOT installed in MIDDLEWARE |
| CORS | **PASS** | Locked to `whydud.com` in prod, open in dev |
| Card vault safety | **PASS** | No PCI-sensitive fields exist (bank name + variant only) |
| Security headers | **PASS** | HSTS (1yr), X-Frame-Options DENY, nosniff, Permissions-Policy |
| Sentry PII | **PASS** | `send_default_pii=False` |
| `.gitignore` coverage | **PARTIAL** | `backend/.env` not explicitly gitignored |

---

## Phase 13: Confirmed Gaps (Not Built)

| Feature | Status | Notes |
|---------|--------|-------|
| Write a Review | **PASS** — BUILT | Multi-tab form with draft persistence, 4 sub-components |
| Email webhook handler | **PASS** — BUILT | HMAC auth, AES-256-GCM encryption, Celery dispatch |
| Notification bell | **PASS** — BUILT | In header, polls every 30s |
| Forgot password email | **PASS** — BUILT | Celery task + view dispatch |
| Deal detection | **PASS** — BUILT | 340-line engine, 4 deal types |
| Rewards engine | **PASS** — BUILT | Full award/deduct/clawback/redeem with caps, levels |
| DPDP compliance | **PASS** — BUILT | Soft delete, hard delete, data export |
| Compare tray (floating) | **PASS** — BUILT | In root layout with context (max 4) |

**Note:** PROGRESS.md lists several of these as "NOT BUILT" but they are now fully implemented. PROGRESS.md is stale.

---

## Phase 14: TypeScript Compilation

| Check | Status | Notes |
|-------|--------|-------|
| `tsc --noEmit` | **FAIL** | 1 error: `Property 'put' does not exist` on apiClient (`auth.ts:65`) |
| `any` type usage | **PASS** | 0 instances across all .ts/.tsx |
| Raw `fetch` in components | **PASS** | 0 violations (2 server-side proxy routes are acceptable) |

---

## Bugs Found (Not Fixed)

| # | Severity | Location | Description |
|---|----------|----------|-------------|
| 1 | **HIGH** | `frontend/src/lib/api/client.ts` | Missing `put` method. `auth.ts:65` calls `apiClient.put()` for marketplace preferences — **compile error + runtime crash** |
| 2 | **HIGH** | `backend/apps/scraping/pipelines.py` | All `process_item(self, item)`, `open_spider(self)`, `close_spider(self)` methods missing required `spider` parameter. Scrapy passes spider as positional arg → **TypeError in production**. Tests don't catch this because they call methods directly. |
| 3 | **HIGH** | `.env.example` (project root) | Contains real secrets committed to git: Django secret key, DB passwords, encryption keys, proxy credentials. These are in git history permanently. |
| 4 | **MEDIUM** | `backend/whydud/celery.py` | 4 periodic tasks NOT registered in Beat schedule: `expire_points` (monthly), `check_return_window_alerts` (daily), `detect_refund_delays` (daily), `recompute_brand_trust_scores` (weekly) |
| 5 | **MEDIUM** | `backend/whydud/celery.py` | Beat collision: `scrape-croma-daily` and `scrape-nykaa-daily` both at 08:00 UTC |
| 6 | **LOW** | `backend/whydud/settings/` | No `PASSWORD_HASHERS` setting. CLAUDE.md says "bcrypt cost 12" but Django defaults to PBKDF2. Still secure, but inconsistent with docs. |
| 7 | **LOW** | `backend/whydud/settings/base.py` | `RateLimitMiddleware` defined in `common/rate_limiting.py` but NOT installed in `MIDDLEWARE` list. No global flood protection at Django level. |
| 8 | **LOW** | `frontend/src/app/(auth)/login/page.tsx` | "Remember me" checkbox rendered but not wired to any state. Always remembers via localStorage. |
| 9 | **LOW** | `backend/requirements/` | sentry-sdk version conflict: `base.txt` pins 2.26.1, `prod.txt` pins 2.12.0 |
| 10 | **LOW** | `frontend/src/components/product/` | Duplicate `ProductCard`: `ProductCard.tsx` (79 lines, older) and `product-card.tsx` (155+ lines, newer). Import ambiguity. |
| 11 | **LOW** | `frontend/src/app/(public)/categories/page.tsx` | Missing — navigating to `/categories` returns 404. Only `/categories/[slug]` exists. |

---

## Recommendations

1. **Add `put` method to `apiClient`** — Copy the `patch` method and change the HTTP method to PUT. This is a one-line fix that unblocks marketplace preferences.

2. **Fix Scrapy pipeline signatures** — Add `spider` parameter to all `process_item`, `open_spider`, and `close_spider` methods. Update tests to pass a spider mock.

3. **Rotate all secrets in `.env.example`** — Replace with placeholder values. If this repo is ever shared, these credentials are exposed via git history. Consider using `git filter-repo` to purge from history.

4. **Register missing Beat tasks** — Add `expire_points`, `check_return_window_alerts`, `detect_refund_delays`, `recompute_brand_trust_scores` to the Beat schedule.

5. **Fix Beat collision** — Stagger `scrape-croma-daily` and `scrape-nykaa-daily` by 30+ minutes.

6. **Install `RateLimitMiddleware`** — Add to MIDDLEWARE list for global flood protection.

7. **Update PROGRESS.md** — Many features listed as "NOT BUILT" are now fully implemented (Write a Review, Deal Detection, Rewards Engine, Compare Tray, DPDP Compliance, Notification Bell).

8. **Create `/categories` index page** — Currently a 404.

9. **Remove duplicate ProductCard** — Delete the older `ProductCard.tsx` and ensure all imports point to `product-card.tsx`.

10. **Decide on password hashing** — Either add bcrypt (`PASSWORD_HASHERS = ['django.contrib.auth.hashers.BCryptSHA256PasswordHasher']`) or update CLAUDE.md to reflect PBKDF2.
