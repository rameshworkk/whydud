# WHYDUD — Admin Tooling & Monitoring Guide

> **What you need:** A single dashboard where you can monitor everything —
> scraper health, data quality, user activity, revenue, content moderation,
> system health — without touching the terminal.
>
> **Current state:** Basic Django Admin with model registration. ScraperRun, AuditLog,
> ModerationQueue, SiteConfig models exist but the admin is barebones.
>
> **This file:** Complete spec of what the admin should contain, plus Claude Code prompts to build it.

---

## WHAT THE ADMIN DASHBOARD NEEDS (Complete List)

### 1. 🕷️ SCRAPING CONSOLE — "Are my scrapers healthy?"

**What you see at a glance:**
- Last scrape time per marketplace (Amazon: 2h ago ✅, Flipkart: 5h ago ✅)
- Success/failure rate last 7 days (bar chart)
- Items scraped per run (line chart, trend)
- Active/queued/failed jobs right now

**Detailed views:**
- **Job History table:** marketplace, spider, status (✅❌🔄), items scraped/created/updated/failed, duration, started_at, completed_at, error message (expandable)
- **Per-marketplace stats:** avg items/run, avg duration, failure rate, last successful run
- **Error log:** last 50 errors with tracebacks (from ScraperJob.error_message)
- **Anti-detection stats:** captcha rate, 403 rate, timeout rate per marketplace

**Actions you can take:**
- ▶️ "Run Amazon Spider Now" button → triggers `run_marketplace_spider.delay('amazon_in')`
- ▶️ "Run Flipkart Spider Now" button → triggers `run_marketplace_spider.delay('flipkart')`
- 🔗 "Scrape Single URL" input → paste any Amazon/Flipkart URL → `scrape_product_adhoc.delay(url)`
- ⏸️ "Pause marketplace" → set marketplace.is_active=False (stops Beat from triggering)
- ⚙️ Edit scraping config: max_pages, delays, timeout, spider settings

---

### 2. 📦 DATA QUALITY CONSOLE — "Is my data clean?"

**What you see at a glance:**
- Total products / listings / snapshots (with trend arrows ↑↓)
- Products missing key data: no images, no price, no brand, no category
- Duplicate products (matching confidence < 0.85 — needs manual merge)
- Orphaned listings (listing exists but no canonical product linked)

**Detailed views:**
- **Product health table:** product name, has_images, has_price, has_brand, has_category, listing_count, dud_score, last_scraped
- **Matching review queue:** products matched with confidence 0.60-0.85 need manual verification
  - Show: Product A (Amazon) ↔ Product B (Flipkart), confidence score, merge/reject buttons
- **Brand aliases:** manage Brand.aliases (e.g., "MI" → "Xiaomi", "SAMSUNG" → "Samsung")
- **Category mapping:** assign uncategorized products to categories
- **Price anomalies:** listings where price changed >50% in 24h (possible error pricing or scrape bug)

**Actions:**
- 🔀 "Merge Products" — select 2+ products → merge into one canonical product, re-link listings
- ✂️ "Split Product" — if wrongly merged, separate back into distinct products
- 🏷️ "Assign Category" — bulk-assign category to uncategorized products
- 🗑️ "Deactivate Product" — mark as inactive (won't show on frontend, but data preserved)
- ✏️ "Edit Product" — override title, images, brand, category, specs

---

### 3. 📊 DUDSCORE CONSOLE — "Are scores trustworthy?"

**What you see at a glance:**
- Score distribution histogram (0-100, how many products in each bucket)
- Average DudScore across all products
- Products scored vs unscored
- Last recalculation date
- Score confidence distribution (how many "very low" vs "high" confidence)

**Detailed views:**
- **Score breakdown per product:** 6 component scores (sentiment, rating quality, price value, credibility, stability, return signal) + fraud multiplier + confidence multiplier
- **Score history:** chart showing how a product's score changed over time (from DudScoreHistory)
- **Anomaly detection:** products where score changed >20 points in one recalculation
- **Config weights:** current DudScoreConfig (w_sentiment, w_rating_quality, etc.) — editable

**Actions:**
- 🔄 "Recalculate All Scores" → triggers `full_dudscore_recalculation.delay()`
- 🔄 "Recalculate This Product" → triggers `compute_dudscore.delay(product_id)`
- ⚙️ "Edit Score Weights" → update DudScoreConfig (with audit log)
- 📊 "Score Simulation" — change weights, preview what scores WOULD be (without saving)

---

### 4. 🛡️ REVIEW MODERATION CONSOLE — "Is user content clean?"

**What you see at a glance:**
- Reviews pending moderation (48h hold, not yet published)
- Flagged reviews (2+ fraud signals)
- Reviews published today / this week
- Fake review detection rate (% flagged of total)

**Detailed views:**
- **Moderation queue:** reviews sorted by publish_at (soonest first)
  - Each review: author, product, rating, text preview, fraud_flags, credibility_score
  - Side-by-side: original review text + fraud signals highlighted
- **Flagged reviews:** filtered to is_flagged=True
  - Show fraud_flags breakdown: copy_paste, rating_burst, suspiciously_short, etc.
  - Credibility score with color coding (red < 0.3, yellow 0.3-0.7, green > 0.7)
- **Reviewer profiles:** top reviewers, their stats, level, suspicious patterns
- **Bulk detection log:** results from last detect_fake_reviews run per product

**Actions:**
- ✅ "Approve" — publish review immediately (override 48h hold)
- ❌ "Reject" — delete review, notify user
- 🚫 "Suspend Reviewer" — flag user account, hide all their reviews
- 🔄 "Re-run Fraud Detection" → triggers detect_fake_reviews for a product
- 📧 "Warn User" — send warning notification about review quality

---

### 5. 👥 USER MANAGEMENT CONSOLE — "Who's using the platform?"

**What you see at a glance:**
- Total users, new signups today/week/month (line chart)
- Active users (logged in last 7 days)
- Users with @whyd.* email activated
- OAuth vs email-password ratio

**Detailed views:**
- **User table:** name, email, @whyd.* email, signup date, last login, review count, subscription tier, status
- **User detail:** full profile, all reviews, all alerts, all preferences, login history, click history
- **Email usage:** which @whyd.* emails are active, how many emails received/sent
- **Reward balances:** top point earners, redemption history

**Actions:**
- 🚫 "Suspend User" — deactivate account, hide reviews
- ✅ "Restore User" — reactivate
- 🔑 "Reset Password" — force password reset
- 💎 "Grant Points" — manually award reward points
- 📧 "Send Notification" — send custom notification to user

---

### 6. 💰 REVENUE & AFFILIATE CONSOLE — "Am I making money?"

**What you see at a glance:**
- Total clicks today / this week / this month
- Clicks by marketplace (pie chart)
- Click-through rate (clicks / product page views)
- Top clicked products (revenue potential)
- Revenue estimate (if affiliate networks provide conversion data)

**Detailed views:**
- **Click log:** timestamp, user (or anonymous), product, marketplace, source page, device type, affiliate URL
- **Marketplace performance:** clicks, CTR, average price at click, per marketplace
- **Source page analysis:** where clicks come from (product_page, comparison, deal, search, homepage)
- **Affiliate tag verification:** are tags being injected correctly? Sample URLs to verify
- **Subscription stats:** free vs pro users, MRR, churn

**Actions:**
- 📊 "Export Click Data" → CSV download for affiliate reconciliation
- ⚙️ "Update Affiliate Tags" → edit marketplace.affiliate_tag + affiliate_param
- 💳 "Manage Subscriptions" → view/cancel Razorpay subscriptions

---

### 7. 📧 EMAIL SYSTEM CONSOLE — "Is email working?"

**What you see at a glance:**
- Emails received today / this week
- Emails sent today (vs daily limit of 10/user)
- Email parse success rate
- Orders detected from emails

**Detailed views:**
- **Inbound log:** received_at, from, to (@whyd.*), subject, marketplace detected, parse status
- **Send log:** sent_at, from (@whyd.*), to, subject, resend_message_id, delivery status
- **Parse results:** emails → detected orders, refunds, subscriptions, shipping updates
- **Rate limits:** per-user daily/monthly send counts
- **Webhook health:** last webhook received, failures, signature verification errors

**Actions:**
- 📨 "Replay Email" — re-process a failed email through the parser
- ⚙️ "Edit Parse Rules" — marketplace sender patterns, regex rules
- 🔑 "Rotate Encryption Key" — generate new EMAIL_ENCRYPTION_KEY (careful!)

---

### 8. 🔔 NOTIFICATION CONSOLE — "Are notifications reaching users?"

**What you see at a glance:**
- Notifications sent today (in-app + email)
- Notification delivery rate (email sent successfully / total email queued)
- Most common notification types
- Unread notification backlog

**Detailed views:**
- **Notification log:** type, user, title, sent_at, is_read, email_sent, email_sent_at
- **Failed emails:** notifications where email_sent=False, error details
- **Type breakdown:** price_drop, return_window, review_upvote, etc. — volume per type
- **User engagement:** read rates per notification type

**Actions:**
- 📢 "Broadcast Notification" — send to all users (system announcements)
- 🔄 "Retry Failed Emails" — re-queue failed notification emails
- ⚙️ "Default Preferences" — set default in_app/email toggles for new users

---

### 9. 🔍 SEARCH & DISCOVERY CONSOLE — "Is search working?"

**What you see at a glance:**
- Meilisearch index health (document count, index size, last update)
- Top search queries today (what are users searching for?)
- Zero-result queries (what are users NOT finding?)
- Search latency (avg response time)

**Detailed views:**
- **Search log:** query, results_count, user, timestamp, filters applied
- **Zero-result queries:** sorted by frequency — these are product gaps or missing data
- **Index stats:** documents indexed, filterable/sortable attributes, index size
- **Popular searches:** trending queries, rising queries

**Actions:**
- 🔄 "Full Reindex" → triggers `full_reindex.delay()`
- 🔄 "Selective Sync" → sync specific product IDs
- ⚙️ "Edit Search Settings" — searchable attributes, ranking rules, stop words

---

### 10. ⚙️ SYSTEM HEALTH CONSOLE — "Is the platform stable?"

**What you see at a glance:**
- Service status: Django ✅, Celery Worker ✅, Celery Beat ✅, Postgres ✅, Redis ✅, Meilisearch ✅
- Celery queue depths (how many tasks waiting per queue)
- Database size (total, per schema, per table)
- Redis memory usage
- Error rate (500s in last hour)

**Detailed views:**
- **Celery task monitor:** active/reserved/scheduled tasks per queue
- **Failed tasks:** last 50 Celery task failures with tracebacks
- **Database stats:** row counts per table, table sizes, index sizes
- **TimescaleDB stats:** chunk info, compression ratio, retention policy
- **API response times:** p50, p95, p99 per endpoint (from logs/Sentry)

**Actions:**
- 🔄 "Restart Celery Worker" (if possible via supervisor/systemd)
- 🗑️ "Purge Failed Tasks" — clear dead letter queue
- 📊 "Database Vacuum" — trigger VACUUM ANALYZE
- ⚙️ "SiteConfig" — edit runtime config (send limits, scrape intervals, score thresholds)
- 📋 "Audit Log" — immutable log of all admin actions (who changed what, when)

---

## APPROACH: DJANGO ADMIN vs CUSTOM DASHBOARD

**Two options:**

### Option A: Enhanced Django Admin (Faster to Build)
- Use Django Admin's built-in infrastructure
- Add custom admin views, charts via `django-admin-charts` or inline JavaScript
- Django Admin already has: auth, permissions, CRUD, filters, search, bulk actions
- **Downside:** Limited UI customization, looks "admin-y"

### Option B: Custom React Dashboard at admin.whydud.com (Better UX)
- Separate Next.js app with full control over UI
- API endpoints serve data, React renders charts/tables
- **Downside:** 2-3x more work to build

**Recommendation: Start with Option A (Enhanced Django Admin)** — it's 80% of what you need in 20% of the time. All the models already exist and are registered. We just need better admin classes with custom views, charts, and actions.

---

## CLAUDE CODE PROMPTS — BUILD THE ADMIN

### Prompt AD-1 — Scraping Console (Enhanced Django Admin)
```
Read PROGRESS.md — admin_tools app exists with ScraperRun, AuditLog, ModerationQueue, SiteConfig.
Read backend/apps/scraping/models.py for ScraperJob model.

Enhance the Django Admin for scraping monitoring:

1. In backend/apps/scraping/admin.py, create a rich ScraperJobAdmin:
   - list_display: marketplace_slug, spider_name, status_badge, items_scraped, items_created, items_updated, error_count, duration_display, started_at
   - status_badge: method that returns colored HTML:
     ✅ completed (green), ❌ failed (red), 🔄 running (blue), ⏳ queued (grey)
   - duration_display: human-readable "3m 42s" or "1h 15m"
   - error_count: count from errors JSONB field
   - list_filter: status, marketplace_slug, started_at (date hierarchy)
   - search_fields: marketplace_slug, spider_name
   - readonly_fields: everything (jobs shouldn't be manually edited)
   - ordering: -started_at

2. Add custom admin actions:
   - "Run Amazon Spider Now": calls run_marketplace_spider.delay('amazon_in')
   - "Run Flipkart Spider Now": calls run_marketplace_spider.delay('flipkart')
   - Both should show success message with task ID

3. Add a custom admin view for the scraping dashboard:
   Create a custom changelist view that adds stats at the top:
   - In get_changelist method or via extra_context in changelist_view:
     - last_successful_scrape per marketplace
     - total_items_scraped_today
     - success_rate_7d (successful / total jobs last 7 days)
     - jobs_running_now count

4. Add inline "Scrape Single URL" form:
   - Text input for URL
   - Dropdown for marketplace (auto-detect from URL domain)
   - Submit button → calls scrape_product_adhoc.delay(url, marketplace)

Use format_html() for all HTML rendering. No external JS libraries needed.
```

### Prompt AD-2 — Product Data Quality Admin
```
Enhance backend/apps/products/admin.py:

1. ProductAdmin enhancements:
   - list_display: title (truncated 60 chars), brand, category, current_best_price_display, listing_count, dud_score_display, has_images_icon, status, updated_at
   - current_best_price_display: format as "₹XX,XXX" with Indian numbering
   - dud_score_display: colored badge (red <40, yellow 40-70, green >70)
   - has_images_icon: ✅ if images array is non-empty, ❌ if empty
   - listing_count: annotated count of related ProductListings
   - list_filter: status, category, brand, has images (custom filter), has DudScore (custom filter)
   - search_fields: title, slug, brand__name
   - Custom filters:
     - "Has Images": filter products with/without images
     - "Has DudScore": filter scored/unscored products
     - "Listing Count": 0 listings, 1 listing, 2+ listings (multi-marketplace)
     - "Price Range": <₹5K, ₹5K-₹20K, ₹20K-₹50K, >₹50K

2. ProductListingAdmin enhancements:
   - list_display: product_title, marketplace, current_price_display, mrp_display, discount_pct, in_stock_icon, seller, match_confidence, match_method, updated_at
   - Inline on ProductAdmin: show all listings for a product as a table

3. Custom admin action: "Merge Selected Products"
   - Select 2+ products → merges all into the first one
   - Moves all listings from product B/C/D → product A
   - Recalculates aggregates on product A
   - Creates AuditLog entry

4. Add data quality summary at top of Product changelist:
   - Total products, active products
   - Missing images count, missing brand count, missing category count
   - Unscored products count
   - Products with 0 listings

Don't touch models — only admin.py changes.
```

### Prompt AD-3 — Review Moderation Admin
```
Enhance backend/apps/reviews/admin.py:

1. ReviewAdmin:
   - list_display: product_title, author_name, rating_stars, credibility_badge, source, is_published, is_flagged, fraud_flags_summary, created_at
   - rating_stars: render as "⭐⭐⭐⭐☆" (filled/empty stars)
   - credibility_badge: colored (🟢>0.7, 🟡0.3-0.7, 🔴<0.3)
   - fraud_flags_summary: comma-joined flag names or "—" if clean
   - list_filter: is_published, is_flagged, source, rating, credibility_score ranges
   - search_fields: body_positive, body_negative, product__title, user__email
   - Custom filters:
     - "Pending Publication": is_published=False AND publish_at > now
     - "Ready to Publish": is_published=False AND publish_at <= now
     - "Flagged": is_flagged=True

2. Custom admin actions:
   - "Approve & Publish Now": set is_published=True, publish_at=now() for selected reviews
   - "Reject & Delete": delete selected reviews, create AuditLog entries
   - "Re-run Fraud Detection": call detect_fake_reviews(product_id) for each product in selection
   - "Suspend Reviewer": set user.is_active=False, hide all their reviews

3. ReviewerProfileAdmin:
   - list_display: user_email, reviewer_level_badge, total_reviews, total_upvotes_received, review_quality_avg, leaderboard_rank, is_top_reviewer
   - reviewer_level_badge: colored (🥉 bronze, 🥈 silver, 🥇 gold, 💎 platinum)
   - ordering: leaderboard_rank

4. Add moderation dashboard stats at top:
   - Pending reviews (awaiting 48h hold)
   - Flagged reviews needing attention
   - Reviews published today/this week
   - Average credibility score
```

### Prompt AD-4 — DudScore Admin
```
Enhance backend/apps/scoring/admin.py:

1. DudScoreConfigAdmin:
   - list_display: version, is_active, w_sentiment, w_rating_quality, w_price_value, w_review_credibility, w_price_stability, w_return_signal, anomaly_spike_threshold, updated_at
   - Only one config should be is_active=True at a time
   - On save: create AuditLog entry with old/new weights

2. DudScoreHistoryAdmin:
   - list_display: product_title, score_display, confidence, version, component_summary, time
   - score_display: colored badge
   - component_summary: mini bar chart as HTML (6 tiny colored bars showing relative scores)
   - list_filter: version, time (date hierarchy)
   - search_fields: product__title
   - readonly_fields: everything (history is immutable)
   - ordering: -time

3. Custom admin actions on ProductAdmin:
   - "Recalculate DudScore": calls compute_dudscore.delay(product_id) for selected
   - "Full Recalculation (All Products)": calls full_dudscore_recalculation.delay()

4. Add to Product detail page in admin:
   - Inline showing last 10 DudScoreHistory entries for this product
   - Shows component_scores JSONB formatted as a readable table
```

### Prompt AD-5 — Click Tracking & Affiliate Admin
```
Enhance backend/apps/pricing/admin.py:

1. ClickEventAdmin:
   - list_display: product_title, marketplace_name, source_page, device_type, price_at_click_display, affiliate_tag, clicked_at
   - list_filter: marketplace__name, source_page, device_type, clicked_at (date hierarchy)
   - search_fields: product__title, affiliate_url
   - readonly_fields: everything
   - ordering: -clicked_at

2. Add stats at top of ClickEvent changelist:
   - Total clicks today / this week / this month
   - Clicks by marketplace (counts)
   - Top 5 clicked products today
   - Click source breakdown (product_page vs comparison vs deal vs search)

3. MarketplaceAdmin enhancements:
   - list_display: name, slug, base_url, affiliate_tag, affiliate_param, is_active, listing_count
   - Editable: affiliate_tag, affiliate_param, is_active (inline editing)

4. PriceAlertAdmin:
   - list_display: user_email, product_title, target_price_display, current_price_display, marketplace, is_active, is_triggered, triggered_at
   - list_filter: is_active, is_triggered, marketplace
```

### Prompt AD-6 — User & Notification Admin
```
Enhance backend/apps/accounts/admin.py:

1. Custom UserAdmin (extend Django's UserAdmin):
   - list_display: email, name, is_active, date_joined, last_login, review_count, has_whydud_email, subscription_tier
   - review_count: annotated count
   - has_whydud_email: ✅/❌ icon
   - list_filter: is_active, is_staff, date_joined, subscription_tier
   - search_fields: email, name
   - Inlines: WhydudEmailInline, NotificationPreferenceInline

2. NotificationAdmin:
   - list_display: user_email, type, title_truncated, is_read, email_sent, created_at
   - list_filter: type, is_read, email_sent, created_at (date hierarchy)
   - readonly_fields: everything except is_read

3. Custom admin action: "Send Broadcast Notification"
   - Opens form: type, title, body, action_url
   - Creates Notification for ALL active users
   - Queues emails for users with email preference enabled

4. Add user stats at top of User changelist:
   - Total users, new today, new this week
   - Active last 7 days
   - With @whyd.* email
   - OAuth vs password signup ratio
```

### Prompt AD-7 — System Health Admin View
```
Create a custom admin view at /admin/system-health/:

In backend/apps/admin_tools/admin.py, add a custom admin view:

from django.contrib.admin import AdminSite
from django.urls import path

class WhydudAdminSite(AdminSite):
    site_header = "WHYDUD Admin"
    site_title = "WHYDUD"
    index_title = "Platform Management"

Add a custom view accessible from admin sidebar:

def system_health_view(request):
    """Dashboard showing platform health metrics."""
    
    context = {
        # Database stats
        'product_count': Product.objects.count(),
        'listing_count': ProductListing.objects.count(),
        'snapshot_count': PriceSnapshot.objects.count(),
        'user_count': User.objects.count(),
        'review_count': Review.objects.count(),
        
        # Scraper health
        'last_amazon_scrape': ScraperJob.objects.filter(marketplace_slug='amazon_in', status='completed').order_by('-completed_at').first(),
        'last_flipkart_scrape': ScraperJob.objects.filter(marketplace_slug='flipkart', status='completed').order_by('-completed_at').first(),
        'scrape_success_rate_7d': calculate_success_rate(days=7),
        'jobs_running': ScraperJob.objects.filter(status='running').count(),
        
        # Queue depths (from Redis)
        'celery_queues': get_celery_queue_depths(),
        
        # Content health
        'reviews_pending': Review.objects.filter(is_published=False, publish_at__lte=now()).count(),
        'reviews_flagged': Review.objects.filter(is_flagged=True).count(),
        'products_unscored': Product.objects.filter(dud_score__isnull=True, status='active').count(),
        'products_no_images': Product.objects.filter(images=[], status='active').count(),
        
        # Today's activity
        'clicks_today': ClickEvent.objects.filter(clicked_at__date=today()).count(),
        'alerts_triggered_today': PriceAlert.objects.filter(triggered_at__date=today()).count(),
        'notifications_sent_today': Notification.objects.filter(created_at__date=today()).count(),
        
        # Meilisearch
        'meilisearch_status': check_meilisearch_health(),
    }
    
    return render(request, 'admin/system_health.html', context)

Create template: backend/templates/admin/system_health.html
- Extends admin/base_site.html
- Cards layout with all the stats
- Color-coded: green (healthy), yellow (warning), red (critical)
- Auto-refresh every 60 seconds

Register the URL:
    path('system-health/', admin.site.admin_view(system_health_view), name='system-health')

Add link to admin index page (or sidebar).
```

### Prompt AD-8 — Audit Log Integration
```
Make ALL admin actions create AuditLog entries automatically.

Create backend/apps/admin_tools/mixins.py:

class AuditLogMixin:
    """Mixin for ModelAdmin that auto-logs all create/update/delete actions."""
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        AuditLog.objects.create(
            admin_user=request.user,
            action='update' if change else 'create',
            target_type=obj.__class__.__name__,
            target_id=str(obj.pk),
            old_value=form.initial if change else {},
            new_value=form.cleaned_data,
            ip_address=get_client_ip(request)
        )
    
    def delete_model(self, request, obj):
        AuditLog.objects.create(
            admin_user=request.user,
            action='delete',
            target_type=obj.__class__.__name__,
            target_id=str(obj.pk),
            old_value=model_to_dict(obj),
            ip_address=get_client_ip(request)
        )
        super().delete_model(request, obj)

Apply AuditLogMixin to ALL admin classes:
- ProductAdmin, ReviewAdmin, UserAdmin, DudScoreConfigAdmin, MarketplaceAdmin, etc.

This creates an immutable audit trail of every admin action — who changed what, when, from what IP.

Don't touch the AuditLog model — it's already built and read-only in admin.
```

---

## MONITORING WITHOUT ADMIN (Terminal Commands)

While the admin is being built, here are quick terminal commands for monitoring:

### Daily Health Check Script
```
Create backend/management/commands/health_check.py:

Outputs a full platform health report:

  python manage.py health_check

Output:
  ╔══════════════════════════════════════════════╗
  ║           WHYDUD HEALTH CHECK                ║
  ║           2026-02-26 14:30 IST               ║
  ╠══════════════════════════════════════════════╣
  ║ SCRAPERS                                     ║
  ║   Amazon.in:  last run 2h ago ✅              ║
  ║   Flipkart:   last run 5h ago ✅              ║
  ║   Jobs today:  4 ✅ / 0 ❌                    ║
  ╠══════════════════════════════════════════════╣
  ║ DATA                                         ║
  ║   Products:    1,247 (↑23 today)             ║
  ║   Listings:    2,891                         ║
  ║   Snapshots:   12,450 (↑2,340 today)         ║
  ║   Brands:      187                           ║
  ║   Missing images: 12 ⚠️                      ║
  ║   Unscored: 45 ⚠️                            ║
  ╠══════════════════════════════════════════════╣
  ║ USERS                                        ║
  ║   Total: 342 | New today: 5                  ║
  ║   Active (7d): 89                            ║
  ╠══════════════════════════════════════════════╣
  ║ ENGAGEMENT                                   ║
  ║   Clicks today: 234                          ║
  ║   Alerts triggered: 3                        ║
  ║   Reviews pending: 7                         ║
  ║   Reviews flagged: 2 ⚠️                      ║
  ╠══════════════════════════════════════════════╣
  ║ SEARCH                                       ║
  ║   Meilisearch: ✅ 1,247 docs indexed         ║
  ║   Last reindex: 8h ago                       ║
  ╠══════════════════════════════════════════════╣
  ║ CELERY                                       ║
  ║   default: 0 queued | scraping: 0 queued     ║
  ║   email: 0 queued | scoring: 0 queued        ║
  ║   alerts: 0 queued                           ║
  ╚══════════════════════════════════════════════╝
```

---

## OPTIONAL: FLOWER (Celery Monitoring UI)

Flower is a ready-made web UI for monitoring Celery tasks. Zero code needed.

```powershell
# Install
pip install flower

# Run (in its own terminal)
celery -A whydud flower --port=5555

# Open http://localhost:5555
```

Flower gives you:
- Real-time task monitor (active, completed, failed)
- Worker status (online, heartbeat, resource usage)
- Task details (args, kwargs, traceback on failure)
- Queue depths
- Rate limiting controls
- Task revocation (cancel running tasks)

**This is the fastest way to monitor Celery tasks and scraping jobs.**

---

## SUMMARY — WHAT TO BUILD

```
Prompt AD-1: Scraping Console (ScraperJobAdmin + run buttons)      — ~200 lines
Prompt AD-2: Data Quality (ProductAdmin + merge + filters)          — ~250 lines
Prompt AD-3: Review Moderation (ReviewAdmin + fraud badges)         — ~200 lines
Prompt AD-4: DudScore Admin (config + history + recalc buttons)     — ~150 lines
Prompt AD-5: Clicks & Affiliate (ClickEventAdmin + stats)           — ~150 lines
Prompt AD-6: Users & Notifications (UserAdmin + broadcast)          — ~200 lines
Prompt AD-7: System Health Dashboard (custom admin view + template) — ~300 lines
Prompt AD-8: Audit Log Integration (mixin for all admins)           — ~100 lines

TOTAL: 8 prompts, ~1,550 lines of admin code
TIMELINE: 2 Claude Code sessions (4 prompts each)

QUICK WIN: Install Flower right now for instant Celery monitoring:
  pip install flower
  celery -A whydud flower --port=5555
```
