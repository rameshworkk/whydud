# WHYDUD — Frontend Wiring Tasks (Make Backend Visible)

> **Problem:** Massive backend progress (DudScore, fraud detection, scraping, email,
> affiliate tracking, notifications, admin) but NONE of it is visible in the frontend.
>
> **This file:** 28 focused Claude Code prompts to wire backend → frontend.
> Same rules: 1 prompt per paste, 5-8 prompts per session, fresh session every 5-8 prompts.

---

## PRIORITY ORDER

```
Sprint A: Wire existing features into visible UI (Prompts A1-A10)
  → Notification bell, Write a Review, Preferences, Compare tray, Recently viewed

Sprint B: Surface backend intelligence in product pages (Prompts B1-B7)
  → DudScore components, fraud badges, price history, deal detection, similar products

Sprint C: Email features in Inbox (Prompts C1-C3)
  → Compose, Reply, Send buttons

Sprint D: Dashboard completion (Prompts D1-D4)
  → Purchases, Rewards, Refunds, Subscriptions full UI

Sprint E: Visual polish to match Figma (Prompts E1-E4)
  → Homepage, Product Detail, Search, Compare, Dashboard
```

---

## SPRINT A: WIRE EXISTING FEATURES INTO UI

### A1 — Notification Bell in Header
```
Read docs/ARCHITECTURE.md Section 9 (notifications table).

The backend has:
- GET /api/v1/notifications/ (paginated)
- GET /api/v1/notifications/unread-count
- PATCH /api/v1/notifications/:id/read
- POST /api/v1/notifications/mark-all-read

Create frontend/src/components/notifications/notification-bell.tsx:
- "use client" component
- Bell icon (lucide-react Bell)
- Red badge with unread count (polls GET /unread-count every 30s)
- Click opens a dropdown panel (max 5 recent notifications)
- Each notification: icon by type, title, body truncated, relative time
- "Mark all read" button at top
- "View all →" link to /notifications at bottom
- Click a notification → PATCH read + navigate to action_url

Add notificationsApi to frontend/src/lib/api/products.ts:
- getUnreadCount() → GET /api/v1/notifications/unread-count
- list(cursor?) → GET /api/v1/notifications/
- markRead(id) → PATCH /api/v1/notifications/:id/read
- markAllRead() → POST /api/v1/notifications/mark-all-read

Wire into Header component (src/components/layout/header.tsx):
- Show NotificationBell only when user is authenticated (useAuth)
- Position: right side of header, before user avatar/menu

Don't create the full /notifications page yet — just the bell + dropdown.
```

### A2 — Notification Center Page
```
Create frontend/src/app/(dashboard)/notifications/page.tsx:
- Full notification list with cursor pagination
- Filter tabs: All | Price Drops | Reviews | Alerts | System
- Each notification card: type icon, title, body, timestamp, read/unread styling
- Click → navigate to action_url
- Bulk "Mark all read" button
- Empty state: "No notifications yet"
- Loading skeleton

Add to sidebar navigation (src/components/layout/sidebar.tsx):
- Add "Notifications" link with bell icon, between Dashboard and Inbox
```

### A3 — Notification Preferences in Settings
```
The backend has:
- GET /api/v1/notifications/preferences
- PATCH /api/v1/notifications/preferences

Add a "Notifications" tab to the Settings page (src/app/(dashboard)/settings/page.tsx):

For each notification type show two toggles:
  - "In-App" toggle (on/off)
  - "Email" toggle (on/off)

Types to show:
  - Price Drop Alerts
  - Return Window Reminders
  - Refund Delay Warnings
  - Back in Stock
  - Review Upvotes
  - Price Alert Triggered
  - Discussion Replies
  - Level Up
  - Points Earned
  - Subscription Renewal

Add notificationsApi.getPreferences() and .updatePreferences(data) to API client.
Load current preferences on mount, save on toggle change (debounced 500ms).
```

### A4 — Write a Review Page (4-Tab Flow)
```
Read docs/ARCHITECTURE.md Section 9 (reviews table, review_features).

The backend has:
- POST /api/v1/products/:slug/reviews (submit)
- POST /api/v1/reviews/:id/purchase-proof (upload)
- GET /api/v1/products/:slug/review-features (category-specific features)

Create frontend/src/app/(public)/product/[slug]/review/page.tsx:

Tab 1 — "Verify Purchase":
  - Platform dropdown (Amazon, Flipkart, Croma, Other)
  - Seller name input
  - Purchase date picker
  - Price paid (₹ input)
  - Upload proof image (drag + drop, max 5MB)
  - Optional — skip verification

Tab 2 — "Your Review":
  - Overall star rating (1-5, clickable stars)
  - Review title input
  - "What did you like?" textarea
  - "What didn't you like?" textarea
  - Photo/video upload (up to 5 images, 1 video)
  - NPS: "How likely to recommend?" (0-10 slider)

Tab 3 — "Rate Features":
  - Fetch GET /api/v1/products/:slug/review-features
  - For each feature: label + 5-star rating
  - These are dynamic per category (phones get battery_life, camera; ACs get cooling, noise)
  - If no features for this category, skip this tab

Tab 4 — "Seller Feedback":
  - Delivery rating (1-5 stars)
  - Packaging rating (1-5 stars)
  - Accuracy rating (1-5 stars)
  - Communication rating (1-5 stars)

Navigation: Next/Back buttons between tabs. Final "Submit Review" on tab 4.
Submit: POST all data to /api/v1/products/:slug/reviews
Success: redirect to product page with toast "Review submitted! It'll be published within 48 hours."

Create reusable StarRatingInput component at src/components/reviews/star-rating-input.tsx.
```

### A5 — "Write a Review" Button on Product Page
```
In frontend/src/app/(public)/product/[slug]/page.tsx:

Add a "Write a Review" button in the reviews section.
- If user is logged in: link to /product/[slug]/review
- If not logged in: link to /login?redirect=/product/[slug]/review
- If user already reviewed this product: show "Edit Your Review" instead

Add reviewsApi.checkMyReview(productSlug) → GET /api/v1/products/:slug/reviews/mine
Returns the user's review if it exists, or 404.
```

### A6 — Purchase Preferences Page (Dynamic Questionnaire)
```
Read docs/ARCHITECTURE.md Section 9 (purchase_preferences, category_preference_schemas).

Backend has:
- GET /api/v1/preferences/:category_slug/schema (returns JSONB schema)
- GET /api/v1/preferences/:category_slug (user's saved answers)
- POST /api/v1/preferences/:category_slug (save answers)

Create frontend/src/components/preferences/preference-form.tsx:
- "use client" component
- Props: schema (PreferenceSchema), initialValues?, onSubmit
- Renders sections from schema.sections dynamically
- Field type rendering:
  - "number" → number input with unit label + optional quick_select chip buttons
  - "currency" → ₹ prefixed input
  - "dropdown" → Select component
  - "radio" → RadioGroup
  - "tags" → multi-select clickable tag chips
  - "toggle" → Switch
  - "slider" → Slider with min/max/step
  - "range_slider" → dual-handle range slider
- Each section: icon + title heading + fields grid

Create frontend/src/app/(dashboard)/preferences/page.tsx:
- Category selector (cards or dropdown — Air Purifier, AC, Water Purifier, Fridge, Washing Machine, Vehicle, Laptop)
- Select category → fetch schema → render PreferenceForm
- Pre-fill with saved preferences if they exist
- Save button → POST to API
- Success toast

Add preferencesApi to API client:
- getSchema(categorySlug) → GET schema
- getPreferences(categorySlug) → GET saved
- savePreferences(categorySlug, data) → POST
```

### A7 — Floating Compare Tray
```
Create frontend/src/contexts/compare-context.tsx:
- CompareProvider wraps the app
- State: products[] (max 4), isOpen boolean
- Methods: addProduct(product), removeProduct(id), clearAll(), toggleTray()
- Persist to localStorage so selections survive navigation

Create frontend/src/components/compare/compare-tray.tsx:
- Fixed bottom bar (like a cookie banner but for comparison)
- Shows when 1+ products are added
- Each product: small thumbnail + name + ✕ remove button
- Empty slots: dashed border "Add product"
- "Compare Now" button (disabled if < 2 products) → navigates to /compare?ids=id1,id2,id3
- Collapse/expand toggle

Create frontend/src/components/product/add-to-compare-button.tsx:
- Small button on ProductCard and product detail page
- If product already in compare: "Remove from Compare" (red)
- If compare is full (4): disabled with tooltip "Max 4 products"
- Otherwise: "Compare" with + icon

Wire CompareProvider into root layout.
Wire AddToCompareButton into ProductCard component.
```

### A8 — Recently Viewed
```
Backend has:
- POST /api/v1/me/recently-viewed (log a view)
- GET /api/v1/me/recently-viewed (get recent 20)

Create frontend/src/hooks/use-recently-viewed.ts:
- On product page mount: POST /api/v1/me/recently-viewed { product_id }
- For anonymous users: store in localStorage instead
- Debounce: don't re-post if same product viewed within 5 minutes

Wire into product detail page (src/app/(public)/product/[slug]/page.tsx):
- Add useEffect that calls the hook on mount

Add "Recently Viewed" section to homepage:
- Only show if user is logged in OR localStorage has items
- Horizontal scroll of ProductCards (max 10)
- Position: below "Trending Products", above "Price Dropping"
```

### A9 — Price Alert Button on Product Page
```
Backend has:
- POST /api/v1/alerts/price (create alert)
- GET /api/v1/alerts (list user's alerts)
- PATCH /api/v1/alerts/:id (update target price)
- DELETE /api/v1/alerts/:id (delete)

Create frontend/src/components/product/price-alert-button.tsx:
- "🔔 Set Price Alert" button on product detail page
- Click opens a modal/drawer:
  - Current price shown (read-only)
  - Target price input (₹, pre-filled to 10% below current)
  - Marketplace filter: "Any" or specific marketplace dropdown
  - "Create Alert" button
- If user already has an alert for this product:
  - Button shows "Alert active at ₹X,XXX" (green)
  - Modal shows existing alert with Edit / Delete options
- If not logged in: redirect to login with return URL

Wire into product detail page, next to the "Add to Wishlist" button.
```

### A10 — Sidebar Navigation Update
```
Update frontend/src/components/layout/sidebar.tsx:

Add these links to the dashboard sidebar (after existing items):
- 📋 My Reviews → /my-reviews (already exists)
- 🔔 Notifications → /notifications
- ⚙️ Preferences → /preferences
- 💰 Alerts → /alerts (already exists)
- 🏆 Leaderboard → /leaderboard

Make sure the active link is highlighted based on current route.
Ensure mobile nav (MobileNav component) also has these links.
```

---

## SPRINT B: SURFACE BACKEND INTELLIGENCE

### B1 — DudScore Component Breakdown on Product Page
```
The DudScoreGauge component already shows the overall score.
Add a breakdown section below it showing the 6 component scores.

Backend: GET /api/v1/products/:slug already returns dud_score.
Add to ProductDetailSerializer: dud_score_components field that returns the latest
DudScoreHistory.component_scores JSONB (if it exists).

Create frontend/src/components/product/dudscore-breakdown.tsx:
- 6 horizontal bars, one per component:
  - Sentiment: 😊 (color: warm)
  - Rating Quality: ⭐ (distribution health)
  - Price Value: 💰 (value for money)
  - Review Credibility: 🛡️ (trustworthiness)
  - Price Stability: 📊 (price consistency)
  - Return Signal: 🔄 (low return rate)
- Each bar: label, 0-100% fill, score value
- Confidence badge: "Based on X reviews" with confidence level
- Tooltip on each component explaining what it measures

Wire into product detail page, below DudScoreGauge.
Only show if dud_score_components exists (hide for products without enough data).
```

### B2 — Fraud/Credibility Badges on Reviews
```
The backend now computes credibility_score and fraud_flags on each review.
Surface this in the review cards.

Update ReviewCard component (src/components/product/review-card.tsx):
- Add "Verified Purchase" green badge if is_verified_purchase=True
- Add credibility indicator:
  - High (>0.8): green checkmark "Trusted Review"
  - Medium (0.5-0.8): no badge (default)
  - Low (<0.5): orange warning "Low Credibility"
- If review is_flagged: show subtle "Under Review" grey badge
- Show reviewer level badge (bronze/silver/gold/platinum) next to author name

Update the Review type in types.ts to include:
  credibilityScore, fraudFlags, isFlagged, isVerifiedPurchase,
  reviewerLevel (from author's reviewer profile)
```

### B3 — Price History Chart Enhancement
```
The PriceChart component exists but shows basic data.
Now that scraping creates real PriceSnapshots, enhance it:

Update frontend/src/components/product/price-chart.tsx:
- Add marketplace filter buttons (show/hide specific marketplace lines)
- Add time range selector: 1W | 1M | 3M | 6M | 1Y | All
- Add "Lowest Ever" horizontal dashed line with label
- Add "Current Best" annotation on the chart
- Color-code by marketplace (Amazon orange, Flipkart blue, Croma green, etc.)
- Hover tooltip: date, price, marketplace
- If no price history: show "Price history will be available after first scrape"
```

### B4 — Cross-Platform Price Comparison Panel
```
Create frontend/src/components/product/marketplace-comparison.tsx:
- Full comparison table (replaces or enhances existing MarketplacePrices):
  - Columns: Marketplace | Seller | Price | MRP | Discount | Stock | Rating | Action
  - Marketplace: logo + name
  - Best price row highlighted with green background + "Best Price" badge
  - "Lowest Ever" badge if current_price <= lowest_price_ever
  - Action: "Buy on X →" button (uses clicksApi.track for affiliate tracking)
  - EMI option line below price if available
  - Seller rating stars
- Sort by: Price (default) | Rating | Marketplace

Wire into product detail page, replacing or below current MarketplacePrices component.
```

### B5 — Deal Badges on Product Cards
```
The backend has deals detection (deal_type: error_price, lowest_ever, genuine_discount).

Update ProductCard component (src/components/product/product-card.tsx):
- If product has an active deal, show a badge:
  - error_price: red "🔥 Error Price!" badge (pulsing)
  - lowest_ever: green "📉 Lowest Ever" badge
  - genuine_discount: blue "X% Off" badge with discount percentage
- Badge positioned top-right corner of card image

Backend change needed: include active_deal in ProductListSerializer
  (deal_type, discount_pct, if active deal exists for this product)
```

### B6 — Similar/Alternative Products Section
```
Add to product detail page:

Create frontend/src/components/product/similar-products.tsx:
- Server component
- Fetch: GET /api/v1/products/:slug/similar (needs new backend endpoint)
- Shows horizontal scroll of 4-8 ProductCards
- Title: "Similar Products" or "You Might Also Like"
- If no similar products: don't render section

Backend: Add SimilarProductsView to products/views.py:
  GET /api/v1/products/:slug/similar
  - Same category + similar price range (±30%)
  - Exclude current product
  - Order by dud_score DESC
  - Limit 8

Wire into product page below reviews section.
```

### B7 — Share Product Button + OG Meta
```
Add share button to product detail page:

Create frontend/src/components/product/share-button.tsx:
- Button with share icon
- Click opens share options:
  - "Copy Link" → copies product URL to clipboard + toast
  - "WhatsApp" → opens wa.me with pre-filled message (product title + price + URL)
  - "Twitter/X" → opens tweet intent with product title + URL
  - Uses Web Share API on mobile (navigator.share) as primary

Update product page's generateMetadata() (src/app/(public)/product/[slug]/page.tsx):
- og:title → product title
- og:description → "₹X,XXX | DudScore: Y/100 | Compare prices across Z marketplaces"
- og:image → product image URL
- og:type → "product"
- twitter:card → "summary_large_image"
```

---

## SPRINT C: EMAIL FEATURES IN INBOX

### C1 — Compose Email Button
```
The backend has POST /api/v1/inbox/send. The Inbox page exists.

Add "Compose" button to Inbox page (src/app/(dashboard)/inbox/page.tsx):
- Floating action button or top-right "✏️ Compose" button
- Opens a compose modal/drawer:
  - From: user's @whyd.* email (read-only, auto-filled)
  - To: email input (with validation)
  - Subject: text input
  - Body: rich text editor (or simple textarea for v1)
  - Send button
- On send: POST /api/v1/inbox/send
- Success: close modal + toast "Email sent!" + refresh inbox
- Rate limit error (429): show "Daily send limit reached"

Add inboxApi.send(to, subject, bodyHtml) to API client.
```

### C2 — Reply Button on Email
```
The backend has POST /api/v1/inbox/:id/reply.

In the Inbox email detail view:
- Add "↩️ Reply" button below the email body
- Click opens inline reply editor (below original email):
  - Shows "Re: [original subject]" (read-only)
  - Shows "To: [original sender]" (read-only)
  - Textarea/editor for reply body
  - Send button
- On send: POST /api/v1/inbox/:id/reply { body_html }
- Success: toast + refresh email thread

Add inboxApi.reply(emailId, bodyHtml) to API client.
```

### C3 — Sent Folder in Inbox
```
Currently inbox only shows inbound emails.
Add a "Sent" tab that shows outbound emails.

Update Inbox page:
- Add tabs: "Inbox" | "Sent" | "Starred"
- Sent tab: GET /api/v1/inbox/?direction=outbound
- Same email list UI but shows "To: X" instead of "From: X"

Backend: Update InboxListView to accept ?direction=inbound|outbound query param.
Default: inbound (preserves existing behavior).
```

---

## SPRINT D: DASHBOARD COMPLETION

### D1 — Purchases Page (Full UI)
```
Currently ⚠️ Basic at /purchases.

Rebuild frontend/src/app/(dashboard)/purchases/page.tsx:
- Summary cards at top: Total Spend (this month), Total Orders, Avg Order Value
- Order list (newest first):
  - Each order card: product image, product name, price ₹, marketplace logo, date, status badge
  - Status: confirmed, shipped, delivered, returned, refunded
  - Click to expand: order ID, seller, tracking link
- Filters: marketplace dropdown, date range, status
- Search bar: search across product names / order IDs
- Pagination: cursor-based

Uses purchasesApi.list(filters) — ensure API supports marketplace/status/date filters.
```

### D2 — Rewards Page (Full UI)
```
Currently ⚠️ Basic at /rewards.

Rebuild frontend/src/app/(dashboard)/rewards/page.tsx:
- Hero card: current points balance (large number), "X points = ₹Y"
- "How to Earn" section: grid of activity cards
  - Write a Review: 20 pts
  - Review with Photo: +10 bonus
  - Review with Video: +20 bonus
  - Connect Email: 50 pts
  - Verified Purchase Review: 40 pts
  - Refer a Friend: 30 pts
- "Redeem" section: Gift card catalog
  - Cards: Amazon, Flipkart, Swiggy (with denominations ₹100, ₹250, ₹500)
  - Click → confirm modal → redeem → show gift card code
- "History" tab: points ledger
  - Date | Action | Points (+/-) | Balance
  - Cursor pagination

Uses rewardsApi: getBalance(), getCatalog(), redeem(cardId, denomination), getHistory()
```

### D3 — Refunds Page (Full UI)
```
Currently ⚠️ Basic at /refunds.

Rebuild frontend/src/app/(dashboard)/refunds/page.tsx:
- Active refunds section (top):
  - Per refund: product, amount, marketplace, initiated date, expected date
  - Countdown timer: "Expected in X days"
  - Status: processing, approved, credited, delayed
  - If delayed (past expected date): red "⚠️ Delayed by X days" warning
- Refund history section (below):
  - Completed refunds with final amount, date credited
- Empty state: "No refunds tracked. Connect your email to auto-detect refunds."

Uses purchasesApi.getRefunds() — already wired, needs better rendering.
```

### D4 — Subscriptions Page (Full UI)
```
Currently ⚠️ Basic at /subscriptions.

Rebuild frontend/src/app/(dashboard)/subscriptions/page.tsx:
- Summary: "You have X active subscriptions costing ₹Y/month (₹Z/year)"
- Subscription cards:
  - Service name + logo (Netflix, Spotify, etc.)
  - Amount per billing period
  - Next renewal date
  - Total spent so far
  - Status badge: active, expiring soon, cancelled
- "Expiring Soon" section: subscriptions renewing within 7 days
- Quick actions: "Set Reminder" (notification), "Manage" (external link)
- Empty state: "No subscriptions detected. Connect your email to auto-detect."

Uses purchasesApi.getSubscriptions()
```

---

## SPRINT E: VISUAL POLISH (Match Figma)

### E1 — Homepage Figma Match
```
Open docs/figma/homepage.png (or the Figma link) side-by-side with localhost:3000.

Compare and fix ALL differences:
- Hero section: layout, gradient, CTA buttons, text sizing
- Category pills/cards: exact styling, icons, colors
- Product grid: card shadows, badge positions, price formatting
- Section headings: font size, weight, spacing
- "View more" links: color, arrow icon
- Footer: layout, link columns, social icons

DON'T add new features. ONLY fix visual styling to match Figma exactly.
Use Tailwind classes only. Update globals.css if needed for custom values.
```

### E2 — Product Detail Figma Match
```
Open docs/figma/Product_detail_page.png side-by-side.

Fix ALL visual differences:
- DudScore gauge: position, size, colors
- Image gallery: thumbnail strip, zoom behavior
- Price section: font size, marketplace logos, "best price" highlight
- Specs table: alternating rows, font styling
- Review section: card layout, vote buttons
- "Buy" buttons: colors per marketplace, hover states
- Breadcrumb: styling, separator icons
```

### E3 — Search + Compare Figma Match
```
Search page (docs/figma/Search_result_page-1.png):
- Filter sidebar: checkbox styling, price range slider, brand list
- Product grid: card spacing, badge positions
- Sort dropdown: styling
- Results count text

Compare page (docs/figma/Comparison_results.png):
- Table layout: sticky header, alternating column colors
- Score bars: color coding, width percentages
- Price cells: highlight best price per row
- "Add to compare" empty slot styling
```

### E4 — Dashboard + Seller Figma Match
```
Dashboard (docs/figma/expense_tracker_mockup.png):
- Spending chart: colors, axes labels, ₹ formatting (not $)
- Insight cards: layout, icons, colors
- Recent purchases: list styling

Seller page (docs/figma/Seller_detail_page-1.png):
- Seller info header: rating stars, verification badge
- Product listing grid: card styling
- Trust indicators section
```

---

## SUMMARY

```
Sprint A: Wire features into UI      — 10 prompts (notifications, reviews, preferences, compare, alerts)
Sprint B: Surface intelligence        —  7 prompts (DudScore breakdown, fraud badges, price chart, deals, similar)
Sprint C: Email in Inbox              —  3 prompts (compose, reply, sent folder)
Sprint D: Dashboard completion        —  4 prompts (purchases, rewards, refunds, subscriptions)
Sprint E: Visual polish               —  4 prompts (Figma matching)

TOTAL: 28 Claude Code prompts

Estimated: 4-5 sessions × 6 prompts each = done in ~5 days
```

---

## RECOMMENDED SESSION PLAN

```
Session 1: A1, A2, A3, A4, A5 (Notifications + Write Review)
Session 2: A6, A7, A8, A9, A10 (Preferences + Compare + Alerts + Sidebar)
Session 3: B1, B2, B3, B4, B5 (DudScore + Fraud + Price Chart + Deals)
Session 4: B6, B7, C1, C2, C3 (Similar + Share + Email)
Session 5: D1, D2, D3, D4 (Dashboard pages)
Session 6: E1, E2, E3, E4 (Figma polish)
```
