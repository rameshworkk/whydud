"""Scrapy item pipelines for validation, product matching, and persistence.

Pipeline order (configured in scrapy_settings.py):
  100 — ValidationPipeline    → drop items missing required fields
  200 — NormalizationPipeline → clean titles, normalise specs
  400 — ProductPipeline       → match/create Product + Listing + PriceSnapshot
  500 — MeilisearchIndexPipeline → batch-sync products to Meilisearch
"""
import logging
import os
import re
from decimal import Decimal

from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Required fields — items without these are dropped
# ---------------------------------------------------------------------------
REQUIRED_FIELDS = ("marketplace_slug", "external_id", "url", "title")


# ===================================================================
# 100 — Validation
# ===================================================================

class ValidationPipeline:
    """Drop items that lack required fields."""

    def process_item(self, item, spider):
        missing = [f for f in REQUIRED_FIELDS if not item.get(f)]
        if missing:
            spider.items_failed += 1
            raise DropItem(f"Missing required fields: {missing}")
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
            spider.items_failed += 1
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

        # ------- 4. Find or create ProductListing + Product ---------------
        listing = ProductListing.objects.filter(
            marketplace=marketplace,
            external_id=item["external_id"],
        ).select_related("product").first()

        if listing:
            # Update existing listing
            product = listing.product
            self._update_listing(listing, item, seller, now)
            self._update_product_from_listing(product, item, brand, now)
        else:
            # 4-step matching engine (Steps 1-3)
            result = match_product(item, brand=brand)
            product = result.product

            listing = self._create_listing(
                product, marketplace, seller, item, now,
                match_confidence=Decimal(str(result.confidence)),
                match_method=result.method,
            )

        # ------- 5. PriceSnapshot — ALWAYS record after every scrape --------
        # Raw SQL because price_snapshots is a TimescaleDB hypertable with no
        # auto-increment id column (managed=False). ORM .create() fails with
        # "column price_snapshots.id does not exist".
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

        # ------- 6. Recalculate canonical product aggregates (Step 4) -----
        update_canonical_product(product)

        # Track product ID for batch Meilisearch sync in close_spider
        self._track_product(spider, str(product.id))

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
                "title", "current_price", "mrp", "discount_pct",
                "in_stock", "rating", "review_count", "seller",
                "last_scraped_at", "updated_at",
            ]
        )

    @staticmethod
    def _update_product_from_listing(product, item, brand, now):
        """Push fresh data onto the canonical Product."""
        update_fields = ["last_scraped_at", "updated_at"]

        product.last_scraped_at = now

        if brand and not product.brand:
            product.brand = brand
            update_fields.append("brand")

        # Update images if we have more / better ones
        if item.get("images") and (
            not product.images or len(item["images"]) > len(product.images)
        ):
            product.images = item["images"]
            update_fields.append("images")

        # Update specs if richer
        if item.get("specs") and (
            not product.specs or len(item["specs"]) > len(product.specs)
        ):
            product.specs = item["specs"]
            update_fields.append("specs")

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
        product_ids = list(
            getattr(spider, ProductPipeline._product_ids_attr, set())
        )
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
