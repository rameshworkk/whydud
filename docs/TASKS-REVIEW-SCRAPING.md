# WHYDUD — Review Scraping System

> **Problem:** Scraped products have 0 reviews. Platform looks empty and untrustworthy.
> **Solution:** Scrape marketplace reviews alongside products — usernames, ratings, text,
> dates, photos, verified purchase status, helpful vote counts.
>
> **Approach:** Extend existing Amazon + Flipkart spiders to also scrape review pages.
> Store as `source="amazon_in"` or `source="flipkart"` reviews (not user-submitted).
> These are clearly attributed: "Review from Amazon.in" badge in the UI.

---

## DATA MODEL — What We Scrape Per Review

```
From Amazon.in review page:
  - reviewer_name         "Rahul S."
  - reviewer_external_id  "A2B3C4D5E6" (Amazon profile ID)
  - rating                4 (1-5 stars)
  - title                 "Great phone, average camera"
  - body                  "Been using this for 3 months now..."
  - date                  "2026-01-15"
  - is_verified_purchase  True/False ("Verified Purchase" badge)
  - helpful_votes         234 ("234 people found this helpful")
  - images                ["https://images-na.ssl-images-amazon.com/...jpg", ...]
  - country               "India"
  - variant               "Color: Blue, Size: 128GB"
  - review_url            "https://www.amazon.in/gp/customer-reviews/R1ABC..."

From Flipkart review page:
  - reviewer_name         "Flipkart Customer" or actual name
  - reviewer_external_id  None (Flipkart doesn't expose profile IDs)
  - rating                4 (1-5 stars)
  - title                 "Value for money"
  - body                  "Good product for the price..."
  - date                  "2026-01-15"
  - is_verified_purchase  True (Flipkart only shows "Certified Buyer")
  - helpful_votes         89 ("89 found helpful")
  - images                ["https://rukminim2.flixcart.com/...jpg", ...]
  - country               None
  - variant               "Color: Black, Storage: 256 GB"
  - review_url            None (Flipkart doesn't have standalone review URLs)
```

## HOW IT MAPS TO YOUR EXISTING REVIEW MODEL

The Review model already has these fields (from PROGRESS.md):

```python
class Review:
    # Existing fields that we'll populate:
    product           FK → Product (canonical)
    user              FK → User (NULL for scraped reviews — no Whydud account)
    rating            int (1-5)
    title             str
    body_positive     text  # "What did you like?" — we put full review text here
    body_negative     text  # Leave empty for scraped reviews
    source            str   # "amazon_in" / "flipkart" / "whydud" (for user-submitted)
    is_verified_purchase  bool
    is_published      bool  # True immediately for scraped reviews
    publish_at        datetime
    sentiment_score   float  # Calculated by DudScore pipeline
    credibility_score float  # Calculated by fraud detection
    content_hash      str    # SHA-256 for copy-paste detection
    fraud_flags       JSONB  # Populated by fraud detection
    is_flagged        bool
    images            JSONB  # Array of image URLs
    created_at        datetime  # Use the review's actual date from marketplace

    # NEW fields needed for scraped reviews:
    external_reviewer_name   str     # "Rahul S." — display name from marketplace
    external_reviewer_id     str     # Amazon profile ID (nullable)
    external_review_id       str     # Amazon review ID like "R1ABC..." or Flipkart equivalent
    external_review_url      str     # Direct link to review on marketplace (nullable)
    helpful_vote_count       int     # "234 people found this helpful"
    marketplace              FK → Marketplace  # Which marketplace this review came from
    variant_info             str     # "Color: Blue, Size: 128GB"
```

---

## ARCHITECTURE DECISION

**Scraped reviews are NOT linked to a User account.**
- `user = NULL` for all scraped reviews
- `source = "amazon_in"` or `source = "flipkart"` identifies them
- `external_reviewer_name` is what we display instead of a User profile
- They show a badge: "Review from Amazon.in" or "Review from Flipkart"
- They count toward DudScore calculation (sentiment, rating quality, credibility)
- They go through fraud detection (copy-paste, suspiciously short, etc.)
- They do NOT count toward Whydud reviewer profiles/leaderboard

**This is standard practice** — sites like PriceRunner, Trustpilot aggregators, and Google Shopping all aggregate marketplace reviews with source attribution.

---

## CLAUDE CODE PROMPTS

### Prompt RV-1 — Add Review Fields + Migration
```
Read backend/apps/reviews/models.py.

Add these new fields to the Review model for scraped marketplace reviews:

  external_reviewer_name = models.CharField(max_length=200, blank=True, default="")
  # Display name from marketplace ("Rahul S.", "Flipkart Customer")

  external_reviewer_id = models.CharField(max_length=100, blank=True, default="")
  # Marketplace profile ID (Amazon: "A2B3C4D5E6", Flipkart: empty)

  external_review_id = models.CharField(max_length=200, blank=True, default="", db_index=True)
  # Unique review ID from marketplace (Amazon: "R1ABCDEF", Flipkart: generated from content hash)
  # Used for deduplication — don't re-import reviews we already have

  external_review_url = models.URLField(max_length=500, blank=True, default="")
  # Direct link to review on marketplace (for "Read on Amazon" link)

  helpful_vote_count = models.PositiveIntegerField(default=0)
  # "234 people found this helpful"

  marketplace = models.ForeignKey(
      "products.Marketplace", null=True, blank=True,
      on_delete=models.SET_NULL, related_name="reviews"
  )
  # Which marketplace this review was scraped from

  variant_info = models.CharField(max_length=300, blank=True, default="")
  # "Color: Blue, Size: 128GB" — product variant the review is for

Make sure user field is nullable: user = models.ForeignKey(..., null=True, blank=True, ...)
If user is already nullable, don't change it. If not, make it nullable.

Add a unique constraint: (external_review_id, marketplace) — prevents duplicate imports.
  class Meta:
      constraints = [
          models.UniqueConstraint(
              fields=["external_review_id", "marketplace"],
              condition=models.Q(external_review_id__gt=""),
              name="unique_external_review_per_marketplace"
          )
      ]

Create and run the migration:
  python manage.py makemigrations reviews
  python manage.py migrate reviews

Don't change any existing fields or break existing functionality.
```

### Prompt RV-2 — Review Scrapy Item + Shared Pipeline
```
Read backend/apps/scraping/items.py (has ProductItem).

Add a new ReviewItem to items.py:

  class ReviewItem(scrapy.Item):
      # Required
      marketplace_slug = scrapy.Field()     # "amazon_in" / "flipkart"
      product_external_id = scrapy.Field()  # ASIN or FPID — links to ProductListing
      rating = scrapy.Field()               # int 1-5
      body = scrapy.Field()                 # Full review text

      # Optional
      title = scrapy.Field()                # Review title/headline
      reviewer_name = scrapy.Field()        # Display name
      reviewer_id = scrapy.Field()          # Platform profile ID
      review_id = scrapy.Field()            # Platform review ID (for dedup)
      review_url = scrapy.Field()           # Direct URL to review
      review_date = scrapy.Field()          # Date string (spider normalizes to YYYY-MM-DD)
      is_verified_purchase = scrapy.Field() # bool
      helpful_votes = scrapy.Field()        # int
      images = scrapy.Field()               # list of image URLs
      variant = scrapy.Field()              # "Color: Blue, 128GB"
      country = scrapy.Field()              # "India"

Now add a ReviewPipeline to backend/apps/scraping/pipelines.py:

  class ReviewValidationPipeline:
      """Validates ReviewItems — drops if missing required fields."""
      def process_item(self, item, spider):
          if not isinstance(item, ReviewItem):
              return item  # Pass through ProductItems
          if not item.get("marketplace_slug") or not item.get("product_external_id"):
              raise DropItem("Missing marketplace or product ID")
          if not item.get("rating") or not item.get("body"):
              raise DropItem("Missing rating or body")
          if len(item.get("body", "")) < 5:
              raise DropItem("Review body too short")
          return item

  class ReviewPersistencePipeline:
      """Persists ReviewItems to the Review model."""
      def process_item(self, item, spider):
          if not isinstance(item, ReviewItem):
              return item

          # Find the ProductListing → get canonical Product
          listing = ProductListing.objects.filter(
              marketplace__slug=item["marketplace_slug"],
              external_id=item["product_external_id"]
          ).select_related("product", "marketplace").first()

          if not listing:
              raise DropItem(f"No listing for {item['marketplace_slug']}:{item['product_external_id']}")

          # Generate external_review_id if not provided
          review_id = item.get("review_id", "")
          if not review_id:
              # Hash from marketplace + product + reviewer + date for dedup
              hash_input = f"{item['marketplace_slug']}:{item['product_external_id']}:{item.get('reviewer_name','')}:{item.get('review_date','')}:{item['body'][:100]}"
              review_id = hashlib.sha256(hash_input.encode()).hexdigest()[:32]

          # Dedup check
          if Review.objects.filter(
              external_review_id=review_id,
              marketplace=listing.marketplace
          ).exists():
              raise DropItem(f"Duplicate review: {review_id}")

          # Parse date
          review_date = None
          if item.get("review_date"):
              try:
                  review_date = dateutil.parser.parse(item["review_date"])
              except (ValueError, TypeError):
                  review_date = timezone.now()
          else:
              review_date = timezone.now()

          # Content hash for fraud detection
          content_hash = hashlib.sha256(item["body"].encode()).hexdigest()

          # Create review
          review = Review.objects.create(
              product=listing.product,
              user=None,  # Scraped, not user-submitted
              rating=int(item["rating"]),
              title=item.get("title", "")[:500],
              body_positive=item["body"],
              body_negative="",
              source=item["marketplace_slug"],
              is_verified_purchase=bool(item.get("is_verified_purchase", False)),
              is_published=True,
              publish_at=review_date,
              content_hash=content_hash,
              images=item.get("images", []),
              external_reviewer_name=item.get("reviewer_name", "")[:200],
              external_reviewer_id=item.get("reviewer_id", "")[:100],
              external_review_id=review_id,
              external_review_url=item.get("review_url", "")[:500],
              helpful_vote_count=int(item.get("helpful_votes", 0)),
              marketplace=listing.marketplace,
              variant_info=item.get("variant", "")[:300],
              created_at=review_date,  # Use actual review date
          )

          spider.reviews_saved = getattr(spider, "reviews_saved", 0) + 1
          return item

Register both pipelines in scrapy_settings.py after the product pipelines:
  "apps.scraping.pipelines.ReviewValidationPipeline": 150,
  "apps.scraping.pipelines.ReviewPersistencePipeline": 450,

Pipeline order:
  100: ValidationPipeline (products)
  150: ReviewValidationPipeline (reviews)
  200: NormalizationPipeline (products)
  400: ProductPipeline (products)
  450: ReviewPersistencePipeline (reviews)
  500: MeilisearchIndexPipeline (products)
```

### Prompt RV-3 — Amazon.in Review Spider
```
Read backend/apps/scraping/spiders/amazon_spider.py.
Read backend/apps/scraping/spiders/base_spider.py for the base class.

Create backend/apps/scraping/spiders/amazon_review_spider.py:

class AmazonReviewSpider(BaseWhydudSpider):
    name = "amazon_in_reviews"
    allowed_domains = ["amazon.in"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_review_pages = int(kwargs.get("max_review_pages", 3))  # 30 reviews per page × 3 = ~90 reviews per product
        self.reviews_scraped = 0

    def start_requests(self):
        """Get all Amazon ProductListings that have fewer than 10 reviews in our DB."""
        from apps.products.models import ProductListing
        from apps.reviews.models import Review
        from django.db.models import Count, Q

        listings = ProductListing.objects.filter(
            marketplace__slug="amazon_in",
            in_stock=True
        ).annotate(
            review_count=Count("product__reviews", filter=Q(product__reviews__source="amazon_in"))
        ).filter(
            review_count__lt=10  # Only scrape if we have < 10 Amazon reviews
        ).order_by("-product__total_reviews")[:200]  # Prioritize products with most reviews on Amazon

        for listing in listings:
            asin = listing.external_id
            url = f"https://www.amazon.in/product-reviews/{asin}/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews&sortBy=helpful&pageNumber=1"
            yield scrapy.Request(
                url,
                callback=self.parse_review_page,
                meta={"asin": asin, "page": 1},
                headers=self._make_headers()
            )

    def parse_review_page(self, response):
        """Parse an Amazon.in review listing page."""
        asin = response.meta["asin"]
        page = response.meta["page"]

        reviews = response.css('div[data-hook="review"]')
        if not reviews:
            # Try alternative selector
            reviews = response.css("div.review")

        for review_el in reviews:
            item = ReviewItem()
            item["marketplace_slug"] = "amazon_in"
            item["product_external_id"] = asin

            # Review ID
            review_id = review_el.attrib.get("id", "")
            item["review_id"] = review_id

            # Rating (1-5)
            rating_text = review_el.css('i[data-hook="review-star-rating"] span.a-icon-alt::text').get("")
            # Format: "4.0 out of 5 stars"
            if not rating_text:
                rating_text = review_el.css("i.review-rating span.a-icon-alt::text").get("")
            try:
                item["rating"] = int(float(rating_text.split(" ")[0]))
            except (ValueError, IndexError):
                item["rating"] = None  # Will be dropped by validation

            # Title
            item["title"] = review_el.css('a[data-hook="review-title"] span:not(.a-icon-alt)::text').get("").strip()
            if not item["title"]:
                item["title"] = review_el.css("a[data-hook='review-title']::text").get("").strip()

            # Body
            body_el = review_el.css('span[data-hook="review-body"] span::text').getall()
            item["body"] = " ".join(t.strip() for t in body_el if t.strip())
            if not item["body"]:
                item["body"] = review_el.css("span[data-hook='review-body']::text").get("").strip()

            # Reviewer name
            item["reviewer_name"] = review_el.css("span.a-profile-name::text").get("").strip()

            # Reviewer ID (from profile link)
            profile_link = review_el.css("a.a-profile::attr(href)").get("")
            if "/profile/" in profile_link:
                item["reviewer_id"] = profile_link.split("/profile/")[-1].split("/")[0].split("?")[0]

            # Date
            # Format: "Reviewed in India on 15 January 2026"
            date_text = review_el.css('span[data-hook="review-date"]::text').get("")
            if " on " in date_text:
                date_str = date_text.split(" on ")[-1].strip()
                item["review_date"] = date_str  # Pipeline will parse
            # Country
            if "in India" in date_text:
                item["country"] = "India"

            # Verified purchase
            verified = review_el.css('span[data-hook="avp-badge"]::text').get("")
            item["is_verified_purchase"] = "Verified Purchase" in verified

            # Helpful votes
            helpful_text = review_el.css('span[data-hook="helpful-vote-statement"]::text').get("")
            # "234 people found this helpful" or "One person found this helpful"
            if helpful_text:
                helpful_text = helpful_text.strip().lower()
                if helpful_text.startswith("one"):
                    item["helpful_votes"] = 1
                else:
                    try:
                        item["helpful_votes"] = int(helpful_text.split(" ")[0].replace(",", ""))
                    except ValueError:
                        item["helpful_votes"] = 0
            else:
                item["helpful_votes"] = 0

            # Images
            images = review_el.css('img[data-hook="review-image-tile"]::attr(src)').getall()
            # Upgrade thumbnail to full size
            item["images"] = [img.replace("_SY88", "_SL1500").replace("_CR0,0,88,88", "") for img in images]

            # Variant
            variant_text = review_el.css("a.a-size-mini.a-link-normal.a-color-secondary::text").get("")
            if not variant_text:
                variant_text = review_el.css('div[data-hook="format-strip"]::text').get("")
            item["variant"] = variant_text.strip()

            # Review URL
            review_link = review_el.css('a[data-hook="review-title"]::attr(href)').get("")
            if review_link:
                item["review_url"] = response.urljoin(review_link)

            yield item
            self.reviews_scraped += 1

        # Pagination — follow next page
        if page < self.max_review_pages and len(reviews) >= 8:  # Amazon shows 10/page, 8+ means probably more
            next_page = page + 1
            next_url = f"https://www.amazon.in/product-reviews/{asin}/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews&sortBy=helpful&pageNumber={next_page}"
            yield scrapy.Request(
                next_url,
                callback=self.parse_review_page,
                meta={"asin": asin, "page": next_page},
                headers=self._make_headers()
            )

    def closed(self, reason):
        self.logger.info(f"Amazon review spider finished. Reviews scraped: {self.reviews_scraped}")

Register in ScrapingConfig.spider_map (common/app_settings.py):
  "amazon_in_reviews": "amazon_in_reviews"

Add to scraping runner so it can be invoked:
  python -m apps.scraping.runner amazon_in_reviews --max-review-pages 3
```

### Prompt RV-4 — Flipkart Review Spider
```
Read backend/apps/scraping/spiders/flipkart_spider.py for Flipkart patterns.

Create backend/apps/scraping/spiders/flipkart_review_spider.py:

class FlipkartReviewSpider(BaseWhydudSpider):
    name = "flipkart_reviews"
    allowed_domains = ["flipkart.com"]

    Flipkart reviews are on the product page itself but paginated via API.
    Two approaches:

    APPROACH A — Scrape review pages directly:
    Review URL pattern: https://www.flipkart.com/product-name/product-reviews/{fpid}?page=1&sortOrder=MOST_HELPFUL

    APPROACH B — Use Flipkart's internal review API (more reliable):
    https://www.flipkart.com/api/3/product/reviews?productId={fpid}&page=1&sortOrder=MOST_HELPFUL

    Use Approach A (HTML scraping) — more reliable, same pattern as product spider.

    def start_requests(self):
        Same pattern as Amazon: get ProductListings with slug="flipkart" and <10 reviews.
        Build review page URLs from the product listing's external_url.

    def parse_review_page(self, response):
        Flipkart review selectors:

        Review container: div.col._2wzgFH (or div[class*="review-container"])

        Each review:
        - Rating: div._3LWZlK or div.XQDdHH (just the number text)
        - Title: p._2-N8zT or p[class*="review-title"] (bold text above review body)
        - Body: div.t-ZTKy div or div[class*="review-body"]
        - Reviewer name: p._2sc7ZR or p[class*="reviewer-name"]
        - Date: p._2mcZGo or p[class*="review-date"] (format: "Jan, 2026" or "15 Jan, 2026")
        - Verified: "Certified Buyer" text near reviewer name
        - Helpful: span._1_BQL8 or similar (format: "89" next to thumbs up icon)
        - Images: div._1HxXwr img::attr(src) (review images)
        - Variant: multiple small grey text spans below reviewer name

        IMPORTANT: Flipkart class names change frequently (obfuscated).
        Use multiple fallback selectors per field, similar to product spider.
        Also try these patterns:
        - Review blocks: div[class*="review"], div[class*="_1AtV"], div.row
        - Rating number: within first div of review block
        - Read More: some reviews truncated, full text may need Playwright click

    Pagination: look for "NEXT" link or page=N+1 pattern in pagination section.

    Register in spider_map: "flipkart_reviews": "flipkart_reviews"
```

### Prompt RV-5 — Integrate Review Scraping into Main Pipeline
```
Read backend/apps/scraping/tasks.py.

Goal: After every product scrape completes, automatically scrape reviews too.

Option A — Chain task (recommended):
In run_marketplace_spider task, after successful product spider completion,
automatically trigger the review spider:

  # In run_marketplace_spider, after spider success:
  if marketplace_slug == "amazon_in":
      from apps.scraping.tasks import run_review_spider
      run_review_spider.delay("amazon_in", max_review_pages=3)
  elif marketplace_slug == "flipkart":
      run_review_spider.delay("flipkart", max_review_pages=3)

Add new Celery task:

  @shared_task(queue="scraping", bind=True, max_retries=1)
  def run_review_spider(self, marketplace_slug, max_review_pages=3):
      """Scrape reviews from marketplace for products that need them."""
      spider_map = {
          "amazon_in": "amazon_in_reviews",
          "flipkart": "flipkart_reviews",
      }
      spider_name = spider_map.get(marketplace_slug)
      if not spider_name:
          return {"error": f"No review spider for {marketplace_slug}"}

      # Run via subprocess (same pattern as product spider)
      cmd = [
          sys.executable, "-m", "apps.scraping.runner",
          spider_name,
          "--max-review-pages", str(max_review_pages)
      ]
      # ... subprocess execution (copy pattern from run_spider)

      # After completion, trigger DudScore recalc for products that got new reviews
      # And run fraud detection on new reviews

Option B — Celery Beat schedule (independent):
Add to celery.py beat_schedule:

  "scrape-amazon-reviews-daily": {
      "task": "apps.scraping.tasks.run_review_spider",
      "schedule": crontab(minute=0, hour=4),  # 04:00 UTC, after product scrapes finish
      "args": ["amazon_in"],
      "kwargs": {"max_review_pages": 3},
      "options": {"queue": "scraping"}
  },
  "scrape-flipkart-reviews-daily": {
      "task": "apps.scraping.tasks.run_review_spider",
      "schedule": crontab(minute=0, hour=7),  # 07:00 UTC
      "args": ["flipkart"],
      "kwargs": {"max_review_pages": 3},
      "options": {"queue": "scraping"}
  },

Implement BOTH — chain after product scrape + independent daily schedule.
The review spider already handles dedup (skips existing external_review_id), so double-running is safe.
```

### Prompt RV-6 — Post-Scrape Intelligence: Fraud Detection + DudScore on New Reviews
```
After review scraping completes, we need to:
1. Run fraud detection on products that got new reviews
2. Recalculate DudScore for those products
3. Update product review counts

Add to run_review_spider task, after spider completes:

  # Get products that got new reviews in this run
  from apps.reviews.models import Review
  from datetime import timedelta

  recent_reviews = Review.objects.filter(
      source=marketplace_slug,
      created_at__gte=timezone.now() - timedelta(hours=2)  # Reviews just imported
  ).values_list("product_id", flat=True).distinct()

  product_ids = list(recent_reviews)

  # 1. Run fraud detection per product
  from apps.reviews.fraud_detection import detect_fake_reviews
  for pid in product_ids:
      try:
          detect_fake_reviews(pid)
      except Exception as e:
          logger.warning(f"Fraud detection failed for {pid}: {e}")

  # 2. Recalculate DudScore per product
  from apps.scoring.tasks import compute_dudscore
  for pid in product_ids:
      compute_dudscore.delay(str(pid))

  # 3. Update product aggregate review stats
  from apps.products.models import Product
  from django.db.models import Avg, Count
  for pid in product_ids:
      product = Product.objects.get(id=pid)
      stats = product.reviews.filter(is_published=True).aggregate(
          avg_rating=Avg("rating"),
          total_reviews=Count("id")
      )
      product.avg_rating = stats["avg_rating"] or 0
      product.total_reviews = stats["total_reviews"] or 0
      product.save(update_fields=["avg_rating", "total_reviews"])

  return {
      "marketplace": marketplace_slug,
      "products_with_new_reviews": len(product_ids),
      "fraud_detection_run": True,
      "dudscore_recalc_queued": True,
  }
```

### Prompt RV-7 — Update Review Serializer + Frontend Display
```
Update backend/apps/reviews/serializers.py:

In ReviewSerializer (or ReviewListSerializer), add the new fields:

  external_reviewer_name = serializers.CharField(read_only=True)
  helpful_vote_count = serializers.IntegerField(read_only=True)
  marketplace_name = serializers.CharField(source="marketplace.name", read_only=True, default=None)
  marketplace_slug = serializers.CharField(source="marketplace.slug", read_only=True, default=None)
  variant_info = serializers.CharField(read_only=True)
  external_review_url = serializers.URLField(read_only=True)
  is_scraped = serializers.SerializerMethodField()

  def get_is_scraped(self, obj):
      return obj.source in ("amazon_in", "flipkart") and obj.user is None

This way the frontend can distinguish:
  - is_scraped=True → show "Review from Amazon.in" badge, external_reviewer_name, external_review_url
  - is_scraped=False → show Whydud user profile, reviewer level badge

Update frontend/src/lib/api/types.ts — add to Review type:
  externalReviewerName?: string
  helpfulVoteCount: number
  marketplaceName?: string
  marketplaceSlug?: string
  variantInfo?: string
  externalReviewUrl?: string
  isScraped: boolean

Update frontend/src/components/product/review-card.tsx:
  - If review.isScraped:
    - Show marketplace badge: "Review from Amazon.in" (orange) or "Review from Flipkart" (blue)
    - Show external_reviewer_name instead of user profile
    - Show helpful_vote_count: "👍 234 found helpful"
    - Show variant_info as grey chip: "Color: Blue, 128GB"
    - Show "Read on Amazon →" link using external_review_url
    - Show review images in a small gallery
  - If NOT scraped:
    - Show Whydud user profile, reviewer level badge (existing behavior)
    - Show "Verified Whydud Review" green badge

Add sorting option to review list on product page:
  Sort by: Most Helpful (helpful_vote_count DESC) | Newest | Highest Rating | Lowest Rating

Add filter: "All Reviews" | "Amazon.in" | "Flipkart" | "Whydud"
```

### Prompt RV-8 — Test the Full Review Pipeline
```
Test the review scraping end-to-end:

Step 1 — Test single Amazon product reviews:
  cd backend
  python -m apps.scraping.runner amazon_in_reviews \
    --max-review-pages 1

Step 2 — Verify reviews in DB:
  python manage.py shell -c "
from apps.reviews.models import Review
amazon = Review.objects.filter(source='amazon_in')
print(f'Amazon reviews: {amazon.count()}')
for r in amazon.order_by('-helpful_vote_count')[:5]:
    print(f'  ⭐{r.rating} | {r.external_reviewer_name} | {r.helpful_vote_count} helpful | {r.title[:50]}')
    print(f'    {r.body_positive[:100]}...')
    print(f'    Verified: {r.is_verified_purchase} | Images: {len(r.images)}')
    print()
"

Step 3 — Test Flipkart reviews:
  python -m apps.scraping.runner flipkart_reviews \
    --max-review-pages 1

Step 4 — Check review counts per product:
  python manage.py shell -c "
from apps.products.models import Product
from django.db.models import Count
products = Product.objects.annotate(
    review_count=Count('reviews')
).filter(review_count__gt=0).order_by('-review_count')[:10]
for p in products:
    amazon_count = p.reviews.filter(source='amazon_in').count()
    flipkart_count = p.reviews.filter(source='flipkart').count()
    print(f'{p.title[:50]}: {p.review_count} total ({amazon_count} Amazon, {flipkart_count} Flipkart)')
"

Step 5 — Run fraud detection on products with new reviews:
  python manage.py shell -c "
from apps.reviews.fraud_detection import detect_fake_reviews
from apps.products.models import Product
from django.db.models import Count
for p in Product.objects.annotate(rc=Count('reviews')).filter(rc__gt=0)[:20]:
    result = detect_fake_reviews(str(p.id))
    print(f'{p.title[:40]}: {result}')
"

Step 6 — Verify frontend shows reviews:
  Open http://localhost:3000/product/[any-product-slug]
  Scroll to reviews section — should now show scraped reviews with marketplace badges.
```

---

## SCRAPING SCHEDULE (After Setup)

```
Product scrape (existing):
  Amazon:   every 6h (00, 06, 12, 18 UTC)
  Flipkart: every 6h (03, 09, 15, 21 UTC)

Review scrape (new):
  Amazon reviews:   daily at 04:00 UTC (after product scrape completes)
  Flipkart reviews: daily at 07:00 UTC (after product scrape completes)
  Also: chained after every product scrape

Post-review pipeline (automatic):
  Fraud detection → DudScore recalc → Review count update → Meilisearch sync
```

## EXPECTED RESULTS

```
Per product with Amazon reviews:
  ~30 reviews (3 pages × 10/page), sorted by most helpful
  Top reviews with 100-1000+ helpful votes
  Mix of verified and unverified purchases
  Images on ~20% of reviews

Per product with Flipkart reviews:
  ~30 reviews (3 pages × 10/page), sorted by most helpful
  Mostly "Certified Buyer" reviews
  Images on ~15% of reviews

For 500+ products:
  ~15,000-30,000 total scraped reviews
  Immediate DudScore calculation with real sentiment data
  Fraud detection identifies low-quality imported reviews
  Product pages go from empty → rich with real user feedback
```

---

## SESSION PLAN

```
Session 1: RV-1 (migration), RV-2 (items + pipeline), RV-3 (Amazon spider)
Session 2: RV-4 (Flipkart spider), RV-5 (integration), RV-6 (post-scrape intelligence)
Session 3: RV-7 (serializer + frontend), RV-8 (testing)
```
