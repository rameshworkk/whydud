"""Scrapy item pipelines for validation, product matching, and persistence.

Pipeline order (configured in scrapy_settings.py):
  100 — ValidationPipeline          → drop ProductItems missing required fields
  150 — ReviewValidationPipeline    → drop ReviewItems missing required fields
  200 — NormalizationPipeline       → clean titles, normalise specs
  400 — ProductPipeline             → match/create Product + Listing + PriceSnapshot
  450 — ReviewPersistencePipeline   → persist ReviewItems to Review model
  500 — MeilisearchIndexPipeline    → batch-sync products to Meilisearch
  600 — SpiderStatsUpdatePipeline   → update ScraperJob row with item counts
"""
import hashlib
import logging
import os
import re
from decimal import Decimal

import dateutil.parser
from scrapy.exceptions import DropItem

from apps.scraping.items import ReviewItem

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Required fields — items without these are dropped
# ---------------------------------------------------------------------------
REQUIRED_FIELDS = ("marketplace_slug", "external_id", "url", "title")


# ===================================================================
# 100 — Validation
# ===================================================================

class ValidationPipeline:
    """Drop ProductItems that lack required fields (skip ReviewItems)."""

    def process_item(self, item, spider):
        if isinstance(item, ReviewItem):
            return item  # ReviewItems validated by ReviewValidationPipeline
        missing = [f for f in REQUIRED_FIELDS if not item.get(f)]
        if missing:
            spider.items_failed = getattr(spider, "items_failed", 0) + 1
            raise DropItem(f"Missing required fields: {missing}")
        return item


# ===================================================================
# 150 — Review Validation
# ===================================================================

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


# ===================================================================
# 200 — Normalisation
# ===================================================================

class NormalizationPipeline:
    """Clean and normalise scraped data before persistence."""

    _WHITESPACE_RE = re.compile(r"\s+")
    _BRAND_STRIP_RE = re.compile(
        r"^(visit the\s+|brand:\s*)", flags=re.IGNORECASE
    )

    def process_item(self, item, spider):
        # Title: collapse whitespace, strip
        if item.get("title"):
            item["title"] = self._WHITESPACE_RE.sub(" ", item["title"]).strip()

        # Brand: normalise casing
        if item.get("brand"):
            brand = self._BRAND_STRIP_RE.sub("", item["brand"]).strip()
            # Title-case multi-word brands, upper-case single words ≤4 chars
            if len(brand.split()) == 1 and len(brand) <= 4:
                brand = brand.upper()
            else:
                brand = brand.title()
            item["brand"] = brand

        # Specs: strip whitespace from keys and values
        if item.get("specs") and isinstance(item["specs"], dict):
            item["specs"] = {
                k.strip(): v.strip()
                for k, v in item["specs"].items()
                if k.strip() and v.strip()
            }

        # About bullets: remove empty strings
        if item.get("about_bullets"):
            item["about_bullets"] = [
                b.strip() for b in item["about_bullets"] if b.strip()
            ]

        # Images: deduplicate while preserving order
        if item.get("images"):
            seen: set[str] = set()
            unique: list[str] = []
            for img in item["images"]:
                if img not in seen:
                    seen.add(img)
                    unique.append(img)
            item["images"] = unique

        return item


# ===================================================================
# 400 — Product matching + Persistence + Price snapshots
# ===================================================================

class ProductPipeline:
    """Persist scraped items into Django models.

    Workflow per item:
      1. Resolve Marketplace by slug.
      2. Find or create Seller.
      3. Look up existing ProductListing by (marketplace, external_id).
         a. If found → update listing fields + update its Product.
         b. If new   → run product-matching to find canonical Product.
                        If no match → create new Product.
                        Then create ProductListing.
      4. Record a PriceSnapshot (raw SQL to avoid ORM/hypertable issues).
      5. Recompute Product.current_best_price across all its listings.
    """

    def open_spider(self, spider):
        """Ensure Django is initialised (needed when Scrapy runs standalone)."""
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "whydud.settings.dev")
        import django

        django.setup()
        logger.info("ProductPipeline: Django initialised")

    def process_item(self, item, spider):
        if isinstance(item, ReviewItem):
            return item  # ReviewItems handled by ReviewPersistencePipeline

        from django.utils import timezone

        from apps.pricing.models import PriceSnapshot
        from apps.products.matching import (
            match_product,
            resolve_or_create_brand,
            resolve_category,
            update_canonical_product,
        )
        from apps.products.models import (
            Marketplace,
            ProductListing,
            Seller,
        )

        now = timezone.now()

        # ------- 1. Marketplace -------------------------------------------
        try:
            marketplace = Marketplace.objects.get(slug=item["marketplace_slug"])
        except Marketplace.DoesNotExist:
            logger.error(f"Marketplace '{item['marketplace_slug']}' not found — skipping item")
            spider.items_failed = getattr(spider, "items_failed", 0) + 1
            raise DropItem(f"Unknown marketplace: {item['marketplace_slug']}")

        # ------- 2. Seller ------------------------------------------------
        seller = None
        if item.get("seller_name"):
            from django.utils.text import slugify

            # Use external_seller_id for uniqueness (the DB constraint is
            # on marketplace + external_seller_id). Fall back to a slug
            # derived from the seller name when no explicit ID is available.
            ext_id = item.get("external_seller_id") or slugify(item["seller_name"])
            seller, _ = Seller.objects.get_or_create(
                marketplace=marketplace,
                external_seller_id=ext_id,
                defaults={
                    "name": item["seller_name"],
                    "fulfilled_by": item.get("fulfilled_by") or "",
                },
            )

        # ------- 3. Brand (alias-aware resolution) ------------------------
        brand = resolve_or_create_brand(item["brand"]) if item.get("brand") else None

        # ------- 3b. Category resolution (slug → breadcrumbs → auto-create) -
        category = resolve_category(item.get("category_slug"))
        # If no category from slug, try to auto-create from breadcrumbs
        if not category and item.get("breadcrumbs"):
            category = self._resolve_category_from_breadcrumbs(item["breadcrumbs"])

        # ------- 4. Find or create ProductListing + Product ---------------
        listing = ProductListing.objects.filter(
            marketplace=marketplace,
            external_id=item["external_id"],
        ).select_related("product").first()

        if listing:
            # Update existing listing
            product = listing.product
            self._update_listing(listing, item, seller, now)
            self._update_product_from_listing(product, item, brand, category, now)
        else:
            # 4-step matching engine (Steps 1-3)
            result = match_product(item, brand=brand, category=category)
            product = result.product

            listing = self._create_listing(
                product, marketplace, seller, item, now,
                match_confidence=Decimal(str(result.confidence)),
                match_method=result.method,
            )

        # ------- 5. PriceSnapshot — record only when price is available --------
        # Raw SQL because price_snapshots is a TimescaleDB hypertable with no
        # auto-increment id column (managed=False). ORM .create() fails with
        # "column price_snapshots.id does not exist".
        # Skip if price is None — hypertable has NOT NULL constraint on price.
        # Wrapped in try/except: a missing snapshot is recoverable, a dropped
        # product item is not.
        if listing.current_price is not None:
            try:
                from django.db import connection

                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO price_snapshots
                            (time, listing_id, product_id, marketplace_id, price, mrp, in_stock, seller_name)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            now,
                            listing.id,
                            product.id,
                            marketplace.id,
                            listing.current_price,
                            listing.mrp,
                            listing.in_stock,
                            item.get("seller_name") or "",
                        ],
                    )
            except Exception:
                logger.warning(
                    "Failed to insert PriceSnapshot for listing %s — "
                    "product saved, snapshot skipped",
                    listing.id,
                    exc_info=True,
                )

        # ------- 6. Recalculate canonical product aggregates (Step 4) -----
        update_canonical_product(product)

        # Track product ID for batch Meilisearch sync in close_spider
        self._track_product(spider, str(product.id))

        return item

    @staticmethod
    def _resolve_category_from_breadcrumbs(breadcrumbs: list[str]):
        """Auto-create a category hierarchy from breadcrumb trail.

        Uses the deepest meaningful breadcrumb as the category.
        Skips generic terms like "Home", "All Categories".
        """
        from django.utils.text import slugify
        from apps.products.models import Category

        skip_terms = {"home", "all categories", "all", "search", "products"}

        # Walk breadcrumbs from deepest to shallowest
        for crumb in reversed(breadcrumbs):
            clean = crumb.strip()
            if not clean or clean.lower() in skip_terms:
                continue
            slug = slugify(clean)
            if not slug or len(slug) < 2:
                continue

            # Check if category exists
            category = Category.objects.filter(slug=slug).first()
            if category:
                return category

            # Auto-create — find parent from the next level up
            parent = None
            crumb_idx = breadcrumbs.index(crumb)
            if crumb_idx > 0:
                parent_crumb = breadcrumbs[crumb_idx - 1].strip()
                parent_slug = slugify(parent_crumb)
                if parent_slug and parent_slug.lower() not in skip_terms:
                    parent = Category.objects.filter(slug=parent_slug).first()

            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": clean,
                    "parent": parent,
                    "level": crumb_idx if crumb_idx >= 0 else 0,
                },
            )
            if created:
                logger.info("Auto-created category from breadcrumbs: %s (slug=%s, parent=%s)", clean, slug, parent)
            return category

        return None

    # Collect product IDs so MeilisearchIndexPipeline can batch-sync them
    _product_ids_attr = "_synced_product_ids"

    @staticmethod
    def _track_product(spider, product_id: str) -> None:
        """Stash product ID on the spider for downstream pipeline access."""
        if not hasattr(spider, ProductPipeline._product_ids_attr):
            setattr(spider, ProductPipeline._product_ids_attr, set())
        getattr(spider, ProductPipeline._product_ids_attr).add(product_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _update_listing(listing, item, seller, now):
        """Update an existing ProductListing with fresh scraped data."""
        listing.title = item["title"]
        listing.external_url = item["url"]
        listing.current_price = item.get("price")
        listing.mrp = item.get("mrp")
        listing.in_stock = item.get("in_stock", True)
        listing.rating = item.get("rating")
        listing.review_count = item.get("review_count") or 0
        listing.last_scraped_at = now
        if seller:
            listing.seller = seller
        if item.get("mrp") and item.get("price") and item["mrp"] > 0:
            listing.discount_pct = round(
                (1 - item["price"] / item["mrp"]) * 100, 2
            )
        listing.save(
            update_fields=[
                "title", "external_url", "current_price", "mrp", "discount_pct",
                "in_stock", "rating", "review_count", "seller",
                "last_scraped_at", "updated_at",
            ]
        )

    @staticmethod
    def _update_product_from_listing(product, item, brand, category, now):
        """Push fresh data onto the canonical Product."""
        update_fields = ["last_scraped_at", "updated_at"]

        product.last_scraped_at = now

        if brand and not product.brand:
            product.brand = brand
            update_fields.append("brand")

        if category and not product.category:
            product.category = category
            update_fields.append("category")

        # Update images if we have more / better ones
        if item.get("images") and (
            not product.images or len(item["images"]) > len(product.images)
        ):
            product.images = item["images"]
            update_fields.append("images")

        # Update specs — merge new specs into existing (richer data over time)
        if item.get("specs"):
            existing = product.specs or {}
            new_specs = item["specs"]
            if not existing or len(new_specs) > len(existing):
                # Merge: keep old specs, overwrite with new
                merged = {**existing, **new_specs}
                product.specs = merged
                update_fields.append("specs")

        # Update description if we have a better one
        if item.get("description") and not product.description:
            product.description = item["description"][:5000]
            update_fields.append("description")

        # Update rating / review aggregation
        if item.get("rating") is not None:
            product.avg_rating = item["rating"]
            update_fields.append("avg_rating")
        if item.get("review_count") is not None:
            product.total_reviews = max(product.total_reviews, item["review_count"])
            update_fields.append("total_reviews")

        product.save(update_fields=update_fields)

    @staticmethod
    def _create_listing(product, marketplace, seller, item, now,
                        match_confidence=None, match_method=""):
        """Create a new ProductListing."""
        from apps.products.models import ProductListing

        discount_pct = None
        if item.get("mrp") and item.get("price") and item["mrp"] > 0:
            discount_pct = round(
                (1 - item["price"] / item["mrp"]) * 100, 2
            )

        listing = ProductListing.objects.create(
            product=product,
            marketplace=marketplace,
            seller=seller,
            external_id=item["external_id"],
            external_url=item["url"],
            title=item["title"],
            current_price=item.get("price"),
            mrp=item.get("mrp"),
            discount_pct=discount_pct,
            in_stock=item.get("in_stock", True),
            rating=item.get("rating"),
            review_count=item.get("review_count") or 0,
            match_confidence=match_confidence or Decimal("1.00"),
            match_method=match_method or "external_id",
            last_scraped_at=now,
        )
        logger.info(
            f"Created listing: {item['external_id']} on {marketplace.slug}"
        )
        return listing


# ===================================================================
# 450 — Review Persistence
# ===================================================================

class ReviewPersistencePipeline:
    """Persists ReviewItems to the Review model."""

    def process_item(self, item, spider):
        if not isinstance(item, ReviewItem):
            return item

        from django.utils import timezone

        from apps.products.models import ProductListing
        from apps.reviews.models import Review

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
            hash_input = (
                f"{item['marketplace_slug']}:{item['product_external_id']}:"
                f"{item.get('reviewer_name', '')}:{item.get('review_date', '')}:"
                f"{item['body'][:100]}"
            )
            review_id = hashlib.sha256(hash_input.encode()).hexdigest()[:32]

        # Dedup check
        if Review.objects.filter(
            external_review_id=review_id,
            marketplace=listing.marketplace
        ).exists():
            raise DropItem(f"Duplicate review: {review_id}")

        # Parse date — ensure timezone-aware (Django USE_TZ=True)
        review_date = None
        if item.get("review_date"):
            try:
                review_date = dateutil.parser.parse(item["review_date"])
                if review_date.tzinfo is None:
                    review_date = timezone.make_aware(
                        review_date, timezone.get_default_timezone()
                    )
            except (ValueError, TypeError):
                review_date = timezone.now()
        else:
            review_date = timezone.now()

        # Content hash for fraud detection
        content_hash = hashlib.sha256(item["body"].encode()).hexdigest()

        # Create review
        Review.objects.create(
            product=listing.product,
            user=None,  # Scraped, not user-submitted
            rating=int(item["rating"]),
            title=item.get("title", "")[:500],
            body=item["body"],
            source=Review.Source.SCRAPED,
            is_verified_purchase=bool(item.get("is_verified_purchase", False)),
            is_published=True,
            review_date=review_date,
            content_hash=content_hash,
            media=item.get("images", []),
            external_reviewer_name=item.get("reviewer_name", "")[:200],
            external_reviewer_id=item.get("reviewer_id", "")[:100],
            external_review_id=review_id,
            external_review_url=item.get("review_url", "")[:500],
            helpful_vote_count=int(item.get("helpful_votes", 0)),
            marketplace=listing.marketplace,
            variant_info=item.get("variant", "")[:300],
        )

        spider.reviews_saved = getattr(spider, "reviews_saved", 0) + 1
        return item


# ===================================================================
# 500 — Meilisearch indexing
# ===================================================================

class MeilisearchIndexPipeline:
    """Batch-sync products touched during a spider run to Meilisearch.

    Collects product IDs stashed on the spider by ProductPipeline, then
    pushes them all in ``close_spider`` using the search task helper.
    Per-item ``process_item`` is a no-op (batch is more efficient).
    """

    def process_item(self, item, spider):
        return item

    def close_spider(self, spider):
        """Sync all products from this spider run to Meilisearch."""
        _attr = getattr(ProductPipeline, "_product_ids_attr", "_synced_product_ids")
        product_ids = list(getattr(spider, _attr, set()))
        if not product_ids:
            return

        logger.info(
            "MeilisearchIndexPipeline: syncing %d products from %s",
            len(product_ids), spider.name,
        )

        try:
            from apps.search.tasks import sync_products_to_meilisearch
            sync_products_to_meilisearch.delay(product_ids=product_ids)
        except Exception:
            logger.exception("Failed to queue Meilisearch sync for %d products", len(product_ids))


# ===================================================================
# 600 — ScraperJob stats (real-time item counts)
# ===================================================================

class SpiderStatsUpdatePipeline:
    """Update ScraperJob row with real-time item counts.

    Writes every 50 items (not every item) to avoid excessive DB writes.
    Final update happens in close_spider.
    """

    def __init__(self):
        self._count = 0
        self._last_update = 0

    def process_item(self, item, spider):
        self._count += 1
        if self._count - self._last_update >= 50:
            self._update_job(spider)
            self._last_update = self._count
        return item

    def close_spider(self, spider):
        self._update_job(spider)

    def _update_job(self, spider):
        job_id = getattr(spider, "job_id", None)
        if not job_id:
            return
        try:
            from apps.scraping.models import ScraperJob

            ScraperJob.objects.filter(id=job_id).update(
                items_scraped=getattr(spider, "items_scraped", 0),
                items_failed=getattr(spider, "items_failed", 0),
            )
        except Exception:
            pass  # Best effort
