# WHYDUD Internal Knowledge Base

---

# 🏠 Home

Welcome to the WHYDUD internal knowledge base. This is the single source of truth for everything about our platform — product vision, architecture, development processes, code patterns, deployment, and operations.

**Quick Links:**
- Product Overview → see "1. Product" section
- Architecture → see "2. Architecture" section  
- Development Guide → see "3. Development" section
- Operations → see "4. Operations" section
- Code Reference → see "5. Code Reference" section
- Team & Processes → see "6. Team" section

**Last Updated:** February 2026

---

# 1. 🎯 Product

## 1.1 What is WHYDUD?

WHYDUD is India's first product intelligence and trust platform. We help consumers make smarter purchase decisions by aggregating product data across marketplaces, computing trust scores, tracking prices, and providing transparent buying tools.

**Core Value Proposition:** "Before you buy, check if it's a Dud."

**Target Market:** Indian consumers who shop across Amazon.in, Flipkart, Croma, Reliance Digital, and 10+ other marketplaces.

## 1.2 Product Pillars

### DudScore (0-100 Trust Score)
Every product gets a DudScore computed from 6 weighted components:
- **Sentiment Score** (25%) — NLP analysis of review text, weighted by recency
- **Rating Quality** (15%) — Distribution health, not just average stars
- **Price Value** (15%) — Value-for-money compared to category peers
- **Review Credibility** (20%) — Verified purchase %, review depth, copy-paste detection
- **Price Stability** (10%) — Price consistency, flash sale frequency
- **Return Signal** (15%) — Return/refund rates from email intelligence

Multipliers applied: Fraud penalty (if >30% reviews flagged) and Confidence (based on data volume).

### Cross-Marketplace Price Intelligence
- Real-time prices from Amazon.in, Flipkart, Croma, Reliance Digital, and more
- Price history charts (TimescaleDB time-series data)
- Lowest-ever price tracking
- Price drop alerts (user-configurable target price)
- Error pricing detection (price < 50% of 30-day avg)

### Email Intelligence (@whyd.in / @whyd.click / @whyd.shop)
- Users get a free @whyd.* email address
- Forward marketplace order confirmations → auto-parsed into purchase history
- Track refunds, returns, delivery status automatically
- Detect subscription renewals (Netflix, Spotify, etc.)
- All email bodies encrypted at rest (AES-256-GCM)

### Total Cost of Ownership (TCO) Calculator
- Per-category cost models (AC → energy + maintenance + filter; Vehicle → fuel + insurance + depreciation)
- Dynamic input schemas stored as JSONB (admin can add new categories without code changes)
- Preset modes: Default, Conservative, Optimistic
- Comparison mode: side-by-side TCO for up to 3 products

### Community Trust
- Write Reviews with purchase verification (proof of purchase upload)
- Category-specific feature ratings (phones: battery, camera; ACs: cooling, noise)
- Seller feedback (delivery, packaging, accuracy, communication)
- Reviewer levels: Bronze → Silver → Gold → Platinum
- Weekly leaderboard with top reviewer rankings
- Fake review detection (5 rule-based signals + credibility scoring)

## 1.3 User Roles

| Role | Description | Permissions |
|---|---|---|
| Anonymous | No account | Browse products, search, compare, view DudScores |
| Free User | Registered | Everything above + wishlists, alerts, @whyd.* email, write reviews, TCO calculator |
| Pro User | ₹99/month | Everything above + unlimited alerts, ad-free, priority support |
| Admin | Internal | Full platform management via Django Admin |

## 1.4 Monetization

1. **Affiliate Revenue** — "Buy on Amazon/Flipkart" buttons inject affiliate tags. Click tracking via ClickEvent model.
2. **Pro Subscriptions** — ₹99/month via Razorpay (unlimited alerts, ad-free)
3. **Future: Brand Dashboard** — Brands pay to monitor sentiment and competitive positioning

## 1.5 Pages & Navigation

### Public Pages (no login required)
| Page | Route | Description |
|---|---|---|
| Homepage | `/` | Hero, category pills, trending products, price drops, deals |
| Search | `/search` | Meilisearch-powered, filters, sorting |
| Product Detail | `/product/[slug]` | DudScore gauge, marketplace prices, price chart, reviews, TCO, specs |
| Compare | `/compare` | Side-by-side comparison of up to 4 products |
| Seller | `/seller/[slug]` | Seller profile, ratings, product listings |
| Deals | `/deals` | Active deals (error pricing, lowest-ever, genuine discounts) |
| Categories | `/categories/[slug]` | Category browsing with filters |
| Leaderboard | `/leaderboard` | Top reviewer rankings by level/category |

### Dashboard Pages (login required)
| Page | Route | Description |
|---|---|---|
| Dashboard | `/dashboard` | Spending overview, charts, insights |
| Inbox | `/inbox` | Email client UI (inbound + outbound + sent) |
| Wishlists | `/wishlists` | Tabbed wishlists with price tracking |
| Settings | `/settings` | 6 tabs: profile, email, cards, password, notifications, preferences |
| My Reviews | `/my-reviews` | User's reviews with edit/delete |
| Alerts | `/alerts` | Price alerts + stock alerts |
| Purchases | `/purchases` | Auto-detected purchase history from emails |
| Rewards | `/rewards` | Points balance, gift card catalog, redemption |
| Refunds | `/refunds` | Refund tracking with status timelines |
| Subscriptions | `/subscriptions` | Detected recurring subscriptions |
| Notifications | `/notifications` | Notification center with filters |
| Preferences | `/preferences` | Purchase preference questionnaires per category |

---

# 2. 🏗️ Architecture

## 2.1 System Overview

**Architecture Style:** Modular Monolith (NOT microservices) — optimized for solo founder, single VPS deployment.

```
┌─────────────────────────────────────────────────────────┐
│                   Caddy (Reverse Proxy)                  │
│                   Port 80/443 + Auto SSL                 │
├──────────────────────┬──────────────────────────────────┤
│   Next.js (SSR)      │     Django API (DRF)             │
│   Port 3000          │     Port 8000                    │
│   Frontend           │     Backend                      │
├──────────────────────┴──────────────────────────────────┤
│                                                          │
│  ┌──────────┐  ┌───────┐  ┌────────────┐  ┌──────────┐ │
│  │PostgreSQL│  │ Redis │  │Meilisearch │  │ Celery   │ │
│  │+Timescale│  │       │  │            │  │ Workers  │ │
│  │  :5432   │  │ :6379 │  │   :7700    │  │ + Beat   │ │
│  └──────────┘  └───────┘  └────────────┘  └──────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │            Scrapy Spiders (subprocess)            │   │
│  │     Amazon.in + Flipkart + future marketplaces    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 2.2 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind CSS + shadcn/ui | Server-rendered React UI |
| API | Django 5 + Django REST Framework | REST API with serializers |
| Database | PostgreSQL 16 + TimescaleDB | Relational + time-series data |
| Search | Meilisearch v1.7 | Full-text search + autocomplete |
| Queue | Celery + Redis | Background task processing |
| Scheduler | Celery Beat (DatabaseScheduler) | Periodic task scheduling |
| Cache | Redis | API response caching, rate limiting |
| Scraping | Scrapy + Playwright | Marketplace data collection |
| NLP | TextBlob + spaCy | Sentiment analysis for DudScore |
| Email Inbound | Cloudflare Email Workers → Django webhook | Receive user emails |
| Email Outbound | Resend API | Send from @whyd.* addresses |
| Payments | Razorpay | Pro subscriptions |
| Encryption | AES-256-GCM (cryptography lib) | Email bodies, OAuth tokens at rest |
| Deployment | Docker Compose + Caddy | Single VPS, auto SSL |
| Monitoring | Flower (Celery) + Django Admin + Sentry | Operations |

## 2.3 Database Schema

**7 PostgreSQL schemas:**
| Schema | Apps | Key Tables |
|---|---|---|
| `public` | products, pricing, reviews, deals, search, scraping | Product, ProductListing, PriceSnapshot⚡, Review, Deal, ScraperJob |
| `users` | accounts, wishlists, rewards | User, WhydudEmail, Notification, PriceAlert, Wishlist, RewardBalance |
| `email_intel` | email_intel | InboxEmail, ParsedOrder, RefundTracking, DetectedSubscription |
| `scoring` | scoring | DudScoreConfig, DudScoreHistory⚡ |
| `community` | discussions | DiscussionThread, DiscussionReply |
| `tco` | tco | TCOModel, CityReferenceData |
| `admin` | admin_tools | AuditLog, ModerationQueue, ScraperRun, SiteConfig |

⚡ = TimescaleDB hypertable (time-series optimized)

**14 Django Apps, 49+ model classes, 27+ migrations.**

## 2.4 Data Flow — Scraping Pipeline

```
Every 6 hours (Celery Beat triggers per-marketplace):

1. Spider launches (Amazon or Flipkart)
   → Rotates User-Agents, respects robots.txt, random delays
   → Follows category pages → product pages
   → Extracts: title, price, MRP, images, specs, seller, ratings

2. ValidationPipeline
   → Drops items missing required fields

3. NormalizationPipeline
   → Cleans titles, normalizes brand casing, deduplicates images

4. ProductPipeline
   → match_product() — 4-step matching engine:
     Step 1: EAN barcode exact match (confidence 1.0)
     Step 2: Brand + model + variant (confidence 0.95)
     Step 3: Brand + model only (confidence 0.85)
     Step 4: Fuzzy title match (confidence 0.70, needs review)
   → Creates/updates ProductListing
   → Inserts PriceSnapshot (TimescaleDB)
   → Updates Product.current_best_price

5. MeilisearchIndexPipeline
   → Queues selective search index sync

6. Post-scrape triggers:
   → sync_products_to_meilisearch.delay()
   → check_price_alerts.delay()
```

## 2.5 Data Flow — Email Intelligence

```
1. Email arrives at user@whyd.in
2. Cloudflare Email Worker → POST /webhooks/email/inbound
3. Django validates HMAC signature
4. Encrypts body (AES-256-GCM) → creates InboxEmail
5. Queues parse_email.delay(email_id)
6. Parser:
   → detect_marketplace() — sender domain matching
   → categorize_email() — order_confirm, shipping, delivery, return, refund
   → Extract structured data → ParsedOrder / RefundTracking / DetectedSubscription
7. User sees email in /inbox, parsed data in /purchases, /refunds, /subscriptions
```

## 2.6 Celery Beat Schedule (Automated Pipeline)

| Task | Schedule | Queue |
|---|---|---|
| Amazon.in scrape | Every 6h (00, 06, 12, 18 UTC) | scraping |
| Flipkart scrape | Every 6h (03, 09, 15, 21 UTC) | scraping |
| Meilisearch full reindex | Daily 01:00 UTC | scoring |
| Price alert check | Every 4h | alerts |
| Publish pending reviews | Hourly | default |
| Update reviewer profiles | Weekly (Monday 00:00) | scoring |
| DudScore full recalculation | Monthly (1st, 03:00) | scoring |

---

# 3. 💻 Development

## 3.1 Local Setup

### Prerequisites
- Docker Desktop (for Postgres, Redis, Meilisearch)
- Python 3.12+ with virtualenv
- Node.js 18+ with npm
- Playwright (`playwright install chromium`)

### Start Infrastructure
```bash
docker compose -f docker-compose.dev.yml up -d
# Starts: postgres:5432, redis:6379, meilisearch:7700
```

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py seed_marketplaces
python manage.py seed_products
python manage.py sync_meilisearch
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

### Celery Workers (separate terminals)
```bash
# Worker (all queues)
celery -A whydud worker -l info -Q default,scraping,email,scoring,alerts -c 4

# Beat (scheduler)
celery -A whydud beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Flower (monitoring)
celery -A whydud flower --port=5555
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Verify
- Django Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/v1/products/
- Meilisearch: http://localhost:7700
- Frontend: http://localhost:3000
- Flower: http://localhost:5555

## 3.2 Coding Standards

### Python
- Type hints on ALL functions
- Docstrings on all public functions
- Prices as integer paisa (₹1 = 100 paisa), never float
- All timestamps UTC (TIMESTAMPTZ)
- Business logic in service layer or model methods, NEVER in views
- Background work ALWAYS via Celery, never synchronous in views
- Config values in `common/app_settings.py` or SiteConfig, never hardcoded

### TypeScript
- Strict mode, no `any`
- Server components by default, `"use client"` only for interactivity
- All API calls through `src/lib/api/` — never raw fetch
- Every data component needs skeleton loading state
- Mobile-first responsive

### Database
- UUIDs for user-facing entities
- BIGSERIAL for high-volume append tables
- JSONB for flexible schemas
- TimescaleDB hypertables for time-series
- Indexes on all FKs and common query columns

### Security
- AES-256-GCM for email bodies and OAuth tokens at rest
- bcrypt (cost 12) for passwords
- HTTP-only, Secure, SameSite=Strict cookies
- HTML sanitization (nh3) on all email content
- Never store card numbers/CVV — only bank name + variant
- Never display decrypted data in admin UI

## 3.3 Git Workflow

```
main branch — always deployable
Feature branches: feature/description
Commit after every logical unit of work
Descriptive commit messages: "Add notification bell component with unread count polling"
Update PROGRESS.md after completing work
```

## 3.4 Project File Structure

```
whydud/
├── backend/
│   ├── whydud/                    # Settings, URLs, Celery config
│   │   ├── settings/              # base.py, dev.py, prod.py
│   │   ├── celery.py              # Beat schedule, queue config
│   │   └── urls.py                # Root URL routing
│   ├── apps/
│   │   ├── accounts/              # User, Email, OAuth, Notifications
│   │   ├── products/              # Product, Listing, Category, Brand, Matching
│   │   ├── pricing/               # PriceSnapshot, Alerts, ClickTracking
│   │   ├── reviews/               # Review, Fraud Detection, Reviewer Profiles
│   │   ├── scoring/               # DudScore Algorithm, Components, History
│   │   ├── email_intel/           # Inbox, Parsing, Send Service
│   │   ├── wishlists/             # Wishlist CRUD
│   │   ├── deals/                 # Deal Detection
│   │   ├── rewards/               # Points, Gift Cards
│   │   ├── discussions/           # Community threads
│   │   ├── tco/                   # TCO Calculator
│   │   ├── search/                # Meilisearch sync
│   │   ├── scraping/              # Spiders, Pipelines, Runner
│   │   └── admin_tools/           # Audit, Moderation, SiteConfig
│   └── common/                    # Encryption, Pagination, AppSettings
├── frontend/
│   ├── src/app/                   # Next.js App Router pages
│   ├── src/components/            # React components by domain
│   ├── src/lib/api/               # API client + typed endpoints
│   ├── src/contexts/              # Auth, Compare providers
│   └── src/hooks/                 # Custom hooks
├── docker/                        # Dockerfiles, compose, Caddyfile
├── docs/                          # Architecture, Tasks, Admin specs
├── PROGRESS.md                    # Implementation status
└── CLAUDE.md                      # AI assistant instructions
```

---

# 4. ⚙️ Operations

## 4.1 Deployment (Single VPS — Contabo)

```
Docker Compose with 9 production services:
  Caddy (reverse proxy, auto SSL)
  PostgreSQL 16 + TimescaleDB
  Redis 7
  Meilisearch v1.7
  Django (Gunicorn, 3 workers)
  Celery Worker (4 concurrent, 5 queues)
  Celery Beat
  Email Worker (2 concurrent, email queue)
  Next.js (SSR)
```

## 4.2 Monitoring

### Flower (Celery Tasks)
```
http://localhost:5555
- Real-time task monitor
- Queue depths
- Worker status
- Task failures with tracebacks
```

### Django Admin
```
http://localhost:8000/admin/
- 10 monitoring consoles (scraping, data quality, DudScore, reviews, users, clicks, email, notifications, search, system health)
```

### Health Check Command
```bash
python manage.py health_check
# Shows: scraper status, data counts, user metrics, queue depths, search health
```

## 4.3 Common Operations

### Run Scraper Manually
```python
# Via Celery (background)
from apps.scraping.tasks import run_marketplace_spider
run_marketplace_spider.delay('amazon_in')

# Via CLI (see output)
python -m apps.scraping.runner amazon_in --max-pages 2
```

### Recalculate DudScores
```python
from apps.scoring.tasks import full_dudscore_recalculation
full_dudscore_recalculation.delay()
```

### Reindex Meilisearch
```python
from apps.search.tasks import full_reindex
full_reindex.delay()
```

### Check Price Alerts
```python
from apps.pricing.tasks import check_price_alerts
check_price_alerts.delay()
```

## 4.4 Environment Variables

```
# Required (dev)
DATABASE_URL=postgres://whydud:whydud_dev@localhost:5432/whydud
REDIS_URL=redis://localhost:6379/0
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_MASTER_KEY=masterKey
DJANGO_SECRET_KEY=(generated)
EMAIL_ENCRYPTION_KEY=(64-char hex)
OAUTH_ENCRYPTION_KEY=(64-char hex)
GOOGLE_CLIENT_ID=(OAuth)
GOOGLE_CLIENT_SECRET=(OAuth)

# Required (production)
RESEND_API_KEY=(from resend.com)
RAZORPAY_KEY_ID=(from Razorpay)
RAZORPAY_KEY_SECRET=(from Razorpay)
CLOUDFLARE_EMAIL_SECRET=(webhook verification)
SENTRY_DSN=(error monitoring)
```

---

# 5. 📝 Code Reference

## 5.1 API Endpoints (Selected)

### Auth
```
POST /api/v1/auth/register/
POST /api/v1/auth/login/
POST /api/v1/auth/logout/
GET  /api/v1/me/
POST /api/v1/auth/change-password/
POST /api/v1/auth/oauth/exchange-code/
```

### Products
```
GET  /api/v1/products/                    # List (paginated, filterable)
GET  /api/v1/products/:slug/             # Detail
GET  /api/v1/products/:slug/listings/    # Marketplace listings
GET  /api/v1/products/:slug/price-history/ # Time-series prices
GET  /api/v1/products/:slug/reviews/     # Reviews
GET  /api/v1/products/:slug/similar/     # Similar products
POST /api/v1/products/:slug/reviews/     # Submit review
GET  /api/v1/products/compare/?ids=a,b,c # Compare
```

### Notifications
```
GET  /api/v1/notifications/              # List
GET  /api/v1/notifications/unread-count  # Badge count
PATCH /api/v1/notifications/:id/read     # Mark read
POST /api/v1/notifications/mark-all-read # Bulk read
GET  /api/v1/notifications/preferences   # User prefs
PATCH /api/v1/notifications/preferences  # Update prefs
```

### Alerts
```
POST /api/v1/alerts/price               # Create price alert
GET  /api/v1/alerts/                     # List alerts
POST /api/v1/alerts/stock               # Create stock alert
```

### Click Tracking
```
POST /api/v1/clicks/track               # Track affiliate click
GET  /api/v1/clicks/history             # User's click history
```

### Email
```
POST /api/v1/inbox/send                 # Compose email
POST /api/v1/inbox/:id/reply            # Reply to email
```

### Trending
```
GET  /api/v1/trending/products          # Most viewed this week
GET  /api/v1/trending/rising            # Biggest DudScore improvement
GET  /api/v1/trending/price-dropping    # Consistent downward trend
```

## 5.2 Key Code Patterns

### API Response Format
```python
# All API responses follow this format:
{"success": True, "data": {...}}
{"success": False, "error": "message"}
```

### Pagination (Cursor-based)
```python
# common/pagination.py
# Response: {"results": [...], "next_cursor": "abc123", "has_more": true}
```

### Price Formatting (Frontend)
```typescript
// src/lib/utils/format.ts
formatPrice(priceInPaisa: number): string
// formatPrice(1599900) → "₹15,999"  (Indian numbering)
```

### Auth Token Flow
```
Login → API returns token
→ Stored in localStorage (whydud_auth_token) + cookie (whydud_auth)
→ API client attaches to all requests
→ Middleware checks cookie for protected routes
→ AuthProvider restores session on mount via GET /me
```

### Product Matching (Scraping)
```python
# apps/products/matching.py
match_product(item) → MatchResult(product, confidence, method, is_new)
# Confidence: 1.0 (EAN), 0.95 (brand+model+variant), 0.85 (brand+model), 0.70 (fuzzy)
```

### DudScore Calculation
```python
# apps/scoring/components.py → apps/scoring/tasks.py
raw_score = (w_sentiment × sentiment + w_rating × rating_quality + ...) × fraud_multiplier × confidence_multiplier
# Scaled to 0-100, stored with full component breakdown in DudScoreHistory
```

---

# 6. 👥 Team & Processes

## 6.1 Team

| Role | Person | Email |
|---|---|---|
| Founder & Developer | Ramesh | ramesh@whydud.com |

## 6.2 Communication

| Channel | Purpose |
|---|---|
| ramesh@whydud.com | Primary work email |
| support@whydud.com | Customer support |
| admin@whydud.com | Service registrations, DNS |
| partnerships@whydud.com | Business inquiries |

## 6.3 Tools

| Tool | Purpose | URL |
|---|---|---|
| GitHub | Code repository | github.com/rameshworkk/whydud |
| Zoho Mail | Team email (whydud.com) | mail.zoho.in |
| Notion | Knowledge base (this document) | notion.so |
| Resend | Transactional email (whyd.in/click/shop) | resend.com |
| Cloudflare | DNS + Email routing | dash.cloudflare.com |
| Razorpay | Payments | dashboard.razorpay.com |
| Docker Hub | Container images | hub.docker.com |
| Contabo | VPS hosting | my.contabo.com |

## 6.4 Key Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-01 | Modular monolith over microservices | Solo founder, single VPS, simpler ops |
| 2026-01 | @whyd.* email as primary intelligence path | More reliable than Gmail OAuth, full control |
| 2026-01 | TimescaleDB for price data | Native time-series queries, compression, retention |
| 2026-01 | Scrapy over Puppeteer-only | Built-in pipeline, middleware, concurrent requests |
| 2026-02 | Django Admin over custom admin dashboard | 80% value in 20% time, built-in auth/CRUD |
| 2026-02 | Resend over SendGrid | Simpler API, better pricing, modern DX |
| 2026-02 | Zoho Mail over Google Workspace | Free for 5 users, Indian company |
| 2026-02 | Notion over Confluence | Free unlimited pages solo, better UX |

---

# 7. 📋 Glossary

| Term | Definition |
|---|---|
| **DudScore** | 0-100 trust score computed from 6 weighted components |
| **Canonical Product** | The deduplicated product entity that listings from multiple marketplaces link to |
| **ProductListing** | A marketplace-specific listing (one Product can have multiple Listings) |
| **PriceSnapshot** | A single price observation at a point in time (TimescaleDB hypertable) |
| **Paisa** | 1/100th of a Rupee. All prices stored as integer paisa (₹15,999 = 1599900 paisa) |
| **@whyd.* email** | User's free email address on whyd.in, whyd.click, or whyd.shop domains |
| **Match Confidence** | 0-1 score indicating how certain the product matching engine is that two listings are the same product |
| **Reviewer Level** | Bronze (1-4 reviews), Silver (5-14), Gold (15-29), Platinum (30+) |
| **SiteConfig** | Runtime key-value config store in admin schema, editable without code deploy |
| **TCO** | Total Cost of Ownership — lifetime cost estimate including purchase price, energy, maintenance, etc. |
| **NPS** | Net Promoter Score — "How likely to recommend?" (0-10) asked in reviews |
