# WHYDUD — Complete Email Stack Architecture

**Version:** 1.0
**Domains:** whydud.com (corporate) + whyd.xyz (user shopping emails)
**Status:** Architecture Specification

---

## TWO DOMAINS, TWO PURPOSES

```
whydud.com — Corporate/Internal
  support@whydud.com        → Customer support inbox
  hello@whydud.com          → General inquiries
  team@whydud.com           → Internal team
  noreply@whydud.com        → Transactional emails (verify, reset, alerts)
  admin@whydud.com          → Admin notifications
  partnerships@whydud.com   → Business inquiries
  legal@whydud.com          → Legal notices
  abuse@whydud.com          → Abuse reports (required by RFC)
  postmaster@whydud.com     → Email delivery issues (required by RFC)

whyd.xyz — User Shopping Emails
  ramesh@whyd.xyz           → User's shopping email (assigned by Whydud)
  priya.sharma@whyd.xyz     → User's shopping email
  techguru42@whyd.xyz       → User's shopping email
  → Every registered user gets one free @whyd.xyz address
  → Used on Amazon, Flipkart, Myntra etc. for order tracking
```

**Why two domains?**
- whydud.com is your brand. If whyd.xyz gets flagged by any spam filter (unlikely but possible with high-volume user emails), your corporate email stays clean.
- whyd.xyz is short (8 chars including @) — easy for users to type on mobile while registering on marketplace apps.
- Separate DNS records, separate reputation, separate management.

---

## THE EMAIL STACK

### Layer 1: DNS (Both Domains)

```
whydud.com DNS Records:
  MX    10  route1.mx.cloudflare.net       ← Cloudflare Email Routing
  MX    20  route2.mx.cloudflare.net
  TXT      "v=spf1 include:_spf.mx.cloudflare.net include:amazonses.com ~all"
  TXT      _dmarc  "v=DMARC1; p=quarantine; rua=mailto:dmarc@whydud.com"
  CNAME    resend._domainkey  → (from Resend dashboard)   ← DKIM for sending

whyd.xyz DNS Records:
  MX    10  route1.mx.cloudflare.net       ← Cloudflare Email Routing
  MX    20  route2.mx.cloudflare.net
  TXT      "v=spf1 include:_spf.mx.cloudflare.net ~all"
  TXT      _dmarc  "v=DMARC1; p=reject; rua=mailto:dmarc-xyz@whydud.com"
  
  NOTE: whyd.xyz does NOT need sending DKIM — we never SEND from @whyd.xyz
        We only RECEIVE. Users register this email on marketplaces, 
        and marketplaces send TO this address. We receive and parse.
```

### Layer 2: Receiving Emails

```
┌─────────────────────────────────────────────────────────────┐
│                    CLOUDFLARE EMAIL ROUTING                   │
│                    (Free tier — unlimited)                    │
│                                                              │
│  Catch-all rule for whyd.xyz:                                │
│    *@whyd.xyz → Cloudflare Email Worker (code)               │
│                                                              │
│  Specific rules for whydud.com:                              │
│    support@whydud.com   → Cloudflare Worker → forward to     │
│                           support tool (Crisp/Intercom)      │
│    hello@whydud.com     → forward to founder's Gmail         │
│    noreply@whydud.com   → drop (no replies expected)         │
│    abuse@whydud.com     → forward to founder's Gmail         │
│    postmaster@whydud.com→ forward to founder's Gmail         │
│    *@whydud.com         → reject (no catch-all for corp)     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              CLOUDFLARE EMAIL WORKER (JavaScript)            │
│                                                              │
│  For *@whyd.xyz emails:                                      │
│    1. Extract recipient: ramesh@whyd.xyz                     │
│    2. Extract sender: auto-confirm@amazon.in                 │
│    3. Extract subject, date, size                            │
│    4. Read raw email body (MIME)                             │
│    5. POST to Django webhook:                                │
│       POST https://api.whydud.com/webhooks/email/inbound     │
│       Headers: X-Webhook-Secret: {HMAC signature}            │
│       Body: {                                                │
│         recipient: "ramesh@whyd.xyz",                        │
│         sender: "auto-confirm@amazon.in",                    │
│         subject: "Your order #123-456 has been placed",      │
│         raw_email: "<base64 encoded MIME>",                  │
│         received_at: "2026-02-24T10:30:00Z"                 │
│       }                                                      │
│    6. Return 200 to Cloudflare                               │
│                                                              │
│  For support@whydud.com:                                     │
│    1. Forward to support tool webhook                        │
│    2. Also POST metadata to Django for tracking              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              DJANGO WEBHOOK HANDLER                          │
│              POST /webhooks/email/inbound                     │
│                                                              │
│  1. Validate HMAC signature                                  │
│  2. Look up recipient username → find WhydudEmail record     │
│     ramesh@whyd.xyz → WhydudEmail(username="ramesh")         │
│  3. Look up user_id from WhydudEmail                         │
│  4. Encrypt email body with AES-256-GCM                      │
│  5. Store in InboxEmail table:                               │
│     - user_id, whydud_email_id                               │
│     - sender, subject, body_encrypted                        │
│     - category: 'uncategorized' (parsed async)               │
│  6. Dispatch Celery task: parse_email.delay(inbox_email_id)  │
│  7. Return 200 immediately (< 100ms response)                │
│                                                              │
│  If recipient not found:                                     │
│     → Store in dead letter queue                             │
│     → Could be: typo, deleted account, spam                  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              CELERY TASK: parse_email                         │
│              Queue: email (isolated from main workers)        │
│                                                              │
│  1. Decrypt email body                                       │
│  2. Detect marketplace from sender:                          │
│     auto-confirm@amazon.in → Amazon                          │
│     noreply@flipkart.com → Flipkart                          │
│     noreply@myntra.com → Myntra                              │
│     (pattern matching on sender domain)                      │
│                                                              │
│  3. Categorize email:                                        │
│     - Order confirmation                                     │
│     - Shipping update                                        │
│     - Delivery confirmation                                  │
│     - Refund processed                                       │
│     - Return initiated                                       │
│     - Subscription renewal                                   │
│     - Promotional (ignored for parsing)                      │
│     - OTP / Security (ignored, auto-archive)                 │
│                                                              │
│  4. Parse based on category:                                 │
│     Order → extract: order_id, product_name, price, quantity │
│     Refund → extract: order_id, refund_amount, reason        │
│     Shipping → extract: order_id, tracking_number, ETA       │
│     Return → extract: order_id, return_window_end            │
│                                                              │
│  5. Match parsed product to Whydud product catalog:          │
│     "Samsung Galaxy S24 FE 5G (256GB)" from email            │
│     → fuzzy match → Product(slug="samsung-galaxy-s24-fe")    │
│     → Store match_confidence score                           │
│                                                              │
│  6. Create/update ParsedOrder record                         │
│  7. Update InboxEmail category + parse_status                │
│  8. If return window detected: schedule alert Celery task    │
│  9. If order detected: check for affiliate click attribution │
└─────────────────────────────────────────────────────────────┘
```

### Layer 3: Sending Emails

```
┌─────────────────────────────────────────────────────────────┐
│                    RESEND (Transactional)                     │
│                    From: noreply@whydud.com                   │
│                    Free: 100 emails/day                       │
│                    Paid: $20/mo for 50K/mo                    │
│                                                              │
│  Sends:                                                      │
│    - Email verification (register flow)                      │
│    - Password reset                                          │
│    - Price drop alerts                                       │
│    - Return window reminders (3 days, 1 day before expiry)   │
│    - Weekly purchase summary                                 │
│    - Deal alerts (blockbuster deals matching wishlist)        │
│    - Reward points notifications                             │
│    - Admin digests                                           │
│                                                              │
│  NOTE: We NEVER send FROM @whyd.xyz addresses.               │
│  All outbound is from noreply@whydud.com or alerts@whydud.com│
│  @whyd.xyz is receive-only.                                  │
└─────────────────────────────────────────────────────────────┘
```

### Layer 4: Support (Corporate)

```
Option A (Free/Low-cost — RECOMMENDED for launch):
  Crisp.chat — Free tier: 2 seats, live chat + email inbox
  support@whydud.com → Cloudflare forwards to Crisp inbox
  Shared inbox for support team
  Integrates with website as chat widget

Option B (Growth stage):
  Intercom or Freshdesk
  When you have >100 support tickets/day

For launch: Crisp free tier is more than enough.
```

---

## EMAIL AVAILABILITY, ASSIGNMENT & SUGGESTIONS

### How Username Availability Works

```
User Flow:
  Register → Step 2: "Choose your @whyd.xyz email"
  
  ┌────────────────────────────────────────────────────┐
  │  📧 Get your free @whyd.xyz shopping email          │
  │                                                     │
  │  Use this email on Amazon, Flipkart, Myntra etc.   │
  │  We'll automatically track all your orders.         │
  │                                                     │
  │  ┌──────────────────────┐                           │
  │  │ ramesh.kumar         │ @whyd.xyz                 │
  │  └──────────────────────┘                           │
  │  ✅ ramesh.kumar@whyd.xyz is available!             │
  │                                                     │
  │  Suggestions:                                       │
  │  • ramesh.kumar      (your name)                    │
  │  • rameshk            (short form)                  │
  │  • kumar.ramesh       (reversed)                    │
  │                                                     │
  │  [Create Email]           [Skip for now →]          │
  └────────────────────────────────────────────────────┘
```

### Backend: Availability Check API

```
GET /api/v1/email/whydud/check?username=ramesh.kumar

Response (available):
{
  "success": true,
  "data": {
    "username": "ramesh.kumar",
    "available": true,
    "email": "ramesh.kumar@whyd.xyz"
  }
}

Response (taken):
{
  "success": true,
  "data": {
    "username": "ramesh.kumar",
    "available": false,
    "suggestions": [
      "ramesh.kumar2",
      "ramesh.k",
      "kumar.ramesh",
      "rameshkumar26",
      "ramesh.k.whydud"
    ]
  }
}

Response (reserved/invalid):
{
  "success": true,
  "data": {
    "username": "admin",
    "available": false,
    "reason": "reserved",
    "suggestions": ["ramesh.admin", "admin.user"]
  }
}
```

### Username Rules

```python
USERNAME_RULES = {
    "min_length": 3,
    "max_length": 30,
    "allowed_chars": r'^[a-z0-9][a-z0-9._-]*[a-z0-9]$',  # letters, numbers, dots, hyphens, underscores
    "cannot_start_with": ['.', '-', '_'],
    "cannot_end_with": ['.', '-', '_'],
    "no_consecutive_special": True,   # no ".." or "--" or "__"
    "case_insensitive": True,         # "Ramesh" and "ramesh" are the same
}

# Already seeded in ReservedUsername table (migration 0002):
RESERVED_USERNAMES = [
    # System
    "admin", "administrator", "root", "system", "support", "help",
    "info", "contact", "mail", "email", "postmaster", "abuse",
    "webmaster", "noreply", "no-reply", "mailer-daemon",
    
    # Brand
    "whydud", "whyd", "whydud-team", "official", "team",
    "founder", "ceo", "cto",
    
    # Common
    "test", "testing", "demo", "example", "user", "guest",
    "null", "undefined", "none", "void", "delete", "remove",
    
    # Marketplaces (prevent impersonation)
    "amazon", "flipkart", "myntra", "snapdeal", "meesho",
    "jiomart", "tatacliq", "croma", "reliance", "nykaa", "ajio",
    
    # Functional
    "billing", "payment", "order", "orders", "invoice",
    "refund", "return", "shipping", "delivery", "tracking",
    "alert", "alerts", "notification", "notifications",
    "newsletter", "unsubscribe", "feedback", "report",
    
    # Offensive terms (separate list, loaded from file)
    # ...
]
```

### Suggestion Algorithm

```python
def suggest_usernames(desired: str, user_name: str, user_email: str) -> list[str]:
    """
    Generate 5 available username suggestions when desired username is taken.
    
    Strategies (in order of preference):
    1. Name variations (if user provided their name)
    2. Desired username with small modifications
    3. Email prefix variations
    4. Smart combinations
    """
    suggestions = []
    
    # Strategy 1: Name-based (highest quality)
    if user_name:
        first, last = parse_name(user_name)  # "Ramesh Kumar" → ("ramesh", "kumar")
        candidates = [
            f"{first}.{last}",           # ramesh.kumar
            f"{first}{last[0]}",         # rameshk
            f"{last}.{first}",           # kumar.ramesh
            f"{first[0]}{last}",         # rkumar
            f"{first}-{last}",           # ramesh-kumar
        ]
        for c in candidates:
            if is_available(c) and c != desired:
                suggestions.append(c)
    
    # Strategy 2: Modify desired username
    year = str(datetime.now().year % 100)  # "26"
    candidates = [
        f"{desired}{year}",              # ramesh26
        f"{desired}.whydud",             # ramesh.whydud
        f"the.{desired}",               # the.ramesh
        f"{desired}_{random_digit()}",   # ramesh_7
    ]
    for c in candidates:
        if is_available(c) and c not in suggestions:
            suggestions.append(c)
    
    # Strategy 3: Email prefix
    if user_email:
        prefix = user_email.split('@')[0]  # "ramesh.k.2024" from Gmail
        cleaned = re.sub(r'[^a-z0-9.]', '', prefix.lower())
        if is_available(cleaned) and cleaned not in suggestions:
            suggestions.append(cleaned)
    
    return suggestions[:5]  # Return max 5
```

### Frontend: Real-time Availability Check

```typescript
// In register page, Step 2
const [username, setUsername] = useState("");
const [status, setStatus] = useState<"idle" | "checking" | "available" | "taken">("idle");
const [suggestions, setSuggestions] = useState<string[]>([]);

// Debounced check (300ms after user stops typing)
useEffect(() => {
  if (username.length < 3) return;
  
  const timer = setTimeout(async () => {
    setStatus("checking");
    const result = await api.email.checkAvailability(username);
    if (result.available) {
      setStatus("available");
    } else {
      setStatus("taken");
      setSuggestions(result.suggestions);
    }
  }, 300);
  
  return () => clearTimeout(timer);
}, [username]);

// UI shows:
// "checking" → spinner
// "available" → green checkmark + "ramesh@whyd.xyz is available!"
// "taken" → red X + suggestion chips (clickable to select)
```

---

## MULTI-ACCOUNT EMAIL AGGREGATION

### The Problem
A user might have:
- Personal Gmail: ramesh.kumar@gmail.com → used on Amazon
- Work Gmail: ramesh@company.com → used on Flipkart (personal orders)
- Outlook: r.kumar@outlook.com → used on Myntra
- @whyd.xyz: ramesh@whyd.xyz → just set up, will use going forward

They want ALL purchase data in one place on Whydud.

### The Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ USER: Ramesh Kumar                                            │
│                                                               │
│ Connected Email Sources:                                      │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 📧 ramesh@whyd.xyz                    PRIMARY          │   │
│ │    Status: Active │ Emails: 23 │ Orders detected: 8    │   │
│ │    Method: Direct receive (Cloudflare Worker)           │   │
│ │    Real-time: Yes (instant)                             │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 📧 ramesh.kumar@gmail.com             CONNECTED        │   │
│ │    Status: Syncing │ Emails: 142 │ Orders detected: 34 │   │
│ │    Method: Gmail API (read-only OAuth)                  │   │
│ │    Sync: Every 6 hours │ Last sync: 2h ago              │   │
│ │    Scopes: gmail.readonly                               │   │
│ │    [Disconnect] [Sync Now]                              │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 📧 r.kumar@outlook.com               CONNECTED        │   │
│ │    Status: Active │ Emails: 67 │ Orders detected: 12   │   │
│ │    Method: Microsoft Graph API (read-only OAuth)        │   │
│ │    Sync: Every 6 hours │ Last sync: 1h ago              │   │
│ │    [Disconnect] [Sync Now]                              │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                               │
│ [+ Connect Another Email Account]                             │
│                                                               │
│ TOTAL: 232 emails synced │ 54 orders detected │ 3 sources    │
└──────────────────────────────────────────────────────────────┘
```

### How Each Source Works

```
SOURCE 1: @whyd.xyz (Best — real-time, zero OAuth)
  Flow: Marketplace → sends email → Cloudflare Worker → Django → parsed instantly
  Latency: Seconds
  Privacy: Full control, emails never leave our infrastructure
  Setup: User creates @whyd.xyz → registers on marketplaces with it
  Limitation: Only works for NEW registrations going forward

SOURCE 2: Gmail (Good — periodic sync, OAuth required)
  Flow: User grants read-only access → Celery syncs every 6h → 
        filters shopping emails → parses orders
  Latency: Up to 6 hours
  Privacy: We read emails but ONLY process shopping-related ones.
           Non-shopping emails are ignored (not stored, not processed).
  Setup: Settings → Connect Gmail → OAuth consent → authorize
  Limitation: OAuth tokens expire, user must re-auth occasionally
  
  Gmail API query filter:
    from:(amazon.in OR flipkart.com OR myntra.com OR nykaa.com OR ...)
    subject:(order OR shipped OR delivered OR refund OR return)
    newer_than:90d
  
  This means we ONLY fetch emails from known marketplaces.
  We never access personal, work, or non-shopping emails.

SOURCE 3: Microsoft/Outlook (Good — same pattern as Gmail)
  Flow: Same as Gmail but using Microsoft Graph API
  Setup: Settings → Connect Outlook → OAuth consent → authorize

SOURCE 4: Manual forwarding (Fallback — for users who refuse OAuth)
  Flow: User sets up auto-forward rule in Gmail/Outlook to forward
        shopping emails to their @whyd.xyz address
  Latency: Near real-time (forwarding is fast)
  Privacy: Maximum user control (they choose what to forward)
  Setup: We provide step-by-step instructions per email provider
  Limitation: Requires user to set up mail rules (technical barrier)
```

### Database Schema for Multi-Email

```sql
-- Already exists: accounts.oauth_connections
-- One user → many OAuth connections (Gmail, Outlook, etc.)

-- Email source tracking
CREATE TABLE email_intel.email_sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users.accounts(id),
    source_type     VARCHAR(20) NOT NULL,  -- 'whydud_email', 'gmail', 'outlook', 'forward'
    email_address   VARCHAR(320) NOT NULL,
    
    -- For OAuth sources
    oauth_connection_id  UUID REFERENCES users.oauth_connections(id),
    
    -- For @whyd.xyz
    whydud_email_id UUID REFERENCES users.whydud_emails(id),
    
    -- Sync state
    last_sync_at    TIMESTAMPTZ,
    next_sync_at    TIMESTAMPTZ,
    sync_cursor     VARCHAR(500),   -- Gmail history ID or pagination token
    emails_synced   INTEGER DEFAULT 0,
    orders_detected INTEGER DEFAULT 0,
    
    -- Status
    is_active       BOOLEAN DEFAULT TRUE,
    status          VARCHAR(20) DEFAULT 'active',  -- 'active', 'expired', 'error', 'disconnected'
    error_message   TEXT,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sources_user ON email_intel.email_sources(user_id);
CREATE UNIQUE INDEX idx_sources_email ON email_intel.email_sources(user_id, email_address);

-- InboxEmail already has user_id FK
-- ParsedOrder already has user_id FK + source field
-- Queries across all sources: WHERE user_id = X (regardless of source)
```

---

## CROSS-PLATFORM INVOICE / PURCHASE SEARCH

### The User Problem
"I bought a phone charger 3 months ago but I don't remember if it was on Amazon or Flipkart, and I don't know which email I used. I need the invoice for warranty."

### The Solution

```
┌─────────────────────────────────────────────────────────────┐
│ 🔍 Search your purchases                                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ phone charger                                     🔍     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Filters: [All Platforms ▼] [All Accounts ▼] [Date Range ▼]  │
│                                                              │
│ 3 results found                                              │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ 🛒 Anker 20W USB-C Charger                               ││
│ │ Amazon.in │ ₹899 │ Dec 15, 2025                          ││
│ │ via: ramesh.kumar@gmail.com │ Order #ABC-123-DEF          ││
│ │ Status: Delivered │ Return window: Expired                 ││
│ │ [View Order] [Download Invoice] [View on Amazon]          ││
│ ├──────────────────────────────────────────────────────────┤│
│ │ 🛒 Samsung 25W Charger (duplicate bought by mistake)     ││
│ │ Flipkart │ ₹749 │ Nov 3, 2025                            ││
│ │ via: ramesh@whyd.xyz │ Order #FLP-456-GHI                 ││
│ │ Status: Returned │ Refund: ₹749 received                  ││
│ │ [View Order] [View on Flipkart]                           ││
│ ├──────────────────────────────────────────────────────────┤│
│ │ 🛒 Mi 33W Turbo Charger                                  ││
│ │ Amazon.in │ ₹599 │ Aug 20, 2025                          ││
│ │ via: r.kumar@outlook.com │ Order #AMZ-789-JKL             ││
│ │ Status: Delivered │ Return window: Expired                 ││
│ │ [View Order] [Download Invoice] [View on Amazon]          ││
│ └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### How Search Works

```python
# Full-text search on ParsedOrder + InboxEmail
def search_purchases(user_id: UUID, query: str, filters: dict) -> list:
    """
    Search across ALL email sources for purchase-related content.
    """
    results = ParsedOrder.objects.filter(
        user_id=user_id
    ).select_related(
        'matched_product', 'inbox_email'
    )
    
    # Full-text search on product name + order ID
    if query:
        results = results.filter(
            Q(product_name__icontains=query) |
            Q(order_id__icontains=query) |
            Q(inbox_email__subject__icontains=query)
        )
    
    # Filters
    if filters.get('marketplace'):
        results = results.filter(marketplace=filters['marketplace'])
    if filters.get('email_source'):
        results = results.filter(inbox_email__source_type=filters['email_source'])
    if filters.get('date_from'):
        results = results.filter(order_date__gte=filters['date_from'])
    if filters.get('date_to'):
        results = results.filter(order_date__lte=filters['date_to'])
    
    return results.order_by('-order_date')
```

---

## STRATEGIC BENEFITS OF THE EMAIL SYSTEM

### For Users

| Benefit | Description |
|---|---|
| **Unified purchase history** | See ALL orders across ALL marketplaces in one place |
| **Auto-expense tracking** | No manual entry — purchases auto-detected from emails |
| **Return window alerts** | "Your return window for OnePlus Nord closes in 3 days" |
| **Refund tracking** | "Flipkart refund of ₹1,299 is 5 days late" |
| **Price drop after purchase** | "You bought this for ₹27,000 — it's now ₹24,999. Return window open for 4 more days." |
| **Subscription tracking** | "Your Amazon Prime renews in 7 days (₹1,499)" |
| **Warranty reminders** | "Your Samsung TV warranty expires in 30 days" |
| **Invoice search** | Find any purchase across any platform instantly |
| **Verified purchase reviews** | @whyd.xyz purchase data = verified buyer badge on reviews |
| **Spam-free shopping email** | @whyd.xyz only gets marketplace emails, not spam |
| **No OAuth required** | @whyd.xyz works without giving read access to personal email |

### For Whydud (Business)

| Benefit | Description |
|---|---|
| **Click → Purchase attribution** | Match affiliate clicks to actual orders. Know exact conversion rate. |
| **Real return rate data** | DudScore component: "15% of buyers returned this within 7 days" |
| **Actual price paid data** | Users see ₹27,000 listed but paid ₹25,400 with card discount. Real price data. |
| **Marketplace reliability scoring** | "Amazon delivers 2 days faster than Flipkart on average for this category" |
| **User lock-in / moat** | Once users have 6 months of purchase data on Whydud, switching cost is high |
| **Subscription intelligence** | Know which services users actually pay for (market research) |
| **Category spending data** | Aggregate (anonymous): "Electronics spending up 15% in Delhi this month" |
| **Product lifecycle data** | How long products last before replacement (from repeat purchases) |
| **Review credibility** | Verified purchaser via email = highest trust review. No one else has this. |
| **Anti-fraud signal** | If a "reviewer" has no purchase email for that product → lower credibility |

### For DudScore (Direct Inputs)

```
@whyd.xyz emails feed directly into DudScore:

1. ReturnSignalScore:
   - Return rate calculated from actual return/refund emails
   - Not from marketplace data (which can be manipulated)
   - "23% of Whydud users who bought this returned it"

2. ReviewCredibilityScore:
   - Verified purchaser (email-confirmed) reviews weighted 3x
   - Reviews without purchase verification weighted 0.5x

3. PriceValueScore:
   - Real effective price paid (after card discounts, coupons)
   - Not the listed price

4. PriceStabilityScore:
   - Combined with scraped data for cross-validation
   - Email shows actual paid price vs what marketplace listed
```

---

## EMAIL PRIVACY & TRUST

This is CRITICAL — users are giving you access to their emails. You must be transparent.

### Privacy Principles

```
1. MINIMAL ACCESS: Gmail OAuth requests gmail.readonly scope, but we ONLY 
   process emails from known marketplace domains. Personal emails are never 
   read, stored, or processed.

2. ENCRYPTED STORAGE: All email bodies encrypted with AES-256-GCM at rest.
   Decrypted only when the user views them in their inbox.

3. NO ADMIN ACCESS TO EMAIL BODIES: Admin panel shows metadata only 
   (sender, subject, date, category). Never the email content.

4. USER DELETION: User can disconnect any email source at any time.
   "Delete my data" exports then permanently deletes all email data.

5. RETENTION: Raw emails deleted after 90 days. Parsed order data 
   (product name, price, date) retained as long as account is active.

6. NO SELLING: Email data is NEVER shared with third parties. 
   Only aggregate, anonymized trends are used for platform features.

7. TRANSPARENCY: Settings page shows exactly what data we have from each 
   email source, with counts and last sync time.
```

### Privacy-First UI

```
When connecting Gmail:
┌─────────────────────────────────────────────────────────────┐
│ 🔒 Connect Gmail (Read-Only)                                │
│                                                              │
│ What we'll access:                                          │
│ ✅ Order confirmations from Amazon, Flipkart, Myntra, etc.  │
│ ✅ Shipping & delivery updates                               │
│ ✅ Refund & return notifications                             │
│                                                              │
│ What we'll NEVER access:                                    │
│ ❌ Personal emails                                           │
│ ❌ Work emails                                               │
│ ❌ Banking/financial emails (other than order receipts)       │
│ ❌ Social media notifications                                │
│ ❌ Any non-shopping email                                    │
│                                                              │
│ We filter emails by sender domain. Only emails from known    │
│ marketplace domains (amazon.in, flipkart.com, etc.) are      │
│ processed. Everything else is completely ignored.             │
│                                                              │
│ You can disconnect at any time from Settings.                │
│                                                              │
│ [Connect with Google]       [Maybe Later]                    │
└─────────────────────────────────────────────────────────────┘
```

---

## COST BREAKDOWN

| Component | Cost | Notes |
|---|---|---|
| Cloudflare Email Routing | Free | Unlimited email routing |
| Cloudflare Email Workers | Free | 100K invocations/day (Free tier) |
| Resend (transactional sending) | Free → $20/mo | 100/day free, $20 for 50K/mo |
| Crisp (support inbox) | Free | 2 seats free tier |
| whyd.xyz domain | ~$10/year | One-time purchase |
| whydud.com domain | ~$12/year | Already purchased? |
| Gmail API | Free | Google Cloud free tier (10K queries/day) |
| Microsoft Graph API | Free | Free tier sufficient |
| **Total at launch** | **~$2/month** | Domain costs amortized |
| **Total at 10K users** | **~$22/month** | Resend paid tier |

---

## IMPLEMENTATION IN YOUR CODEBASE

### What Already Exists (from PROGRESS.md)
- ✅ WhydudEmail model (username, is_active, user FK)
- ✅ ReservedUsername model + seed migration (~80 reserved)
- ✅ InboxEmail model (encrypted body, category, marketplace)
- ✅ ParsedOrder model (order_id, product_name, price, matched_product)
- ✅ OAuthConnection model (encrypted tokens)
- ✅ Webhook endpoint (accepts POST, but parsing is stub)
- ✅ Email worker Celery queue (isolated)

### What Needs Building
- ❌ Cloudflare Email Worker JavaScript code
- ❌ Webhook handler: actually parse + store (currently stub)
- ❌ Email categorization logic
- ❌ Order/refund/return parser per marketplace
- ❌ Gmail OAuth frontend flow
- ❌ Gmail sync Celery task
- ❌ Multi-email source management
- ❌ Purchase search API
- ❌ Inbox frontend wired to real data
- ❌ Username suggestion algorithm
- ❌ Availability check with debounced frontend
