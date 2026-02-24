# WHYDUD — Complete Platform Architecture v2.0 (UNIFIED)

**Version:** 2.1 (Multi-Domain Email + Click Tracking + Admin)
**Date:** February 24, 2026
**Status:** Pre-seed Architecture Blueprint — APPROVED FOR DEVELOPMENT
**Supersedes:** v2.0, v1.0, v1.1, v1.2, v1.3 (all previous amendments merged)
**v2.1 Changes:** Multi-domain email (whyd.in/.click/.shop), send capability via Resend, affiliate click tracking, admin tooling schema, multi-account email aggregation

---

## EXECUTIVE SUMMARY

**Whydud** is a production-grade, India-first product intelligence and trust platform that prevents users from buying bad products. It combines product aggregation, price intelligence, review fraud detection, purchase analytics, and a proprietary trust score (DudScore) into a single platform.

### Constraints

| Constraint | Value |
|---|---|
| Team | Solo founder / 1-2 devs |
| Timeline | 2-3 months to MVP |
| Budget | < ₹8,500/mo (~$100) |
| Hosting | VPS (Contabo/Hetzner), minimal cloud dependency |
| Geography | India-first (₹, Amazon.in + Flipkart + 10 more) |
| Revenue | Affiliate + freemium subscription |
| Data | Own scrapers (no third-party APIs) |
| Stack | Django backend + Next.js frontend |
| Database | PostgreSQL 16 + TimescaleDB |

### Core Moat

1. **@whyd.* shopping email** — Users get a free shopping email on their choice of domain (whyd.in, whyd.click, whyd.shop). Full send+receive via Cloudflare Email Routing (receive) + Resend API (send). All order/refund/return emails auto-parsed for purchase intelligence. No own email server needed.
2. **DudScore** — Proprietary trust-adjusted value score (not a simple rating average)
3. **Smart Payment Optimizer** — "Use your HDFC card on Amazon to save ₹1,500" (personalized to user's cards)
4. **Total Cost of Ownership** — "This 3-star AC costs ₹7,000 MORE over 5 years than the 5-star"
5. **Fake review detection** — Review authenticity scoring with fraud signals
6. **Blockbuster Deals** — Error pricing and verified genuine discount detection

---

## TABLE OF CONTENTS

1. Feature Decomposition & Phasing
2. User Role Matrix
3. User Stories
4. DudScore Algorithm
5. Fraud & Abuse Prevention
6. Data Flow Architecture
7. System Architecture
8. Tech Stack
9. Database Schema
10. API Contracts
11. Frontend Architecture
12. Edge Cases
13. Page-Level Component Breakdown
14. Deployment Plan
15. Observability & Monitoring
16. Security Strategy
17. Scaling Strategy (10K → 10M)
18. Cost Optimization
19. Admin Tooling Architecture

---

## 1. FEATURE DECOMPOSITION & PHASING

### Phase 1 — MVP (Month 1-3)

#### P0 — Must Ship (Weeks 1-8)

| # | Feature | Complexity |
|---|---|---|
| 1 | **Product Search** — Autocomplete, fuzzy search, filters, sorting, SEO | High |
| 2 | **Product Pages** — Specs, multi-marketplace prices, review summary, affiliate links, DudScore | Medium |
| 3 | **Price Tracking** — Daily snapshots (TimescaleDB), historical graph, lowest-ever | Medium |
| 4 | **DudScore v1** — Sentiment + rating quality + price value + review credibility + price stability | High |
| 5 | **Review Aggregation** — Pull from Amazon.in + Flipkart, sentiment analysis, pros/cons extraction | High |
| 6 | **Review Voting** — Upvote/downvote reviews, credibility weighting | Low |
| 7 | **Comparison Engine** — Side-by-side up to 4 products, spec normalization | Medium |
| 8 | **User Auth** — Email/password + Google OAuth + Django AllAuth | Low |
| 9 | **@whyd.* Shopping Email** — Username + domain selection (whyd.in/whyd.click/whyd.shop), Cloudflare Email Workers (receive) + Resend API (send), full inbox with reply/compose, rate-limited to marketplace communication | High |
| 10 | **Inbox** — View/search received emails, auto-categorization, auto-parsing | Medium |
| 11 | **Purchase Dashboard** — Lifetime spend, category breakdown, order timeline | Medium |
| 12 | **Wishlists** — Named lists, price tracking, target price alerts, sharing | Medium |
| 13 | **Affiliate Links** — Inject affiliate tags in outbound marketplace links | Low |
| 14 | **Scraper Pipeline** — Amazon.in + Flipkart spiders (Scrapy + Playwright) | Very High |
| 15 | **Smart Payment Optimizer** — Card vault (zero-risk), offer scraping, effective price calculation | High |
| 16 | **User Onboarding** — @whyd.* email setup (username + domain choice), card vault setup, city/TCO profile | Medium |

#### P1 — Should Ship (Weeks 8-12)

| # | Feature | Complexity |
|---|---|---|
| 17 | **Refund Tracker** — Detect return/refund emails, countdown, delay alerts | Medium |
| 18 | **Return Window Tracker** — Countdown, alerts before expiry | Medium |
| 19 | **Post-Purchase Price Drop Alert** — Compare purchase price vs current, "return & rebuy" suggestion | Low |
| 20 | **Subscription Detection** — Auto-renew detection from emails | Medium |
| 21 | **Fake Review Detection v1** — Rule-based (copy-paste, rating anomaly, burst) | High |
| 22 | **Ad-hoc Search Scraping** — If product not in DB, scrape on-demand | High |
| 23 | **TCO Calculator** — AC, refrigerator, washing machine, printer models | Medium |
| 24 | **Blockbuster Deals** — Error pricing detection, lowest-ever, genuine discount verification | Medium |
| 25 | **Rewards/Points System** — Points for reviews, gift card redemption | Medium |
| 26 | **Discussion Threads** — Per-product Q&A and experience sharing | Medium |
| 27 | **Gmail OAuth** — Supplementary historical purchase import | Medium |
| 28 | **Additional Scrapers** — Myntra, Snapdeal, Croma (3-5 more marketplaces) | High |
| 29 | **Razorpay Premium** — Subscription billing, UPI support | Low |

### Phase 2 — Post-Traction (Month 4-8)

| Feature | Phase |
|---|---|
| Admin Console — Moderation | 2A |
| Admin Console — Data Ops | 2A |
| Admin Console — Trust/Scoring Control | 2A |
| Leaderboards (best value, most overpriced, etc.) | 2A |
| Community features (follow reviewers, discussions v2) | 2B |
| Warranty Tracker | 2B |
| Expense Intelligence (impulse detection, regret index) | 2B |
| Marketplace Reliability Scoring (public) | 2B |
| Outlook OAuth | 2B |
| Remaining marketplace scrapers (Nykaa, AJIO, Meesho, JioMart) | 2B |
| Merchant Portal | 3 |
| Public API | 3 |

### Feature Dependency Graph

```
Scrapers ──→ Product DB ──→ Search Index ──→ Product Pages ──→ Comparison
    │              │              │                 │
    ▼              ▼              ▼                 ▼
Price Snapshots  DudScore    Autocomplete    TCO Calculator
(TimescaleDB)      │                              │
    │              ▼                              ▼
    ├── Price Alerts    Leaderboards (Phase 2)  Comparison TCO tab
    ├── Deal Detection
    └── Payment Optimizer
    
@whyd.* Email ──→ Inbox (send+receive) ──→ Auto-Parser ──→ Purchase Dashboard
                                        ──→ Click Attribution ──→ Affiliate Revenue
                                  │                    │
                                  ▼                    ▼
                           Refund Tracker        Price Drop Alerts
                           Return Window         Subscription Detection
                           
Gmail OAuth ──→ Historical Import ──→ (same dashboard, source='gmail')

Card Vault ──→ Offer Matching ──→ Effective Price ──→ Product Page + Deals
```

---

## 2. USER ROLE MATRIX

### Role Definitions

| Role | Description | Auth | Phase |
|---|---|---|---|
| Anonymous Visitor | Browse, search, compare (limited) | No | 1 |
| Registered User | Wishlists, alerts, reviews, @whyd.* email | Yes | 1 |
| Connected User | @whyd.* active OR Gmail/Outlook linked, full purchase intelligence | Yes + email | 1 |
| Premium User | All features, higher limits, priority alerts, subscription detection | Yes + payment | 1 |
| Verified Buyer | Purchase matched to review (via email data) | Auto-assigned | 1 |
| Power Reviewer | High-credibility community reviewer (earned) | Auto-assigned | 2 |
| Influencer | Declared affiliation, tagged in reviews | Manual verify | 2 |
| Moderator | Community + content moderation | Admin-assigned | 2 |
| Senior Moderator | Product merges, DudScore overrides | Admin-assigned | 2 |
| Data Ops | Crawler management, ingestion monitoring | Admin-assigned | 2 |
| Fraud Analyst | Trust signals, anomaly investigation | Admin-assigned | 2 |
| Trust Engineer | DudScore weight tuning, ML model review | Admin-assigned | 2 |
| Admin | Full platform control | Admin-assigned | 2 |
| Super Admin | RBAC management, destructive operations | Founder only | 1 |

### Permission Matrix

| Permission | Anon | Registered | Connected | Premium | Mod | Admin | Super |
|---|---|---|---|---|---|---|---|
| Search products | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| View product page | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| View TCO calculator | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Compare products | ✓(2) | ✓(4) | ✓(4) | ✓(4) | ✓ | ✓ | ✓ |
| View deals page | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Personalized deal prices | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Create @whyd.* email | ✗ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| View inbox | ✗ | ✗ | ✓ | ✓ | — | ✓ | ✓ |
| Send/reply from inbox | ✗ | ✗ | ✓ | ✓ | — | ✓ | ✓ |
| Purchase dashboard | ✗ | ✗ | ✓ | ✓ | — | ✓ | ✓ |
| Subscription detection | ✗ | ✗ | ✗ | ✓ | — | ✓ | ✓ |
| Save to wishlist | ✗ | ✓(20) | ✓(50) | ✓(∞) | ✓ | ✓ | ✓ |
| Price alerts | ✗ | ✓(5) | ✓(20) | ✓(∞) | ✓ | ✓ | ✓ |
| Write reviews | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Vote on reviews | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Start discussions | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Earn reward points | ✗ | ✓ | ✓ | ✓ | — | — | — |
| Redeem gift cards | ✗ | ✓ | ✓ | ✓ | — | — | — |
| Save cards (vault) | ✗ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| Connect Gmail/Outlook | ✗ | ✗ | ✓ | ✓ | — | ✓ | ✓ |
| Moderate reviews | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| Adjust DudScore weights | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| Manage RBAC | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |

### Rate Limits by Role

| Action | Anon | Registered | Connected | Premium |
|---|---|---|---|---|
| Search/min | 10 | 30 | 30 | 60 |
| Product views/min | 20 | 60 | 60 | 120 |
| Comparisons/day | 5 | 20 | 20 | ∞ |
| Reviews/day | 0 | 3 | 5 | 10 |
| Votes/day | 0 | 50 | 50 | 100 |
| Discussion threads/day | 0 | 5 | 5 | 10 |
| Discussion replies/day | 0 | 20 | 20 | 50 |
| TCO calculations/day | 5 | 20 | 20 | ∞ |
| Inbox emails (storage) | — | — | 1000 | ∞ |

### Abuse Vectors

| Role | Threat | Mitigation |
|---|---|---|
| Anonymous | Scraping, bot traffic | Rate limit, CAPTCHA after threshold, fingerprinting |
| Registered | Spam reviews, fake accounts, watchlist abuse | Review cooldown, phone verify for reviews, duplicate detection |
| Connected | Fake email data, token farming | Parsing validation, anomaly detection |
| Premium | Subscription sharing, API abuse | Device fingerprint, concurrent session limits |
| Moderator | Biased moderation, data extraction | Audit log, consistency scoring, two-person rule for bans |
| Rewards | Point farming, fake reviews for points | 48-hour review hold, quality check, daily/monthly caps, clawback |

---

## 3. USER STORIES

### Epic 1: Product Discovery

```
US-1.1  Search for "wireless earbuds under ₹2000" → ranked by DudScore, 
        autocomplete, results <200ms, affiliate links on buy buttons
US-1.2  Product page with aggregated specs, multi-marketplace prices, 
        review sentiment, DudScore breakdown, TCO (if applicable)
US-1.3  Compare up to 4 products side-by-side: specs, price, DudScore, 
        TCO, reviews, "better value" auto-highlighted
US-1.4  Search for product not in DB → on-demand scrape → results within 60s
US-1.5  Category-specific dynamic filters (battery life, storage, star rating)
```

### Epic 2: Price Intelligence

```
US-2.1  Price history graph across all marketplaces, lowest-ever marked
US-2.2  Set price alert: "Notify when this drops below ₹1500"
US-2.3  See if "60% off" deal is genuine via price history + inflation detection
US-2.4  "Best time to buy" indicator based on historical patterns
US-2.5  See personalized effective price based on my saved cards
US-2.6  See best card × marketplace combination ranked by effective price
US-2.7  See no-cost EMI options for my specific cards
```

### Epic 3: Review Intelligence

```
US-3.1  AI-generated summary of 500+ reviews: top 3 pros, top 3 cons
US-3.2  See which reviews are likely fake, with explanation
US-3.3  Rating distribution histogram with anomaly detection
US-3.4  Upvote/downvote reviews, sort by most helpful
```

### Epic 4: Shopping Email & Purchase Intelligence

```
US-4.1  Choose username + domain during signup → get ramesh@whyd.in (or .click or .shop)
US-4.2  Real-time availability check with cross-domain suggestions as I type
US-4.3  Step-by-step guide to register chosen email on Amazon, Flipkart, Myntra, etc.
US-4.4  Receive all shopping emails in Whydud inbox (real-time via Cloudflare Workers)
US-4.5  REPLY to marketplace emails from Whydud inbox (sent via Resend)
US-4.6  COMPOSE new email to marketplace support from Whydud inbox
US-4.7  Auto-detect orders, refunds, shipping updates, returns from emails
US-4.8  Purchase dashboard: lifetime spend, category/marketplace breakdown
US-4.9  Return window countdown with alerts at 3 days and 1 day
US-4.10 Refund delay detection with escalation reminders
US-4.11 Post-purchase price drop alert: "Price dropped ₹X — return window still open"
US-4.12 Subscription detection with annual cost calculation
US-4.13 Search across ALL purchases: "find my phone charger invoice" (cross-platform)
US-4.14 Connect Gmail/Outlook for historical purchase data (OAuth read-only)
US-4.15 Forward emails from Whydud inbox to personal email
US-4.16 Change email domain in Settings (whyd.in ↔ .click ↔ .shop)
US-4.17 Disconnect/delete email and all data at any time
```

### Epic 5: TCO Calculator

```
US-5.1  See "Total Cost of Ownership" section on AC product page
US-5.2  Select my city → auto-fill electricity tariff → adjust usage hours
US-5.3  See breakdown: purchase + electricity + maintenance + gas over 5 years
US-5.4  See category rank: "Top 27% cheapest to own"
US-5.5  Compare TCO of 3-star vs 5-star AC: break-even analysis
US-5.6  Save my city/tariff as defaults for all future TCO calculations
```

### Epic 6: Deals & Rewards

```
US-6.1  Browse Blockbuster Deals page: error pricing, lowest-ever, genuine discounts
US-6.2  Filter deals by category, discount %, recency
US-6.3  Earn points for writing reviews (20pts), connecting email (50pts), referrals (30pts)
US-6.4  Redeem points for Amazon/Flipkart/Swiggy gift cards
US-6.5  View points balance, history, and available gift cards
```

### Epic 7: Community

```
US-7.1  Start discussion thread on a product ("Does this support 5G on Jio?")
US-7.2  Reply to threads, upvote/downvote, mark answer as accepted
US-7.3  Choose thread type: question, experience, comparison, tip, alert
```

### Epic 8: User Account

```
US-8.1  Sign up with email/Google OAuth + optional @whyd.* email (choose domain) in under 2 minutes
US-8.2  Save cards to Card Vault (bank name + variant only, no card numbers)
US-8.3  Manage premium subscription via Razorpay
US-8.4  Export personal data (DPDP compliance)
US-8.5  Delete account + all data permanently
```

---

## 4. DUDSCORE ALGORITHM

### Philosophy

DudScore is a **trust-adjusted value signal**, not a rating. A 4.5-star product with fake reviews and price manipulation scores lower than a 4.0-star product with genuine reviews and stable pricing.

### Formula

```
DudScore = (
    W_sentiment × SentimentScore +
    W_rating_quality × RatingQualityScore +
    W_price_value × PriceValueScore +
    W_review_credibility × ReviewCredibilityScore +
    W_price_stability × PriceStabilityScore +
    W_return_signal × ReturnSignalScore
) × FraudPenaltyMultiplier × ConfidenceMultiplier

Normalized to 0-100 scale.
```

### Component Definitions

**SentimentScore (0-1):** Weighted average sentiment polarity across all reviews. Recent reviews weighted higher (exponential decay, half-life = 90 days). Verified purchase reviews weighted 2x. Uses spaCy + TextBlob for v1.

**RatingQualityScore (0-1):** Measures rating distribution health. Penalizes bimodal distributions (indicator of manipulation), rewards natural left-skewed distributions. Computed from standard deviation + kurtosis of rating distribution.

**PriceValueScore (0-1):** Price-to-feature ratio vs category peers. For categories with TCO models: incorporates TCO vs category average (40% weight). Rank-normalized within category.

**ReviewCredibilityScore (0-1):** Composite of verified purchase %, review length quality, copy-paste similarity detection, review burst detection, and reviewer account age distribution.

**PriceStabilityScore (0-1):** Based on price coefficient of variation over 90 days. Penalizes artificial inflation before sales. Penalizes excessive flash sale frequency.

**ReturnSignalScore (0-1):** Aggregated anonymized return/refund data from connected users. Cold start = 0.5 (neutral) if <10 data points.

### Weight Configuration (Versioned, Admin-Adjustable)

| Weight | Default | Range |
|---|---|---|
| W_sentiment | 0.25 | 0.1-0.4 |
| W_rating_quality | 0.15 | 0.05-0.3 |
| W_price_value | 0.20 | 0.1-0.3 |
| W_review_credibility | 0.20 | 0.1-0.35 |
| W_price_stability | 0.10 | 0.05-0.2 |
| W_return_signal | 0.10 | 0.0-0.2 |

Sum of weights = 1.0 (enforced by config validation).

### FraudPenaltyMultiplier (0.5-1.0)

- >30% suspected fake reviews → ×0.7
- Confirmed review farm → ×0.5
- Price inflation fraud → ×0.8
- Compound multipliers. Floor: 0.5.

### ConfidenceMultiplier (0.6-1.0)

- Reviews <5 → 0.6 (badge: "Not enough data")
- Reviews 5-20 → 0.7
- Reviews 20-50 → 0.8
- Reviews 50-200 → 0.9
- Reviews >200 → 1.0
- Price history <7 days → reduce by 0.1
- Single marketplace only → reduce by 0.05

### Display Scale

| Score | Label | Color |
|---|---|---|
| 90-100 | Excellent | Green |
| 70-89 | Good | Light green |
| 50-69 | Average | Yellow |
| 30-49 | Below Average | Orange |
| 0-29 | Dud | Red |
| NULL | Not Rated | Gray |

### Cold Start, Spike Detection, Recalculation Triggers

- **Cold start:** NULL score until ≥5 reviews. "Preliminary" badge until ≥20 reviews.
- **Spike detection:** If score changes >15 points in 24 hours → hold in pending → alert admin → auto-release after 48 hours if no action.
- **Recalculation triggers:** New reviews (batch), price change (batch), fraud flag (immediate), admin weight change (full recalc), moderator review removal (immediate), monthly scheduled (full).

---

## 5. FRAUD & ABUSE PREVENTION

### Layer 1: Review Fraud Detection (Rule-Based v1)

| Signal | Method | Threshold |
|---|---|---|
| Copy-paste | TF-IDF cosine similarity between reviews | >0.85 similarity → flag both |
| Rating burst | >30% of reviews in 48-hour window | Flag product, especially if all 5-star |
| Length anomaly | >40% of reviews <20 characters | Flag product |
| Distribution anomaly | (5-star% - 4-star%) > 40% | Bimodal flag |
| Reviewer clustering | Multiple reviews from accounts created in same 7-day window | Cluster flag |

v2 (post-launch): LightGBM model trained on moderator-labeled data.

### Layer 2: User Abuse Prevention

| Threat | Detection | Mitigation |
|---|---|---|
| Sockpuppets | Email domain + device fingerprint + behavioral similarity | Shadow ban, phone verification |
| Review spam | Frequency analysis, content similarity | Rate limit, 30-day cooldown per product |
| Point farming | Quality check on reviews, daily/monthly caps | 48-hour hold, clawback on fraud |
| Vote manipulation | Consistent voting patterns, ring detection | Rate limit, sockpuppet scan |
| Scraping/bots | Request patterns, header analysis | Rate limit → CAPTCHA → IP ban |
| OAuth abuse | Token usage anomaly | Token rotation, monitoring |

### Layer 3: Data Integrity

- Price manipulation: Detect MRP inflation >15% within 7 days before "sale"
- Product listing fraud: Title keyword stuffing, spec mismatches across marketplaces
- Offer accuracy: Flag offers not verified within 24 hours

### Layer 4: Platform Security

- Per-IP and per-user rate limiting (token bucket)
- Progressive bot challenges: rate limit → JS challenge → CAPTCHA
- Headless browser detection, TLS fingerprinting

---

## 6. DATA FLOW ARCHITECTURE

### Product Data Pipeline

```
STAGE 1: INGESTION
  Scrapy spiders (Amazon.in, Flipkart, Myntra, Snapdeal, Croma, etc.)
  → Raw HTML/JSON → Parse → Extract structured data → Redis Streams queue

STAGE 2: NORMALIZATION
  Consumer picks from queue → Clean title → Extract brand/model → 
  Normalize specs + units → Classify category → Extract images

STAGE 3: DEDUPLICATION & MATCHING
  Product Matching Engine:
  - Brand + model number match (high confidence >0.9 → auto-merge)
  - Fuzzy title match (medium 0.6-0.9 → manual review queue)
  - Spec similarity (supplementary)
  - Low confidence <0.6 → create new canonical product

STAGE 4: ENRICHMENT
  Per canonical product:
  - Aggregate reviews across marketplaces
  - Run sentiment analysis (spaCy)
  - Extract pros/cons
  - Detect fake reviews (rule-based)
  - Calculate price statistics
  - Scrape bank/card offers
  - Compute DudScore
  - Compute TCO (if category model exists)

STAGE 5: INDEXING
  Push to Meilisearch: full-text fields, filterable attributes, facets

STAGE 6: SERVING
  Meilisearch (search) + PostgreSQL (details) + Redis (cache)
```

### Email Stack Overview

```
Domains:
  whyd.in, whyd.click, whyd.shop  — User shopping emails (send + receive)
  whydud.com                      — Corporate (support, noreply, team)

Receiving: Cloudflare Email Routing (free) → Cloudflare Email Worker → Django webhook
Sending:   Resend API (from user's @whyd.* address, rate-limited to marketplace communication)
Corporate: Resend (noreply@whydud.com), Crisp.chat (support@whydud.com)

All 3 user domains share ONE Cloudflare Email Worker and ONE Django webhook.
No own email server. Zero maintenance.
```

### Email Pipeline — Receiving (All 3 Domains)

```
Email to ramesh@whyd.in (or .click or .shop)
  → Cloudflare MX → Cloudflare Email Worker (single worker, all 3 domains)
  → Extract: recipient (full address incl. domain), sender, subject, raw MIME
  → HMAC-signed POST → Django: POST /webhooks/email/inbound
  → Validate signature → Parse username + domain from recipient
  → Look up WhydudEmail by (username, domain) → find user_id
  → Encrypt raw body (AES-256-GCM) → Store in inbox_emails (direction='inbound')
  → Dispatch Celery task (email queue): parse_email.delay(inbox_email_id)
  → Celery: detect marketplace from sender domain
  → Categorize: order | shipping | delivery | refund | return | subscription | promo | otp | other
  → Parse based on category (AmazonOrderParser, FlipkartRefundParser, etc.)
  → Store structured data in parsed_orders / refund_tracking / return_windows / subscriptions
  → Match to canonical product (fuzzy match on product_name → products table)
  → Check for affiliate click attribution (match recent click_events within 7 days)
  → If return window detected: schedule alert tasks (3-day + 1-day)
  → If order + matching click: mark click_event.purchase_confirmed = True, award points
  → Send real-time notification to user
```

### Email Pipeline — Sending (User Reply/Compose)

```
User clicks Reply or Compose in Whydud inbox
  → Frontend: POST /api/v1/inbox/send { to, subject, body, in_reply_to? }
  → Backend validates:
    1. User owns active WhydudEmail
    2. Rate limit: ≤10 sends/day, ≤50/month (Redis counter)
    3. Recipient is allowed (replied-to sender OR known marketplace domain)
    4. Sanitize HTML body with nh3
  → Call Resend API:
    From: "{user.name} <ramesh@whyd.in>"
    To: recipient
    Headers: In-Reply-To + References (for email threading)
  → Store sent email in inbox_emails (direction='outbound')
  → Return message_id to frontend

Rate Limits:
  10 emails/day per user
  50 emails/month per user
  5 unique recipients/day
  Max attachment: 5MB (Phase 2)
  No BCC allowed

Allowed Recipients:
  - Any address that previously sent TO this user (reply)
  - Known marketplace domains: *@amazon.in, *@flipkart.com, *@myntra.com,
    *@nykaa.com, *@snapdeal.com, *@meesho.com, *@croma.com, *@ajio.com,
    *@tatacliq.com, *@jiomart.com, *@reliancedigital.in (+ subdomains)
  - User-entered address with CAPTCHA (after 5/day)
```

### Email Pipeline — Gmail OAuth (Supplementary)

```
User connects Gmail → OAuth read-only scope → Token encrypted at rest
  → Celery task every 6h: fetch emails from marketplace senders only
  → Gmail API query: from:(amazon.in OR flipkart.com OR ...) newer_than:90d
  → Same parser pipeline → Results merge into parsed_orders (source='gmail')
  → User can disconnect → All synced data deleted within 24h
```

### Email Pipeline — Multi-Account Aggregation

```
One user can have:
  - 1 @whyd.* email (primary, created during registration)
  - N Gmail connections (OAuth, read-only, periodic sync)
  - N Outlook connections (Microsoft Graph, read-only, periodic sync)

All sources tracked in email_intel.email_sources table.
All sources feed into same inbox_emails + parsed_orders via user_id FK.
Cross-platform search: WHERE user_id = X AND product_name ILIKE '%query%'
```

### DNS Configuration (All 3 User Domains — Identical Pattern)

```
whyd.in / whyd.click / whyd.shop:
  MX    10  route1.mx.cloudflare.net           ← Receive
  MX    20  route2.mx.cloudflare.net
  TXT       "v=spf1 include:_spf.mx.cloudflare.net include:resend.com ~all"
  TXT       _dmarc "v=DMARC1; p=reject; rua=mailto:dmarc@whydud.com"
  CNAME     resend._domainkey → (from Resend dashboard)  ← DKIM for sending

Cloudflare Email Routing catch-all rules:
  *@whyd.in    → Email Worker "whydud-email-handler"
  *@whyd.click → Email Worker "whydud-email-handler"
  *@whyd.shop  → Email Worker "whydud-email-handler"

whydud.com (corporate):
  MX → Cloudflare Email Routing
  support@whydud.com → Crisp.chat
  noreply@whydud.com → Resend (transactional sending)
```

### Email Cost

```
Cloudflare Email Routing (receive, all 3 domains)  Free
Cloudflare Email Workers                            Free (100K/day)
Resend (send from @whyd.* + noreply@whydud.com)    Free → $20/mo (50K/mo)
Domains: whyd.in + whyd.click + whyd.shop           ~₹3,000/yr total
Crisp.chat (support inbox)                          Free (2 seats)
Total at launch: ~₹3,000/yr + $0/mo
Total at 10K users: ~₹3,000/yr + $20/mo
```

### Retention Policy

| Data | Retention | Notes |
|---|---|---|
| Raw scraped HTML | 7 days | Delete |
| Product data | Forever | Core feature |
| Price snapshots (TimescaleDB) | Forever (compressed after 30 days) | Continuous aggregates for charts |
| Reviews | Forever | Core feature |
| User data | Until deletion requested | Soft delete → hard delete 30 days |
| Email OAuth tokens | Until disconnect | Immediate hard delete |
| Inbox emails (received) | Until user deletes or account deletion | Encrypted at rest |
| Inbox emails (sent) | Forever (within account lifetime) | User may need for disputes |
| Raw email bodies | 90 days encrypted, then metadata-only | Subject + sender kept, body purged |
| Gmail/Outlook synced emails | Until source disconnected | Hard delete within 24h of disconnect |
| Parsed order data | Until user deletes | Hard delete within 24h of request |
| Click events | Forever | Revenue attribution data |
| Admin audit logs | 7 years | Legal requirement |
| Search logs | 90 days | Anonymize after 30 days |

---

## 7. SYSTEM ARCHITECTURE

### Architecture: Modular Monolith (Django) + SSR Frontend (Next.js)

**Why this split:**
- 70-80% of server workload is Python-native (scraping, NLP, ML, data processing)
- Django gives free admin panel (~60% of Phase 2 admin console)
- Next.js gives SSR for SEO + React for interactive UI
- Both deployable on single VPS via Docker Compose

```
┌──────────────────────────────────────────────────────────────┐
│                      CONTABO VPS                              │
│               (6 vCPU, 16GB RAM, 400GB SSD)                  │
│                                                              │
│  ┌──────┐    ┌───────────────────────────────────────────┐   │
│  │Caddy │    │          Next.js Frontend (SSR)            │   │
│  │Proxy │───▶│  All UI pages, React components, API client│   │
│  │+SSL  │    └───────────────────────────────────────────┘   │
│  │      │         ▲                                          │
│  │      │         │ REST API (JSON)                          │
│  │      │         ▼                                          │
│  │      │    ┌───────────────────────────────────────────┐   │
│  │      │───▶│       Django Backend (Gunicorn)            │   │
│  │      │    │  DRF APIs, Auth, Business Logic, Admin     │   │
│  └──────┘    └───────────────────────────────────────────┘   │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │            Celery Workers (4 concurrent)               │   │
│  │  Scraping, DudScore, Price Alerts, Search Indexing,   │   │
│  │  Deal Detection, TCO Computation, Review Analysis      │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │           Celery Beat (Scheduler)                      │   │
│  │  Cron: scrape daily, price alerts 4-hourly, deals 30m │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │         Email Worker (Isolated Celery Queue)           │   │
│  │  Processes @whyd.* inbound + Gmail sync              │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────┐ ┌───────────┐ ┌───────────────┐           │
│  │ PostgreSQL   │ │   Redis   │ │  Meilisearch  │           │
│  │ +TimescaleDB │ │ Cache+Q   │ │  Search       │           │
│  └─────────────┘ └───────────┘ └───────────────┘           │
└──────────────────────────────────────────────────────────────┘

External (Free Tiers):
  Cloudflare (CDN, DNS, Email Workers)
  Resend (transactional email, 100/day free)
  Google OAuth (Gmail API)
  Razorpay (payments, 2% per transaction)
```

### Container Layout (Docker Compose)

| Service | RAM | Role |
|---|---|---|
| frontend (Next.js) | ~1GB | SSR + static serving |
| backend (Django + Gunicorn, 3 workers) | ~1GB | API + Django Admin |
| celery-worker (4 concurrent) | ~2GB | All background tasks |
| celery-beat | ~256MB | Task scheduler |
| email-worker (2 concurrent) | ~512MB | Isolated email processing |
| postgres (TimescaleDB) | ~2GB | Primary database |
| redis | ~512MB | Cache + queue broker + sessions + rate limits |
| meilisearch | ~1GB | Search engine |
| caddy | ~64MB | Reverse proxy + auto SSL |
| **Total** | **~8-9GB** | Fits 16GB VPS comfortably |

### Caddy Routing

```
whydud.com {
    handle /api/*    { reverse_proxy backend:8000 }
    handle /admin/*  { reverse_proxy backend:8000 }
    handle /webhooks/* { reverse_proxy backend:8000 }
    handle           { reverse_proxy frontend:3000 }
}
```

---

## 8. TECH STACK

| Layer | Technology | Rationale |
|---|---|---|
| **Backend** | Django 5 + Django REST Framework | Python ecosystem for scraping/NLP/ML. Free admin panel. Battle-tested ORM + migrations. |
| **Frontend** | Next.js 15 (App Router) | SSR for SEO. React for interactive UI. |
| **Language (BE)** | Python 3.12 | Scraping (Scrapy), NLP (spaCy), ML (scikit-learn), data (pandas/numpy) |
| **Language (FE)** | TypeScript (strict) | Type safety, shared API types |
| **Database** | PostgreSQL 16 + TimescaleDB | Relational + JSONB flexibility + time-series (price snapshots) |
| **Search** | Meilisearch v1.7 | Typo-tolerant, faceted search. <100MB RAM for 1M docs. 10x simpler than Elasticsearch. |
| **Cache/Queue** | Redis 7 | Cache + Celery broker + sessions + rate limiter. One tool, four uses. |
| **Task Queue** | Celery + Redis + Celery Beat | Production-grade async tasks. Cron scheduling. Retries. Separate queues. |
| **Scraping** | Scrapy + Playwright (Python) | Scrapy for structure, Playwright for JS-rendered pages. Industrial-grade. |
| **NLP** | spaCy + TextBlob | Sentiment analysis, entity extraction. Transformers for v2. |
| **Data Processing** | pandas + numpy | DudScore computation, TCO calculations, analytics. |
| **Auth** | Django AllAuth + DRF TokenAuth | Social auth (Google OAuth), email auth, session management. |
| **Styling** | Tailwind CSS 4 | Utility-first, minimal overhead. |
| **UI Components** | shadcn/ui | Copy-paste, no lock-in, accessible. |
| **Charts** | Recharts | Price charts, spend dashboards, TCO breakdown. |
| **Reverse Proxy** | Caddy 2 | Auto-SSL, zero config, health checks. |
| **CDN/DNS** | Cloudflare (free) | DDoS protection, CDN, DNS, Email Workers. |
| **Email Receive** | Cloudflare Email Workers | Free 100K/day. Webhook to Django. |
| **Email Send** | Resend (free 100/day) | Price alerts, refund alerts, notifications. |
| **Payments** | Razorpay | Indian payments, UPI, subscriptions. |
| **Monitoring** | Better Stack (free 5 monitors) + Pino logging | Uptime + structured logs. |
| **Container** | Docker + Docker Compose | Standard deployment. Portable between VPS providers. |
| **CI/CD** | GitHub Actions | Type check → lint → test → build → deploy to VPS. |
| **Backups** | pg_dump + Backblaze B2 (free 10GB) | 6-hourly DB backups. |

---

## 9. DATABASE SCHEMA

### Schema Organization

```
PostgreSQL Schemas:
  public          — Products, listings, reviews, sellers, offers, deals
  users           — Accounts, sessions, OAuth, wishlists, cards, rewards
  email_intel     — Inbox emails, parsed orders, refunds, returns, subscriptions (ISOLATED)
  scoring         — DudScore config + history
  tco             — TCO models, city data, calculations
  community       — Discussions, threads, votes
  admin           — Audit logs, RBAC, moderation cases (Phase 2)

TimescaleDB Hypertables:
  price_snapshots       — Price tracking (core hypertable)
  dudscore_history      — Score changes over time
  email_receive_metrics — Email volume monitoring
  scraper_metrics       — Crawler health tracking
```

### Core Tables (All Schemas)

```sql
-- ================================================================
-- SCHEMA: public (Products, Listings, Reviews, Offers, Deals)
-- ================================================================

CREATE TABLE marketplaces (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(100) NOT NULL,
    base_url        VARCHAR(500) NOT NULL,
    affiliate_tag   VARCHAR(100),
    affiliate_param VARCHAR(50),
    scraper_status  VARCHAR(20) DEFAULT 'active',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
-- Seed: amazon_in, flipkart, myntra, snapdeal, croma, tatacliq, 
-- reliancedigital, nykaa, ajio, meesho, jiomart

CREATE TABLE categories (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    name            VARCHAR(200) NOT NULL,
    parent_id       INTEGER REFERENCES categories(id),
    spec_schema     JSONB,
    level           SMALLINT NOT NULL DEFAULT 0,
    has_tco_model   BOOLEAN DEFAULT FALSE,
    product_count   INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE brands (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    name            VARCHAR(200) NOT NULL,
    aliases         TEXT[],
    verified        BOOLEAN DEFAULT FALSE,
    logo_url        VARCHAR(500),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(500) UNIQUE NOT NULL,
    title           VARCHAR(1000) NOT NULL,
    brand_id        INTEGER REFERENCES brands(id),
    category_id     INTEGER REFERENCES categories(id),
    description     TEXT,
    specs           JSONB,
    images          JSONB,

    dud_score               DECIMAL(5,2),
    dud_score_confidence    VARCHAR(20),
    dud_score_updated_at    TIMESTAMPTZ,
    avg_rating              DECIMAL(3,2),
    total_reviews           INTEGER DEFAULT 0,
    lowest_price_ever       DECIMAL(12,2),
    lowest_price_date       DATE,
    current_best_price      DECIMAL(12,2),
    current_best_marketplace VARCHAR(50),

    status          VARCHAR(20) DEFAULT 'active',
    merged_into_id  UUID REFERENCES products(id),
    is_refurbished  BOOLEAN DEFAULT FALSE,
    first_seen_at   TIMESTAMPTZ DEFAULT NOW(),
    last_scraped_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_products_brand ON products(brand_id);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_dudscore ON products(dud_score DESC NULLS LAST);
CREATE INDEX idx_products_status ON products(status) WHERE status = 'active';

CREATE TABLE sellers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    marketplace_id  INTEGER NOT NULL REFERENCES marketplaces(id),
    external_seller_id VARCHAR(200),
    name            VARCHAR(500) NOT NULL,
    avg_rating      DECIMAL(3,2),
    total_ratings   INTEGER DEFAULT 0,
    positive_pct    DECIMAL(5,2),
    ships_from      VARCHAR(200),
    fulfilled_by    VARCHAR(100),
    is_verified     BOOLEAN DEFAULT FALSE,
    seller_since    DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(marketplace_id, external_seller_id)
);

CREATE TABLE product_listings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id      UUID NOT NULL REFERENCES products(id),
    marketplace_id  INTEGER NOT NULL REFERENCES marketplaces(id),
    seller_id       UUID REFERENCES sellers(id),
    external_id     VARCHAR(200) NOT NULL,
    external_url    VARCHAR(2000) NOT NULL,
    affiliate_url   VARCHAR(2000),
    title           VARCHAR(1000),
    current_price   DECIMAL(12,2),
    mrp             DECIMAL(12,2),
    discount_pct    DECIMAL(5,2),
    in_stock        BOOLEAN DEFAULT TRUE,
    rating          DECIMAL(3,2),
    review_count    INTEGER DEFAULT 0,
    match_confidence DECIMAL(3,2),
    match_method    VARCHAR(50),
    last_scraped_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(marketplace_id, external_id)
);
CREATE INDEX idx_listings_product ON product_listings(product_id);

-- TimescaleDB Hypertable: Price Snapshots
CREATE TABLE price_snapshots (
    time            TIMESTAMPTZ NOT NULL,
    listing_id      UUID NOT NULL,
    product_id      UUID NOT NULL,
    marketplace_id  INTEGER NOT NULL,
    price           DECIMAL(12,2) NOT NULL,
    mrp             DECIMAL(12,2),
    discount_pct    DECIMAL(5,2),
    in_stock        BOOLEAN,
    seller_name     VARCHAR(500)
);
SELECT create_hypertable('price_snapshots', 'time');
ALTER TABLE price_snapshots SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'listing_id',
    timescaledb.compress_orderby = 'time DESC'
);
SELECT add_compression_policy('price_snapshots', INTERVAL '30 days');

-- Continuous aggregates
CREATE MATERIALIZED VIEW price_daily
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', time) AS day, product_id, marketplace_id,
       AVG(price) AS avg_price, MIN(price) AS min_price, MAX(price) AS max_price,
       last(price, time) AS closing_price, first(price, time) AS opening_price
FROM price_snapshots
GROUP BY day, product_id, marketplace_id;

SELECT add_continuous_aggregate_policy('price_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

CREATE TABLE reviews (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id      UUID NOT NULL REFERENCES product_listings(id),
    product_id      UUID NOT NULL REFERENCES products(id),
    external_review_id VARCHAR(200),
    reviewer_name   VARCHAR(200),
    rating          SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title           VARCHAR(500),
    body            TEXT,
    is_verified_purchase BOOLEAN DEFAULT FALSE,
    review_date     DATE,
    helpful_votes   INTEGER DEFAULT 0,
    sentiment_score DECIMAL(3,2),
    sentiment_label VARCHAR(20),
    extracted_pros  TEXT[],
    extracted_cons  TEXT[],
    credibility_score DECIMAL(3,2),
    fraud_flags     JSONB,
    is_flagged      BOOLEAN DEFAULT FALSE,
    content_hash    VARCHAR(64),
    upvotes         INTEGER DEFAULT 0,
    downvotes       INTEGER DEFAULT 0,
    vote_score      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(listing_id, external_review_id)
);
CREATE INDEX idx_reviews_product ON reviews(product_id);
CREATE INDEX idx_reviews_content_hash ON reviews(content_hash);

CREATE TABLE marketplace_offers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    marketplace_id  INTEGER NOT NULL REFERENCES marketplaces(id),
    scope_type      VARCHAR(20) NOT NULL,
    product_id      UUID REFERENCES products(id),
    listing_id      UUID REFERENCES product_listings(id),
    category_id     INTEGER REFERENCES categories(id),
    offer_type      VARCHAR(30) NOT NULL,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    bank_slug       VARCHAR(50),
    card_type       VARCHAR(20),
    card_network    VARCHAR(20),
    card_variants   TEXT[],
    wallet_provider VARCHAR(50),
    membership_type VARCHAR(50),
    coupon_code     VARCHAR(100),
    discount_type   VARCHAR(20) NOT NULL,
    discount_value  DECIMAL(8,2) NOT NULL,
    max_discount    DECIMAL(12,2),
    min_purchase    DECIMAL(12,2),
    emi_tenures     INTEGER[],
    emi_interest_rate DECIMAL(5,2),
    emi_processing_fee DECIMAL(8,2),
    valid_from      DATE,
    valid_until     DATE,
    is_active       BOOLEAN DEFAULT TRUE,
    stackable       BOOLEAN DEFAULT FALSE,
    source          VARCHAR(30) NOT NULL,
    last_verified_at TIMESTAMPTZ,
    terms_conditions TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_offers_active ON marketplace_offers(marketplace_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_offers_product ON marketplace_offers(product_id) WHERE product_id IS NOT NULL;
CREATE INDEX idx_offers_bank ON marketplace_offers(bank_slug) WHERE bank_slug IS NOT NULL;

CREATE TABLE deals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id      UUID NOT NULL REFERENCES products(id),
    listing_id      UUID REFERENCES product_listings(id),
    marketplace_id  INTEGER REFERENCES marketplaces(id),
    deal_type       VARCHAR(30) NOT NULL,
    current_price   DECIMAL(12,2) NOT NULL,
    reference_price DECIMAL(12,2),
    discount_pct    DECIMAL(5,2),
    confidence      VARCHAR(20) NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    detected_at     TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    ended_at        TIMESTAMPTZ,
    views           INTEGER DEFAULT 0,
    clicks          INTEGER DEFAULT 0,
    metadata        JSONB
);
CREATE INDEX idx_deals_active ON deals(is_active, deal_type) WHERE is_active = TRUE;

-- ================================================================
-- SCHEMA: users
-- ================================================================

CREATE TABLE users.accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(320) UNIQUE NOT NULL,
    email_verified  BOOLEAN DEFAULT FALSE,
    password_hash   VARCHAR(200),
    name            VARCHAR(200),
    avatar_url      VARCHAR(500),
    role            VARCHAR(30) DEFAULT 'registered',
    subscription_tier VARCHAR(20) DEFAULT 'free',
    subscription_expires_at TIMESTAMPTZ,
    has_whydud_email BOOLEAN DEFAULT FALSE,
    trust_score     DECIMAL(3,2) DEFAULT 0.50,
    is_suspended    BOOLEAN DEFAULT FALSE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users.whydud_emails (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL UNIQUE REFERENCES users.accounts(id) ON DELETE CASCADE,
    username        VARCHAR(30) NOT NULL,
    domain          VARCHAR(20) NOT NULL DEFAULT 'whyd.in',
    is_active       BOOLEAN DEFAULT TRUE,
    total_emails_received INTEGER DEFAULT 0,
    total_emails_sent     INTEGER DEFAULT 0,
    total_orders_detected INTEGER DEFAULT 0,
    last_email_received_at TIMESTAMPTZ,
    onboarding_complete BOOLEAN DEFAULT FALSE,
    marketplaces_registered JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_domain CHECK (domain IN ('whyd.in', 'whyd.click', 'whyd.shop')),
    CONSTRAINT unique_email_per_domain UNIQUE (username, domain)
);
-- email_address computed in app layer: f"{username}@{domain}"

CREATE TABLE users.reserved_usernames (
    username VARCHAR(30) PRIMARY KEY
);

CREATE TABLE users.oauth_connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users.accounts(id) ON DELETE CASCADE,
    provider        VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(200) NOT NULL,
    access_token_encrypted BYTEA,
    refresh_token_encrypted BYTEA,
    token_expires_at TIMESTAMPTZ,
    scopes          TEXT[],
    connected_at    TIMESTAMPTZ DEFAULT NOW(),
    last_sync_at    TIMESTAMPTZ,
    status          VARCHAR(20) DEFAULT 'active',
    UNIQUE(provider, provider_user_id)
);

CREATE TABLE users.wishlists (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users.accounts(id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL DEFAULT 'My Wishlist',
    is_default      BOOLEAN DEFAULT FALSE,
    is_public       BOOLEAN DEFAULT FALSE,
    share_slug      VARCHAR(100) UNIQUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users.wishlist_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wishlist_id     UUID NOT NULL REFERENCES users.wishlists(id) ON DELETE CASCADE,
    product_id      UUID NOT NULL REFERENCES products(id),
    price_when_added DECIMAL(12,2),
    target_price    DECIMAL(12,2),
    alert_enabled   BOOLEAN DEFAULT TRUE,
    last_alerted_at TIMESTAMPTZ,
    current_price   DECIMAL(12,2),
    price_change_pct DECIMAL(5,2),
    lowest_since_added DECIMAL(12,2),
    notes           TEXT,
    priority        SMALLINT DEFAULT 0,
    added_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(wishlist_id, product_id)
);

CREATE TABLE users.payment_methods (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users.accounts(id) ON DELETE CASCADE,
    method_type     VARCHAR(20) NOT NULL,
    bank_name       VARCHAR(100),
    card_variant    VARCHAR(200),
    card_network    VARCHAR(20),
    wallet_provider VARCHAR(50),
    wallet_balance  DECIMAL(12,2),
    upi_app         VARCHAR(50),
    upi_bank        VARCHAR(100),
    membership_type VARCHAR(50),
    emi_eligible    BOOLEAN DEFAULT FALSE,
    nickname        VARCHAR(100),
    is_preferred    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users.review_votes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id       UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users.accounts(id) ON DELETE CASCADE,
    vote            SMALLINT NOT NULL CHECK (vote IN (-1, 1)),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(review_id, user_id)
);

CREATE TABLE users.reward_points_ledger (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users.accounts(id),
    points          INTEGER NOT NULL,
    action_type     VARCHAR(50) NOT NULL,
    reference_type  VARCHAR(50),
    reference_id    UUID,
    description     VARCHAR(500),
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users.reward_balances (
    user_id         UUID PRIMARY KEY REFERENCES users.accounts(id),
    total_earned    INTEGER DEFAULT 0,
    total_spent     INTEGER DEFAULT 0,
    total_expired   INTEGER DEFAULT 0,
    current_balance INTEGER DEFAULT 0,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users.gift_card_catalog (
    id              SERIAL PRIMARY KEY,
    brand_name      VARCHAR(200) NOT NULL,
    brand_slug      VARCHAR(100) UNIQUE NOT NULL,
    brand_logo_url  VARCHAR(500),
    denominations   JSONB NOT NULL,
    category        VARCHAR(50),
    is_active       BOOLEAN DEFAULT TRUE,
    fulfillment_partner VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users.gift_card_redemptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users.accounts(id),
    catalog_id      INTEGER NOT NULL REFERENCES users.gift_card_catalog(id),
    denomination    DECIMAL(12,2) NOT NULL,
    points_spent    INTEGER NOT NULL,
    status          VARCHAR(30) DEFAULT 'pending',
    gift_card_code  TEXT,
    delivery_email  VARCHAR(320),
    fulfilled_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users.tco_profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL UNIQUE REFERENCES users.accounts(id) ON DELETE CASCADE,
    city_id         INTEGER,
    electricity_tariff_override DECIMAL(6,2),
    ac_hours_per_day SMALLINT,
    ownership_years  SMALLINT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ================================================================
-- SCHEMA: email_intel (ISOLATED)
-- ================================================================

CREATE TABLE email_intel.inbox_emails (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whydud_email_id UUID,
    user_id         UUID NOT NULL,
    message_id      VARCHAR(500) UNIQUE,
    direction       VARCHAR(10) DEFAULT 'inbound',   -- 'inbound' or 'outbound'
    sender_address  VARCHAR(320) NOT NULL,
    sender_name     VARCHAR(200),
    recipient_address VARCHAR(320),                   -- Full recipient including domain
    subject         VARCHAR(1000),
    received_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    body_text       TEXT,
    body_html       TEXT,
    raw_size_bytes  INTEGER,
    has_attachments BOOLEAN DEFAULT FALSE,
    category        VARCHAR(30),
    marketplace     VARCHAR(50),
    confidence      DECIMAL(3,2),
    parse_status    VARCHAR(20) DEFAULT 'pending',
    parsed_entity_type VARCHAR(30),
    parsed_entity_id UUID,
    resend_message_id VARCHAR(200),                   -- For tracking sent email delivery
    is_read         BOOLEAN DEFAULT FALSE,
    is_starred      BOOLEAN DEFAULT FALSE,
    is_deleted      BOOLEAN DEFAULT FALSE,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_inbox_user_date ON email_intel.inbox_emails(user_id, received_at DESC);
CREATE INDEX idx_inbox_unread ON email_intel.inbox_emails(user_id, is_read) WHERE is_read = FALSE AND is_deleted = FALSE;
CREATE INDEX idx_inbox_direction ON email_intel.inbox_emails(user_id, direction, received_at DESC);

-- Multi-account email source tracking
CREATE TABLE email_intel.email_sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users.accounts(id),
    source_type     VARCHAR(20) NOT NULL,             -- 'whydud_email', 'gmail', 'outlook', 'forward'
    email_address   VARCHAR(320) NOT NULL,
    oauth_connection_id UUID REFERENCES users.oauth_connections(id),
    whydud_email_id UUID REFERENCES users.whydud_emails(id),
    last_sync_at    TIMESTAMPTZ,
    next_sync_at    TIMESTAMPTZ,
    sync_cursor     VARCHAR(500),                     -- Gmail history ID / pagination token
    emails_synced   INTEGER DEFAULT 0,
    orders_detected INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    status          VARCHAR(20) DEFAULT 'active',     -- 'active', 'expired', 'error', 'disconnected'
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, email_address)
);

CREATE TABLE email_intel.parsed_orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    source          VARCHAR(20) DEFAULT 'whydud_email',
    order_id        VARCHAR(200),
    marketplace     VARCHAR(50) NOT NULL,
    product_name    VARCHAR(1000) NOT NULL,
    quantity        SMALLINT DEFAULT 1,
    price_paid      DECIMAL(12,2),
    tax             DECIMAL(12,2),
    shipping_cost   DECIMAL(12,2),
    total_amount    DECIMAL(12,2),
    currency        VARCHAR(3) DEFAULT 'INR',
    order_date      DATE,
    delivery_date   DATE,
    seller_name     VARCHAR(500),
    payment_method  VARCHAR(100),
    matched_product_id UUID,
    match_confidence DECIMAL(3,2),
    match_status    VARCHAR(20) DEFAULT 'pending',
    email_message_id VARCHAR(200),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, email_message_id)
);

CREATE TABLE email_intel.refund_tracking (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    order_id        UUID REFERENCES email_intel.parsed_orders(id),
    status          VARCHAR(30) NOT NULL,
    refund_amount   DECIMAL(12,2),
    initiated_at    TIMESTAMPTZ,
    expected_by     TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    marketplace     VARCHAR(50),
    delay_days      INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE email_intel.return_windows (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    order_id        UUID REFERENCES email_intel.parsed_orders(id),
    window_end_date DATE NOT NULL,
    is_extended     BOOLEAN DEFAULT FALSE,
    alert_sent_3day BOOLEAN DEFAULT FALSE,
    alert_sent_1day BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE email_intel.subscriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    service_name    VARCHAR(200) NOT NULL,
    amount          DECIMAL(12,2),
    currency        VARCHAR(3) DEFAULT 'INR',
    billing_cycle   VARCHAR(20),
    next_renewal    DATE,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ================================================================
-- TABLE: click_events (Affiliate Click Tracking)
-- ================================================================

CREATE TABLE public.click_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users.accounts(id),          -- NULL for anonymous
    session_id      VARCHAR(100),
    product_id      UUID NOT NULL REFERENCES public.products(id),
    listing_id      UUID REFERENCES public.product_listings(id),
    marketplace_id  INTEGER NOT NULL REFERENCES public.marketplaces(id),
    source_page     VARCHAR(50) NOT NULL,                        -- 'product_page', 'comparison', 'deal', 'search', 'homepage'
    source_section  VARCHAR(50),                                 -- 'best_deal_card', 'marketplace_prices'
    affiliate_url   VARCHAR(2000) NOT NULL,
    affiliate_tag   VARCHAR(100),
    sub_tag         VARCHAR(200),                                -- user123_prod456_click789
    purchase_confirmed BOOLEAN DEFAULT FALSE,
    confirmation_source VARCHAR(30),                             -- 'email_parsed', 'affiliate_report', 'user_reported'
    confirmed_at    TIMESTAMPTZ,
    price_at_click  DECIMAL(12,2),
    device_type     VARCHAR(20),
    referrer        VARCHAR(500),
    clicked_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_clicks_user ON public.click_events(user_id, clicked_at DESC);
CREATE INDEX idx_clicks_product ON public.click_events(product_id, clicked_at DESC);
CREATE INDEX idx_clicks_unconfirmed ON public.click_events(user_id, purchase_confirmed)
    WHERE purchase_confirmed = FALSE;

-- ================================================================
-- SCHEMA: admin (Platform Operations)
-- ================================================================

CREATE SCHEMA IF NOT EXISTS admin;

CREATE TABLE admin.audit_log (
    id              BIGSERIAL PRIMARY KEY,
    actor_id        UUID NOT NULL,
    actor_email     VARCHAR(320) NOT NULL,
    actor_role      VARCHAR(30) NOT NULL,
    action_type     VARCHAR(100) NOT NULL,             -- 'user.suspend', 'product.merge', 'review.remove'
    action_category VARCHAR(50) NOT NULL,              -- 'user_management', 'moderation', 'data_ops', 'scoring', 'system'
    entity_type     VARCHAR(50) NOT NULL,
    entity_id       VARCHAR(200) NOT NULL,
    entity_label    VARCHAR(500),
    old_value       JSONB,
    new_value       JSONB,
    reason          TEXT NOT NULL,                     -- Admin MUST provide reason
    ip_address      INET,
    is_automated    BOOLEAN DEFAULT FALSE,
    is_reversible   BOOLEAN DEFAULT TRUE,
    reversed_by     BIGINT REFERENCES admin.audit_log(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_actor ON admin.audit_log(actor_id, created_at DESC);
CREATE INDEX idx_audit_entity ON admin.audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_action ON admin.audit_log(action_type, created_at DESC);

CREATE TABLE admin.moderation_queue (
    id              BIGSERIAL PRIMARY KEY,
    entity_type     VARCHAR(50) NOT NULL,              -- 'review', 'thread', 'reply', 'product'
    entity_id       VARCHAR(200) NOT NULL,
    reason          VARCHAR(100) NOT NULL,             -- 'auto_flagged', 'user_reported', 'new_account'
    priority        VARCHAR(10) NOT NULL DEFAULT 'medium',
    details         JSONB,
    assigned_to     UUID,
    status          VARCHAR(20) DEFAULT 'pending',     -- 'pending', 'in_review', 'approved', 'rejected'
    resolved_by     UUID,
    resolution      VARCHAR(50),
    resolution_note TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);
CREATE INDEX idx_modqueue_status ON admin.moderation_queue(status, priority, created_at);

CREATE TABLE admin.scraper_runs (
    id              BIGSERIAL PRIMARY KEY,
    marketplace_id  INTEGER NOT NULL,
    spider_name     VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL,              -- 'running', 'completed', 'failed', 'cancelled'
    started_at      TIMESTAMPTZ NOT NULL,
    completed_at    TIMESTAMPTZ,
    products_scraped INTEGER DEFAULT 0,
    products_failed  INTEGER DEFAULT 0,
    pages_crawled   INTEGER DEFAULT 0,
    error_message   TEXT,
    triggered_by    VARCHAR(50),                       -- 'schedule', 'manual', 'adhoc'
    triggered_by_user UUID
);
CREATE INDEX idx_scraper_runs ON admin.scraper_runs(marketplace_id, started_at DESC);

CREATE TABLE admin.alerts (
    id              BIGSERIAL PRIMARY KEY,
    severity        VARCHAR(10) NOT NULL,              -- 'critical', 'high', 'medium', 'low'
    category        VARCHAR(50) NOT NULL,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    acknowledged_by UUID,
    acknowledged_at TIMESTAMPTZ,
    snoozed_until   TIMESTAMPTZ,
    auto_resolved   BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);

CREATE TABLE admin.site_config (
    id              SERIAL PRIMARY KEY,
    key             VARCHAR(200) UNIQUE NOT NULL,
    value           JSONB NOT NULL,
    description     TEXT,
    category        VARCHAR(50),
    value_type      VARCHAR(20),
    updated_by      UUID,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ================================================================
-- SCHEMA: scoring
-- ================================================================

CREATE TABLE scoring.dudscore_config (
    id              SERIAL PRIMARY KEY,
    version         INTEGER NOT NULL,
    w_sentiment     DECIMAL(4,3) NOT NULL,
    w_rating_quality DECIMAL(4,3) NOT NULL,
    w_price_value   DECIMAL(4,3) NOT NULL,
    w_review_credibility DECIMAL(4,3) NOT NULL,
    w_price_stability DECIMAL(4,3) NOT NULL,
    w_return_signal DECIMAL(4,3) NOT NULL,
    fraud_penalty_threshold DECIMAL(3,2) NOT NULL,
    min_review_threshold INTEGER NOT NULL,
    cold_start_penalty DECIMAL(3,2) NOT NULL,
    anomaly_spike_threshold DECIMAL(5,2) NOT NULL,
    is_active       BOOLEAN DEFAULT FALSE,
    activated_at    TIMESTAMPTZ,
    created_by      UUID,
    change_reason   TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT weights_sum CHECK (
        ABS(w_sentiment + w_rating_quality + w_price_value +
            w_review_credibility + w_price_stability + w_return_signal - 1.0) < 0.001
    )
);

-- ================================================================
-- SCHEMA: tco
-- ================================================================

CREATE TABLE tco.models (
    id              SERIAL PRIMARY KEY,
    category_id     INTEGER NOT NULL REFERENCES categories(id),
    name            VARCHAR(200) NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    is_active       BOOLEAN DEFAULT TRUE,
    input_schema    JSONB NOT NULL,
    cost_components JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(category_id, version)
);

CREATE TABLE tco.city_reference_data (
    id              SERIAL PRIMARY KEY,
    city_name       VARCHAR(200) NOT NULL,
    state           VARCHAR(100) NOT NULL,
    electricity_tariff_residential DECIMAL(6,2),
    cooling_days_per_year INTEGER,
    humidity_level  VARCHAR(20),
    water_tariff_per_kl DECIMAL(6,2),
    water_hardness  VARCHAR(20),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(city_name, state)
);

-- ================================================================
-- SCHEMA: community
-- ================================================================

CREATE TABLE community.discussion_threads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id      UUID NOT NULL REFERENCES products(id),
    user_id         UUID NOT NULL,
    thread_type     VARCHAR(20) NOT NULL,
    title           VARCHAR(300) NOT NULL,
    body            TEXT NOT NULL,
    reply_count     INTEGER DEFAULT 0,
    upvotes         INTEGER DEFAULT 0,
    downvotes       INTEGER DEFAULT 0,
    view_count      INTEGER DEFAULT 0,
    is_pinned       BOOLEAN DEFAULT FALSE,
    is_locked       BOOLEAN DEFAULT FALSE,
    is_removed      BOOLEAN DEFAULT FALSE,
    last_reply_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_threads_product ON community.discussion_threads(product_id, created_at DESC);

CREATE TABLE community.discussion_replies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id       UUID NOT NULL REFERENCES community.discussion_threads(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL,
    parent_reply_id UUID REFERENCES community.discussion_replies(id),
    body            TEXT NOT NULL,
    upvotes         INTEGER DEFAULT 0,
    downvotes       INTEGER DEFAULT 0,
    is_accepted     BOOLEAN DEFAULT FALSE,
    is_removed      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE community.discussion_votes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    target_type     VARCHAR(10) NOT NULL,
    target_id       UUID NOT NULL,
    vote            SMALLINT NOT NULL CHECK (vote IN (-1, 1)),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, target_type, target_id)
);

-- ================================================================
-- SCHEMA: admin (Phase 2 — Defined now, built later)
-- ================================================================

CREATE TABLE admin.action_logs (
    id              BIGSERIAL PRIMARY KEY,
    actor_id        UUID NOT NULL,
    action_type     VARCHAR(100) NOT NULL,
    entity_type     VARCHAR(50) NOT NULL,
    entity_id       VARCHAR(200) NOT NULL,
    old_value       JSONB,
    new_value       JSONB,
    reason          TEXT,
    ip_address      INET,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_actor ON admin.action_logs(actor_id);
CREATE INDEX idx_audit_entity ON admin.action_logs(entity_type, entity_id);
```

### Bank/Card Reference Data

```sql
CREATE TABLE bank_cards (
    id              SERIAL PRIMARY KEY,
    bank_slug       VARCHAR(50) NOT NULL,
    bank_name       VARCHAR(100) NOT NULL,
    card_variant    VARCHAR(200) NOT NULL,
    card_type       VARCHAR(20) NOT NULL,
    card_network    VARCHAR(20),
    is_co_branded   BOOLEAN DEFAULT FALSE,
    co_brand_partner VARCHAR(50),
    default_cashback_pct DECIMAL(4,2),
    logo_url        VARCHAR(500),
    UNIQUE(bank_slug, card_variant, card_type)
);
-- Seed: HDFC (Regalia, Millennia, Diners, MoneyBack), SBI (SimplyCLICK, Prime, Elite),
-- ICICI (Amazon Pay, Coral, Rubyx), Axis (Flipkart, My Zone, Magnus),
-- Kotak (811, Royale Signature), AMEX (Membership, SmartEarn), etc.
```

---

## 10. API CONTRACTS

### API Design Principles

- REST with consistent response wrapper: `{ success, data?, error?: { code, message } }`
- Cursor-based pagination (not offset)
- Rate limiting headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- Auth: HTTP-only secure cookies (session) or Bearer token (API)
- Timestamps: ISO 8601 UTC
- Prices: Paisa (integer) in API, display layer converts to ₹

### Complete Endpoint Map (~65+ endpoints)

```
SEARCH & DISCOVERY
  GET    /api/v1/search                           # Product search with filters/facets
  GET    /api/v1/search/autocomplete              # Autocomplete suggestions
  POST   /api/v1/search/adhoc                     # Trigger on-demand scrape

PRODUCTS
  GET    /api/v1/products/:slug                   # Full product page data
  GET    /api/v1/products/:slug/price-history     # Price chart data
  GET    /api/v1/products/:slug/reviews           # Paginated reviews
  GET    /api/v1/products/:slug/best-deals        # Personalized card × marketplace deals
  GET    /api/v1/products/:slug/tco               # TCO calculation
  GET    /api/v1/products/:slug/discussions        # Discussion threads

COMPARISON
  GET    /api/v1/compare                          # Compare up to 4 products
  GET    /api/v1/compare/best-deals               # Deals across comparison set
  POST   /api/v1/compare/tco                      # TCO comparison

DEALS
  GET    /api/v1/deals                            # Browse active deals
  GET    /api/v1/deals/:id                        # Deal detail
  POST   /api/v1/deals/:id/click                  # Track affiliate click

AUTH
  POST   /api/v1/auth/register                    # Email registration
  POST   /api/v1/auth/login                       # Email login
  POST   /api/v1/auth/google                      # Google OAuth
  POST   /api/v1/auth/logout                      # Logout
  GET    /api/v1/me                               # Current user profile
  DELETE /api/v1/me                               # Account deletion

@WHYD.* SHOPPING EMAIL
  POST   /api/v1/email/whydud/create              # Create email (username + domain)
  GET    /api/v1/email/whydud/check-availability?username=X&domain=Y  # Availability + cross-domain suggestions
  GET    /api/v1/email/whydud/status               # Email status + stats
  PATCH  /api/v1/email/whydud/onboarding           # Update onboarding progress
  PUT    /api/v1/email/whydud/domain               # Change domain (whyd.in ↔ .click ↔ .shop)
  GET    /api/v1/email/whydud/suggestions?name=X&email=Y  # Username suggestions

INBOX
  GET    /api/v1/inbox                            # List emails (filtered, paginated)
  GET    /api/v1/inbox/:id                        # Read email (decrypts body)
  PATCH  /api/v1/inbox/:id                        # Mark read/starred
  DELETE /api/v1/inbox/:id                        # Soft delete
  POST   /api/v1/inbox/send                       # Send/reply email via Resend (rate-limited)
  POST   /api/v1/inbox/:id/forward                # Forward to personal email
  POST   /api/v1/inbox/:id/reparse                # Re-run parser
  PATCH  /api/v1/inbox/bulk                       # Bulk mark read/delete
  GET    /api/v1/inbox/stats                      # Inbox analytics
  GET    /api/v1/inbox/sent                       # Sent emails list

EMAIL SOURCES (Multi-Account)
  GET    /api/v1/email/sources                    # List connected email sources
  POST   /api/v1/email/connect/google             # Connect Gmail (OAuth read-only)
  POST   /api/v1/email/connect/outlook            # Connect Outlook (Microsoft Graph)
  POST   /api/v1/email/sources/:id/sync           # Trigger manual sync
  DELETE /api/v1/email/sources/:id                # Disconnect source + delete data

AFFILIATE CLICK TRACKING
  POST   /api/v1/clicks/track                     # Log click, return affiliate redirect URL
  GET    /api/v1/clicks/history                   # User's click history (transparency)

PURCHASES
  GET    /api/v1/purchases                        # Order history (all sources aggregated)
  GET    /api/v1/purchases/search?q=charger       # Cross-platform purchase search
  GET    /api/v1/purchases/dashboard              # Spend analytics
  GET    /api/v1/purchases/refunds                # Refund tracking
  GET    /api/v1/purchases/return-windows         # Return window countdowns
  GET    /api/v1/purchases/subscriptions          # Detected subscriptions
  GET    /api/v1/purchases/price-drops            # Post-purchase price drops

WISHLISTS
  GET    /api/v1/wishlists                        # User's wishlists
  POST   /api/v1/wishlists                        # Create wishlist
  PATCH  /api/v1/wishlists/:id                    # Update wishlist
  DELETE /api/v1/wishlists/:id                    # Delete wishlist
  POST   /api/v1/wishlists/:id/items              # Add product
  DELETE /api/v1/wishlists/:id/items/:product_id   # Remove product
  PATCH  /api/v1/wishlists/:id/items/:product_id   # Update target price/notes
  GET    /api/v1/wishlists/shared/:slug            # Public wishlist

CARD VAULT
  GET    /api/v1/cards                            # List saved payment methods
  POST   /api/v1/cards                            # Add payment method
  PATCH  /api/v1/cards/:id                        # Update
  DELETE /api/v1/cards/:id                        # Remove
  GET    /api/v1/cards/banks                      # List all banks
  GET    /api/v1/cards/banks/:slug/variants        # Bank card variants

REVIEWS & VOTES
  POST   /api/v1/reviews/:id/vote                 # Upvote/downvote
  DELETE /api/v1/reviews/:id/vote                 # Remove vote

DISCUSSIONS
  POST   /api/v1/products/:slug/discussions       # Create thread
  GET    /api/v1/discussions/:id                   # Thread with replies
  POST   /api/v1/discussions/:id/replies           # Add reply
  PATCH  /api/v1/discussions/:id                   # Edit thread
  DELETE /api/v1/discussions/:id                   # Soft delete
  POST   /api/v1/discussions/:id/vote              # Vote on thread
  POST   /api/v1/discussions/replies/:id/vote      # Vote on reply
  POST   /api/v1/discussions/replies/:id/accept    # Mark as answer

REWARDS
  GET    /api/v1/rewards/balance                  # Points balance
  GET    /api/v1/rewards/history                  # Points ledger
  GET    /api/v1/rewards/gift-cards               # Gift card catalog
  POST   /api/v1/rewards/redeem                   # Redeem points
  GET    /api/v1/rewards/redemptions              # Redemption history

TCO
  GET    /api/v1/tco/models/:category_slug         # TCO model for category
  GET    /api/v1/tco/cities                        # City list with tariffs
  PATCH  /api/v1/tco/profile                       # Save TCO preferences

SUBSCRIPTION
  POST   /api/v1/subscription/create              # Razorpay order
  POST   /api/v1/subscription/verify              # Payment verification
  POST   /api/v1/subscription/cancel              # Cancel premium

OFFERS
  GET    /api/v1/offers/active                    # Browse all offers

WEBHOOKS (INTERNAL)
  POST   /webhooks/email/inbound                  # Cloudflare Email Worker
  POST   /webhooks/razorpay                       # Payment callbacks
```

---

## 11. FRONTEND ARCHITECTURE

### Project Structure

```
frontend/
├── src/
│   ├── app/                      # Next.js App Router
│   │   ├── (public)/             # Public routes
│   │   │   ├── page.tsx          # Homepage
│   │   │   ├── search/           # Search results
│   │   │   ├── product/[slug]/   # Product page
│   │   │   ├── compare/          # Comparison
│   │   │   ├── deals/            # Blockbuster deals
│   │   │   └── categories/[slug]/
│   │   ├── (auth)/               # Auth routes
│   │   │   ├── login/
│   │   │   ├── register/         # Multi-step: account → @whyd.* → onboarding
│   │   │   └── layout.tsx
│   │   ├── (dashboard)/          # Authenticated routes
│   │   │   ├── dashboard/        # Purchase dashboard
│   │   │   ├── inbox/            # @whyd.* inbox
│   │   │   ├── wishlists/
│   │   │   ├── purchases/
│   │   │   ├── refunds/
│   │   │   ├── subscriptions/
│   │   │   ├── rewards/          # Points + gift cards
│   │   │   ├── settings/         # Profile + cards + @whyd.* + TCO
│   │   │   └── layout.tsx
│   │   ├── api/                  # Next.js API routes (proxy to Django if needed)
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/                   # shadcn/ui base
│   │   ├── product/              # Product domain
│   │   ├── search/               # Search domain
│   │   ├── dashboard/            # Dashboard domain
│   │   ├── inbox/                # Email inbox
│   │   ├── deals/                # Deals domain
│   │   ├── rewards/              # Rewards domain
│   │   ├── tco/                  # TCO calculator
│   │   ├── payments/             # Card vault + deal optimizer
│   │   ├── discussions/          # Threads + replies
│   │   └── layout/               # Header, footer, sidebar
│   ├── lib/
│   │   ├── api/                  # Django API client (typed)
│   │   └── utils/
│   ├── hooks/
│   └── config/
├── public/
├── tailwind.config.ts
├── next.config.ts
└── package.json
```

### Design Principles

| Principle | Implementation |
|---|---|
| Atomic Design | ui/ (atoms) → domain components (molecules) → pages (templates) |
| API Abstraction | All calls through lib/api/. Never raw fetch in components. |
| Error Boundaries | Every page wrapped. Graceful fallback. |
| Skeleton Loading | Every data component has skeleton variant. |
| Lazy Loading | Dynamic imports for charts, comparison tables, TCO calculator. |
| Image Optimization | Next.js Image. WebP/AVIF. Lazy below fold. |
| Responsive | Mobile-first. sm(640) md(768) lg(1024) xl(1280). |
| Accessible | ARIA labels, keyboard nav, focus management, AA+ contrast. |
| SEO | SSR product pages. Dynamic meta + JSON-LD. Sitemap. |
| Dark Mode | CSS variables via Tailwind. System preference + user toggle. |

---

## 12. EDGE CASES (COMPREHENSIVE)

### Product Data
- Same product with slight title variations → fuzzy matching + manual review queue
- Bundle vs base product → separate entries, tagged relationship
- Refurbished vs new → `is_refurbished` flag, separate DudScore
- Storage/color variants → variant dimension on canonical product
- Product discontinued → status change, keep history, suggest alternatives
- Marketplace removes listing → `in_stock: false`, retain data
- Price = ₹0 or ₹99,99,999 → validation, reject outliers, flag for review
- Specs conflict between marketplaces → use more detailed source, flag for moderator
- Flash sale price (2 hours) → mark as flash, don't use for "lowest ever" unless >24h
- Coupon/bank discount → show note "Additional offers may apply", don't include in base history

### Email
- Order email in Hindi → v1 English only, queue non-English for future
- Multiple items in one order → parse each line item separately
- Email format changes (Amazon redesign) → parser versioning, success rate monitoring, rollback
- Duplicate emails → dedup on message_id header
- User has 10,000+ emails → paginated processing, limit initial sync to 12 months
- OAuth token expires → refresh flow, notify if refresh fails, don't delete data
- @whyd.* spam → per-address rate limit (500/day), sender blocklists

### Payments/Offers
- Offer expired between scrape and user view → show "Offer may have expired", confidence badge
- Two bank offers from same bank → typically don't stack, greedy selection
- User's card not in our database → "Add manually" option, suggest closest match
- Offer terms change mid-day → 6-hour scrape cycle catches most, flag staleness

### TCO
- Product missing key spec (annual consumption kWh) → use category average, flag as estimated
- City not in reference data → nearest city auto-suggest, or manual tariff entry
- TCO model doesn't exist for category → show "TCO not available" gracefully
- Unreasonable inputs (24hrs/day AC usage) → validate, show warning but allow

### DudScore
- Product with 2 five-star reviews → low confidence (0.6), "Preliminary" badge
- Sudden influx of 1-star reviews → spike detection, hold for review
- Excellent reviews but way overpriced → PriceValueScore pulls score down (feature, not bug)
- Brand new category (<5 products) → neutral PriceValueScore (0.5)

### User
- Sign up with email, later Google OAuth with same email → merge accounts
- Premium expires with 30 wishlist items (free allows 20) → keep all, pause alerts beyond limit
- @whyd.* address receives non-shopping email → categorize as "other", don't parse
- User deletes account → all data (including @whyd.* emails) hard deleted within 24 hours

### Email
- Username taken on whyd.in but available on whyd.click → show as cross-domain suggestion
- User changes domain → old domain address keeps receiving for 90 days (grace period, forwarded to new)
- Marketplace sends verification OTP email → user sees it in inbox, clicks link (opens in browser)
- User needs to REPLY to marketplace → uses inbox Reply, sent via Resend with proper threading headers
- User tries to send to non-marketplace personal contact → blocked with friendly error message
- Email body contains tracking pixel → external images proxied, pixel blocked
- Cloudflare Worker fails → email forwarded to dead letter address for manual retry
- Resend send fails → retry 3× with exponential backoff, notify user if all fail
- User hits 10/day send limit → show "Limit reached. Resets at midnight UTC."
- Multiple users try same username+domain simultaneously → DB unique constraint handles race condition
- Large attachment (>25MB) → Cloudflare Worker drops, bounce notification to sender
- User replies to email thread → In-Reply-To + References headers set for proper threading in recipient's mail client
- Email from unknown sender to @whyd.* → stored as 'other' category, not parsed, still viewable in inbox

---

## 13. PAGE-LEVEL COMPONENT BREAKDOWN

### All Pages (14 pages)

| # | Route | Page | Auth |
|---|---|---|---|
| 1 | `/` | Homepage | No |
| 2 | `/search` | Search Results | No |
| 3 | `/product/:slug` | Product Detail | No |
| 4 | `/compare` | Comparison | No |
| 5 | `/deals` | Blockbuster Deals | No |
| 6 | `/login` | Login | No |
| 7 | `/register` | Multi-step Registration | No |
| 8 | `/dashboard` | Purchase Dashboard | Yes (Connected) |
| 9 | `/inbox` | @whyd.* Inbox | Yes (Connected) |
| 10 | `/wishlists` | Wishlists | Yes |
| 11 | `/rewards` | Rewards + Gift Cards | Yes |
| 12 | `/discussions/:id` | Thread Detail | No (to read), Yes (to post) |
| 13 | `/settings` | Settings (Profile, Cards, @whyd.*, TCO, Subscription) | Yes |
| 14 | `/admin/*` | Django Admin (Phase 2 — free from Django) | Admin |

### Key Page Structures

**Product Page** — The most complex page:
```
/product/:slug
├── Breadcrumbs
├── ProductHero (image gallery + title + DudScore + key specs)
├── PricingPanel (ENHANCED)
│   ├── Multi-marketplace prices
│   ├── PersonalizedDealCard (best card × marketplace combo)
│   ├── AllDealOptions (ranked by effective price)
│   ├── EMI options
│   ├── PriceAlertButton
│   └── WishlistButton
├── DudScoreBreakdown (radar chart + component bars)
├── PriceHistory (TimescaleDB-powered chart)
├── TCOSection (if category supports it)
│   ├── Input form (city, usage, tariff)
│   ├── Cost breakdown chart
│   ├── Category rank
│   └── Conclusion
├── SpecsTable
├── OffersSection (all bank/card offers)
├── ReviewsSection
│   ├── AI summary (pros/cons)
│   ├── Rating distribution + anomaly flag
│   ├── ReviewCard × N (with vote buttons + credibility badge)
│   └── LoadMore
├── DiscussionsSection (threads preview)
├── SimilarProducts
└── Footer
```

**Inbox** — Two-panel email client:
```
/inbox
├── InboxSidebar (folders: All, Orders, Shipping, Refunds, Subscriptions, Promos, Starred, Trash)
├── EmailList (sender, subject, category badge, time, parsed badge)
├── EmailReader (header + parsed data card + sanitized HTML body)
```

**Dashboard** — Purchase intelligence:
```
/dashboard
├── SpendOverview (lifetime total + monthly trend chart)
├── CategoryBreakdown (pie chart)
├── MarketplaceBreakdown (bar chart)
├── AlertsPanel (return windows expiring, refunds pending, price drops)
├── RecentOrders (last 10)
├── DudExposureCard ("X% of purchases scored below 40")
├── EmailSyncStatus
```

---

## 14. DEPLOYMENT PLAN

### Infrastructure

```
VPS: Contabo VPS M (6 vCPU, 16GB RAM, 400GB SSD) — ~€10-12/mo
     Or Hetzner CPX31 (4 vCPU, 8GB RAM) — ~€15/mo
Location: EU (Contabo) or Ashburn (Hetzner) — Cloudflare CDN handles India latency
Domain: whydud.com + whyd.in + whyd.click + whyd.shop
Cloudflare: Free tier (DNS, CDN, DDoS, Email Workers, Page Rules)
```

### Docker Compose (Production)

9 containers as defined in Section 7. Total RAM: ~8-9GB.

### CI/CD Pipeline (GitHub Actions)

```
Push to main → TypeScript check → Lint → Tests → Build Docker images → 
Push to GHCR → SSH to VPS → Pull images → docker compose up -d → 
Run migrations → Health check → Rollback on failure
```

### Backup Strategy

```
PostgreSQL: pg_dump every 6 hours → compress → Backblaze B2 (free 10GB)
Redis: AOF persistence (data is cache — loss is recoverable)
Meilisearch: Daily snapshot (can rebuild from PostgreSQL)
VPS: Weekly Contabo snapshot
```

---

## 15. OBSERVABILITY & MONITORING

### Logging

Structured JSON logging (Python `structlog`):
```json
{"level": "info", "timestamp": "...", "service": "backend", "request_id": "...", 
 "action": "product_search", "query": "earbuds", "results": 42, "latency_ms": 87}
```

### Key Metrics & Alert Thresholds

| Metric | Alert If |
|---|---|
| API p95 latency | >500ms |
| Error rate | >1% |
| Scraper success rate | <90% per marketplace |
| Search latency p95 | >200ms |
| DB connection pool | >80% |
| Redis memory | >80% |
| Email parse success rate | <95% |
| Disk usage | >80% |
| CPU sustained | >90% for 5min |

### Tools

- Better Stack (free: 5 monitors, 3-min interval) for uptime
- Cron health check script → Telegram bot notification on failure
- Scraper failure → Telegram alert
- Django Silk (debug) or django-prometheus (production) for API metrics

---

## 16. SECURITY STRATEGY

### Authentication

- Passwords: bcrypt (cost 12), min 8 chars, 5 failed attempts → 15min lockout
- Sessions: HTTP-only, Secure, SameSite=Strict, 7-day expiry (30-day with remember me)
- OAuth: PKCE flow, state parameter, tokens AES-256-GCM encrypted at rest

### Data Protection

- Email bodies: encrypted at rest (AES-256-GCM, key in env var)
- OAuth tokens: encrypted at rest (separate key)
- Card vault: NO card numbers stored. Zero PCI-DSS requirement.
- Email HTML: sanitized with nh3 (Rust-based), external images proxied
- TLS 1.3 everywhere (Caddy auto-SSL), HSTS headers

### DPDP Act Compliance (India)

- Clear consent before data collection (consent modal)
- Purpose limitation (only order extraction, stated clearly)
- Data minimization (structured data only, not email body analysis beyond parsing)
- Right to erasure (account deletion within 72 hours)
- Right to data portability (JSON export)
- Grievance officer designated

### Security Headers

```
CSP: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

---

## 17. SCALING STRATEGY

| Users | Infrastructure | Changes |
|---|---|---|
| 0-10K | Single VPS (16GB), Docker Compose | Current architecture. Optimize queries + caching. |
| 10K-100K | 2 VPS nodes | Separate DB to dedicated VPS. Read replica. CDN handles statics. |
| 100K-1M | 3-5 nodes, Docker Swarm or K8s | Horizontal app scaling. Dedicated scraper nodes. Redis Cluster. Partition price_snapshots. |
| 1M-10M | Full distributed | Multi-region. Kafka replacing Redis Streams. Elasticsearch if Meilisearch hits limits. Dedicated ML servers. |

### Key Principle

Optimize before scaling out. PostgreSQL handles 10M+ rows with proper indexing. Cache aggressively (product pages = 1hr, search = 15min, DudScores = until recalculated). Background everything. Denormalize for reads.

---

## 18. COST OPTIMIZATION

### Launch Budget

| Item | Monthly Cost |
|---|---|
| Contabo VPS M | ~$12 |
| whyd.in + whyd.click + whyd.shop domains | ~₹3,000/yr (~$36/yr) |
| Proxy rotation (scraping) | $20-50 |
| Cloudflare | $0 |
| Resend | $0 |
| Better Stack | $0 |
| GitHub | $0 |
| Backblaze B2 | $0 |
| Google OAuth | $0 |
| Razorpay | 2% per transaction |
| Gift card fulfillment | Variable (per redemption) |
| **TOTAL** | **$35-65/mo** |

### Revenue at 10K Users

```
Affiliate (5% click, 3% convert, ₹2K avg, 4% commission): ~₹12,000/mo ($140)
Premium (5% convert, ₹99/mo): ~₹49,500/mo ($590)
Combined: ~$730/mo (12x infrastructure cost)
```

---

## 19. ADMIN TOOLING (Phase 2 — Designed Now, Built Later)

### Django Admin (Free, Immediate)

Django gives us 60% of admin tooling for free:
- User management (search, view, edit, suspend)
- Product CRUD
- Review management
- Category/brand management
- DudScore config management
- Offer management
- All with audit trail via django-simple-history

### Custom Admin Consoles (Phase 2)

| Console | Purpose | Key Modules |
|---|---|---|
| Moderation | Trust & community management | User health, review queue, product merge/split |
| Data Ops | Ingestion control | Crawler dashboard, matching queue, email parse monitor |
| Trust & Scoring | DudScore governance | Weight editor, sandbox mode, config versioning |
| Platform Control | NOC / observability | System health, fraud heatmap, incident management |

Hosted at `admin.whydud.com`. Separate Next.js app or Django admin extensions. Full RBAC with atomic permissions.

---

## DEVELOPMENT PLAN

### Sprint 1 (Weeks 1-3): Foundation

```
Week 1:
  □ Project scaffolding (Django + Next.js + Docker Compose)
  □ PostgreSQL + TimescaleDB setup
  □ Redis setup
  □ Meilisearch setup
  □ Caddy reverse proxy config
  □ Django project structure (all apps created)
  □ Database migrations (all schemas)
  □ Django Admin basic setup

Week 2:
  □ User auth (Django AllAuth — email + Google OAuth)
  □ @whyd.* email system (Cloudflare Email Workers + webhook + Resend sending)
  □ Username registration + validation
  □ Next.js project setup + Tailwind + shadcn/ui
  □ API client layer (typed)
  □ Layout components (header, footer, sidebar)

Week 3:
  □ Product models + basic Django Admin
  □ Meilisearch integration (indexer + search API)
  □ Homepage (frontend)
  □ Search page with filters (frontend)
  □ Auth pages: login, register (multi-step with @whyd.* domain selection)
  □ Onboarding flow
```

### Sprint 2 (Weeks 3-6): Scrapers + Products

```
Week 4:
  □ Base spider class (Scrapy)
  □ Amazon.in spider (products + prices + reviews + offers)
  □ Proxy manager + anti-detection middleware
  □ Celery + Celery Beat setup

Week 5:
  □ Flipkart spider
  □ Product matching engine v1 (brand + model + fuzzy)
  □ Price snapshot pipeline (TimescaleDB hypertables)
  □ Continuous aggregates (daily/weekly)
  □ Product detail page (frontend — full)

Week 6:
  □ Price history charts (Recharts + TimescaleDB)
  □ Review aggregation + deduplication
  □ Review voting (upvote/downvote)
  □ Bank/card offer scraping (integrated into product spiders)
  □ Search with autocomplete + dynamic filters (frontend)
```

### Sprint 3 (Weeks 6-9): Intelligence + Email

```
Week 7:
  □ Sentiment analysis pipeline (spaCy + TextBlob)
  □ DudScore v1 engine (pandas/numpy)
  □ Fake review detection (rule-based v1)
  □ DudScore display on product pages (frontend)

Week 8:
  □ Inbound email processing pipeline
  □ Order parsers (Amazon, Flipkart)
  □ Email categorization engine
  □ Inbox page (frontend — two-panel)
  □ Purchase dashboard (frontend)

Week 9:
  □ Card vault (API + settings page)
  □ Deal optimizer engine (effective price calculation)
  □ Personalized deal display on product pages
  □ Wishlist system (API + frontend)
  □ Price alert worker (Celery)
```

### Sprint 4 (Weeks 9-12): Polish + Launch

```
Week 10:
  □ Comparison engine + page (with TCO tab)
  □ TCO engine + models (AC, fridge, washer, printer)
  □ City reference data (top 50 Indian cities)
  □ TCO calculator on product pages (frontend)
  □ Blockbuster deals detection engine

Week 11:
  □ Deals page (frontend)
  □ Refund/return tracking
  □ Subscription detection
  □ Post-purchase price drop alerts
  □ Discussion threads (basic)
  □ Rewards points system + gift card catalog

Week 12:
  □ Rewards page (frontend)
  □ Razorpay premium subscription
  □ 2-3 additional marketplace spiders (Myntra, Croma, Snapdeal)
  □ SEO (sitemap, meta tags, JSON-LD, Open Graph)
  □ Production deployment to VPS
  □ Monitoring setup (Better Stack + Telegram alerts)
  □ Final testing + bug fixes
  □ LAUNCH
```

---

## HOW TO MOVE FORWARD: DEVELOPMENT APPROACH

### Recommended Development Setup

```
Option A: Claude Code in VS Code (RECOMMENDED)
  ├── Install Claude Code extension in VS Code
  ├── Open the monorepo (backend/ + frontend/ + docker/)
  ├── Claude Code can:
  │   ├── Generate Django models, serializers, views, URLs
  │   ├── Generate Next.js pages, components, hooks
  │   ├── Write Scrapy spiders
  │   ├── Write Celery tasks
  │   ├── Create Docker configs
  │   ├── Write tests
  │   ├── Debug errors in context
  │   └── Iterate on code with full codebase awareness
  ├── Workflow: Architecture doc → Sprint task → Claude Code generates → You review → Commit
  └── Advantage: Claude sees your ENTIRE codebase, understands the architecture, maintains consistency

Option B: Claude Chat (current interface)
  ├── Generate files module by module
  ├── Download and integrate manually
  └── Disadvantage: No codebase context between sessions

Option C: Hybrid
  ├── Use Claude Chat for architecture decisions and Figma → code translation
  ├── Use Claude Code for actual implementation
  └── This is often the best approach
```

### Recommended Workflow

```
1. SETUP (Day 1)
   ├── Install Claude Code in VS Code
   ├── Create GitHub repo (private)
   ├── Initialize project structure:
   │   ├── django-admin startproject whydud backend/
   │   ├── npx create-next-app frontend/
   │   └── Docker Compose scaffold
   ├── Share this architecture document with Claude Code as context
   └── Purchase: whydud.com + whyd.in + whyd.click + whyd.shop domains, Contabo VPS

2. DEVELOPMENT (Sprints 1-4)
   ├── Work sprint by sprint from the plan above
   ├── Each task: describe to Claude Code → review generated code → test → commit
   ├── Share Figma screens for frontend tasks
   ├── Deploy to VPS every week (practice CI/CD early)
   └── Test with real scraping data by Week 4

3. FIGMA INTEGRATION
   ├── Share Figma screens here in Claude Chat
   ├── I'll extract design tokens, component patterns, layout structure
   ├── Generate frontend components matching the designs
   └── You integrate into the Next.js project via Claude Code
```

### What I Need From You Next

```
1. ✅ Architecture approval (this document)
2. 📎 Share your Figma screens (whatever you have)
3. 🛠️ Set up Claude Code in VS Code
4. 🌐 Purchase domains (whydud.com + whyd.in + whyd.click + whyd.shop)
5. 💻 Provision Contabo VPS
```

Once you share the Figma screens, I'll:
- Extract the design language (colors, typography, spacing, component patterns)
- Map each screen to the architecture
- Identify any gaps between design and architecture
- Generate a design token system
- Start creating production-ready frontend components

**This architecture document is your single source of truth. All development should reference it.**
