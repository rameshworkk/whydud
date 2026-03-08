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

    @classmethod
    def from_crawler(cls, crawler):
        pipe = cls()
        pipe._crawler = crawler
        return pipe

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

    @classmethod
    def from_crawler(cls, crawler):
        pipe = cls()
        pipe._crawler = crawler
        return pipe

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
            self._crawler.spider.items_failed = getattr(self._crawler.spider, "items_failed", 0) + 1
            raise DropItem(f"Unknown marketplace: {item['marketplace_slug']}")

        # ------- 2. Seller ------------------------------------------------
        seller = None
        if item.get("seller_name"):
            from django.utils.text import slugify

            # Use external_seller_id for uniqueness (the DB constraint is
            # on marketplace + external_seller_id). Fall back to a slug
            # derived from the seller name when no explicit ID is available.
            ext_id = item.get("external_seller_id") or slugify(item["seller_name"])
            seller, created = Seller.objects.get_or_create(
                marketplace=marketplace,
                external_seller_id=ext_id,
                defaults={
                    "name": item["seller_name"],
                    "fulfilled_by": item.get("fulfilled_by") or "",
                    "avg_rating": item.get("seller_rating"),
                },
            )
            # Update seller rating on existing sellers
            if not created and item.get("seller_rating") is not None:
                seller.avg_rating = item["seller_rating"]
                seller.save(update_fields=["avg_rating", "updated_at"])

        # ------- 3. Brand (alias-aware resolution) ------------------------
        brand = resolve_or_create_brand(item["brand"]) if item.get("brand") else None

        # ------- 3b. Category resolution (canonical mapper) ----------------
        from apps.products.category_mapper import resolve_canonical_category

        category = resolve_canonical_category(
            marketplace_slug=item.get("marketplace_slug", ""),
            breadcrumbs=item.get("breadcrumbs", []) or [],
            title=item.get("title", ""),
            raw_category=item.get("category", ""),
        )

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
                from django.db import connections

                db_alias = "write" if "write" in connections.databases else "default"
                with connections[db_alias].cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO price_snapshots
                            (time, listing_id, product_id, marketplace_id,
                             price, mrp, in_stock, seller_name, source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                            "scraper",
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

        # ------- 7. Close backfill loop if this was an enrichment scrape --
        if listing:
            self._close_backfill_loop(listing)

        # Track product ID for batch Meilisearch sync in close_spider
        self._track_product(self._crawler.spider, str(product.id))

        return item

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

        update_fields = [
            "title", "external_url", "current_price", "mrp", "discount_pct",
            "in_stock", "rating", "review_count", "seller",
            "last_scraped_at", "updated_at",
        ]

        # Extended listing fields — only overwrite when spider provides data
        if item.get("variant_options") is not None:
            listing.variant_options = item["variant_options"]
            update_fields.append("variant_options")
        if item.get("offer_details") is not None:
            listing.offer_details = item["offer_details"]
            update_fields.append("offer_details")
        if item.get("about_bullets"):
            listing.about_bullets = item["about_bullets"]
            update_fields.append("about_bullets")
        if item.get("warranty"):
            listing.warranty = item["warranty"][:500]
            update_fields.append("warranty")
        if item.get("delivery_info"):
            listing.delivery_info = item["delivery_info"][:500]
            update_fields.append("delivery_info")
        if item.get("return_policy"):
            listing.return_policy = item["return_policy"][:500]
            update_fields.append("return_policy")

        listing.save(update_fields=update_fields)

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

        # Physical / identification fields — first-wins (only fill if empty)
        _spec_field_map = {
            "country_of_origin": ("country_of_origin", ["Country of Origin", "country of origin"], 200),
            "manufacturer": ("manufacturer", ["Manufacturer", "manufacturer"], 500),
            "model_number": ("model_number", ["Item model number", "Model Number", "Model Name"], 200),
            "weight": ("weight", ["Item Weight", "Product Weight", "Weight"], 100),
            "dimensions": ("dimensions", ["Product Dimensions", "Item Dimensions", "Dimensions"], 200),
        }
        for field_name, (item_key, spec_keys, max_len) in _spec_field_map.items():
            if not getattr(product, field_name, ""):
                # Check item directly first (spider may set these)
                val = item.get(item_key)
                if not val:
                    # Fall back to extracting from specs dict
                    specs = item.get("specs") or {}
                    for sk in spec_keys:
                        val = specs.get(sk)
                        if val:
                            break
                if val:
                    setattr(product, field_name, str(val)[:max_len])
                    update_fields.append(field_name)

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
            # Extended fields
            variant_options=item.get("variant_options"),
            offer_details=item.get("offer_details"),
            about_bullets=item.get("about_bullets") or None,
            warranty=(item.get("warranty") or "")[:500],
            delivery_info=(item.get("delivery_info") or "")[:500],
            return_policy=(item.get("return_policy") or "")[:500],
        )
        logger.info(
            f"Created listing: {item['external_id']} on {marketplace.slug}"
        )
        return listing

    def _close_backfill_loop(self, listing):
        """If this listing was scraped as part of backfill enrichment,
        mark it complete and optionally chain review scraping.

        For non-backfill scrapes (99% of cases), finds 0 matches and returns
        instantly. Uses composite index on (external_id, marketplace_slug).
        Must NEVER crash the main pipeline — everything is wrapped in try/except.
        """
        try:
            from apps.pricing.models import BackfillProduct

            # Find matching backfill records with pending/enriching status
            matching = BackfillProduct.objects.filter(
                marketplace_slug=listing.marketplace.slug,
                external_id=listing.external_id,
                scrape_status__in=("pending", "enriching"),
            )

            # Check if any need reviews BEFORE updating status
            needs_reviews = list(
                matching.filter(review_status="pending")
                .values_list("id", flat=True)
            )

            # Mark enrichment complete
            updated = matching.update(
                scrape_status="scraped",
                product_listing=listing,
            )

            if updated > 0:
                self._upgrade_lightweight_product(listing)
                logger.info(
                    "Backfill enrichment complete: %s", listing.external_id
                )

                # Chain review scraping for eligible products
                if needs_reviews:
                    try:
                        from apps.pricing.backfill.enrichment import (
                            queue_review_scraping,
                        )

                        queue_review_scraping.delay(
                            listing_id=str(listing.id),
                            marketplace_slug=listing.marketplace.slug,
                            external_id=listing.external_id,
                        )
                        logger.info(
                            "Chained review scraping for %s",
                            listing.external_id,
                        )
                    except ImportError:
                        pass  # enrichment module not built yet

        except ImportError:
            pass  # backfill module not available
        except Exception as e:
            logger.debug("Backfill loop skipped: %s", e)

    @staticmethod
    def _upgrade_lightweight_product(listing):
        """Upgrade Product from lightweight to full after enrichment scrape."""
        try:
            from apps.products.models import Product

            product = listing.product
            if not product or not product.is_lightweight:
                return

            updates = {"is_lightweight": False}
            if listing.rating and not product.avg_rating:
                updates["avg_rating"] = listing.rating
            if listing.review_count and (
                not product.total_reviews or product.total_reviews == 0
            ):
                updates["total_reviews"] = listing.review_count

            Product.objects.filter(id=product.id).update(**updates)
        except Exception as e:
            logger.debug("Lightweight upgrade skipped: %s", e)


# ===================================================================
# 450 — Review Persistence
# ===================================================================

class ReviewPersistencePipeline:
    """Persists ReviewItems to the Review model."""

    @classmethod
    def from_crawler(cls, crawler):
        pipe = cls()
        pipe._crawler = crawler
        return pipe

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

        self._crawler.spider.reviews_saved = getattr(self._crawler.spider, "reviews_saved", 0) + 1
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

    @classmethod
    def from_crawler(cls, crawler):
        pipe = cls()
        pipe._crawler = crawler
        return pipe

    def process_item(self, item, spider):
        return item

    def close_spider(self, spider):
        """Sync all products from this spider run to Meilisearch."""
        spider = self._crawler.spider
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

    @classmethod
    def from_crawler(cls, crawler):
        pipe = cls()
        pipe._crawler = crawler
        pipe._count = 0
        pipe._last_update = 0
        return pipe

    def __init__(self):
        self._count = 0
        self._last_update = 0

    def process_item(self, item, spider):
        self._count += 1
        if self._count - self._last_update >= 50:
            self._update_job()
            self._last_update = self._count
        return item

    def close_spider(self, spider):
        self._update_job()

    def _update_job(self):
        spider = self._crawler.spider
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
