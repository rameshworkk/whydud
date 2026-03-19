"""Pricing models: snapshots, offers, wishlists price alerts, backfill staging.

PostgreSQL schema: public (price_snapshots hypertable via TimescaleDB)
"""
import uuid
from django.db import models


class PriceSnapshot(models.Model):
    """TimescaleDB hypertable — one row per price check per listing.
    
    NOTE: Create hypertable manually after migration:
      SELECT create_hypertable('price_snapshots', 'time');
    """
    # No auto pk — TimescaleDB hypertable uses composite key (time, listing_id)
    time = models.DateTimeField()
    listing = models.ForeignKey(
        "products.ProductListing", on_delete=models.CASCADE, db_column="listing_id"
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, db_column="product_id"
    )
    marketplace = models.ForeignKey(
        "products.Marketplace", on_delete=models.CASCADE, db_column="marketplace_id"
    )
    price = models.DecimalField(max_digits=12, decimal_places=2)
    mrp = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    in_stock = models.BooleanField(null=True)
    seller_name = models.CharField(max_length=500, blank=True)
    source = models.CharField(max_length=30, default="scraper")

    class Meta:
        db_table = "price_snapshots"
        managed = False  # TimescaleDB manages this table
        ordering = ["-time"]


class MarketplaceOffer(models.Model):
    """Bank/card offers scraped from marketplace pages."""

    class DiscountType(models.TextChoices):
        FLAT = "flat", "Flat Off"
        PERCENT = "percent", "Percent Off"
        CASHBACK = "cashback", "Cashback"
        NO_COST_EMI = "no_cost_emi", "No Cost EMI"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    marketplace = models.ForeignKey("products.Marketplace", on_delete=models.CASCADE)
    scope_type = models.CharField(max_length=20)  # product, listing, category, sitewide
    product = models.ForeignKey(
        "products.Product", on_delete=models.SET_NULL, null=True, blank=True
    )
    listing = models.ForeignKey(
        "products.ProductListing", on_delete=models.SET_NULL, null=True, blank=True
    )
    category = models.ForeignKey(
        "products.Category", on_delete=models.SET_NULL, null=True, blank=True
    )
    offer_type = models.CharField(max_length=30)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    bank_slug = models.CharField(max_length=50, blank=True)
    card_type = models.CharField(max_length=20, blank=True)
    card_network = models.CharField(max_length=20, blank=True)
    card_variants = models.JSONField(default=list)
    wallet_provider = models.CharField(max_length=50, blank=True)
    membership_type = models.CharField(max_length=50, blank=True)
    coupon_code = models.CharField(max_length=100, blank=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    max_discount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    min_purchase = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    emi_tenures = models.JSONField(default=list)
    emi_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    emi_processing_fee = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    stackable = models.BooleanField(default=False)
    source = models.CharField(max_length=30)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    terms_conditions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_offers"
        indexes = [
            models.Index(fields=["marketplace", "is_active"]),
            models.Index(fields=["bank_slug"]),
        ]

    def __str__(self) -> str:
        return self.title


class PriceAlert(models.Model):
    """User price drop alert — standalone or linked to a wishlist item."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="price_alerts")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    target_price = models.DecimalField(max_digits=12, decimal_places=2)
    current_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    marketplace = models.ForeignKey(
        "products.Marketplace", on_delete=models.SET_NULL, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    is_triggered = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(null=True, blank=True)
    triggered_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    triggered_marketplace = models.CharField(max_length=50, blank=True)
    notification_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users"."price_alerts'
        unique_together = [("user", "product", "marketplace")]
        indexes = [
            models.Index(fields=["is_active", "product"], condition=models.Q(is_active=True), name="idx_alerts_active"),
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} alert on {self.product_id} @ ₹{self.target_price}"


class ClickEvent(models.Model):
    """Affiliate click tracking — one row per outbound marketplace click."""

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="click_events"
    )
    session_id = models.CharField(max_length=100, null=True, blank=True)
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="click_events")
    listing = models.ForeignKey(
        "products.ProductListing", on_delete=models.SET_NULL, null=True, blank=True, related_name="click_events"
    )
    marketplace = models.ForeignKey("products.Marketplace", on_delete=models.CASCADE, related_name="click_events")
    source_page = models.CharField(max_length=50)  # product_page, comparison, deal, search, homepage
    source_section = models.CharField(max_length=50, blank=True)  # best_deal_card, marketplace_prices
    affiliate_url = models.URLField(max_length=2000)
    affiliate_tag = models.CharField(max_length=100, blank=True)
    sub_tag = models.CharField(max_length=200, blank=True)
    purchase_confirmed = models.BooleanField(default=False)
    confirmation_source = models.CharField(max_length=30, blank=True)  # email_parsed, affiliate_report, user_reported
    confirmed_at = models.DateTimeField(null=True, blank=True)
    price_at_click = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    device_type = models.CharField(max_length=20, blank=True)
    referrer = models.CharField(max_length=500, blank=True)
    ip_hash = models.CharField(max_length=64, null=True, blank=True)
    user_agent_hash = models.CharField(max_length=64, null=True, blank=True)
    clicked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "click_events"
        indexes = [
            models.Index(fields=["user", "-clicked_at"]),
            models.Index(fields=["product", "-clicked_at"]),
        ]

    def __str__(self) -> str:
        return f"Click {self.id}: {self.product_id} via {self.marketplace_id}"


class BackfillProduct(models.Model):
    """Staging table for the multi-phase price history backfill pipeline.

    Lifecycle: discovered → bh_filled → ph_extended → done
    Phase 1 creates the record, Phase 2-3 enrich it, Phase 4 links to our catalog.
    """

    class Status(models.TextChoices):
        DISCOVERED = "discovered", "Discovered"
        BH_FILLING = "bh_filling", "BH Filling"      # Worker has claimed for Phase 2
        BH_FILLED = "bh_filled", "BuyHatke Filled"
        PH_EXTENDING = "ph_extending", "PH Extending"  # Worker has claimed for Phase 3
        PH_EXTENDED = "ph_extended", "PH Extended"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    class ScrapeStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ENRICHING = "enriching", "Enriching"
        SCRAPED = "scraped", "Scraped"
        FAILED = "failed", "Failed"

    class EnrichmentMethod(models.TextChoices):
        PENDING = "pending", "Pending"
        PLAYWRIGHT = "playwright", "Playwright"
        CURL_CFFI = "curl_cffi", "curl_cffi"
        SKIPPED = "skipped", "Skipped"

    class ReviewStatus(models.TextChoices):
        SKIP = "skip", "Skip"
        PENDING = "pending", "Pending"
        SCRAPING = "scraping", "Scraping"
        SCRAPED = "scraped", "Scraped"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Discovery fields (Phase 1)
    ph_code = models.CharField(max_length=20, unique=True, db_index=True)
    ph_url = models.URLField(max_length=500, blank=True)
    marketplace_slug = models.CharField(max_length=50, db_index=True)
    external_id = models.CharField(max_length=200, db_index=True)  # ASIN or FSID
    marketplace_url = models.URLField(max_length=2000, blank=True)
    title = models.CharField(max_length=1000, blank=True)
    brand_name = models.CharField(max_length=200, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    current_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Latest known price in paisa (from tracker or raw_price_data)",
    )
    category_name = models.CharField(
        max_length=100, blank=True, db_index=True,
        help_text="Inferred from title via regex (e.g. smartphone, laptop, tv)",
    )

    # Link to our ProductListing (populated when matched)
    product_listing = models.ForeignKey(
        "products.ProductListing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="backfill_records",
    )

    # Price history metadata (Phase 2)
    price_data_points = models.IntegerField(default=0)
    history_from = models.DateTimeField(null=True, blank=True)
    history_to = models.DateTimeField(null=True, blank=True)

    # Cached raw price points for later injection (Phase 2/3)
    raw_price_data = models.JSONField(
        default=list, blank=True,
        help_text="Cached raw price points: [{t, p, s}, ...]",
    )

    # BuyHatke prediction & popularity (Phase 2)
    bh_prediction_days = models.IntegerField(null=True, blank=True)
    bh_prediction_weeks = models.IntegerField(null=True, blank=True)
    bh_prediction_months = models.IntegerField(null=True, blank=True)
    bh_popularity = models.IntegerField(null=True, blank=True)

    # PriceHistory.app summary (Phase 3)
    min_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    min_price_date = models.DateTimeField(null=True, blank=True)
    max_price_date = models.DateTimeField(null=True, blank=True)

    # Status tracking
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DISCOVERED
    )
    scrape_status = models.CharField(
        max_length=20, choices=ScrapeStatus.choices, default=ScrapeStatus.PENDING
    )
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    # Enrichment routing
    enrichment_priority = models.SmallIntegerField(
        default=3,
        db_index=True,
        help_text="0=on-demand, 1=Playwright, 2=curl_cffi, 3=curl_cffi-low",
    )
    enrichment_method = models.CharField(
        max_length=20,
        choices=EnrichmentMethod.choices,
        default=EnrichmentMethod.PENDING,
    )
    enrichment_queued_at = models.DateTimeField(null=True, blank=True)

    # Review tracking (only for top 100K products)
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.SKIP,
        help_text="Review scraping status — only top 100K get reviews",
    )
    review_count_scraped = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "backfill_products"
        indexes = [
            models.Index(fields=["status", "marketplace_slug"]),
            models.Index(fields=["external_id", "marketplace_slug"]),
            models.Index(
                fields=["scrape_status", "enrichment_priority", "created_at"],
                name="idx_backfill_enrich_queue",
            ),
            models.Index(
                fields=["review_status", "scrape_status"],
                name="idx_backfill_review_queue",
            ),
        ]

    def append_price_data(self, price_points, source: str) -> int:
        """Append price points to raw_price_data cache (dedup-safe).

        Args:
            price_points: List of objects with .time and .price attributes.
            source: Source tag (e.g. "buyhatke", "pricehistory_app").

        Returns:
            Number of new entries added.
        """
        existing = {(e["t"], e["s"]) for e in self.raw_price_data}
        new_entries = []
        for pp in price_points:
            t = pp.time.isoformat() if hasattr(pp.time, "isoformat") else str(pp.time)
            p = str(pp.price)
            key = (t, source)
            if key not in existing:
                new_entries.append({"t": t, "p": p, "s": source})
                existing.add(key)
        # Create new list for Django JSONField change detection
        self.raw_price_data = self.raw_price_data + new_entries
        return len(new_entries)

    def __str__(self) -> str:
        return f"{self.marketplace_slug}/{self.external_id} ({self.status})"


class EnrichmentPriorityRule(models.Model):
    """Admin-configurable rules for custom enrichment priority assignment.

    Rules are evaluated in order (lowest ``order`` first). Each rule defines
    filters (marketplace, category, price range, brand pattern, min data points)
    and a target priority. When ``apply_custom_priority_rules()`` runs, matching
    BackfillProducts are updated to the rule's target priority.
    """

    PRIORITY_CHOICES = [
        (0, "P0 — On-demand"),
        (1, "P1 — Playwright"),
        (2, "P2 — curl_cffi"),
        (3, "P3 — curl_cffi-low"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=200,
        help_text="Human-readable rule name (e.g. 'Apple phones > ₹50K → P1')",
    )
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(
        default=0,
        help_text="Evaluation order — lower runs first. Later rules can override earlier ones.",
    )

    # Filters — all optional, combined with AND
    marketplace_slug = models.CharField(
        max_length=50, blank=True,
        help_text="Filter by marketplace (e.g. 'amazon-in', 'flipkart'). Blank = any.",
    )
    category_name = models.CharField(
        max_length=100, blank=True,
        help_text="Exact category match (e.g. 'smartphone', 'laptop'). Blank = any.",
    )
    category_pattern = models.CharField(
        max_length=200, blank=True,
        help_text="Regex pattern for category (e.g. 'smartphone|laptop'). Blank = any.",
    )
    brand_pattern = models.CharField(
        max_length=200, blank=True,
        help_text="Regex pattern for title/brand (e.g. '^(apple|samsung)'). Blank = any.",
    )
    title_contains = models.CharField(
        max_length=200, blank=True,
        help_text="Case-insensitive substring match on title. Blank = any.",
    )
    min_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Minimum current_price in paisa (e.g. 5000000 = ₹50K). Null = no minimum.",
    )
    max_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Maximum current_price in paisa. Null = no maximum.",
    )
    min_data_points = models.IntegerField(
        null=True, blank=True,
        help_text="Minimum price_data_points. Null = no minimum.",
    )

    # Target
    target_priority = models.SmallIntegerField(
        choices=PRIORITY_CHOICES,
        help_text="Priority to assign to matching products.",
    )
    also_mark_reviews = models.BooleanField(
        default=False,
        help_text="Also set review_status='pending' for matched products.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "enrichment_priority_rules"
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"{self.name} → P{self.target_priority}"

    def build_queryset(self):
        """Build a queryset of BackfillProducts matching this rule's filters.

        Only targets products with scrape_status='pending' (not yet enriched).
        """
        qs = BackfillProduct.objects.filter(scrape_status="pending")

        if self.marketplace_slug:
            qs = qs.filter(marketplace_slug=self.marketplace_slug)
        if self.category_name:
            qs = qs.filter(category_name=self.category_name)
        if self.category_pattern:
            qs = qs.filter(category_name__iregex=self.category_pattern)
        if self.brand_pattern:
            qs = qs.filter(title__iregex=self.brand_pattern)
        if self.title_contains:
            qs = qs.filter(title__icontains=self.title_contains)
        if self.min_price is not None:
            qs = qs.filter(current_price__gte=self.min_price)
        if self.max_price is not None:
            qs = qs.filter(current_price__lte=self.max_price)
        if self.min_data_points is not None:
            qs = qs.filter(price_data_points__gte=self.min_data_points)

        return qs

    def preview_count(self) -> int:
        """Return count of products that would be affected by this rule."""
        return self.build_queryset().count()
