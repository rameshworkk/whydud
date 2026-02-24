# WHYDUD — Claude Code Task Prompts (v2.2)

> **Rules:** Run ONE prompt per session block (5-8 prompts max before fresh session).
> Each prompt is atomic — creates 1-3 files max. Reference docs, don't paste content.
> After each prompt: review output → git commit → update PROGRESS.md → next prompt.
>
> **Before first session:** `$env:CLAUDE_CODE_MAX_OUTPUT_TOKENS = "50000"`

---

## PHASE 0: CONTEXT RECOVERY (use at start of every new session)

```
Read CLAUDE.md and PROGRESS.md. Check what files exist in backend/apps/ and frontend/src/.
List what's done and what's next. Then continue with the task I give you.
```

---

## PHASE 1: DATABASE MIGRATIONS (v2.2 schema updates)

> These update existing models to match ARCHITECTURE.md v2.2.
> Run in order. Each creates 1 migration file.

### 1.1 — Multi-domain email field
```
Read docs/ARCHITECTURE.md Section 9, users schema, WhydudEmail table.

In backend/apps/accounts/models.py:
- Add `domain` field to WhydudEmail: CharField(max_length=20, default='whyd.in', choices=[('whyd.in','whyd.in'),('whyd.click','whyd.click'),('whyd.shop','whyd.shop')])
- Update unique constraint: unique_together = ['username', 'domain']
- Update __str__ to return f"{username}@{domain}"

Run makemigrations accounts. Don't touch any other model.
```

### 1.2 — Email direction + recipient fields
```
In backend/apps/email_intel/models.py, InboxEmail model:
- Add `direction` CharField(max_length=10, default='inbound') — choices: inbound, outbound
- Add `recipient_address` CharField(max_length=320, null=True, blank=True)
- Add `resend_message_id` CharField(max_length=200, null=True, blank=True)

Run makemigrations email_intel. Only touch InboxEmail model.
```

### 1.3 — Email sources table
```
Read docs/ARCHITECTURE.md Section 9, email_intel schema, email_sources table.

In backend/apps/email_intel/models.py, create NEW model EmailSource:
- id: UUIDField primary key
- user: ForeignKey to accounts.Account
- source_type: CharField — 'whydud', 'gmail', 'outlook', 'forwarding'
- email_address: CharField(max_length=320)
- provider_config: JSONField(default=dict, blank=True) — encrypted OAuth tokens etc
- sync_status: CharField — 'active', 'paused', 'error', 'disconnected'
- last_synced_at: DateTimeField(null=True)
- is_primary: BooleanField(default=False)
- created_at, updated_at

Run makemigrations email_intel.
```

### 1.4 — Click events table
```
Read docs/ARCHITECTURE.md Section 9, public schema, click_events table.

In backend/apps/pricing/models.py, create NEW model ClickEvent:
- id: BigAutoField primary key
- user: ForeignKey(nullable) to accounts.Account
- session_id: CharField(max_length=100, null=True)
- product: ForeignKey to products.Product
- listing: ForeignKey to products.ProductListing
- marketplace: ForeignKey to products.Marketplace
- affiliate_url: URLField
- clicked_at: DateTimeField(auto_now_add=True)
- referrer_page: CharField(max_length=200, null=True) — 'product_page', 'compare', 'deal'
- ip_hash: CharField(max_length=64, null=True)
- user_agent_hash: CharField(max_length=64, null=True)

Index on (user, clicked_at DESC) and (product, clicked_at DESC).
Run makemigrations pricing.
```

### 1.5 — Price alerts table
```
Read docs/ARCHITECTURE.md Section 9, users schema, price_alerts table.

In backend/apps/wishlists/models.py (or create backend/apps/pricing/models.py if better fit), create PriceAlert:
- id: UUIDField primary key
- user: ForeignKey to accounts.Account
- product: ForeignKey to products.Product
- target_price: DecimalField(max_digits=12, decimal_places=2)
- current_price: DecimalField(max_digits=12, decimal_places=2, null=True)
- marketplace: ForeignKey(nullable) to Marketplace — NULL = any marketplace
- is_active: BooleanField(default=True)
- is_triggered: BooleanField(default=False)
- triggered_at: DateTimeField(null=True)
- triggered_price: DecimalField(null=True)
- notification_sent: BooleanField(default=False)
- created_at, updated_at

Run makemigrations.
```

### 1.6 — Compare sessions + recently viewed + stock alerts
```
In backend/apps/products/models.py, create 3 small models:

CompareSession:
- id: UUIDField pk
- user: ForeignKey(nullable) to Account
- session_id: CharField(max_length=100, null=True) — for anonymous users
- product_ids: ArrayField(UUIDField(), max_length=4)
- created_at, updated_at

RecentlyViewed:
- id: BigAutoField pk
- user: ForeignKey(nullable) to Account
- session_id: CharField(null=True)
- product: ForeignKey to Product
- viewed_at: DateTimeField(auto_now_add=True)
- Unique together: (user, product) or (session_id, product)

StockAlert:
- id: UUIDField pk
- user: ForeignKey to Account
- product: ForeignKey to Product
- listing: ForeignKey to ProductListing
- is_active: BooleanField(default=True)
- notified_at: DateTimeField(null=True)
- created_at

Run makemigrations products.
```

### 1.7 — Update reviews table (Write a Review support)
```
Read docs/ARCHITECTURE.md Section 9, reviews table (the expanded one with user_id, source, etc).

In backend/apps/reviews/models.py, update the Review model. Add these fields:
- user: ForeignKey(nullable) to accounts.Account — NULL for scraped reviews
- source: CharField(max_length=20, default='scraped') — 'scraped' or 'whydud'
- body_positive: TextField(null=True, blank=True) — "What did you like?"
- body_negative: TextField(null=True, blank=True) — "What you didn't like?"
- nps_score: SmallIntegerField(null=True, validators=[MinValueValidator(0), MaxValueValidator(10)])
- media: JSONField(default=list, blank=True) — [{url, type, thumbnail}]
- has_purchase_proof: BooleanField(default=False)
- purchase_proof_url: CharField(max_length=500, null=True, blank=True)
- purchase_platform: CharField(max_length=50, null=True, blank=True)
- purchase_seller: CharField(max_length=200, null=True, blank=True)
- purchase_delivery_date: DateField(null=True, blank=True)
- purchase_price_paid: DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
- feature_ratings: JSONField(default=dict, blank=True) — {"battery_life": 4, "camera": 3}
- seller_delivery_rating: SmallIntegerField(null=True, validators 1-5)
- seller_packaging_rating: SmallIntegerField(null=True, validators 1-5)
- seller_accuracy_rating: SmallIntegerField(null=True, validators 1-5)
- seller_communication_rating: SmallIntegerField(null=True, validators 1-5)
- is_published: BooleanField(default=True)
- publish_at: DateTimeField(null=True)
- updated_at: DateTimeField(auto_now=True)

Add unique_together = ['user', 'product'] (one review per product per user).
Add index on (user) WHERE user IS NOT NULL.
Add index on (source, product).

Run makemigrations reviews.
```

### 1.8 — Notifications tables
```
In backend/apps/accounts/models.py (or create a new notifications app if preferred), create 2 models:

Notification:
- id: BigAutoField pk
- user: ForeignKey to Account, on_delete CASCADE
- type: CharField(max_length=50) — 'price_drop', 'return_window', 'refund_delay', 'back_in_stock', 'review_upvote', 'price_alert', 'discussion_reply', 'level_up', 'points_earned', 'subscription_renewal'
- title: CharField(max_length=500)
- body: TextField(null=True, blank=True)
- action_url: CharField(max_length=500, null=True, blank=True)
- action_label: CharField(max_length=100, null=True, blank=True)
- entity_type: CharField(max_length=50, null=True) — 'product', 'review', 'order', 'alert'
- entity_id: CharField(max_length=200, null=True)
- metadata: JSONField(default=dict, blank=True)
- is_read: BooleanField(default=False)
- email_sent: BooleanField(default=False)
- email_sent_at: DateTimeField(null=True)
- created_at: DateTimeField(auto_now_add=True)

Index: (user, created_at DESC), partial index on is_read=False.

NotificationPreference:
- id: UUIDField pk
- user: OneToOneField to Account, on_delete CASCADE
- price_drops: JSONField(default={"in_app": True, "email": True})
- return_windows: JSONField(default={"in_app": True, "email": True})
- refund_delays: JSONField(default={"in_app": True, "email": True})
- back_in_stock: JSONField(default={"in_app": True, "email": False})
- review_upvotes: JSONField(default={"in_app": True, "email": False})
- price_alerts: JSONField(default={"in_app": True, "email": True})
- discussion_replies: JSONField(default={"in_app": True, "email": False})
- level_up: JSONField(default={"in_app": True, "email": False})
- created_at, updated_at

Run makemigrations.
```

### 1.9 — Purchase preferences tables
```
Create 2 models. Can go in backend/apps/accounts/models.py or a new preferences app.

PurchasePreference:
- id: UUIDField pk
- user: ForeignKey to Account, on_delete CASCADE
- category: ForeignKey to products.Category
- preferences: JSONField — stores full questionnaire answers
- created_at, updated_at
- unique_together = ['user', 'category']
- Index on user.

CategoryPreferenceSchema:
- id: AutoField pk
- category: OneToOneField to products.Category
- schema: JSONField — UI schema defining the questionnaire structure
- version: IntegerField(default=1)
- is_active: BooleanField(default=True)
- created_at

Run makemigrations.
```

### 1.10 — Reviewer profiles table
```
In backend/apps/reviews/models.py, create ReviewerProfile:
- id: UUIDField pk
- user: OneToOneField to accounts.Account, on_delete CASCADE
- total_reviews: IntegerField(default=0)
- total_upvotes_received: IntegerField(default=0)
- total_helpful_votes: IntegerField(default=0)
- review_quality_avg: DecimalField(max_digits=3, decimal_places=2, default=0)
- reviewer_level: CharField(max_length=20, default='bronze') — 'bronze', 'silver', 'gold', 'platinum'
- badges: JSONField(default=list, blank=True)
- leaderboard_rank: IntegerField(null=True)
- is_top_reviewer: BooleanField(default=False)
- created_at, updated_at

Run makemigrations reviews. Then run `python manage.py migrate` to apply ALL migrations.
```

---

## PHASE 2: API ENDPOINTS (new features)

### 2.1 — Write a Review API
```
Read docs/ARCHITECTURE.md Section 10, "REVIEWS (Write a Review)" endpoints.

Create in backend/apps/reviews/:

serializers.py — add:
- WriteReviewSerializer: validates overall rating (required), title, body_positive, body_negative,
  nps_score, feature_ratings (JSONB), purchase proof fields, seller ratings.
  Enforces: one review per user per product. Sets source='whydud', is_published=False,
  publish_at=now()+48hours.
- MyReviewsSerializer: list serializer for user's own reviews.

views.py — add:
- WriteReviewView (POST /api/v1/products/:slug/reviews) — authenticated only.
  Creates review with 48hr publish hold. If purchase_proof uploaded, set has_purchase_proof=True.
- EditReviewView (PATCH /api/v1/reviews/:id) — owner only.
- DeleteReviewView (DELETE /api/v1/reviews/:id) — owner only.
- MyReviewsView (GET /api/v1/me/reviews) — list user's reviews.
- ReviewFeaturesView (GET /api/v1/products/:slug/review-features) — returns category-specific
  feature rating keys from category.spec_schema.review_features.

Wire URLs in reviews/urls.py. Include in whydud/urls.py.
```

### 2.2 — Purchase proof upload endpoint
```
In backend/apps/reviews/views.py, add:

UploadPurchaseProofView (POST /api/v1/reviews/:id/purchase-proof):
- Accepts multipart/form-data with image file
- Validates: file is image (jpg/png/pdf), max 5MB
- Saves to media/review-proofs/{review_id}/{filename}
- Updates review: has_purchase_proof=True, purchase_proof_url=saved_path
- Returns updated review

Wire URL: /api/v1/reviews/:id/purchase-proof
```

### 2.3 — Notifications API
```
Read docs/ARCHITECTURE.md Section 10, "NOTIFICATIONS" endpoints.

Create backend/apps/accounts/notification_serializers.py:
- NotificationSerializer: id, type, title, body, action_url, action_label, is_read, created_at
- NotificationPreferenceSerializer: all preference fields

Create backend/apps/accounts/notification_views.py:
- NotificationListView (GET /api/v1/notifications) — paginated, user's notifications
- UnreadCountView (GET /api/v1/notifications/unread-count) — returns {count: N}
- MarkReadView (PATCH /api/v1/notifications/:id/read) — sets is_read=True
- MarkAllReadView (POST /api/v1/notifications/mark-all-read) — bulk update
- DismissView (DELETE /api/v1/notifications/:id)
- PreferencesView (GET + PATCH /api/v1/notifications/preferences)

Wire URLs. Include in whydud/urls.py.
```

### 2.4 — Purchase Preferences API
```
Read docs/ARCHITECTURE.md Section 10, "PURCHASE PREFERENCES" endpoints.

Create serializers + views (can be in accounts app or new preferences app):

Serializers:
- PurchasePreferenceSerializer: category_slug (read), preferences (JSONB), updated_at
- CategoryPreferenceSchemaSerializer: category_slug, schema (JSONB), version

Views:
- PreferenceListView (GET /api/v1/preferences) — all user's category preferences
- PreferenceDetailView (GET/POST/PATCH/DELETE /api/v1/preferences/:category_slug)
- PreferenceSchemaView (GET /api/v1/preferences/:category_slug/schema) — returns questionnaire schema

Wire URLs.
```

### 2.5 — Price alerts API
```
Read docs/ARCHITECTURE.md Section 10, "PRICE ALERTS" endpoints.

In backend/apps/pricing/ (or wishlists):

Serializers:
- PriceAlertSerializer: product (slug), target_price, marketplace (optional), is_active, is_triggered

Views:
- CreatePriceAlertView (POST /api/v1/alerts/price)
- ListAlertsView (GET /api/v1/alerts) — user's active alerts
- UpdateAlertView (PATCH /api/v1/alerts/:id) — update target price or pause
- DeleteAlertView (DELETE /api/v1/alerts/:id)
- TriggeredAlertsView (GET /api/v1/alerts/triggered) — recently triggered

Wire URLs.
```

### 2.6 — Reviewer profile + leaderboard API
```
Read docs/ARCHITECTURE.md Section 10, "REVIEWER PROFILE" endpoints.

In backend/apps/reviews/:

Serializers:
- ReviewerProfileSerializer: user_name, total_reviews, reviewer_level, badges, leaderboard_rank

Views:
- MyReviewerProfileView (GET /api/v1/me/reviewer-profile)
- LeaderboardView (GET /api/v1/leaderboard/reviewers) — top 20 this week, paginated
- CategoryLeaderboardView (GET /api/v1/leaderboard/reviewers/:category_slug)

Wire URLs.
```

### 2.7 — Trending & analytics API
```
Read docs/ARCHITECTURE.md Section 10, "TRENDING & ANALYTICS" endpoints.

In backend/apps/products/views.py, add:
- TrendingProductsView (GET /api/v1/trending/products) — most viewed this week
  Query: products ordered by view_count DESC, filter last 7 days from recently_viewed
- RisingProductsView (GET /api/v1/trending/rising) — biggest DudScore increase in 30d
- PriceDroppingView (GET /api/v1/trending/price-dropping) — consistent downward trend
- CategoryLeaderboardView (GET /api/v1/categories/:slug/leaderboard) — top 10 by DudScore
- MostLovedView (GET /api/v1/categories/:slug/most-loved) — highest DudScore
- MostHatedView (GET /api/v1/categories/:slug/most-hated) — lowest DudScore

Wire URLs under products/urls.py.
```

### 2.8 — Cross-platform listings + compare + share APIs
```
Read docs/ARCHITECTURE.md Section 10, "CROSS-PLATFORM" + "COMPARISON" + "SHARE" endpoints.

In backend/apps/products/views.py, add:
- ProductListingsView (GET /api/v1/products/:slug/listings) — all marketplace listings
- BestPriceView (GET /api/v1/products/:slug/best-price) — lowest price + affiliate link
- SimilarProductsView (GET /api/v1/products/:slug/similar) — same category + price range
- AlternativeProductsView (GET /api/v1/products/:slug/alternatives) — direct competitors
- ShareProductView (GET /api/v1/products/:slug/share) — generate OG meta + share URL
- ShareCompareView (GET /api/v1/compare/share?products=...) — comparison share URL

In backend/apps/products/views.py, update CompareView to include:
- Marketplace × product price matrix
- Spec diff highlighting

Wire all URLs.
```

### 2.9 — Recently viewed + stock alerts APIs
```
In backend/apps/products/views.py:
- RecentlyViewedListView (GET /api/v1/me/recently-viewed) — last 20 products
- LogViewView (POST /api/v1/me/recently-viewed) — log a product view
- CreateStockAlertView (POST /api/v1/alerts/stock) — back-in-stock alert
- ListStockAlertsView (GET /api/v1/alerts/stock)
- DeleteStockAlertView (DELETE /api/v1/alerts/stock/:id)

Wire URLs.
```

### 2.10 — Dynamic TCO API
```
Read docs/ARCHITECTURE.md Section 10, "TCO (Dynamic Per-Category)" endpoints.

In backend/apps/tco/views.py, update/add:
- TCOModelView (GET /api/v1/tco/models/:category_slug) — returns model + input_schema
- TCOCalculateView (POST /api/v1/tco/calculate) — receives user inputs, evaluates cost formula, returns breakdown {purchase, ongoing, resale, total, per_year, per_month}
- TCOCompareView (GET /api/v1/tco/compare?products=slug1,slug2,slug3) — side-by-side TCO

The calculate view should parse cost_components JSONB formula and evaluate it
with user-provided inputs. Return: {total, per_year, per_month, breakdown: {purchase, ongoing_annual, one_time_risk, resale}}.

Wire URLs.
```

---

## PHASE 3: FRONTEND — New Types + API Client Extensions

### 3.1 — Add new TypeScript types
```
In frontend/src/lib/api/types.ts, add these interfaces:

// Reviews
WriteReviewPayload: { rating, title, body_positive, body_negative, nps_score, feature_ratings, purchase_platform, purchase_seller, purchase_delivery_date, purchase_price_paid, seller_delivery_rating, seller_packaging_rating, seller_accuracy_rating, seller_communication_rating }
ReviewFeature: { key: string, label: string, icon: string }
ReviewerProfile: { total_reviews, reviewer_level, badges, leaderboard_rank }

// Notifications
Notification: { id, type, title, body, action_url, action_label, is_read, created_at, metadata }
NotificationPreferences: { price_drops, return_windows, refund_delays, back_in_stock, review_upvotes, price_alerts, discussion_replies, level_up }

// Preferences
PurchasePreference: { category_slug, preferences: Record<string, any>, updated_at }
PreferenceSchema: { category_slug, schema: { sections: PreferenceSection[] }, version }
PreferenceSection: { key, title, icon, fields: PreferenceField[] }
PreferenceField: { key, type, label, unit?, options?, min?, max?, default?, quick_select? }

// Alerts
PriceAlert: { id, product, target_price, current_price, marketplace, is_active, is_triggered, triggered_at }
StockAlert: { id, product, listing, is_active, created_at }

// TCO
TCOModel: { category_slug, input_schema, cost_components, presets }
TCOResult: { total, per_year, per_month, breakdown: { purchase, ongoing_annual, one_time_risk, resale } }

Don't touch existing types. Only add new ones.
```

### 3.2 — API client: reviews, notifications, preferences
```
Create 3 new files in frontend/src/lib/api/:

reviews.ts:
- submitReview(slug, payload: WriteReviewPayload)
- editReview(id, payload)
- deleteReview(id)
- getMyReviews()
- getReviewFeatures(slug) → ReviewFeature[]
- uploadPurchaseProof(reviewId, file: File)
- getReviewerProfile() → ReviewerProfile
- getLeaderboard(page?) → ReviewerProfile[]

notifications.ts:
- getNotifications(page?) → Notification[]
- getUnreadCount() → {count: number}
- markAsRead(id)
- markAllAsRead()
- dismissNotification(id)
- getNotificationPreferences() → NotificationPreferences
- updateNotificationPreferences(prefs)

preferences.ts:
- getPreferences() → PurchasePreference[]
- getPreference(categorySlug) → PurchasePreference
- savePreference(categorySlug, data)
- updatePreference(categorySlug, data)
- deletePreference(categorySlug)
- getPreferenceSchema(categorySlug) → PreferenceSchema
```

### 3.3 — API client: alerts, trending, TCO
```
Create/update files in frontend/src/lib/api/:

alerts.ts:
- createPriceAlert(productId, targetPrice, marketplace?)
- getAlerts() → PriceAlert[]
- updateAlert(id, targetPrice)
- deleteAlert(id)
- getTriggeredAlerts() → PriceAlert[]
- createStockAlert(productId, listingId)
- getStockAlerts() → StockAlert[]
- deleteStockAlert(id)

trending.ts:
- getTrendingProducts() → Product[]
- getRisingProducts() → Product[]
- getPriceDropping() → Product[]
- getCategoryLeaderboard(slug) → Product[]
- getMostLoved(slug) → Product[]
- getMostHated(slug) → Product[]

Update tco.ts:
- getTCOModel(categorySlug) → TCOModel
- calculateTCO(inputs) → TCOResult
- compareTCO(productSlugs) → TCOResult[]
```

---

## PHASE 4: FRONTEND — Components (build bottom-up)

### 4.1 — Notification bell icon
```
Create frontend/src/components/notifications/notification-bell.tsx:
- "use client" component
- Bell icon (lucide-react Bell) in header
- Red badge with unread count (fetched from /api/v1/notifications/unread-count)
- On click: dropdown showing last 5 notifications
- Each notification: icon (type-specific), title, timestamp, read/unread indicator
- "View all" link → /notifications
- Poll every 30 seconds for unread count (useEffect + setInterval)

Props: none (fetches own data via useAuth context for user)
```

### 4.2 — Notification card + list
```
Create frontend/src/components/notifications/notification-card.tsx:
- Notification type icon (📉 price, 📦 order, ⭐ review, 🔔 alert)
- Title (font-semibold), body text (text-slate-600)
- Action button (orange, small) if action_url exists
- Timestamp (timeAgo format)
- Unread: bg-orange-50 left border. Read: bg-white.
- On click: mark as read + navigate to action_url

Create frontend/src/components/notifications/notification-list.tsx:
- Filter tabs: All | Price Drops | Orders | Reviews | System
- Maps notifications → NotificationCard
- "Mark all as read" button at top
- Empty state: "No notifications yet"
```

### 4.3 — Star rating input component
```
Create frontend/src/components/reviews/star-rating-input.tsx:
- "use client" component
- 5 clickable stars (lucide Star icon)
- Hover: fill stars up to hovered position (yellow)
- Click: set rating
- Props: value: number, onChange: (rating: number) => void, size?: 'sm' | 'md' | 'lg'
- Display only mode: readonly prop (no hover/click, just display)
```

### 4.4 — Write a Review tabs (Tab 1 + Tab 2)
```
Create frontend/src/components/review/verify-purchase-tab.tsx:
- "Do you have proof of purchase?" Yes/No radio
- If Yes: upload invoice button (file input, image/pdf)
- Purchase details form: Platform dropdown, Seller name input, Delivery date picker, Price paid ₹ input
- "Earn a credibility badge" callout card
- [Skip] [Next →] buttons

Create frontend/src/components/review/leave-review-tab.tsx:
- Overall rating (StarRatingInput, required)
- "Rate other features >" link
- Review title input (placeholder: "What's important for people to know?")
- "What did you like?" textarea
- "What you didn't like?" textarea
- Media upload: "Add photos or videos" button (multi-file)
- NPS score: 0-10 horizontal scale with labels "Not likely" to "Extremely likely"
- [Next →] button
```

### 4.5 — Write a Review tabs (Tab 3 + Tab 4)
```
Create frontend/src/components/review/rate-features-tab.tsx:
- "use client" component
- Fetches feature keys from API: GET /api/v1/products/:slug/review-features
- Renders 2-column grid of StarRatingInput for each feature
- Example: "Battery Life" ⭐⭐⭐⭐☆, "Camera Quality" ⭐⭐⭐☆☆
- Features are dynamic per category (phones vs ACs vs air purifiers)
- [Skip] [Next →] buttons

Create frontend/src/components/review/seller-feedback-tab.tsx:
- "Rate the Seller" heading
- StarRatingInput × 4: Delivery Speed, Packaging Quality, Product Accuracy, Communication
- [Submit Review] button (orange, full width)
- On submit: calls submitReview API with all data from all 4 tabs
```

### 4.6 — Write a Review page
```
Create frontend/src/app/(review)/product/[slug]/review/page.tsx:
- "use client" page
- Layout: 2-column — left: product image + title sidebar, right: tabbed form
- shadcn Tabs component with 4 tabs: "Verify Purchase", "Leave a Review", "Rate Features", "Seller Feedback"
- Tab state managed in parent — all tab data stored in single state object
- User can freely navigate between tabs (no forced order)
- Submit only enabled when rating (required) is filled
- On submit: POST to API, show success toast, redirect to product page
- Auth required — redirect to /login if not authenticated

Uses: VerifyPurchaseTab, LeaveReviewTab, RateFeaturesTab, SellerFeedbackTab
```

### 4.7 — Notification center page
```
Create frontend/src/app/(dashboard)/notifications/page.tsx:
- Page heading: "Notifications"
- Uses NotificationList component
- Server component wrapper that fetches initial data
- Client component inside for interactivity (mark read, filters)
- Pagination at bottom

Update frontend/src/components/layout/header.tsx:
- Add NotificationBell component next to user avatar
- Show bell icon for logged-in users only
```

### 4.8 — Preference questionnaire renderer (dynamic)
```
Create frontend/src/components/preferences/preference-form.tsx:
- "use client" component
- Props: schema: PreferenceSchema, initialValues?: Record<string, any>, onSubmit
- Renders sections from schema.sections dynamically
- Field type rendering:
  - "number" → NumberInput with unit label + optional quick_select chips
  - "currency" → ₹ prefixed input
  - "dropdown" → Select component
  - "radio" → RadioGroup
  - "tags" → multi-select tag chips (toggle on/off)
  - "toggle" → Switch component
  - "slider" → Slider with min/max
  - "range_slider" → dual-handle range slider
- Each section: icon + title + fields
- [Save Preferences] button at bottom
- Form validation: required fields only

This is the KEY component — schema-driven, no hardcoded category logic.
```

### 4.9 — Preferences page
```
Create frontend/src/app/(dashboard)/preferences/page.tsx:
- Page heading: "Purchase Preferences"
- CategorySelector: grid of cards (Air Purifier, AC, Water Purifier, Refrigerator, Washing Machine, Vehicle, Laptop)
  Each card: icon + name + "Saved ✓" badge if user has preferences
- On card click: fetch schema for that category → show PreferenceForm
- PreferenceForm pre-filled with existing preferences if any
- On save: POST/PATCH to API
- Success toast on save
```

### 4.10 — Price alert button + modal
```
Create frontend/src/components/product/price-alert-button.tsx:
- "use client" component
- Button: "🔔 Set Price Alert" (outline style)
- On click: opens Dialog/Sheet with:
  - Current price display
  - Target price input (₹)
  - Marketplace selector: "Any marketplace" or specific (dropdown)
  - [Set Alert] button
- On submit: POST /api/v1/alerts/price
- If alert already exists for this product: show "Alert active at ₹X" with edit/delete options
- Props: productId, currentPrice, marketplaces[]
```

### 4.11 — Floating compare tray
```
Create frontend/src/components/compare/compare-tray.tsx:
- "use client" component, rendered in root layout
- Fixed bottom bar, appears when 1+ products added to compare
- Shows 1-4 product thumbnails + prices
- [Compare Now] button → navigates to /compare?products=slug1,slug2
- [✕] button per product to remove
- Persists across navigation via React context (CompareContext)

Create frontend/src/hooks/use-compare.ts:
- CompareContext provider
- addToCompare(product), removeFromCompare(slug), clearCompare()
- products: Product[] (max 4)
- State stored in React context (NOT localStorage per artifact rules)

Create frontend/src/components/product/add-to-compare-button.tsx:
- Button: "⚖ Compare" — adds product to compare tray
- If already in tray: "✓ In Compare" (green, click to remove)
```

### 4.12 — My Reviews page + Alerts page
```
Create frontend/src/app/(dashboard)/my-reviews/page.tsx:
- Heading: "My Reviews"
- List of user's reviews (from GET /api/v1/me/reviews)
- Each review: product name, rating, date, publish status ("Publishing in 23h" or "Published")
- Edit / Delete buttons per review
- Empty state: "You haven't written any reviews yet. Start reviewing!"

Create frontend/src/app/(dashboard)/alerts/page.tsx:
- Two sections: "Price Alerts" + "Stock Alerts"
- Price Alerts: product name, target price, current price, status (active/triggered), edit/delete
- Stock Alerts: product name, marketplace, status, delete
- Empty states for each section
```

---

## PHASE 5: FRONTEND — TCO + Leaderboard + Trending

### 5.1 — Dynamic TCO calculator
```
Update frontend/src/components/tco/tco-calculator.tsx:
- "use client" component
- Fetches TCO model from API: GET /api/v1/tco/models/:category_slug
- Renders input fields dynamically from model.input_schema.inputs
- Each field: label, type (number/currency/decimal), default value
- Ownership years selector (slider or dropdown)
- Preset buttons: Default / Conservative / Optimistic (from model.input_schema.presets)
- On change: POST /api/v1/tco/calculate with current inputs
- Results: stacked bar chart (Recharts) — Purchase (orange), Ongoing (blue), Resale (green)
- Total cost, per-year, per-month summary cards

Props: categorySlug, products (for comparison mode, up to 3)
```

### 5.2 — Reviewer leaderboard page
```
Create frontend/src/app/(public)/leaderboard/page.tsx:
- Heading: "Top Reviewers This Week"
- Table/cards: Rank, Reviewer name, Level badge (colored: bronze/silver/gold/platinum), 
  Total reviews, Upvotes received
- Top 3 highlighted with larger cards
- Category filter dropdown
- Pagination
- Uses GET /api/v1/leaderboard/reviewers
```

### 5.3 — Trending sections for homepage
```
Create frontend/src/components/product/trending-section.tsx:
- Reusable section component
- Props: title, endpoint (trending/rising/price-dropping), limit
- Fetches products from API
- Renders ProductCard grid (4 columns desktop, 2 mobile)
- "View all →" link

Update homepage page.tsx to include:
- "Trending Products" section (GET /api/v1/trending/products)
- "Price Dropping" section (GET /api/v1/trending/price-dropping)
(Only add these sections, don't rebuild the whole homepage)
```

---

## PHASE 6: SEED DATA

### 6.1 — Category preference schemas seed
```
Create backend/apps/accounts/management/commands/seed_preference_schemas.py (or appropriate app):

Django management command that creates CategoryPreferenceSchema records for:

1. Air Purifiers — full schema from ARCHITECTURE.md Epic 8 US-8.1:
   Sections: Room Requirements, Health & Sensitivity, Filtration, Performance, Smart Features, Cost
   (Use the exact field structure from ARCHITECTURE.md)

2. ACs — sections: Room, Type/Tonnage, Energy, Smart Features, Budget
3. Water Purifiers — sections: Water Source, Purification, Capacity, Smart, Budget
4. Refrigerators — sections: Capacity, Type, Energy, Features, Budget
5. Washing Machines — sections: Capacity, Type, Programs, Budget
6. Vehicles — sections: Type, Fuel, Budget, Use Case, Features
7. Laptops — sections: Use Case, Screen, RAM/Storage, GPU, Budget

Each schema: JSONB with {sections: [{key, title, icon, fields: [{key, type, label, options?, ...}]}]}
Run: python manage.py seed_preference_schemas
```

### 6.2 — TCO model seeds
```
Create backend/apps/tco/management/commands/seed_tco_models.py:

Django management command that creates TCOModel records for:

1. AC (Split): input_schema with fields from ARCHITECTURE.md Epic 5
   (purchase_price, resale_value, annual_energy_kwh, electricity_price, annual_maintenance,
    filter_cost, filter_frequency, compressor_prob, compressor_cost)
   + presets (default, conservative, optimistic)
   + cost_components formula

2. Air Purifier: filter replacement, energy, CADR degradation
3. Water Purifier: cartridge/membrane, water, electricity, maintenance
4. Refrigerator: energy, maintenance, compressor
5. Washing Machine: energy, water, detergent, maintenance

Run: python manage.py seed_tco_models
```

### 6.3 — Review feature ratings seed
```
Create a management command or data migration that updates categories.spec_schema
to include review_features for existing categories:

Phones: [
  {key: "style_design", label: "Style & Design"},
  {key: "battery_life", label: "Battery Life"},
  {key: "user_friendliness", label: "User Friendliness"},
  {key: "performance", label: "Performance"},
  {key: "camera_quality", label: "Camera Quality"},
  {key: "value_for_money", label: "Value for Money"},
  {key: "durability", label: "Durability"}
]

ACs: [Cooling, Energy Efficiency, Noise, Build Quality, Smart Features, Installation, Value]
Air Purifiers: [Filtration, Noise, Coverage, Filter Life, Smart Features, Build, Value]
Water Purifiers: [Purification Quality, Taste, Flow Rate, Filter Life, Build, Value]

Update the spec_schema JSONField to include {"review_features": [...]} for each category.
```

---

## PHASE 7: CELERY TASKS (background jobs)

### 7.1 — Notification dispatch task
```
Create backend/apps/accounts/tasks.py (or notifications/tasks.py):

@shared_task
def create_notification(user_id, type, title, body, action_url=None, action_label=None, entity_type=None, entity_id=None, metadata=None):
    """Creates in-app notification and optionally sends email based on user preferences."""
    1. Create Notification record
    2. Check NotificationPreference for this type
    3. If email=True: queue send_notification_email task
    4. Return notification_id

@shared_task
def send_notification_email(notification_id):
    """Sends email notification via Resend API."""
    1. Fetch notification + user
    2. Render email template (plain + HTML)
    3. Send via Resend to user's @whyd.* email or personal email
    4. Update notification.email_sent = True

Register tasks in Celery.
```

### 7.2 — Review publish task + reviewer level calculation
```
Create/update backend/apps/reviews/tasks.py:

@shared_task
def publish_pending_reviews():
    """Runs every hour. Publishes reviews past their 48hr hold."""
    Reviews.objects.filter(is_published=False, publish_at__lte=now()).update(is_published=True)

@shared_task
def update_reviewer_profiles():
    """Runs weekly (Celery Beat). Updates reviewer levels and leaderboard."""
    For each user with reviews:
    - Count total reviews, total upvotes received
    - Set level: bronze (1-4), silver (5-14), gold (15-29), platinum (30+)
    - Rank by total_upvotes_received this week → set leaderboard_rank
    - Save ReviewerProfile

Register both in Celery Beat schedule:
- publish_pending_reviews: every 1 hour
- update_reviewer_profiles: every Monday 00:00 UTC
```

### 7.3 — Price alert check task
```
Create/update backend/apps/pricing/tasks.py:

@shared_task
def check_price_alerts():
    """Runs after every scrape cycle. Checks if any price alerts are triggered."""
    active_alerts = PriceAlert.objects.filter(is_active=True, is_triggered=False)
    for alert in active_alerts:
        current = get_current_best_price(alert.product, alert.marketplace)
        if current and current <= alert.target_price:
            alert.is_triggered = True
            alert.triggered_at = now()
            alert.triggered_price = current
            alert.save()
            # Create notification
            create_notification.delay(
                user_id=alert.user_id,
                type='price_alert',
                title=f"Price alert! {alert.product.title} is now ₹{current}",
                action_url=f"/product/{alert.product.slug}",
                action_label="Buy Now"
            )
```

---

## PHASE 8: INTEGRATION + POLISH

### 8.1 — Wire notification bell into header
```
In frontend/src/components/layout/header.tsx:
- Import NotificationBell component
- Add it next to the user avatar (right side of header)
- Only show for logged-in users (check useAuth)
- Add "Post a Review" button linking to /product/:slug/review (needs recent product context)
Don't change anything else in the header.
```

### 8.2 — Add "Write a Review" button to product page
```
In the product detail page (frontend/src/app/(public)/product/[slug]/page.tsx):
- Add "Write a Review" button/link below the reviews section
- Links to /product/{slug}/review
- Only show for logged-in users
- If user already has a review: show "Edit Your Review" instead
Don't rebuild the product page. Just add the button.
```

### 8.3 — Settings page: notification preferences tab
```
In frontend/src/app/(dashboard)/settings/page.tsx:
- Add a new tab: "Notifications"
- Notification preferences form: toggle switches per notification type
  Each row: notification type name | In-app toggle | Email toggle
- Fetches from GET /api/v1/notifications/preferences
- On save: PATCH /api/v1/notifications/preferences
- Success toast on save
```

### 8.4 — Add sidebar links for new pages
```
In frontend/src/components/layout/sidebar.tsx:
- Add nav links: Notifications (🔔), My Reviews (⭐), Preferences (⚙), Alerts (📊), Leaderboard (🏆)
- Use lucide-react icons
- Active state: orange text + bg-orange-50
Don't change anything else.
```

---

## TROUBLESHOOTING

If Claude Code hits token limit:
- Break further: "Just create the serializer, not the views"
- Or: "Just add fields to Review model, don't create migrations yet"

If context compacted:
- "Read CLAUDE.md and PROGRESS.md. Check backend/apps/ and frontend/src/. Continue with [task]."

If migration errors:
- "Run python manage.py showmigrations. Then fix [specific app] migration."

Session management:
- Fresh session every 5-8 prompts
- Git commit after every successful prompt
- Update PROGRESS.md after every phase completion
