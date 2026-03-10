# Whydud — Complete Codebase Knowledge Base

> **Purpose:** This document is a comprehensive knowledge transfer guide for the Whydud codebase. It explains every major system, component, pattern, and decision — both in programmer terms and in plain language for beginners. Use it as your single source of truth when onboarding, debugging, or building new features.
>
> **Last updated:** 2026-03-10

---

## Table of Contents

1. [What Is Whydud?](#1-what-is-whydud)
2. [Tech Stack Overview](#2-tech-stack-overview)
3. [Project Structure](#3-project-structure)
4. [Programming Concepts & Principles](#4-programming-concepts--principles)
5. [Backend — Django](#5-backend--django)
   - 5.1 [Settings & Configuration](#51-settings--configuration)
   - 5.2 [Django Apps (13 Total)](#52-django-apps-13-total)
   - 5.3 [Common Utilities](#53-common-utilities)
   - 5.4 [Celery — Background Task System](#54-celery--background-task-system)
   - 5.5 [Database Design](#55-database-design)
6. [Frontend — Next.js](#6-frontend--nextjs)
   - 6.1 [App Router & Route Groups](#61-app-router--route-groups)
   - 6.2 [Authentication System](#62-authentication-system)
   - 6.3 [API Client Layer](#63-api-client-layer)
   - 6.4 [Components](#64-components)
   - 6.5 [State Management](#65-state-management)
   - 6.6 [Type System](#66-type-system)
   - 6.7 [Styling & Design System](#67-styling--design-system)
7. [Scraping System](#7-scraping-system)
   - 7.1 [Spider Architecture](#71-spider-architecture)
   - 7.2 [Middlewares — Proxy & Retry](#72-middlewares--proxy--retry)
   - 7.3 [Pipelines — Data Processing](#73-pipelines--data-processing)
   - 7.4 [Task Orchestration](#74-task-orchestration)
8. [Backfill Pipeline](#8-backfill-pipeline)
   - 8.1 [The Five Phases](#81-the-five-phases)
   - 8.2 [Lightweight Products](#82-lightweight-products)
   - 8.3 [Enrichment System](#83-enrichment-system)
   - 8.4 [Price Injection](#84-price-injection)
9. [Infrastructure & Deployment](#9-infrastructure--deployment)
   - 9.1 [Docker Compose](#91-docker-compose)
   - 9.2 [Caddy Reverse Proxy](#92-caddy-reverse-proxy)
   - 9.3 [Worker Nodes & WireGuard](#93-worker-nodes--wireguard)
10. [Security](#10-security)
11. [Data Safety Rules](#11-data-safety-rules)
12. [Key Patterns & Conventions](#12-key-patterns--conventions)
13. [Environment Variables](#13-environment-variables)
14. [Troubleshooting Guide](#14-troubleshooting-guide)
15. [Glossary](#15-glossary)

---

## 1. What Is Whydud?

### In Plain Language

Whydud is a website that helps Indian shoppers make smarter buying decisions. Think of it as a "product truth engine." Before you buy a phone, AC, or laptop, Whydud shows you:

- **The real price history** — Is this sale genuine or was the MRP inflated?
- **Reviews you can trust** — Which reviews are fake? Which are from real buyers?
- **DudScore** — A single number (0–100) telling you if a product is worth buying
- **Price comparison** — The same product's price across Amazon, Flipkart, Myntra, Croma, and 8+ more marketplaces
- **Total Cost of Ownership** — "This 3-star AC costs ₹7,000 more over 5 years than the 5-star"
- **Smart payment advice** — "Use your HDFC card on Amazon to save ₹1,500"

Users get a free shopping email address (@whyd.in, @whyd.click, or @whyd.shop) that automatically tracks their purchases, refunds, and return windows.

### In Programmer Terms

Whydud is a **modular monolith** — a single Django backend serving a Next.js frontend, with Scrapy-based web scraping, Celery for async processing, PostgreSQL+TimescaleDB for storage, and Meilisearch for full-text search. It aggregates product data from 12+ Indian e-commerce marketplaces, runs fraud detection on reviews, computes a proprietary trust score (DudScore), and provides purchase intelligence via email integration.

### Revenue Model

- **Affiliate links** — Every "Buy" button on Whydud contains an affiliate tag. When users purchase through Whydud, we earn a commission.
- **Premium subscriptions** — ₹99/month for advanced features (subscription detection, higher limits).

### Core Differentiators (The "Moat")

| Feature | What It Does | Why It Matters |
|---------|-------------|----------------|
| @whyd.* email | Free shopping email that auto-parses orders | No competitor does this in India |
| DudScore | Trust-adjusted value score (0–100) | Goes beyond star ratings — accounts for fake reviews, price manipulation |
| Payment Optimizer | Matches user's bank cards to best offers | Personalized savings per user |
| TCO Calculator | 5-year cost projection (purchase + electricity + maintenance) | Helps with appliance decisions |
| Fake Review Detection | Rule-based fraud scoring on reviews | Identifies suspicious patterns (bursts, duplicates, short 5-stars) |

---

## 2. Tech Stack Overview

### For Beginners: What Each Technology Does

| Technology | What It Is | Why We Use It |
|-----------|-----------|---------------|
| **Django** | A Python web framework | Handles all server-side logic, database operations, and API endpoints |
| **Django REST Framework (DRF)** | Extension for Django | Makes it easy to build JSON APIs that the frontend consumes |
| **Next.js** | A React framework | Renders web pages (both on the server and in the browser) |
| **TypeScript** | JavaScript with types | Catches bugs before they reach production |
| **Tailwind CSS** | Utility-first CSS | Write styles directly in HTML/JSX without separate CSS files |
| **PostgreSQL** | Relational database | Stores all our data (products, users, reviews, etc.) |
| **TimescaleDB** | Time-series extension for PostgreSQL | Efficiently stores millions of price history data points |
| **Redis** | In-memory data store | Caching, session storage, message broker for background tasks |
| **Meilisearch** | Search engine | Fast, typo-tolerant product search and autocomplete |
| **Celery** | Task queue | Runs background jobs (scraping, email sending, score calculation) |
| **Scrapy** | Web scraping framework | Crawls Amazon, Flipkart, etc. for product data |
| **Playwright** | Browser automation | Controls a real browser for pages that require JavaScript |
| **Docker** | Containerization | Packages everything so it runs the same on any server |
| **Caddy** | Web server / reverse proxy | Routes traffic, handles HTTPS certificates automatically |
| **WireGuard** | VPN tunnel | Securely connects worker nodes to the main server |

### For Programmers: Version Specifics

```
Backend:   Python 3.12+ | Django 5.x | DRF | Celery 5.x | Scrapy
Frontend:  Node.js | Next.js 15.1.0 (App Router) | React 19 | TypeScript 5.7 (strict)
Database:  PostgreSQL 16 + TimescaleDB | Redis 7
Search:    Meilisearch
Infra:     Docker Compose | Caddy 2 | WireGuard
Email:     Cloudflare Email Workers (receive) + Resend API (send)
Payments:  Razorpay (planned)
Monitoring: Structlog (JSON) + Sentry + Discord webhooks
```

---

## 3. Project Structure

```
whydud/
├── CLAUDE.md                    # AI assistant instructions (coding conventions)
├── PROGRESS.md                  # What's built, what's next — read FIRST
├── BACKFILL.md                  # Backfill pipeline deep dive
│
├── backend/
│   ├── whydud/                  # Django project settings
│   │   ├── settings/
│   │   │   ├── base.py          # Shared settings (DB, installed apps, middleware)
│   │   │   ├── dev.py           # Development overrides (DEBUG=True)
│   │   │   └── prod.py          # Production overrides (HTTPS, Sentry)
│   │   ├── urls.py              # Root URL routing (/api/v1/...)
│   │   └── celery.py            # Celery config (queues, beat schedule)
│   │
│   ├── apps/                    # 13 Django apps
│   │   ├── accounts/            # User auth, profiles, shopping emails
│   │   ├── products/            # Product catalog, listings, sellers, categories
│   │   ├── pricing/             # Price snapshots, alerts, offers, backfill pipeline
│   │   ├── reviews/             # Reviews, voting, fraud detection, reviewer profiles
│   │   ├── scoring/             # DudScore algorithm, brand trust scores
│   │   ├── email_intel/         # Inbox emails, order parsing, refund tracking
│   │   ├── wishlists/           # User wishlists with price tracking
│   │   ├── deals/               # Blockbuster deal detection
│   │   ├── rewards/             # Points, gift cards, gamification
│   │   ├── discussions/         # Product Q&A threads
│   │   ├── tco/                 # Total Cost of Ownership calculator
│   │   ├── search/              # Meilisearch integration
│   │   └── scraping/            # Scrapy spiders, pipelines, middlewares
│   │
│   ├── common/                  # Shared utilities
│   │   ├── utils.py             # API response wrappers
│   │   ├── pagination.py        # Cursor-based pagination
│   │   ├── permissions.py       # Custom DRF permissions
│   │   ├── rate_limiting.py     # Token-bucket rate limiter
│   │   ├── app_settings.py      # All tuneable config values
│   │   ├── encryption.py        # AES-256-GCM encryption helpers
│   │   └── middleware.py        # Request ID middleware
│   │
│   └── requirements/
│       ├── base.txt             # Core dependencies
│       ├── dev.txt              # Dev-only (debug toolbar, etc.)
│       └── prod.txt             # Production (gunicorn, sentry)
│
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   │   ├── (public)/        # Public routes (homepage, search, product)
│   │   │   ├── (auth)/          # Auth routes (login, register, OAuth)
│   │   │   └── (dashboard)/     # Protected routes (dashboard, inbox, settings)
│   │   │
│   │   ├── components/          # React components organized by domain
│   │   │   ├── ui/              # Base UI (button, card, input — shadcn/ui)
│   │   │   ├── layout/          # Header, Footer, Sidebar, MobileNav
│   │   │   ├── product/         # ProductCard, PriceChart, DudScoreGauge
│   │   │   ├── reviews/         # ReviewCard, WriteReviewForm
│   │   │   ├── search/          # SearchBar, SearchFilters
│   │   │   ├── dashboard/       # DashboardCharts, StatCard
│   │   │   ├── inbox/           # EmailList, EmailReader
│   │   │   ├── tco/             # TCOCalculator, TCOBreakdown
│   │   │   └── ...              # compare/, deals/, rewards/, wishlists/, etc.
│   │   │
│   │   ├── lib/
│   │   │   ├── api/             # API client + domain modules
│   │   │   │   ├── client.ts    # Base HTTP client (token, case conversion)
│   │   │   │   ├── types.ts     # API envelope types (ApiSuccess, ApiError)
│   │   │   │   ├── auth.ts      # Auth, WhydudEmail, CardVault API calls
│   │   │   │   ├── products.ts  # Products, categories, deals, clicks API
│   │   │   │   ├── search.ts    # Search + autocomplete
│   │   │   │   ├── reviews.ts   # Reviews, reviewer profiles, leaderboard
│   │   │   │   ├── inbox.ts     # Inbox, purchases, refunds, subscriptions
│   │   │   │   ├── wishlists.ts # Wishlist CRUD
│   │   │   │   ├── alerts.ts    # Price + stock alerts
│   │   │   │   ├── rewards.ts   # Points, gift cards
│   │   │   │   ├── tco.ts       # TCO calculator
│   │   │   │   └── ...          # discussions, notifications, sellers, brands
│   │   │   │
│   │   │   └── utils/
│   │   │       ├── format.ts    # formatPrice(), formatDate(), dudScoreColour()
│   │   │       └── cn.ts        # Tailwind class merge helper
│   │   │
│   │   ├── contexts/
│   │   │   ├── auth-context.tsx  # Global auth state (user, token, login/logout)
│   │   │   └── compare-context.tsx # Compare tray state (max 4 products)
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAuth.ts       # Auth hook re-export
│   │   │   └── useSearchAutocomplete.ts # Debounced autocomplete
│   │   │
│   │   ├── types/               # TypeScript type definitions
│   │   │   ├── product.ts       # Product, Review, Deal, PricePoint, etc.
│   │   │   └── user.ts          # User, WhydudEmail, PaymentMethod, etc.
│   │   │
│   │   └── config/
│   │       └── marketplace.ts   # Marketplace registry (slug → name, badge, color)
│   │
│   ├── package.json
│   ├── tsconfig.json            # TypeScript strict config
│   ├── next.config.ts           # Next.js config (rewrites, images, standalone)
│   └── tailwind.config.ts       # Custom colors, fonts, spacing
│
├── docker/
│   ├── docker-compose.yml       # Production: 10 services
│   ├── docker-compose.worker.yml # Remote worker node
│   ├── Caddyfile                # Reverse proxy config
│   ├── Dockerfiles/
│   │   ├── backend.Dockerfile   # Django + Playwright + spaCy (~3GB)
│   │   └── worker-light.Dockerfile # Slim worker (no Playwright, ~1GB)
│   ├── cloud-init-worker.yml    # OCI instance auto-setup
│   └── postgres/
│       └── init.sql             # Create DB schemas
│
└── docs/
    ├── ARCHITECTURE.md          # Full system architecture (v2.2)
    ├── DESIGN-SYSTEM.md         # Visual specs, color palette, components
    ├── figma/                   # Reference screenshots for each page
    └── codebase-knowledge-base.md  # THIS FILE
```

---

## 4. Programming Concepts & Principles

This section explains key programming concepts used throughout the codebase. If you're experienced, skip ahead. If you're a beginner, this will help you understand the "why" behind our code patterns.

### 4.1 Modular Monolith

**What it means:** All code lives in one repository and one deployable unit (unlike microservices, where each feature is a separate service). However, the code is organized into independent "modules" (Django apps) with clear boundaries.

**Why:** For a small team (1–2 developers), microservices add enormous complexity (network calls between services, distributed transactions, independent deployments). A monolith is simpler to develop, test, and deploy. The "modular" part means we can extract a service later if we need to scale one part independently.

**In our code:** Each Django app (`accounts`, `products`, `pricing`, etc.) is a self-contained module with its own models, views, serializers, and tasks. Apps communicate through well-defined interfaces (imports and Celery tasks), not HTTP calls.

### 4.2 API-First Architecture

**What it means:** The backend exposes a JSON API. The frontend is a separate application that consumes this API. They communicate over HTTP.

**Why:** This decouples the frontend from the backend. We could replace Next.js with a mobile app or a different web framework, and the backend wouldn't change. It also means the frontend team and backend team can work independently.

**In our code:**
- Backend: Django REST Framework (DRF) serves JSON at `/api/v1/...`
- Frontend: Next.js calls these endpoints via the API client (`src/lib/api/client.ts`)

### 4.3 Server-Side Rendering (SSR) vs Client-Side Rendering (CSR)

**What it means:**
- **SSR:** The server generates the HTML. The browser receives a fully rendered page. Good for SEO and initial load speed.
- **CSR:** The browser receives a minimal HTML shell, then JavaScript fetches data and renders the page. Good for interactive UIs.

**In our code:** Next.js App Router uses **Server Components** by default (SSR). Components that need interactivity (forms, modals, state) use `"use client"` directive (CSR). This gives us the best of both worlds.

### 4.4 Cursor-Based Pagination

**What it means:** Instead of page numbers (page 1, page 2...), the API returns a "cursor" — an opaque token pointing to the next set of results.

**Why:** Offset-based pagination (`LIMIT 20 OFFSET 100`) is slow for large datasets (the database still scans and skips 100 rows). Cursor pagination (`WHERE id > last_seen_id LIMIT 20`) is constant-time regardless of how deep you paginate.

**In our code:** `common/pagination.py` implements `CursorPagination`. Every paginated API returns `{ data: [...], pagination: { next: "cursor_token", previous: "cursor_token" } }`.

### 4.5 Token-Based Authentication

**What it means:** After login, the server gives the client a random string (token). The client sends this token with every subsequent request to prove their identity.

**Why:** Simpler than session-based auth for API-first apps. Tokens are stateless — the server doesn't need to look up a session store on every request (though we do store tokens in the database for revocation).

**In our code:**
- Backend: DRF `TokenAuthentication`. Token created at login, deleted at logout.
- Frontend: Token stored in `localStorage`. Sent as `Authorization: Token {token}` header.
- Cookie: `whydud_auth=1` flag set for Next.js middleware (edge-level route protection).

### 4.6 Task Queues (Celery)

**What it means:** Some operations take too long for a web request (scraping a product page takes 3–10 seconds, sending an email takes 1–2 seconds). Instead of making the user wait, we put the job in a queue and return immediately. A separate "worker" process picks up the job and runs it in the background.

**Why:** Web requests should respond in <500ms. Background tasks can take minutes. Separating them keeps the user experience snappy.

**In our code:**
- **Celery** is our task queue system
- **Redis** is the message broker (passes jobs from the web process to workers)
- Tasks are defined with `@shared_task` decorator in each app's `tasks.py`
- **Celery Beat** is the scheduler — runs recurring tasks on a cron-like schedule

### 4.7 Time-Series Data (TimescaleDB)

**What it means:** Price snapshots are "time-series data" — data points indexed by time. A product might have thousands of price points spanning years. Regular PostgreSQL tables are slow for time-range queries on millions of rows.

**Why:** TimescaleDB extends PostgreSQL with "hypertables" — tables automatically partitioned by time. Queries like "get all prices for this product in the last 90 days" are fast because they only scan the relevant time partition.

**In our code:**
- `PriceSnapshot` and `DudScoreHistory` are TimescaleDB hypertables
- They use `managed = False` in Django (Django doesn't create the table — our migration does)
- The migration uses `raw_conn.autocommit = True` because TimescaleDB DDL cannot run inside a transaction

### 4.8 Separation of Concerns

**What it means:** Each layer of the application has one job:

| Layer | Job | In Our Code |
|-------|-----|-------------|
| **Views** | Accept HTTP request, return HTTP response | `views.py` — thin, delegates to services |
| **Serializers** | Validate input, format output | `serializers.py` — all API validation |
| **Services / Model Methods** | Business logic | `services.py`, model methods |
| **Tasks** | Background processing | `tasks.py` |
| **Models** | Data structure + database operations | `models.py` |

**Rule:** Business logic should NEVER live in views. Views should be thin — validate input (via serializer), call a service, return the result.

### 4.9 Idempotency

**What it means:** Running the same operation twice produces the same result as running it once. If you accidentally trigger a scraping task twice, it shouldn't create duplicate products.

**In our code:**
- `bulk_create(ignore_conflicts=True)` — inserting a duplicate is silently ignored
- `unique_together` constraints prevent duplicate listings/reviews
- Content hashing on reviews detects duplicate submissions
- Meilisearch syncs use document IDs (updating the same ID is a no-op)

---

## 5. Backend — Django

### 5.1 Settings & Configuration

Settings live in `backend/whydud/settings/` with three files:

| File | Purpose | When Used |
|------|---------|-----------|
| `base.py` | Shared settings (installed apps, middleware, database schemas, REST config) | Always loaded first |
| `dev.py` | `DEBUG=True`, local database credentials, no HTTPS | Local development |
| `prod.py` | `DEBUG=False`, reads secrets from env vars, HTTPS headers, Sentry | Production server |

**Key settings from `base.py`:**

```python
# Database: PostgreSQL 16 + TimescaleDB
# search_path includes all 7 schemas: public, users, email_intel, scoring, tco, community, admin

# Auth: Custom User model (email-based, no username)
AUTH_USER_MODEL = 'accounts.User'

# REST Framework: Token auth, cursor pagination, wrapped responses
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.TokenAuthentication'],
    'DEFAULT_PAGINATION_CLASS': 'common.pagination.CursorPagination',
    'EXCEPTION_HANDLER': 'common.utils.custom_exception_handler',
}

# Encryption keys for email bodies and OAuth tokens
EMAIL_ENCRYPTION_KEY = env('EMAIL_ENCRYPTION_KEY')
OAUTH_ENCRYPTION_KEY = env('OAUTH_ENCRYPTION_KEY')
```

**Tuneable Values — `common/app_settings.py`:**

All runtime-configurable values are centralized here. Never hardcode values that might change.

```python
class ScrapingConfig:
    max_listing_pages = 5        # Safety cap: pages per category crawl
    proxy_ban_max_retries = 5    # Before marking proxy as permanently banned
    worker_id = env('CELERY_WORKER_ID', 'default')

class ScoringConfig:
    sentiment_half_life_days = 90     # Recent reviews matter more
    verified_purchase_weight = 2.0    # 2x weight for verified buyers
    flash_sale_penalty_threshold = 10 # >10 discount events = instability

class RewardsConfig:
    write_review = 20      # Points for writing a review
    connect_email = 50     # Points for connecting shopping email
    daily_cap = 100        # Max points per day
    monthly_cap = 500      # Max points per month
    points_per_rupee = 10  # 10 points = ₹1 gift card
```

### 5.2 Django Apps (13 Total)

Each app follows the same structure:

```
apps/{app_name}/
├── models.py          # Database models (tables)
├── views.py           # API endpoints
├── serializers.py     # Input validation + output formatting
├── urls.py            # URL routing for this app
├── tasks.py           # Celery background tasks
├── admin.py           # Django admin registration
├── services.py        # Business logic (optional)
└── migrations/        # Database schema changes
```

---

#### App 1: `accounts` — Identity & Authentication

**Purpose:** Everything about who the user is — registration, login, OAuth, shopping emails, payment methods, notification preferences.

**Database schema:** `users`

**Models (8):**

| Model | What It Stores | Key Fields |
|-------|---------------|------------|
| `User` | User identity (custom — uses email, not username) | email, name, role, subscription_tier, trust_score, has_whydud_email |
| `WhydudEmail` | The user's shopping email (1 per user) | username, domain (whyd.in/click/shop), total_emails_received, total_orders_detected |
| `OAuthConnection` | Google OAuth tokens (encrypted) | provider, access_token_encrypted, refresh_token_encrypted, token_expires_at |
| `PaymentMethod` | Bank cards (NO card numbers — just bank + variant) | bank_name, card_variant, card_network, emi_eligible |
| `ReservedUsername` | Blocked shopping email usernames | "admin", "support", brand names, system words |
| `Notification` | In-app notifications | type, title, body, action_url, is_read, email_sent |
| `NotificationPreference` | Per-user notification channel choices | price_drops: {in_app: true, email: true}, ... |
| `PurchasePreference` | Category-specific preferences (room size, budget, etc.) | category, preferences (JSON) |

**API Endpoints:**

```
POST /api/v1/auth/register/              → Create account + send OTP
POST /api/v1/auth/login/                 → Get auth token (lockout after 5 failures)
POST /api/v1/auth/logout/                → Delete token
POST /api/v1/auth/verify-email/          → Validate 6-digit OTP
POST /api/v1/auth/change-password/       → Requires current password
POST /api/v1/auth/forgot-password/       → Send reset email
POST /api/v1/auth/reset-password/        → Validate uid+token, reset
POST /api/v1/auth/oauth-exchange/        → Exchange OAuth code for token
GET  /api/v1/me/                         → Current user profile
GET  /api/v1/me/shopping-email/          → Get/create @whyd.* email
GET  /api/v1/me/payment-methods/         → List saved cards
DELETE /api/v1/me/account/               → Soft-delete (30-day grace)
GET  /api/v1/me/export/                  → Request GDPR data export
```

**Celery Tasks:**
- `send_verification_otp()` — Send 6-digit OTP email
- `send_password_reset_email()` — Send reset link
- `hard_delete_user()` — GDPR: permanently delete user data after 30-day grace
- `generate_data_export()` — Export all user data as JSON
- `create_notification()` — Create in-app + optional email notification

**Auth Flow (step by step):**

```
1. User submits email + password
2. POST /api/v1/auth/register/ → creates User, generates OTP, queues email
3. User enters OTP from email
4. POST /api/v1/auth/verify-email/ → marks email_verified=True
5. POST /api/v1/auth/login/ → returns { token: "abc123", user: {...} }
6. Frontend stores token in localStorage, sets whydud_auth cookie
7. All subsequent requests include: Authorization: Token abc123
8. On logout: DELETE token from server + clear localStorage + delete cookie
```

**OAuth Flow (Google):**

```
1. User clicks "Sign in with Google"
2. Browser → Google consent page
3. Google → /oauth/complete/ (Django AllAuth callback)
4. Backend creates one-time code, redirects → /auth/callback?code=XYZ
5. Frontend: POST /api/v1/auth/oauth-exchange/ with code
6. Backend validates code → returns { token, user }
```

---

#### App 2: `products` — Product Catalog

**Purpose:** The core product database — every product, its listings across marketplaces, sellers, categories, and brands.

**Database schema:** `public`

**Models (11):**

| Model | What It Stores | Key Fields |
|-------|---------------|------------|
| `Marketplace` | Marketplace metadata | slug ("amazon-in"), name, base_url, affiliate_tag |
| `Category` | Product categories (tree structure) | slug, name, parent (self-referencing FK), spec_schema (JSON), has_tco_model |
| `Brand` | Brand master data | slug, name, aliases (JSON), verified, logo_url |
| `Product` | Canonical product record | title, brand, category, dud_score, avg_rating, current_best_price, is_lightweight |
| `ProductListing` | Product on a specific marketplace | product, marketplace, seller, external_id (ASIN), current_price, in_stock |
| `Seller` | Marketplace seller | marketplace, external_seller_id, name, avg_rating, positive_pct |
| `BankCard` | Bank card reference data | bank_slug, card_variant, default_cashback_pct |
| `CompareSession` | User's comparison state | user, product_ids (JSON array of 2–4 UUIDs) |
| `RecentlyViewed` | Recently viewed products | user, product, viewed_at |
| `StockAlert` | Back-in-stock notification | user, product, listing, is_active |
| `CategoryPreferenceSchema` | Dynamic form schema per category | category, schema (JSON) |

**Critical concept — Product vs ProductListing:**

```
Product (canonical)                    ProductListing (per marketplace)
┌─────────────────────┐               ┌───────────────────────────────────┐
│ "iPhone 16 128GB"   │               │ Amazon India: ₹64,999 (in stock) │
│ Brand: Apple         │──── has ────→│ Flipkart:     ₹65,499 (in stock) │
│ Category: Smartphones│  many        │ Croma:        ₹67,000 (in stock) │
│ DudScore: 82         │  listings    │ Myntra:       — (not available)  │
│ Best price: ₹64,999  │               └───────────────────────────────────┘
└─────────────────────┘
```

One **Product** represents the real-world item. Multiple **ProductListings** represent that item on different marketplaces, each with its own price, seller, and stock status.

**`is_lightweight` flag:**

When a product is created from price tracker data (backfill pipeline), it only has basic info (title, price, one thumbnail image). It's marked `is_lightweight=True`. Once a marketplace spider enriches it with full details (specs, image gallery, seller info, reviews), it becomes `is_lightweight=False`.

---

#### App 3: `pricing` — Price Intelligence

**Purpose:** Price history tracking, price alerts, marketplace offers, affiliate click tracking, and the backfill pipeline staging table.

**Database schema:** `public` (snapshots are TimescaleDB hypertable)

**Models (4 + BackfillProduct):**

| Model | What It Stores | Key Fields |
|-------|---------------|------------|
| `PriceSnapshot` | One price data point (TimescaleDB hypertable) | time, listing, product, marketplace, price, mrp, in_stock, source |
| `MarketplaceOffer` | Bank card offers / coupons | marketplace, bank_slug, discount_type, discount_value, valid_until |
| `PriceAlert` | User's target price notification | user, product, target_price, is_triggered |
| `ClickEvent` | Affiliate link clicks | user, product, listing, source_page, affiliate_url, purchase_confirmed |
| `BackfillProduct` | Staging table for backfill pipeline | status, scrape_status, review_status, enrichment_priority, raw_price_data (JSON) |

**PriceSnapshot — The Time-Series Heart:**

Every time we scrape a product's price, we insert a row into `price_snapshots`. With 17M+ products, this table has hundreds of millions of rows. TimescaleDB makes range queries fast.

```sql
-- "What was this product's price over the last 90 days?"
SELECT time, price, marketplace_id
FROM price_snapshots
WHERE product_id = '...'
  AND time > NOW() - INTERVAL '90 days'
ORDER BY time;
-- TimescaleDB scans only the relevant time partitions
```

**Price format:** All prices are stored in **paisa** (integer). ₹64,999 = 6499900 paisa. This avoids floating-point precision issues with currency.

---

#### App 4: `reviews` — Review Intelligence

**Purpose:** Stores reviews (scraped from marketplaces + written on Whydud), detects fake reviews, manages reviewer profiles and gamification.

**Models (3):**

| Model | What It Stores | Key Fields |
|-------|---------------|------------|
| `Review` | Individual product review | product, rating, title, body, source (scraped/whydud), credibility_score, fraud_flags |
| `ReviewVote` | User upvote/downvote on a review | review, user, vote (+1 or -1) |
| `ReviewerProfile` | Gamification stats | user, total_reviews, reviewer_level (bronze/silver/gold/platinum), badges |

**Fraud Detection (`fraud_detection.py`):**

Rule-based system that flags suspicious reviews:

| Rule | What It Detects | Example |
|------|----------------|---------|
| Short 5-star | Short review + perfect rating | "Great product" (10 chars, 5 stars) |
| Review burst | Many same-rating reviews in one day | 15 five-star reviews in 24 hours |
| Duplicate content | Copy-paste reviews | Same review text on multiple products |
| New account pattern | Review from very new account | Account created yesterday, already reviewing |

Each rule adds to a `fraud_flags` JSON array. If total flags exceed a threshold, the review is flagged for moderation.

---

#### App 5: `scoring` — DudScore Algorithm

**Purpose:** Computes the proprietary DudScore (0–100) for every product. Also computes brand trust scores.

**Models (3):**

| Model | What It Stores |
|-------|---------------|
| `DudScoreConfig` | Versioned weight configuration (which factors matter how much) |
| `DudScoreHistory` | Historical score values (TimescaleDB hypertable) |
| `BrandTrustScore` | Brand-level trust aggregation (avg DudScore, fake review %, etc.) |

**DudScore Components:**

```
DudScore = (
    w_sentiment    × SentimentScore        +   # How positive are reviews? (recent = more weight)
    w_rating       × RatingQualityScore    +   # Are ratings balanced or suspicious?
    w_price_value  × PriceValueScore       +   # Is the price fair vs. history?
    w_credibility  × ReviewCredibilityScore +  # Are reviews from real, trusted users?
    w_stability    × PriceStabilityScore   +   # Is the price stable or manipulated?
    w_return       × ReturnSignalScore         # Are people returning this product?
) × FraudPenalty × ColdStartPenalty

Final score: 0 to 100
```

| Score Range | Label | Color |
|-------------|-------|-------|
| 80–100 | Excellent | Green |
| 60–79 | Good | Light Green |
| 40–59 | Average | Yellow |
| 20–39 | Below Average | Orange |
| 0–19 | Dud | Red |

**Brand Trust Score:** Aggregated across all products from a brand. Only brands with 5+ products are scored. Tier: excellent / good / average / poor / avoid.

---

#### App 6: `email_intel` — Purchase Intelligence

**Purpose:** The shopping email system. When users receive order confirmations, shipping updates, or refund notifications at their @whyd.* email, this app parses them into structured data.

**Database schema:** `email_intel` (isolated, encrypted at rest)

**Models (6):**

| Model | What It Stores |
|-------|---------------|
| `InboxEmail` | Raw email (body encrypted with AES-256-GCM) |
| `EmailSource` | Email account connections (whydud, gmail, outlook) |
| `ParsedOrder` | Extracted order data (product, price, seller, delivery date) |
| `RefundTracking` | Refund status + delay monitoring |
| `ReturnWindow` | Return deadline countdown + expiry alerts |
| `DetectedSubscription` | Auto-detected recurring charges (Netflix, Amazon Prime, etc.) |

**Security:** Email bodies are **always encrypted at rest**. The `body_text_encrypted` and `body_html_encrypted` fields store AES-256-GCM ciphertext. Decryption happens only when the user views the email.

---

#### App 7: `wishlists` — Price Tracking Lists

**Models:** `Wishlist` and `WishlistItem`. Users create named lists, add products, set target prices, and get alerts when the price drops.

#### App 8: `deals` — Blockbuster Deal Detection

**Model:** `Deal`. Automatically detects exceptional deals using rules:

| Deal Type | Detection Rule |
|-----------|---------------|
| Error price | Current < 50% of 30-day average |
| Lowest ever | Current < all-time lowest |
| Genuine discount | Current < 85% of MRP |
| Flash sale | 20% overnight drop |

#### App 9: `rewards` — Gamification

**Models:** `RewardPointsLedger`, `RewardBalance`, `GiftCardCatalog`, `GiftCardRedemption`

Users earn points for reviews (20 pts), connecting email (50 pts), referrals (30 pts), etc. Points convert to gift cards at 10 pts = ₹1.

**Anti-gaming measures:** 48-hour hold before awarding review points, minimum 20 characters per review, daily cap of 100 points, monthly cap of 500 points.

#### App 10: `discussions` — Product Q&A

**Models:** `DiscussionThread`, `DiscussionReply`, `DiscussionVote`

Per-product community threads with nested replies and voting. Thread types: question, experience, comparison, tip, alert.

#### App 11: `tco` — Total Cost of Ownership

**Models:** `TCOModel` (per-category cost formula), `CityReferenceData` (electricity tariffs, water hardness by city), `UserTCOProfile` (user's city, usage patterns)

The calculator is **dynamic** — each product category defines its own input schema (JSON) and cost formula. ACs need electricity tariff and usage hours. Water purifiers need water hardness and cartridge costs.

#### App 12: `search` — Meilisearch Integration

**Model:** `SearchLog` (analytics only — tracks queries, result counts, latency)

The actual search index lives in Meilisearch (separate service). Products are synced via Celery tasks after scraping.

#### App 13: `scraping` — Web Scraping

**Model:** `ScraperJob` (tracks spider runs — status, items scraped, errors)

The spiders themselves are in `spiders/` and are covered in [Section 7](#7-scraping-system).

---

### 5.3 Common Utilities

#### API Response Format

**Every API response is wrapped in a standard envelope:**

```json
// Success
{ "success": true, "data": { ... } }

// Error
{ "success": false, "error": { "code": "VALIDATION_ERROR", "message": "Email already exists" } }

// Paginated
{ "success": true, "data": [...], "pagination": { "next": "cursor_abc", "previous": null } }
```

This is enforced by `common/utils.py`:
- `success_response(data, status=200)` — wraps data
- `error_response(code, message, status=400)` — wraps error
- `custom_exception_handler()` — catches all DRF exceptions and wraps them

#### Rate Limiting

Token-bucket algorithm via Redis (`common/rate_limiting.py`):

| Endpoint | Anonymous | Registered | Premium |
|----------|-----------|------------|---------|
| Search | 10/min | 30/min | 60/min |
| Product view | 20/min | 60/min | 120/min |
| Write review | — | 3/day | 10/day |
| Global (all endpoints) | 300/min per IP | — | — |

**Fail-open design:** If Redis is unavailable, rate limiting is bypassed (never block users because Redis is down).

#### Permissions

- `IsConnectedUser` — Requires `has_whydud_email=True` (shopping email connected)
- `IsPremiumUser` — Requires `subscription_tier="premium"`

#### Encryption

`common/encryption.py` provides AES-256-GCM encryption:
- Used for: email bodies, OAuth tokens, gift card codes
- Two separate keys: `EMAIL_ENCRYPTION_KEY` and `OAUTH_ENCRYPTION_KEY`

---

### 5.4 Celery — Background Task System

#### What Celery Does (for beginners)

Imagine a restaurant. The waiter (Django view) takes your order and gives you a ticket number. The kitchen (Celery worker) cooks the food in the background. You don't stand at the counter waiting — you sit down and get notified when it's ready.

Celery works the same way:
1. A user action triggers a task (e.g., "scrape this product")
2. The task is placed in a Redis queue
3. A Celery worker picks it up and processes it
4. The result is stored in the database

#### Queue Architecture

| Queue | Purpose | Workers |
|-------|---------|---------|
| `default` | General tasks (notifications, rewards, data export) | 2 on main server |
| `scraping` | Marketplace spiders + backfill enrichment | 4 on main + 2 on worker nodes |
| `email` | All outbound emails (via Resend API) | 2 on dedicated email worker |
| `scoring` | DudScore calculation, fraud detection, deal detection | Shares `default` workers |
| `alerts` | Price/return/refund alerts (time-critical) | Shares `default` workers |

#### Beat Schedule (Recurring Tasks)

Celery Beat is a scheduler that triggers tasks on a cron-like schedule:

| Task | Frequency | What It Does |
|------|-----------|-------------|
| Amazon spider | Every 6 hours | Scrape Amazon.in for product updates |
| Flipkart spider | Every 6 hours (staggered) | Scrape Flipkart for product updates |
| Other marketplaces | Daily (staggered) | Myntra, Croma, Nykaa, etc. |
| Deal detection | Every 30 minutes | Find error prices, lowest-ever, flash sales |
| Price alerts | Every 4 hours | Check if any user's target price has been hit |
| Enrichment batch | Every 15 minutes | Process pending lightweight products |
| Review completion | Every 15 minutes | Check if review scraping finished |
| DudScore full recalc | Monthly | Recalculate all product scores |
| Stale cleanup | Hourly | Reset stuck enrichment tasks |

#### Discord Notifications

Task success/failure/retry events are sent to Discord via webhook. This provides real-time monitoring without checking logs.

---

### 5.5 Database Design

#### Seven PostgreSQL Schemas

Instead of putting all tables in the default `public` schema, Whydud uses 7 schemas for logical isolation:

| Schema | Tables | Why Isolated |
|--------|--------|-------------|
| `public` | products, listings, sellers, reviews, deals, price_snapshots, search_log, scraper_jobs | Core product data — most queried |
| `users` | users, shopping_emails, payment_methods, notifications, wishlists, rewards, alerts | User data — GDPR, privacy |
| `email_intel` | inbox_emails, parsed_orders, refund_tracking, return_windows, subscriptions | Encrypted email data — highest security |
| `scoring` | dudscore_config, dudscore_history, brand_trust_scores | Scoring engine — isolated for weight tuning |
| `tco` | tco_models, city_reference_data | Calculator data — changes rarely |
| `community` | discussions, replies, votes | Community content — moderation |
| `admin` | audit_logs, moderation_queue, scraper_runs, site_config | Admin operations |

**In Django model Meta:**
```python
class InboxEmail(models.Model):
    class Meta:
        db_table = 'email_intel"."inbox_emails'  # Note the escaped quotes
```

#### TimescaleDB Hypertables

Two tables use TimescaleDB:

1. **`price_snapshots`** — Millions of price data points, partitioned by `time`
2. **`dudscore_history`** — Historical DudScore values, partitioned by `time`

**Migration pattern (critical — easy to get wrong):**

```python
# TimescaleDB DDL CANNOT run inside a transaction
# psycopg3 wraps every execute() in an implicit transaction
# Solution: set raw_conn.autocommit = True

def forward(apps, schema_editor):
    raw_conn = schema_editor.connection.connection
    raw_conn.autocommit = True
    try:
        with raw_conn.cursor() as cur:
            cur.execute("SELECT create_hypertable('price_snapshots', 'time', ...)")
    finally:
        raw_conn.autocommit = False
```

See `pricing/migrations/0002_timescaledb_setup.py` for reference.

---

## 6. Frontend — Next.js

### 6.1 App Router & Route Groups

Next.js 15 uses the **App Router** — every folder under `src/app/` maps to a URL. Route groups (folders in parentheses) organize pages without affecting the URL.

#### Route Map

```
src/app/
├── (public)/                    # No auth required
│   ├── page.tsx                 # / (homepage)
│   ├── search/page.tsx          # /search?q=...
│   ├── product/[slug]/page.tsx  # /product/iphone-16-128gb
│   ├── compare/page.tsx         # /compare?slugs=a,b,c
│   ├── deals/page.tsx           # /deals
│   ├── categories/[slug]/       # /categories/smartphones
│   ├── seller/[slug]/           # /seller/appario-retail
│   ├── brand/[slug]/            # /brand/apple
│   ├── leaderboard/             # /leaderboard (top reviewers)
│   └── lookup/                  # /lookup?url=... (marketplace URL → product)
│
├── (auth)/                      # Login/register pages
│   ├── login/page.tsx           # /login
│   ├── register/page.tsx        # /register (3-step flow)
│   └── auth/callback/page.tsx   # /auth/callback (OAuth)
│
└── (dashboard)/                 # Auth required (middleware-protected)
    ├── dashboard/page.tsx       # /dashboard (spending overview)
    ├── inbox/page.tsx           # /inbox (shopping emails)
    ├── wishlists/page.tsx       # /wishlists
    ├── alerts/page.tsx          # /alerts (price + stock)
    ├── my-reviews/page.tsx      # /my-reviews
    ├── rewards/page.tsx         # /rewards
    ├── settings/page.tsx        # /settings (6 tabs)
    ├── purchases/page.tsx       # /purchases
    ├── refunds/page.tsx         # /refunds
    ├── subscriptions/page.tsx   # /subscriptions
    └── notifications/page.tsx   # /notifications (preferences)
```

#### Server Components vs Client Components

**Server Components** (default — no `"use client"` directive):
- Run on the server at request time
- Can `await` data fetching directly in the component
- Cannot use `useState`, `useEffect`, `onClick`, etc.
- Good for: pages that display data, SEO-critical content

**Client Components** (add `"use client"` at top of file):
- Run in the browser
- Can use React hooks and event handlers
- Used for: forms, interactive UI, real-time updates

**Pattern example:**

```tsx
// Server Component (default) — fetches data on the server
export default async function ProductPage({ params }) {
  const product = await productsApi.getDetail(params.slug);
  return <ProductDetail product={product} />;
}

// Client Component — needs interactivity
"use client";
export function AddToCompareButton({ product }) {
  const { addToCompare } = useCompare();
  return <button onClick={() => addToCompare(product)}>Compare</button>;
}
```

---

### 6.2 Authentication System

#### Architecture

```
┌─────────────────────────────────────────────────────────┐
│ AuthContext (wraps entire app)                           │
│                                                          │
│ State: { user, isLoading, isAuthenticated }              │
│ Methods: login(), logout(), refreshUser()                │
│                                                          │
│ Token Storage:                                           │
│   localStorage → "whydud_auth_token" = "abc123"          │
│   Cookie → "whydud_auth" = "1" (for middleware)          │
└─────────────────────────────────────────────────────────┘
         │                           │
         ▼                           ▼
┌──────────────┐           ┌──────────────────┐
│ API Client   │           │ Next.js Middleware│
│ Adds header: │           │ Checks cookie:   │
│ Authorization│           │ whydud_auth=1?   │
│ : Token abc  │           │ No → redirect    │
└──────────────┘           │ to /login        │
                           └──────────────────┘
```

#### Step-by-Step Login Flow

1. User enters email + password on `/login`
2. Frontend calls `authApi.login(email, password)`
3. Backend validates credentials → returns `{ token: "abc123", user: {...} }`
4. Frontend calls `login(token, user)` from `useAuth()`:
   - Stores token in `localStorage`
   - Sets `whydud_auth=1` cookie (for middleware)
   - Sets `user` in React context
5. User is redirected to `/dashboard`
6. All subsequent API calls include `Authorization: Token abc123` header

#### Auto-401 Handling

If any API call returns HTTP 401 (token expired/invalid):
1. The API client fires a `whydud:auth-expired` browser event
2. `AuthContext` listens for this event
3. Clears token from localStorage, removes cookie
4. Sets `user = null`
5. User sees login page on next navigation

---

### 6.3 API Client Layer

#### How It Works

Every API call goes through `src/lib/api/client.ts`. This client handles:

1. **Base URL resolution** — Server-side uses `INTERNAL_API_URL`, client-side uses Next.js rewrites
2. **Token injection** — Reads from localStorage, adds `Authorization` header
3. **Case conversion** — JavaScript uses `camelCase`, Python uses `snake_case`
   - Request body: `{ targetPrice }` → `{ target_price }`
   - Response body: `{ target_price }` → `{ targetPrice }`
4. **Numeric coercion** — Django's `Decimal` serializes as `"3.92"` (string) → converted to `3.92` (number)
5. **Error handling** — Non-200 responses wrapped in `{ success: false, error: {...} }`

#### Domain API Modules

Each domain (products, auth, reviews, etc.) has its own module in `src/lib/api/`:

```typescript
// src/lib/api/products.ts
export const productsApi = {
  list: (params?) => apiClient.get('/api/v1/products/', { params }),
  getDetail: (slug) => apiClient.get(`/api/v1/products/${slug}/`),
  getPriceHistory: (slug, days = 90) => apiClient.get(`/api/v1/products/${slug}/price-history/`, { params: { days } }),
  getReviews: (slug, params?) => apiClient.get(`/api/v1/products/${slug}/reviews/`, { params }),
  compare: (slugs) => apiClient.get('/api/v1/products/compare/', { params: { slugs: slugs.join(',') } }),
};
```

**All 15+ API modules:**
- `auth.ts` — Login, register, OAuth, shopping email, card vault
- `products.ts` — Product CRUD, price history, reviews, discussions, similar/alternatives
- `search.ts` — Search, autocomplete, ad-hoc scraping
- `reviews.ts` — Submit, edit, delete reviews, reviewer profiles, leaderboard
- `inbox.ts` — Email inbox, purchases, refunds, return windows, subscriptions
- `wishlists.ts` — Wishlist CRUD, add/remove items
- `alerts.ts` — Price alerts, stock alerts
- `rewards.ts` — Balance, history, gift cards, redemptions
- `discussions.ts` — Thread CRUD, replies, voting
- `tco.ts` — Calculator, city data, profiles
- `brands.ts` — Brand trust scores, leaderboard
- `sellers.ts` — Seller profiles, products, reviews
- `notifications.ts` — Notification preferences
- `trending.ts` — Trending/rising/price-dropping products

---

### 6.4 Components

#### Component Organization

Components are organized by domain, not by type:

```
src/components/
├── ui/           # 19 base components (shadcn/ui + Radix)
│                 # button, card, dialog, input, select, skeleton, tabs, badge, etc.
│
├── layout/       # Structural components
│   ├── Header.tsx         # Sticky header: logo, search bar, auth menu
│   ├── Footer.tsx         # Global footer with links
│   ├── Sidebar.tsx        # Dashboard sidebar navigation (desktop)
│   └── MobileNav.tsx      # Mobile hamburger menu
│
├── product/      # Product-specific (15+ components)
│   ├── product-card.tsx             # Product summary card
│   ├── price-chart.tsx              # Recharts price history chart
│   ├── dud-score-gauge.tsx          # Circular score display
│   ├── category-score-bars.tsx      # Score component breakdown
│   ├── cross-platform-price-panel.tsx # Price across marketplaces
│   ├── marketplace-prices.tsx       # Individual listing prices
│   ├── price-alert-button.tsx       # Set price alert
│   ├── add-to-compare-button.tsx    # Add to compare tray
│   ├── share-button.tsx             # Social sharing
│   ├── brand-trust-badge.tsx        # Brand trust display
│   └── SimilarProducts.tsx          # Related product carousel
│
├── reviews/      # Review display and submission
├── search/       # Search bar, filters, sort dropdown
├── compare/      # Compare table, tray, selector
├── dashboard/    # Charts, stat cards, breakdowns
├── inbox/        # Email list, reader, category filter
├── tco/          # TCO calculator, breakdown, comparison
├── deals/        # Deal cards, filters
├── wishlists/    # Wishlist selector, item cards
├── rewards/      # Balance, catalog, redemption
├── discussions/  # Thread list, reply form, voting
├── notifications/ # Bell icon, preference toggles
├── payments/     # Card vault, add card form
└── settings/     # Account info, password, deletion
```

#### Key Component Patterns

**Loading skeleton:** Every data component has a loading state:
```tsx
if (isLoading) return <Skeleton className="h-48 w-full rounded-lg" />;
```

**Error state:** Every data component handles errors:
```tsx
if (error) return <div className="text-red-500">{error}</div>;
```

**Empty state:** Every list handles "no data":
```tsx
if (items.length === 0) return <p className="text-slate-500">No items found.</p>;
```

---

### 6.5 State Management

Whydud uses minimal global state — no Redux or MobX.

| State Type | Tool | What It Manages |
|------------|------|----------------|
| Auth state | `AuthContext` (React Context) | Current user, token, login/logout |
| Compare tray | `CompareContext` (React Context + localStorage) | Up to 4 products for comparison |
| Local state | `useState` | Form inputs, loading flags, UI toggles |
| Server state | Next.js SSR | Page data fetched on the server |

**Why so minimal?** Most data lives on the backend. The frontend fetches it via API calls. Only auth and compare state need to persist across pages.

---

### 6.6 Type System

TypeScript strict mode (`"strict": true`) is enforced. No `any` types allowed.

**Key types in `src/types/`:**

```typescript
// Product types
ProductSummary       // Card view (title, price, rating, image)
ProductDetail        // Full product page (specs, listings, score)
ProductListing       // One marketplace listing
PricePoint           // {time, price, marketplace}
Review               // {rating, title, body, credibility, fraudFlags}
Deal                 // {dealType, currentPrice, discountPct, confidence}

// User types
User                 // {email, name, role, subscriptionTier, hasWhydudEmail}
WhydudEmail          // {username, domain, emailAddress}
PaymentMethod        // {bankName, cardVariant, emiEligible}
InboxEmail           // {subject, category, isRead, isStarred}
ParsedOrder          // {orderId, marketplace, productName, pricePaid}

// API envelope types
ApiSuccess<T>        // {success: true, data: T}
ApiError             // {success: false, error: {code, message}}
ApiResponse<T>       // ApiSuccess<T> | ApiError
PaginatedApiResponse<T> // {success: true, data: T[], pagination: {next, previous}}
```

---

### 6.7 Styling & Design System

#### Color Palette

```
Primary Orange:  #F97316     ← CTAs, highlights, active states
Teal Accent:     #4DB6AC     ← Logo accent, DudScore gauge, secondary elements
Navy Text:       #1E293B     ← Headings, primary text
Star Yellow:     #FBBF24     ← Star ratings
Success Green:   #16A34A     ← Good scores, price drops
Danger Red:      #DC2626     ← Bad scores, price increases
Background:      #F8FAFC     ← Page background (very light gray)
Border:          #E2E8F0     ← Card borders, dividers
Text Secondary:  #64748B     ← Descriptions, timestamps
```

**Rule:** Never use default Tailwind colors (blue-500, indigo-600, etc.). Always use the Whydud palette.

#### Typography

- **Font:** Inter only (loaded via Google Fonts)
- **Headings:** `font-semibold` or `font-bold`
- **Body:** `font-normal` or `font-medium`
- **Code/prices:** JetBrains Mono (monospace)

#### Component Patterns

```
Card:    bg-white rounded-lg border border-slate-200 shadow-sm hover:shadow-md transition-shadow
Button:  Tailwind utilities + hover + focus-visible + active states
Input:   rounded-lg border focus:ring-2 focus:ring-orange-500
Badge:   rounded-full px-2 py-0.5 text-xs font-medium
```

#### Responsive Design

Mobile-first approach using Tailwind breakpoints:
```
text-sm md:text-base lg:text-lg        ← Font size scales up
grid-cols-1 md:grid-cols-2 lg:grid-cols-4  ← Grid columns increase
px-4 md:px-6 lg:px-12                  ← Padding increases
```

---

## 7. Scraping System

### 7.1 Spider Architecture

#### For Beginners: What a Spider Does

A "spider" is a program that automatically visits web pages, reads the data on them, and saves it to our database. Imagine sending a very fast, tireless assistant to every product page on Amazon.in, writing down the price, rating, and specs of each product.

#### Two-Phase Architecture

Scraping happens in two phases to balance speed and accuracy:

```
PHASE 1: Listing Pages (fast, cheap)          PHASE 2: Product Details (slow, accurate)
┌──────────────────────────────┐               ┌────────────────────────────────────┐
│ Visit: amazon.in/s?k=phones  │               │ Visit: amazon.in/dp/B0CX23GFMV    │
│ Method: Plain HTTP            │               │ Method: Playwright (real browser)   │
│ Speed: 100+ pages/minute     │               │ Speed: 3–5 seconds per page         │
│ Cost: Nearly free            │──────────────→│ Cost: Proxy bandwidth ($0.70/GB)    │
│ Gets: Product links, titles  │               │ Gets: Full specs, prices, images,   │
│ NO JavaScript needed         │               │       seller info, offers, reviews  │
└──────────────────────────────┘               └────────────────────────────────────┘
```

**Why two phases?**
- Listing pages (search results) are lightweight — basic HTML, no JavaScript needed
- Product detail pages require JavaScript execution for dynamic content (prices, offers, variants)
- Running Playwright (a real browser) is 50–100x more expensive than plain HTTP
- Phase 1 identifies which products to scrape. Phase 2 gets the details.

**Amazon:** Phase 1 = HTTP, Phase 2 = Playwright
**Flipkart:** Phase 1 = Playwright (dynamic listing), Phase 2 = Try JSON-LD first, fallback to Playwright

#### Spider Files

| File | Marketplace | Phase 1 | Phase 2 |
|------|------------|---------|---------|
| `amazon_spider.py` | Amazon.in | HTTP listings | Playwright details |
| `flipkart_spider.py` | Flipkart | Playwright listings | JSON-LD → Playwright |
| `amazon_review_spider.py` | Amazon reviews | — | Playwright (review pages) |
| `flipkart_review_spider.py` | Flipkart reviews | — | Playwright + JS extraction |
| + 10 more | Myntra, Croma, Nykaa, etc. | Varies | Varies |

#### Base Spider (`base_spider.py`)

All spiders inherit from `BaseWhydudSpider`, which provides:

**Anti-detection measures:**
- **User-Agent rotation:** 25+ realistic browser UAs (Chrome 131, Firefox 133, Edge 131)
- **India-specific headers:** `Accept-Language: en-IN`, Hindi fallback
- **Client Hints:** `Sec-CH-UA` headers that match the User-Agent
- **Random viewport:** Locked per spider session from 7 desktop/mobile sizes
- **Download delay:** 3s base + random jitter (actual: 1.5–4.5s per request)
- **Stealth patches:** Removes `navigator.webdriver` flag, emulates browser plugins

#### Item Definitions (`items.py`)

Two Scrapy item types:

**ProductItem:**
```python
marketplace_slug    # "amazon-in"
external_id         # "B0CX23GFMV" (ASIN for Amazon, PID for Flipkart)
url                 # Full product URL
title               # Product name
price               # Current price in PAISA (integer)
mrp                 # Maximum retail price in PAISA
rating              # 0–5
review_count        # Total reviews
images              # List of image URLs
specs               # Dict of spec name → value
seller_name         # "Appario Retail Private Ltd"
in_stock            # Boolean
category_slug       # For category mapping
# ... and 15+ more fields
```

**ReviewItem:**
```python
marketplace_slug    # "amazon-in"
product_external_id # "B0CX23GFMV"
rating              # 1–5
title               # Review title
body                # Review text
reviewer_name       # "Akash Kumar"
is_verified_purchase # Boolean
helpful_votes       # Integer
review_date         # Date string
```

---

### 7.2 Middlewares — Proxy & Retry

#### For Beginners: Why Proxies?

When you visit Amazon.in from your home, Amazon sees your IP address. If you visit 10,000 product pages in an hour, Amazon blocks you — that's clearly not a normal human.

Proxies are intermediary servers that make requests on your behalf. Each request appears to come from a different location. We use "residential proxies" from DataImpulse — they use real home internet connections, making our requests indistinguishable from real users.

#### Proxy System (`middlewares.py`)

**ProxyPool:** Manages a pool of proxy servers. Round-robin rotation with health tracking.

```
Request → ProxyPool → Pick healthy proxy → Route through proxy → Amazon server
                                                                      ↓
If 403/CAPTCHA → Mark proxy as banned → Exponential backoff → Try again later
```

**Two proxy modes:**

| Mode | How It Works | When Used |
|------|-------------|-----------|
| **Rotating** (DataImpulse) | One gateway URL, different IP per connection | Default for most scraping |
| **Static** (WebShare etc.) | Multiple fixed-IP proxies | When sticky sessions are critical |

**Session Stickiness:**

For product detail pages, we need multiple requests to the same site to appear as one user session. Session stickiness makes all requests with the same "session key" route through the same proxy IP for 10–30 minutes:

```
Product A, request 1 → IP 182.16.x.x (session key: "ab3f8c21")
Product A, request 2 → IP 182.16.x.x (same session key, same IP)
Product B, request 1 → IP 103.47.y.y (new session key: "7d2e1f09")
```

**BackoffRetryMiddleware:** When a request fails, wait before retrying: 5s → 10s → 20s → 40s → 60s (exponential, with 30% random jitter).

---

### 7.3 Pipelines — Data Processing

When a spider yields an item (product or review), it passes through a 7-stage pipeline:

```
Spider yields ProductItem
         │
         ▼
┌─ Stage 100: ValidationPipeline ──────────────────────────────┐
│  Drop items missing: marketplace_slug, external_id, url, title│
└──────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ Stage 150: ReviewValidationPipeline ────────────────────────┐
│  Drop reviews missing: marketplace_slug, product_id, rating, body │
│  Minimum body length: 5 characters                            │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ Stage 200: NormalizationPipeline ───────────────────────────┐
│  Clean title (collapse whitespace)                            │
│  Clean brand ("Visit the Apple Store" → "Apple")              │
│  Deduplicate images, remove empty specs                       │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ Stage 400: ProductPipeline (Core) ──────────────────────────┐
│  1. Resolve marketplace (slug → Marketplace object)           │
│  2. Find/create Seller                                        │
│  3. Resolve Brand + Category (regex + alias mapping)          │
│  4. Find existing ProductListing by (marketplace, external_id)│
│     └─ Found? Update it.                                     │
│     └─ New? Run 4-step matching engine → canonical Product   │
│  5. Insert PriceSnapshot (raw SQL for hypertable)             │
│  6. Update Product.current_best_price                         │
│  7. Close backfill loop (if enrichment)                       │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ Stage 450: ReviewPersistencePipeline ───────────────────────┐
│  Find ProductListing by external_id                           │
│  Dedup via external_review_id + marketplace                   │
│  Create Review with content_hash (fraud detection)            │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ Stage 500: MeilisearchIndexPipeline ────────────────────────┐
│  Collect product IDs → batch sync to Meilisearch on close     │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ Stage 600: SpiderStatsUpdatePipeline ───────────────────────┐
│  Update ScraperJob.items_scraped + items_failed               │
└──────────────────────────────────────────────────────────────┘
```

**The Backfill Loop Hook (`_close_backfill_loop`):**

This is the critical integration point between the scraping pipeline and the backfill system. When a spider scrapes a product that was created as a lightweight record:

1. Find matching `BackfillProduct` by `(marketplace_slug, external_id)`
2. Update: `scrape_status = 'scraped'`, link to `product_listing`
3. If `review_status = 'pending'`: queue review spider
4. Set `Product.is_lightweight = False` (now fully enriched)

**Safety:** This hook is wrapped in `try/except` — it NEVER crashes the main pipeline.

---

### 7.4 Task Orchestration

Spiders are launched via Celery tasks, which spawn subprocesses:

```
Celery Beat Schedule
       │
       ▼
run_marketplace_spider(marketplace_slug)    ← Celery task
       │
       ▼
Creates ScraperJob (status: RUNNING)
       │
       ▼
subprocess: python -m apps.scraping.runner amazon_spider --job-id UUID
       │
       ▼
Scrapy CrawlerProcess starts
       │
       ├── Phase 1: HTTP listing pages → yields ProductItems
       │         │
       │         ▼
       ├── Phase 2: Playwright detail pages → yields ProductItems
       │         │
       │         ▼
       └── Items pass through 7-stage pipeline → Database
       │
       ▼
Spider closes → ScraperJob (status: COMPLETED)
       │
       ▼
Chain: sync_products_to_meilisearch → check_price_alerts → run_review_spider
```

**Why subprocess?** Scrapy's Twisted reactor can only start once per Python process. If a Celery worker tries to start a spider directly, the second spider would crash. Running each spider in a subprocess avoids this.

---

## 8. Backfill Pipeline

### 8.1 The Five Phases

The backfill pipeline discovers products from **external price tracker sites** (BuyHatke, PriceHistory.app, PriceBefore.com), harvests their historical price data, and creates records in our database — all **without scraping the actual marketplace.**

```
Phase 1: DISCOVER                Phase 2: FETCH HISTORY           Phase 3: CREATE + INJECT
┌──────────────────┐            ┌────────────────────┐            ┌────────────────────────┐
│ Crawl tracker    │            │ For each product,  │            │ From tracker data      │
│ sitemaps:        │            │ call tracker API   │            │ alone, create:         │
│ - PriceHistory   │────────→  │ to get 1-5 years   │────────→  │ 1. Product record      │
│ - BuyHatke       │            │ of price history.  │            │ 2. ProductListing      │
│ - PriceBefore    │            │                    │            │ 3. Bulk INSERT all     │
│                  │            │ Store as JSONB     │            │    price_snapshots     │
│ Result: ASIN,    │            │ (200-500 points    │            │                        │
│ title, thumbnail │            │ per product)       │            │ PRODUCT IS LIVE NOW    │
└──────────────────┘            └────────────────────┘            └────────────┬───────────┘
                                                                               │
                                                                Phase 4: ENRICH (background)
                                                                ┌────────────────────────┐
                                                                │ Scrape marketplace for │
                                                                │ full details:          │
                                                                │                        │
                                                                │ P0-P1: Playwright      │
                                                                │ P2-P3: curl_cffi       │
                                                                │                        │
                                                                │ Result: images, specs, │
                                                                │ seller, variants       │
                                                                └────────────┬───────────┘
                                                                             │
                                                                Phase 5: REVIEWS + DUDSCORE
                                                                ┌────────────────────────┐
                                                                │ Top 100K products:     │
                                                                │ 1. Scrape 10-30 reviews│
                                                                │ 2. Run fraud detection │
                                                                │ 3. Calculate DudScore  │
                                                                │                        │
                                                                │ Product is now COMPLETE│
                                                                └────────────────────────┘
```

**Key insight:** Phases 1–3 are **free and fast** (tracker APIs, no proxy cost). After Phase 3, products are live on the site with price charts. Phases 4–5 run in the background and can take days/weeks for millions of products.

---

### 8.2 Lightweight Products

A lightweight product is created from tracker data alone — no marketplace scraping needed:

**What it has (from tracker):**
- Title: "Apple iPhone 16 (Pink, 128 GB)"
- One thumbnail image
- Current price: ₹64,999
- Price history: 200–500 data points spanning months/years
- External ID: "B0CX23GFMV" (ASIN)
- Marketplace URL

**What it's missing (needs enrichment):**
- Full image gallery (6–8 high-res images)
- Specs / technical details
- Seller name + rating
- Review count + average rating
- Variant options (color, storage)
- DudScore (needs reviews)

**On the website:** Lightweight products show a price chart, basic info, and an info banner ("We're fetching full details..."). Empty sections (specs, reviews) are hidden — the page doesn't look broken.

**`Product.is_lightweight = True`** until enrichment completes, then it becomes `False`.

---

### 8.3 Enrichment System

Enrichment fills in the missing data by scraping the actual marketplace.

#### Priority Tiers

| Priority | Method | Who Gets This | Speed |
|----------|--------|--------------|-------|
| **P0** | Playwright | User visited the product page (on-demand) | Immediate |
| **P1** | Playwright | Top brands (Apple, Samsung, etc.) + popular categories | Next 15-min batch |
| **P2** | curl_cffi (→ escalate) | Medium-value products | Next 15-min batch |
| **P3** | curl_cffi only | Long-tail products | Next 15-min batch |

#### curl_cffi vs Playwright

| | curl_cffi | Playwright |
|--|-----------|-----------|
| **What it is** | HTTP client with TLS fingerprint spoofing | Real browser (Chromium) |
| **Memory** | ~5MB per request | ~300MB per browser context |
| **Speed** | 0.5–1s per request | 3–10s per page |
| **Success rate** | ~55% on Amazon | ~95% |
| **Can get** | Title, price, rating, 1 image, specs | Everything (images, variants, offers) |
| **Cannot get** | Full image gallery, bank offers | — |
| **Cost** | Very low bandwidth | High bandwidth |

**Escalation:** If curl_cffi fails 3 times for a product, it escalates to Playwright.

#### Management Command

All backfill operations are managed through one CLI command:

```bash
# Check current status
python manage.py backfill_prices status

# Phase 1: Discover products from trackers
python manage.py backfill_prices discover --source pricehistory --batch 5000

# Phase 2: Fetch price history
python manage.py backfill_prices fetch-history --batch 5000

# Phase 3: Create lightweight records + inject prices
python manage.py backfill_prices create-lightweight --batch 1000

# Phase 4: Run enrichment
python manage.py backfill_prices enrich --batch 100

# Assign priorities
python manage.py backfill_prices assign-priorities
```

---

### 8.4 Price Injection

Historical price data is injected into the `price_snapshots` hypertable using PostgreSQL's COPY protocol:

```python
# fast_inject.py
def copy_inject_snapshots(rows):
    """Bulk-insert price snapshots using COPY (5-10x faster than INSERT)."""
    raw_conn = connection.connection
    with raw_conn.cursor() as cur:
        with cur.copy("COPY price_snapshots (time, listing_id, product_id, ...) FROM STDIN") as copy:
            for row in rows:
                copy.write_row(row)
```

**Why COPY?** For millions of price history rows, regular INSERT is too slow. COPY bypasses per-row parsing and inserts data at near-network speed.

**Price conversion:** Tracker data stores prices in paisa. PriceSnapshot stores in rupees as `Decimal(12,2)`. When injecting: divide paisa by 100.

---

## 9. Infrastructure & Deployment

### 9.1 Docker Compose

Production runs 10 services in Docker Compose:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Compose                           │
│                                                                  │
│  ┌──────┐  ┌──────────┐  ┌───────────┐  ┌──────────────────┐   │
│  │Caddy │→│  Django   │  │ Next.js   │  │   PostgreSQL     │   │
│  │(proxy)│  │ (backend)│  │(frontend) │  │ + TimescaleDB    │   │
│  └──────┘  └──────────┘  └───────────┘  └──────────────────┘   │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Celery   │  │ Celery   │  │  Email   │  │    Redis     │   │
│  │ Worker   │  │  Beat    │  │ Worker   │  │              │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
│                                                                  │
│  ┌──────────┐  ┌──────────┐                                    │
│  │Meilisearch│ │ Flower   │                                    │
│  │          │  │(monitor) │                                    │
│  └──────────┘  └──────────┘                                    │
└─────────────────────────────────────────────────────────────────┘
```

| Service | RAM | Purpose |
|---------|-----|---------|
| Caddy | 64MB | Reverse proxy, auto-SSL, routing |
| PostgreSQL + TimescaleDB | 2GB | Primary database |
| Redis | 512MB | Cache, Celery broker, sessions |
| Meilisearch | 1GB | Product search engine |
| Django (Gunicorn) | 1GB | Backend API (3 workers) |
| Celery Worker | 2GB | Background tasks (4 concurrent) |
| Celery Beat | 256MB | Task scheduler |
| Email Worker | 512MB | Email processing (2 concurrent) |
| Flower | 128MB | Celery monitoring UI |
| Next.js | 512MB | Frontend server |

---

### 9.2 Caddy Reverse Proxy

Caddy routes all traffic:

```
Internet → Caddy → /api/*        → Django backend :8000
                 → /admin/*      → Django backend :8000
                 → /webhooks/*   → Django backend :8000
                 → /flower/*     → Flower :5555
                 → /static/*     → File server
                 → everything else → Next.js :3000
```

**Auto-SSL:** Caddy automatically obtains and renews Let's Encrypt HTTPS certificates. No manual cert management needed.

**Marketplace wildcards:** `whydud.amazon.in/*` redirects to `whydud.com/lookup?url=...`

---

### 9.3 Worker Nodes & WireGuard

#### For Beginners: What a Worker Node Is

The main server handles everything — database, web server, task processing. But scraping and enrichment are compute-heavy (running real browsers). Worker nodes are additional cheap servers that only run enrichment tasks, taking load off the main server.

#### Architecture

```
Main Server (Contabo VPS, 16GB RAM, ₹6,000/month)
┌──────────────────────────────────────────────────┐
│ All services: DB, Redis, Web, Beat, Workers, etc.│
│ WireGuard IP: 10.8.0.1                          │
└────────────────────┬─────────────────────────────┘
                     │ WireGuard VPN tunnel (UDP:51820)
          ┌──────────┴──────────┐
          │                     │
┌─────────┴────────┐  ┌────────┴─────────┐
│ Worker Node 1    │  │ Worker Node 2    │
│ (OCI Free, 1GB)  │  │ (OCI Free, 1GB)  │
│ WG IP: 10.8.0.3  │  │ WG IP: 10.8.0.4  │
│ Queue: scraping   │  │ Queue: scraping   │
│ 2 concurrent      │  │ 2 concurrent      │
└──────────────────┘  └──────────────────┘
```

**WireGuard** creates an encrypted tunnel between the main server and worker nodes. Workers access PostgreSQL and Redis through the VPN (10.8.0.x network), not over the public internet.

**Worker provisioning** is automated via `cloud-init-worker.yml` — a new OCI instance boots, installs Docker and WireGuard, clones the repo, and starts processing tasks automatically.

**Worker Dockerfile (`worker-light.Dockerfile`):** Stripped of Playwright and spaCy (only curl_cffi) to fit in 1GB RAM. These workers handle P2/P3 enrichment (HTTP-only).

---

## 10. Security

### CRITICAL RULES (Never Violate)

| Rule | Why |
|------|-----|
| **NEVER store card numbers** | Legal liability. We store: bank name + variant only |
| **NEVER persist raw email bodies** | Privacy. All email bodies encrypted with AES-256-GCM |
| **OAuth tokens encrypted at rest** | Separate encryption key from email key |
| **Passwords bcrypt cost 12** | Industry standard for password hashing |
| **HTTP-only Secure SameSite=Strict cookies** | Prevents XSS and CSRF token theft |
| **CSRF on all mutations** | Prevents cross-site request forgery |
| **HTML sanitization with nh3** | Prevents XSS from email content |
| **External images proxied** | Prevents tracking pixels in emails |

### Authentication & Authorization

```
Layer 1: Next.js Middleware     → Checks whydud_auth cookie (edge-level, fast)
Layer 2: DRF TokenAuth          → Validates token on every API request
Layer 3: DRF Permissions        → IsAuthenticated, IsConnectedUser, IsPremiumUser
Layer 4: Rate Limiting          → Token-bucket per endpoint per user tier
Layer 5: Login Lockout          → 5 failed attempts → 15-minute ban
```

### Data Isolation

- User data in `users` schema — separate from product data
- Email data in `email_intel` schema — encrypted at rest
- Scoring data in `scoring` schema — protected from accidental modification
- Each schema has its own set of permissions and access patterns

---

## 11. Data Safety Rules

### ABSOLUTE RULES — Never Violate

#### Never Delete Production Data

```python
# ❌ NEVER do this:
Product.objects.all().delete()
Product.objects.filter(created_at__lt=cutoff).delete()

# ✅ SAFE alternatives:
# For seed data:
python manage.py delete_seed_data --confirm

# For full reset:
python manage.py flush  # asks for confirmation

# For targeted deletion (always print count first):
qs = BackfillProduct.objects.filter(status='FAILED')
print(f"Will delete {qs.count()} items")  # ALWAYS print count
qs.delete()
```

#### Never Run Destructive Migrations

```python
# ❌ NEVER in one step:
migrations.RemoveField('Product', 'old_field')

# ✅ SAFE three-step migration:
# Step 1: Add new field
migrations.AddField('Product', 'new_field', ...)
# Step 2: Copy data (separate migration)
# Step 3: Remove old field (separate migration, after verification)
```

Always run `--check` before `--migrate`.

#### Scraping Safety

- Never `--max-pages > 5` without explicit confirmation
- Verify Docker is running before scraping: `docker compose ps`
- Log item counts at spider close
- Never fall back to direct requests when all proxies are banned

#### Backfill Safety

- Never `--batch > 5000` without confirmation
- Never `--concurrency > 30` (overwhelms tracker platforms)
- Always check `backfill_prices status` before and after
- Pipeline hook must NEVER crash the main scraping pipeline

---

## 12. Key Patterns & Conventions

### Backend Conventions

| Convention | Rule |
|-----------|------|
| **Prices** | Always in paisa (integer). Display layer converts to ₹ |
| **Timestamps** | Always UTC + timezone-aware (`timezone.now()`) |
| **API responses** | Always wrapped: `{success, data}` or `{success: false, error: {code, message}}` |
| **Pagination** | Cursor-based (never offset) |
| **Config values** | Through `common/app_settings.py` (never hardcoded) |
| **Background work** | Via Celery tasks (never in request/response cycle) |
| **Business logic** | In services/model methods (never in views) |
| **Type hints** | On all functions |
| **Docstrings** | On all public functions |
| **Logging** | Structlog JSON output |

### Frontend Conventions

| Convention | Rule |
|-----------|------|
| **TypeScript** | Strict mode. No `any` type |
| **Components** | Server Components by default. `"use client"` only for interactivity |
| **API calls** | Through `src/lib/api/` (never raw `fetch`) |
| **Styles** | Tailwind utility classes. Whydud color palette only |
| **Responsive** | Mobile-first: `text-sm md:text-base lg:text-lg` |
| **Prices** | Always ₹ prefix, formatted via `format.ts` |
| **Loading** | Skeleton components for every data component |
| **Error** | Graceful fallbacks, toast notifications |
| **Images** | `next/image` component with remote patterns |

### Affiliate URL Injection

Affiliate tags are injected at **API response time** — never stored in the database:

```python
# In the serializer or view:
listing.affiliate_url = f"{listing.external_url}?tag={marketplace.affiliate_tag}"
# Amazon: &ascsubtag={sub_tag}
# Flipkart: &affExtParam1={sub_tag}
```

The `sub_tag` tracks where the click came from (product page, comparison, deal, search, homepage).

### Lightweight Product UX

When a user visits a lightweight product:
1. Show basic info + price chart (available immediately)
2. Display info banner: "We're fetching full details..."
3. Trigger on-demand enrichment (P0 priority — immediate Playwright)
4. Hide empty sections (don't show blank specs/reviews)
5. After enrichment: page auto-refreshes with full data

---

## 13. Environment Variables

### Backend (Required)

| Variable | Purpose | Example |
|----------|---------|---------|
| `DJANGO_SETTINGS_MODULE` | Which settings file | `whydud.settings.prod` |
| `DJANGO_SECRET_KEY` | Cryptographic signing | (random 50+ chars) |
| `DJANGO_ENV` | Environment flag | `production` |
| `POSTGRES_DB` | Database name | `whydud` |
| `POSTGRES_USER` | Database user | `whydud` |
| `POSTGRES_PASSWORD` | Database password | (secure password) |
| `POSTGRES_HOST` | Database host | `10.8.0.1` |
| `REDIS_URL` | Redis connection | `redis://10.8.0.1:6379/0` |
| `MEILISEARCH_URL` | Search engine URL | `http://meilisearch:7700` |
| `MEILISEARCH_MASTER_KEY` | Search engine auth | (secure key) |
| `RESEND_API_KEY` | Email sending | `re_...` |
| `EMAIL_ENCRYPTION_KEY` | AES-256-GCM for emails | (base64 key) |
| `OAUTH_ENCRYPTION_KEY` | AES-256-GCM for OAuth | (base64 key) |
| `GOOGLE_CLIENT_ID` | Google OAuth | `...apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret | (from Google console) |
| `CELERY_WORKER_ID` | Unique per node | `main`, `oci-w1`, `oci-w2` |
| `SCRAPING_PROXY_LIST` | Proxy URLs | (comma-separated) |
| `DISCORD_WEBHOOK_URL` | Task notifications | `https://discord.com/api/webhooks/...` |

### Frontend (Required)

| Variable | Purpose | Example |
|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | Client-side API URL | `https://whydud.com` |
| `NEXT_PUBLIC_SITE_URL` | OG metadata base | `https://whydud.com` |
| `INTERNAL_API_URL` | Server-side API URL | `http://backend:8000` |

---

## 14. Troubleshooting Guide

### Products Not Appearing on Site

1. **Check scraping pipeline:** Did the spider run? `ScraperJob` status?
2. **Check ProductPipeline:** Was the item dropped by validation? Check spider stats.
3. **Check Meilisearch sync:** Was `sync_products_to_meilisearch` triggered after spider close?
4. **Check PriceSnapshot:** Was price `None`? (NOT NULL constraint prevents insertion)
5. **Check category mapping:** Did the product match a known category?

### Auth Issues

1. **401 on API calls:** Token expired or invalid → frontend clears state, redirects to login
2. **Middleware redirect loop:** Cookie `whydud_auth` missing → check localStorage has token
3. **OAuth failure:** Check Google Client ID/Secret, callback URL configuration

### Enrichment Stuck

1. **Check BackfillProduct.scrape_status:** Should be `pending` or `enriching`
2. **Stuck in `enriching` for 2+ hours:** `cleanup_stale_enrichments` task resets these
3. **curl_cffi failing:** Check proxy health, IP reputation, time of day (IST midnight–6am best)
4. **Playwright failing:** Check browser context memory (max 3 concurrent)

### Worker Node Issues

1. **WireGuard not connecting:** Check `systemctl status wg-quick@wg0`, verify private keys match
2. **Can't reach Redis/PostgreSQL:** Check firewall rules (`ufw allow from 10.8.0.X`)
3. **Celery not picking up tasks:** Verify `CELERY_BROKER_URL` points to WireGuard IP

### Database Issues

1. **TimescaleDB migration fails:** Must use `raw_conn.autocommit = True` (see Section 5.5)
2. **Schema not found:** Check `search_path` includes the schema in Django settings
3. **Price snapshot insert fails:** Hypertable has `managed = False` — use raw SQL, not ORM

---

## 15. Glossary

| Term | Definition |
|------|-----------|
| **ASIN** | Amazon Standard Identification Number — unique product ID on Amazon |
| **Backfill** | Process of importing historical data from external sources |
| **Beat** | Celery's scheduler for recurring tasks |
| **Broker** | Message queue between web server and workers (we use Redis) |
| **CAPTCHA** | Challenge to prove you're human (blocks scrapers) |
| **CSRF** | Cross-Site Request Forgery — attack where a malicious site makes requests on your behalf |
| **curl_cffi** | HTTP client that mimics browser TLS fingerprints |
| **DRF** | Django REST Framework — builds JSON APIs in Django |
| **DudScore** | Whydud's proprietary trust-adjusted product quality score (0–100) |
| **Enrichment** | Scraping full product details for a lightweight record |
| **External ID** | Product identifier on a marketplace (ASIN for Amazon, PID for Flipkart) |
| **Hypertable** | TimescaleDB's time-partitioned table for efficient time-range queries |
| **Idempotent** | An operation that produces the same result whether run once or multiple times |
| **JSON-LD** | Structured data embedded in HTML (used by Flipkart for product info) |
| **Lightweight product** | Product created from tracker data only — no marketplace scrape yet |
| **MRP** | Maximum Retail Price — the printed price on the product (India-specific) |
| **ORM** | Object-Relational Mapping — Django's way of querying databases with Python instead of SQL |
| **Paisa** | 1/100 of a rupee. We store all prices in paisa to avoid floating-point issues |
| **Playwright** | Browser automation tool — controls Chromium to execute JavaScript |
| **Proxy** | Intermediary server that masks your IP address |
| **Residential proxy** | Proxy using real home internet connections (harder to detect) |
| **Scrapy** | Python framework for building web scrapers |
| **Serializer** | DRF component that converts between Python objects and JSON |
| **Session stickiness** | Routing all requests with the same key through the same proxy IP |
| **Slug** | URL-friendly version of a name ("apple-iphone-16" instead of "Apple iPhone 16") |
| **Spider** | A Scrapy program that crawls specific websites |
| **SSR** | Server-Side Rendering — generating HTML on the server |
| **TimescaleDB** | PostgreSQL extension for time-series data |
| **Token** | Random string used to authenticate API requests |
| **Two-phase scraping** | Listing pages (fast HTTP) → Detail pages (Playwright) |
| **UUID** | Universally Unique Identifier — random ID that won't collide |
| **Webhook** | URL that receives push notifications from external services |
| **WireGuard** | Modern VPN protocol for secure server-to-server communication |
| **XSS** | Cross-Site Scripting — attack where malicious scripts are injected into web pages |

---

## Quick Reference Cards

### Adding a New Django App

```bash
1. cd backend && python manage.py startapp {name}
2. Move to backend/apps/{name}/
3. Add 'apps.{name}' to INSTALLED_APPS in settings/base.py
4. Create models.py → serializers.py → views.py → urls.py
5. Add URL route in backend/whydud/urls.py
6. Run: python manage.py makemigrations {name}
7. Run: python manage.py migrate
```

### Adding a New Frontend Page

```bash
1. Create: src/app/(group)/{route}/page.tsx
2. Create API module (if needed): src/lib/api/{domain}.ts
3. Create types (if needed): src/types/{domain}.ts
4. Create components: src/components/{domain}/*.tsx
5. If protected: add path to middleware.ts matcher
6. If dashboard: add to Sidebar navigation
```

### Adding a New Celery Task

```python
# 1. In apps/{name}/tasks.py:
from celery import shared_task

@shared_task(bind=True, max_retries=3, queue='default')
def my_task(self, arg1, arg2):
    """Docstring explaining what this does."""
    # ... business logic ...

# 2. To call it:
my_task.delay(arg1, arg2)           # Async (queued)
my_task.apply_async(args=[...])     # Async with options

# 3. To schedule it (in celery.py beat_schedule):
'my-task-daily': {
    'task': 'apps.name.tasks.my_task',
    'schedule': crontab(hour=0, minute=0),
    'args': (arg1, arg2),
}
```

### Running the Project Locally

```bash
# Start all services:
cd docker && docker compose up -d

# Check status:
docker compose ps

# View logs:
docker compose logs -f backend
docker compose logs -f celery-worker

# Run migrations:
docker compose exec backend python manage.py migrate

# Create superuser:
docker compose exec backend python manage.py createsuperuser

# Seed data:
docker compose exec backend python manage.py seed_data

# Frontend dev server:
cd frontend && npm run dev
```

---

*This knowledge base covers the entire Whydud codebase as of 2026-03-10. For the latest changes, always check `PROGRESS.md` first.*
