# WHYDUD — Progress & Build Status

> **Claude Code: Read this file FIRST at the start of every session.**
> **Then read CLAUDE.md for project conventions.**
> **Then check actual files before building — this status may lag behind reality.**

---

## 🎯 CURRENT TASK

> Update this section every time you switch tasks.

Wire Auth (BLOCKER — unblocks ALL dashboard features):
1. Wire login form → authApi.login() → store token → redirect to /dashboard
2. Wire register form → authApi.register() → auto-login
3. Auth context provider (useAuth hook) → header shows user name
4. Frontend middleware → redirect /dashboard/* to /login if not authenticated
5. Google OAuth frontend flow

After auth: Database migrations for v2.2 (see Priority Build Order below).

---

## What's Working End-to-End

| Feature | Status | Notes |
|---|---|---|
| All 13 Django apps scaffolded | ✅ Built | products, accounts, scraping, scoring, pricing, search, deals, wishlists, rewards, discussions, tco, email_intel, common, payments |
| All database models + migrations | ✅ Built | All migrated, TimescaleDB hypertables, custom schemas |
| All DRF serializers | ✅ Built | List + Detail serializers for all models |
| All DRF views + URL routing | ✅ Built | ~30+ endpoints with real ORM logic, cursor pagination |
| Django Admin | ✅ Built | All models registered at /admin/ |
| Meilisearch | ✅ Built | 31 seeded products indexed, search + autocomplete working |
| Docker Compose | ✅ Built | Django, Next.js, PostgreSQL+TimescaleDB, Redis, Meilisearch, Celery, Caddy |
| Seed data | ✅ Built | 31 products with prices, reviews, marketplace listings |
| Public frontend pages | ✅ Built | Homepage, Search, Product Detail, Compare, Seller, Deals, Categories — pulling real API data |
| Header + Footer + Layout | ✅ Built | But needs polish to match Figma exactly |

## What's Built But NOT Wired

| Feature | What Exists | What's Missing |
|---|---|---|
| Login page | UI form exists | Form has `onSubmit={(e) => e.preventDefault()}` — submits to NOTHING. `authApi.login()` exists but is never called. No token storage. |
| Register page | 3-step UI exists | Same — no API calls wired. Step 2 (@whyd email) and Step 3 (onboarding) not connected. |
| Dashboard pages | UI shells exist | All show "Please log in" because no auth token. Once login is wired, these need to call real APIs. |
| Backend auth endpoints | Views + serializers exist | Working if tested via curl/Postman. Frontend just doesn't call them. |

## What's Stubbed (Code Exists But Methods Are `pass`)

| Feature | What's Stubbed | What Needs Real Implementation |
|---|---|---|
| Scraping spiders | Spider classes for Amazon.in, Flipkart exist | Every method is `pass`. No actual HTML parsing, no selectors, no data extraction. All products come from seed command. |
| Email webhook | Endpoint accepts POST | Does nothing with the data. No parsing, no categorization, no storage. |
| DudScore calculation | Model + config + Celery task exist | Celery task is a stub. No actual sentiment analysis, no rating quality calc, no component scoring. |
| Price history API | View exists | Returns 501 Not Implemented |
| Razorpay payments | View exists | Returns 501 Not Implemented |
| Gmail OAuth | Django AllAuth configured in settings | No frontend OAuth flow. OAuthConnection model exists but no Gmail API calls. |

## What Doesn't Exist At All (v2.2 Additions)

| Feature | Architecture Section | Status |
|---|---|---|
| **Multi-domain email** (whyd.in / whyd.click / whyd.shop) | Section 6 | ❌ NOT BUILT |
| **Email sending** (Reply/Compose via Resend) | Section 6 | ❌ NOT BUILT |
| **Email source aggregation** (multi-account) | Section 6 | ❌ NOT BUILT |
| **Click tracking** (affiliate attribution) | Section 10 | ❌ NOT BUILT |
| **Purchase search** (cross-platform) | Section 10 | ❌ NOT BUILT |
| **Admin audit log** | Section 9 | ❌ NOT BUILT |
| **Admin as independent system** | Section 19 | ❌ NOT BUILT |
| **Price alerts table** | Section 9 | ❌ NOT BUILT |
| **Compare tray (floating)** | Section 13 | ❌ NOT BUILT |
| **Cross-platform price comparison panel** | Section 13 | ❌ NOT BUILT |
| **Recently viewed** | Section 10 | ❌ NOT BUILT |
| **Back-in-stock alerts** | Section 9 | ❌ NOT BUILT |
| **Share product/comparison** | Section 10 | ❌ NOT BUILT |
| **Similar/alternative products** | Section 10 | ❌ NOT BUILT |
| **Product matching engine** | Section 6 | ❌ NOT BUILT |
| **Username suggestions** | Section 10 | ❌ NOT BUILT |
| **Write a Review page** | Section 13 | ❌ NOT BUILT |
| **Purchase proof upload** | Section 9 | ❌ NOT BUILT |
| **Feature-specific ratings** | Section 9 | ❌ NOT BUILT |
| **Seller feedback** | Section 9 | ❌ NOT BUILT |
| **NPS score** | Section 9 | ❌ NOT BUILT |
| **Notifications system** | Section 9 | ❌ NOT BUILT |
| **Notification preferences** | Section 9 | ❌ NOT BUILT |
| **Purchase Preferences** | Section 9 | ❌ NOT BUILT |
| **Reviewer levels & leaderboard** | Section 9 | ❌ NOT BUILT |
| **Trending products** | Section 10 | ❌ NOT BUILT |
| **Dynamic TCO per category** | Section 9 | ⚠️ PARTIAL (table exists, no seed data) |

---

## Priority Build Order

```
BLOCKER — Wire Auth (unblocks ALL dashboard features):
  1. Wire login form → authApi.login() → store token → redirect to /dashboard
  2. Wire register form → authApi.register() → auto-login
  3. Auth context provider (useAuth hook) → header shows user name
  4. Frontend middleware → redirect /dashboard/* to /login if not authenticated
  5. Google OAuth frontend flow

THEN — Database Migrations for v2.2:
  6-18. See docs/TASKS.md Phase 1 (prompts 1.1 through 1.10)

THEN — API Endpoints:
  19-28. See docs/TASKS.md Phase 2 (prompts 2.1 through 2.10)

THEN — Frontend Types + API Client:
  29-31. See docs/TASKS.md Phase 3

THEN — Frontend Components + Pages:
  32-43. See docs/TASKS.md Phase 4

THEN — TCO + Leaderboard + Trending:
  44-46. See docs/TASKS.md Phase 5

THEN — Seed Data:
  47-49. See docs/TASKS.md Phase 6

THEN — Celery Tasks:
  50-52. See docs/TASKS.md Phase 7

THEN — Integration:
  53-56. See docs/TASKS.md Phase 8

THEN — Email System:
  57. Update email webhook handler (parse username + domain from recipient)
  58. Email send service (Resend API integration)
  59. Email categorization + marketplace detection
  60. Order parsers (Amazon, Flipkart, generic)

THEN — Scraping (Replace Seed Data):
  61. Amazon.in spider (real selectors, real parsing)
  62. Flipkart spider
  63. Product matching engine (cross-platform deduplication)
  64. Price snapshot pipeline
  65. Price alert check Celery task
  66. Meilisearch sync after scrapes

THEN — Intelligence:
  67. DudScore calculation (real components)
  68. Fake review detection rules
  69. Deal detection
  70. Dynamic TCO calculator engine
```

---

## Established Patterns (Follow These)

| Pattern | Reference File |
|---|---|
| API response format | `{success: true, data: ...}` — see common/utils.py |
| Cursor pagination | common/pagination.py |
| TimescaleDB hypertable migration | pricing/migrations/0002_timescaledb_setup.py |
| Serializer flat vs nested | ProductListSerializer (flat) vs ProductDetailSerializer (nested) |
| Affiliate URL injection | ProductListingSerializer.get_buy_url() |
| App settings access | common/app_settings.py (never hardcode config values) |
| Card pattern (frontend) | bg-white rounded-lg border border-slate-200 shadow-sm |
| Price formatting (frontend) | src/lib/utils/format.ts formatPrice() |

---

## Credentials Available in .env

```
Check .env for these before using:
  DJANGO_SECRET_KEY         — Required for any Django operation
  DATABASE_URL              — PostgreSQL connection
  REDIS_URL                 — Redis for cache + Celery broker
  MEILISEARCH_URL           — Search engine
  MEILISEARCH_MASTER_KEY    — Search admin key

NOT yet configured (will be added later):
  RESEND_API_KEY            — For email sending (whyd.in/.click/.shop)
  RAZORPAY_KEY_ID           — Payment processing
  RAZORPAY_KEY_SECRET       — Payment processing
  GOOGLE_CLIENT_ID          — OAuth
  GOOGLE_CLIENT_SECRET      — OAuth
  CLOUDFLARE_EMAIL_SECRET   — Email webhook verification

If code references a key that doesn't exist in .env, use a placeholder like
settings.RESEND_API_KEY etc. — the actual value will be added to .env later.
```
