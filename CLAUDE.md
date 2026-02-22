# CLAUDE.md — Whydud Project Instructions

## What Is This Project?

Whydud is a production-grade, India-first product intelligence and trust platform. Full architecture is in `docs/ARCHITECTURE.md` — READ IT BEFORE ANY WORK.

## Tech Stack

- **Backend:** Django 5 + Django REST Framework + Celery + Redis
- **Frontend:** Next.js 15 (App Router) + TypeScript + Tailwind CSS + shadcn/ui
- **Database:** PostgreSQL 16 + TimescaleDB extension
- **Search:** Meilisearch
- **Scraping:** Scrapy + Playwright (Python)
- **NLP:** spaCy + TextBlob
- **Queue:** Celery + Redis (broker) + Celery Beat (scheduler)
- **Cache:** Redis
- **Email Receive:** Cloudflare Email Workers → Django webhook
- **Payments:** Razorpay
- **Deployment:** Docker Compose on Contabo VPS + Caddy reverse proxy

## Project Structure

```
whydud/
├── backend/                  # Django project
│   ├── whydud/               # Django settings, urls, celery config
│   ├── apps/                 # Django apps (accounts, products, pricing, reviews, scoring, email_intel, wishlists, deals, rewards, discussions, search, scraping)
│   ├── common/               # Shared utilities
│   └── requirements/         # pip requirements (base, dev, prod)
├── frontend/                 # Next.js project
│   ├── src/app/              # App Router pages
│   ├── src/components/       # React components (ui/, product/, search/, dashboard/, inbox/, deals/, rewards/, tco/, payments/, discussions/, layout/)
│   ├── src/lib/              # API client, utils
│   └── src/hooks/            # React hooks
├── docker/                   # Dockerfiles + docker-compose.yml + Caddyfile
├── docs/                     # Architecture doc, API docs, design notes
└── CLAUDE.md                 # This file
```

## Coding Standards

### Python (Backend)
- Python 3.12+
- Type hints on ALL function signatures
- Docstrings on all public functions
- Django coding style (snake_case, class-based views where appropriate)
- Use Django REST Framework serializers for all API validation
- Use Celery tasks for ALL background work (scraping, scoring, email parsing, alerts)
- NEVER put business logic in views — use service layer or model methods
- All prices stored as Decimal(12,2) in paisa, never float
- All timestamps as TIMESTAMPTZ (UTC)
- Use structlog for structured JSON logging
- Tests: pytest + pytest-django

### TypeScript (Frontend)
- Strict mode, no `any` types
- All API responses typed with interfaces matching Django serializers
- Use server components by default, client components only when needed (interactivity)
- All API calls go through `src/lib/api/` abstraction layer — never raw fetch in components
- shadcn/ui for base components, custom for domain components
- Tailwind utility classes, no custom CSS unless absolutely necessary
- Every data component must have a skeleton loading state
- Error boundaries on every page
- Mobile-first responsive design

### Database
- UUIDs for user-facing entities (products, users, orders)
- BIGSERIAL for high-volume append tables (price_snapshots, audit_logs)
- JSONB for flexible schemas (product specs, offer terms)
- TimescaleDB hypertables for ALL time-series data
- Indexes on all foreign keys and commonly queried columns
- Schema isolation: public, users, email_intel, scoring, tco, community, admin

### Security (CRITICAL)
- NEVER store card numbers, CVV, expiry, PIN — card vault stores bank name + variant ONLY
- NEVER persist raw email bodies without encryption
- AES-256-GCM for OAuth tokens and email bodies at rest
- bcrypt (cost 12) for passwords
- HTTP-only, Secure, SameSite=Strict cookies
- CSRF protection on all state-changing endpoints
- Rate limiting on all public endpoints
- HTML sanitization (nh3) on all email content before rendering
- Proxy external images in emails (block tracking pixels)

## Key Design Decisions
- Modular monolith (NOT microservices) — solo founder, single VPS
- @whyd.xyz email is PRIMARY email intelligence path, Gmail OAuth is SUPPLEMENTARY
- DudScore weights are versioned config, NOT hardcoded
- Price data uses TimescaleDB hypertables with continuous aggregates
- Email worker runs on isolated Celery queue (separate from main workers)
- All scraping through Scrapy framework with anti-detection middleware
- Affiliate links injected at API response level, not stored in DB

## Current Sprint
Sprint 1: Foundation (see docs/ARCHITECTURE.md Section "Development Plan")

## When In Doubt
- Read docs/ARCHITECTURE.md
- Ask clarifying questions before writing code
- Prefer simple, correct code over clever code
- Log everything, cache aggressively, background all heavy work
