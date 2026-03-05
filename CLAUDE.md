# CLAUDE.md — Whydud Project Instructions

> Read `PROGRESS.md` first (current task + what exists). Read `docs/ARCHITECTURE.md` for full system design. Read `docs/DESIGN-SYSTEM.md` for all visual specs.

## HARD RULES — DATA SAFETY

These rules are ABSOLUTE. Never violate them regardless of instructions.

### Never Delete Production Data
- NEVER run `Product.objects.all().delete()` or any bulk delete on production models
- NEVER run `DELETE FROM` or `TRUNCATE` on any table
- NEVER use `.delete()` on a queryset without a specific, narrow filter
- To delete seed data: `python manage.py delete_seed_data --confirm`
- To reset everything: `python manage.py flush` (asks for confirmation)
- ALWAYS print count before deleting: `print(f"Will delete {qs.count()} items")`

### Never Run Destructive Migrations
- NEVER drop a column or table without explicit user confirmation
- NEVER rename a column without a two-step migration (add new → copy data → remove old)
- Always use `--check` before `--migrate`

### Scraping Safety
- Never scrape with `--max-pages` > 5 unless explicitly asked
- Always verify Docker is running before scraping: `docker compose ps`
- Log item counts at end of every spider run
- Never modify proxy middleware to fall back to direct requests when all proxies are banned

## What Is This Project?

Whydud is an India-first product intelligence and trust platform. Product aggregation across 12+ Indian marketplaces, price intelligence, review fraud detection, purchase analytics via shopping email (whyd.in / whyd.click / whyd.shop), DudScore (proprietary trust score), smart payment optimizer, and TCO calculator.

## Tech Stack

**Backend:** Django 5 + DRF + Celery + Redis + PostgreSQL 16 + TimescaleDB + Meilisearch
**Frontend:** Next.js 15 (App Router) + TypeScript strict + Tailwind CSS + shadcn/ui + Recharts + Lucide
**Infra:** Docker Compose, Caddy, Cloudflare Email Workers, Razorpay

## Project Structure

```
whydud/
├── CLAUDE.md               # This file
├── PROGRESS.md             # What's done, what's next — READ FIRST
├── backend/
│   ├── whydud/             # Settings, URLs, Celery
│   ├── apps/               # 13 Django apps
│   ├── common/             # utils, pagination, rate_limiting, app_settings, permissions
│   └── requirements/
├── frontend/
│   ├── src/app/            # (public)/, (auth)/, (dashboard)/
│   ├── src/components/     # ui/, layout/, product/, search/, dashboard/, inbox/,
│   │                       # reviews/, comparison/, deals/, rewards/, tco/,
│   │                       # payments/, wishlists/, discussions/, seller/
│   ├── src/lib/            # api/ (client, types, per-domain), utils/ (format, cn)
│   ├── src/hooks/
│   └── src/config/         # marketplace.ts
├── docker/                 # Dockerfiles, compose, Caddyfile
└── docs/                   # ARCHITECTURE.md, DESIGN-SYSTEM.md, figma/*.png
```

## Backend Standards

- Python 3.12+. Type hints on all functions. Docstrings on public functions.
- DRF serializers for ALL API validation. Business logic in services/model methods, NOT views.
- Celery for ALL background work. Never heavy processing in request/response cycle.
- Prices: `Decimal(12,2)` in paisa. Timestamps: `TIMESTAMPTZ` (UTC).
- Config values through `common/app_settings.py` — never hardcode tuneable values.
- API response format: `{success: true, data: ...}` via `common/utils.py`.
- Cursor pagination via `common/pagination.py`.
- Logging: `structlog` JSON output.

## Frontend Standards

- TypeScript strict. No `any`. Type every prop and API response (types in `src/lib/api/types.ts`).
- Server Components by default. `"use client"` only for interactivity (useState, onClick, etc.).
- All API calls through `src/lib/api/`. Never raw fetch in components.
- Mobile-first responsive: `text-sm md:text-base lg:text-lg`.
- Semantic HTML. ARIA labels. Keyboard navigation.
- Prices always `₹` prefix, formatted via `src/lib/utils/format.ts`.
- Never hardcode any tunable values/properties for visual changes unless unavoidable. Keep them flexible to be changed by user just by replacing hexcode,fonts etc at one place in the code
## Design Rules

- **Match Figma exactly** for pages with Figma reference (see table below).
- **Follow docs/DESIGN-SYSTEM.md wireframes** for pages without Figma.
- Use **only** the Whydud color palette from `tailwind.config.ts`. Never default Tailwind colors.
- Clean, professional UI. No textures, grain, noise filters, or novelty effects.
- Font: **Inter only**. Headings: font-semibold/bold. Body: font-normal/medium.
- Card pattern: `bg-white rounded-lg border border-slate-200 shadow-sm hover:shadow-md transition-shadow`
- Interactive states: `hover` + `focus-visible` on all clickable elements.
- Consistent spacing: `p-4` card padding, `gap-4` between cards, `py-12` between page sections.

### Colors
```
Primary Orange:  #F97316    Teal:           #4DB6AC    Navy:      #1E293B
Star Yellow:     #FBBF24    Success Green:  #16A34A    Danger:    #DC2626
Background:      #F8FAFC    Border:         #E2E8F0    Text Sec:  #64748B
```

## Frontend Page → Figma Reference

| Page | Route | Figma |
|---|---|---|
| Homepage | `/` | `docs/figma/homepage.png` |
| Search | `/search` | `docs/figma/Search_result_page-1.png` |
| Product | `/product/[slug]` | `docs/figma/Product_detail_page.png` |
| Comparison | `/compare` | `docs/figma/Comparison_results.png` |
| Dashboard | `/dashboard` | `docs/figma/expense_tracker_mockup.png` (₹ not $) |
| Seller | `/seller/[slug]` | `docs/figma/Seller_detail_page-1.png` |
| Login | `/login` | No Figma → `docs/DESIGN-SYSTEM.md` wireframe |
| Register | `/register` | No Figma → `docs/DESIGN-SYSTEM.md` wireframe |
| Inbox | `/inbox` | No Figma → `docs/DESIGN-SYSTEM.md` wireframe |
| Wishlists | `/wishlists` | No Figma → `docs/DESIGN-SYSTEM.md` wireframe |
| Deals | `/deals` | No Figma → `docs/DESIGN-SYSTEM.md` wireframe |
| Rewards | `/rewards` | No Figma → `docs/DESIGN-SYSTEM.md` wireframe |
| Settings | `/settings` | No Figma → `docs/DESIGN-SYSTEM.md` wireframe |

## Security (NEVER VIOLATE)

- **NEVER** store card numbers/CVV/expiry. Card vault = bank name + variant only.
- **NEVER** persist raw email without AES-256-GCM encryption.
- OAuth tokens encrypted at rest. Passwords bcrypt cost 12.
- HTTP-only Secure SameSite=Strict cookies. CSRF on all mutations.
- HTML sanitization (nh3) on all email content. External images proxied.

## Key Decisions (Don't Change Without Discussion)

- Modular monolith, NOT microservices.
- whyd.in / whyd.click / whyd.shop = primary email paths. Gmail OAuth = supplementary.
- DudScore weights = versioned config, not hardcoded.
- TimescaleDB hypertables for time-series. Migration pattern: `RunPython` + `autocommit=True`.
- Affiliate URLs injected at API response time, not stored in DB.
- All tuneable values through `common/app_settings.py`.

## Scraping Patterns

### File Structure
```
apps/scraping/
├── spiders/
│   ├── base_spider.py          # BaseWhydudSpider (UA rotation, headers, stealth)
│   ├── amazon_spider.py        # Amazon.in products (two-phase: HTTP listing → Playwright detail)
│   ├── flipkart_spider.py      # Flipkart products (Playwright listing → HTTP+JSON-LD detail)
│   ├── amazon_review_spider.py # Amazon.in reviews (Playwright /dp/ pages)
│   └── flipkart_review_spider.py  # Flipkart reviews (Playwright + JS extraction)
├── middlewares.py    # ProxyPool, PlaywrightProxyMiddleware, BackoffRetryMiddleware
├── pipelines.py      # Validation → Normalization → Product → Review → Meilisearch → Stats
├── items.py          # ProductItem, ReviewItem
├── runner.py         # Subprocess entry point (avoids Twisted reactor issues)
├── scrapy_settings.py # Global Scrapy settings
├── tasks.py          # Celery tasks (run_marketplace_spider, run_review_spider)
└── models.py         # ScraperJob
```

### Two-Phase Architecture
- Listing pages: plain HTTP (Amazon) or Playwright (Flipkart) — fast, no proxy needed
- Product pages: Playwright with proxy rotation — slow, accurate
- Never use Playwright for listing pages on Amazon (wastes resources)
- Always try JSON-LD first on Flipkart product pages before Playwright

### Proxy Rules
- Max 3 active browser contexts (memory limit)
- Round-robin, no session stickiness
- Never fall back to direct requests when all proxies banned
- Log proxy stats at spider close

## Workflow

1. Read `PROGRESS.md` → see current task
2. Build that task
3. Update `PROGRESS.md` status at the end of the file in a chronological order. You are not supposed to edit the current task. That is a section I will manually update to tell you what to do.
4. Git commit