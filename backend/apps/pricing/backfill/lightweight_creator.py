"""Lightweight record creator — Product + ProductListing from tracker data.

Creates usable product records WITHOUT marketplace scraping. Products
appear on the site immediately with price history charts. Full details
(images, specs, reviews) are filled in later by the enrichment pipeline.

Usage::

    python manage.py backfill_prices create-lightweight --batch 1000
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from django.utils.text import slugify

from apps.pricing.backfill.config import BackfillConfig
from apps.pricing.backfill.injector import inject_price_points
from apps.pricing.models import BackfillProduct

logger = logging.getLogger(__name__)


# Top Indian e-commerce brands — matched against title prefix
TOP_BRANDS = [
    "apple", "samsung", "oneplus", "xiaomi", "realme", "vivo",
    "oppo", "hp", "dell", "lenovo", "asus", "acer", "sony", "lg",
    "boat", "jbl", "bose", "whirlpool", "haier", "google",
    "nothing", "motorola", "nokia", "mi ", "redmi", "poco",
    "honor", "iqoo", "tecno", "infinix", "panasonic", "philips",
    "bosch", "godrej", "crompton", "orient", "bajaj", "havells",
    "voltas", "daikin", "hitachi", "canon", "nikon", "fujifilm",
]


def extract_brand(title: str) -> str | None:
    """Extract brand name from title prefix using TOP_BRANDS list."""
    title_lower = title.lower()
    for brand in TOP_BRANDS:
        if title_lower.startswith(brand):
            return brand.strip().title()
    return None


def _get_current_price(raw_price_data: list[dict]) -> Decimal | None:
    """Extract the most recent price from raw_price_data."""
    if not raw_price_data:
        return None

    # Sort by timestamp descending, pick first valid price
    sorted_data = sorted(
        raw_price_data, key=lambda x: x.get("t", ""), reverse=True,
    )
    for entry in sorted_data:
        try:
            price = Decimal(str(entry["p"]))
            if price > 0:
                return price
        except (InvalidOperation, KeyError, TypeError):
            continue
    return None


def _get_lowest_price(raw_price_data: list[dict]) -> tuple[Decimal | None, str | None]:
    """Find the lowest price and its date from raw_price_data.

    Returns:
        (lowest_price, date_iso_str) or (None, None).
    """
    if not raw_price_data:
        return None, None

    lowest = None
    lowest_date = None
    for entry in raw_price_data:
        try:
            price = Decimal(str(entry["p"]))
            if price > 0 and (lowest is None or price < lowest):
                lowest = price
                lowest_date = entry.get("t")
        except (InvalidOperation, KeyError, TypeError):
            continue
    return lowest, lowest_date


def _generate_unique_slug(title: str) -> str:
    """Generate a unique product slug, appending UUID suffix on collision."""
    from apps.products.models import Product

    base_slug = slugify(title[:200])
    if not base_slug:
        base_slug = "product"

    slug = base_slug
    if not Product.objects.filter(slug=slug).exists():
        return slug

    # Append short UUID suffix
    suffix = uuid.uuid4().hex[:8]
    slug = f"{base_slug}-{suffix}"
    while Product.objects.filter(slug=slug).exists():
        suffix = uuid.uuid4().hex[:8]
        slug = f"{base_slug}-{suffix}"
    return slug


def create_lightweight_records(batch_size: int = 1000) -> dict:
    """Convert BackfillProduct records into Product + ProductListing.

    Processes BackfillProducts that have price history data but no linked
    ProductListing. Creates lightweight Product records (is_lightweight=True)
    and injects historical price data into price_snapshots.

    Args:
        batch_size: Max products to process in this run.

    Returns:
        Dict with counts: {created, linked, skipped, errors, snapshots_injected}
    """
    from apps.products.matching import resolve_or_create_brand
    from apps.products.models import Marketplace, Product, ProductListing

    now = timezone.now()

    # Find candidates: have price data, no listing linked yet
    # Include bh_filled, ph_extended (price history ready), and done (in case
    # some were marked done without creating a product listing).
    candidates = list(
        BackfillProduct.objects.filter(
            status__in=[
                BackfillProduct.Status.BH_FILLED,
                BackfillProduct.Status.PH_EXTENDED,
                BackfillProduct.Status.DONE,
            ],
            product_listing__isnull=True,
        )
        .exclude(raw_price_data=[])
        .exclude(external_id="")
        .exclude(title="")
        .order_by("created_at")[:batch_size]
    )

    if not candidates:
        logger.info("Lightweight creator: no eligible candidates found")
        return {
            "created": 0,
            "linked": 0,
            "skipped": 0,
            "errors": 0,
            "snapshots_injected": 0,
        }

    logger.info("Lightweight creator: processing %d candidates", len(candidates))

    # Cache marketplace lookups
    marketplace_cache: dict[str, Marketplace | None] = {}
    product_ids: list[str] = []

    stats = {
        "created": 0,
        "linked": 0,
        "skipped": 0,
        "errors": 0,
        "snapshots_injected": 0,
    }

    for i, bp in enumerate(candidates):
        try:
            # 1. Resolve marketplace (cached)
            if bp.marketplace_slug not in marketplace_cache:
                marketplace_cache[bp.marketplace_slug] = (
                    Marketplace.objects.filter(slug=bp.marketplace_slug).first()
                )
            marketplace = marketplace_cache[bp.marketplace_slug]
            if not marketplace:
                logger.warning(
                    "Unknown marketplace '%s' for %s — skipping",
                    bp.marketplace_slug, bp.external_id,
                )
                stats["skipped"] += 1
                continue

            # 2. Check if ProductListing already exists for this external_id
            existing_listing = ProductListing.objects.filter(
                marketplace=marketplace,
                external_id=bp.external_id,
            ).select_related("product").first()

            if existing_listing:
                # Link and inject history only
                bp.product_listing = existing_listing
                bp.save(update_fields=["product_listing", "updated_at"])
                injected = _inject_history(bp, existing_listing, marketplace)
                stats["linked"] += 1
                stats["snapshots_injected"] += injected
                logger.info(
                    "Linked existing listing for %s/%s (%d points injected)",
                    bp.marketplace_slug, bp.external_id, injected,
                )
                continue

            # 3. Extract brand from title (fall back to stored brand_name)
            brand_name = extract_brand(bp.title) or bp.brand_name
            brand = resolve_or_create_brand(brand_name) if brand_name else None

            # 4. Get current price from most recent data point
            current_price = _get_current_price(bp.raw_price_data)
            if current_price is None:
                logger.warning(
                    "No valid price in raw_price_data for %s — skipping",
                    bp.external_id,
                )
                stats["skipped"] += 1
                continue

            # 5. Compute lowest price ever from historical data
            lowest_price, lowest_date_str = _get_lowest_price(bp.raw_price_data)
            lowest_date = None
            if lowest_date_str:
                try:
                    from dateutil.parser import parse as parse_dt
                    lowest_date = parse_dt(lowest_date_str).date()
                except (ValueError, TypeError):
                    pass

            # 6. Generate unique slug
            slug = _generate_unique_slug(bp.title)

            # 7. Build marketplace URL
            url_map = BackfillConfig.product_url_map()
            external_url = url_map.get(
                bp.marketplace_slug, "",
            ).replace("{pid}", bp.external_id)
            if not external_url:
                external_url = bp.marketplace_url or ""

            # 8. Infer category from title (enrichment may refine later)
            from apps.products.category_mapper import match_by_keywords
            category = match_by_keywords(bp.title.lower())

            # 9. Create Product (is_lightweight=True)
            images = [bp.image_url] if bp.image_url else []
            product = Product.objects.create(
                slug=slug,
                title=bp.title,
                brand=brand,
                category=category,  # inferred from title; enrichment may correct
                description="",
                specs={},
                images=images,
                current_best_price=current_price,
                current_best_marketplace=bp.marketplace_slug,
                lowest_price_ever=lowest_price,
                lowest_price_date=lowest_date,
                is_lightweight=True,
                status=Product.Status.ACTIVE,
            )

            # 10. Compute discount_pct using max historical price as MRP proxy
            mrp = bp.max_price
            discount_pct = None
            if mrp and current_price and mrp > 0:
                pct = round((1 - float(current_price) / float(mrp)) * 100, 2)
                if pct > 0:
                    discount_pct = pct

            # 11. Create ProductListing
            listing = ProductListing.objects.create(
                product=product,
                marketplace=marketplace,
                external_id=bp.external_id,
                external_url=external_url,
                title=bp.title,
                current_price=current_price,
                mrp=mrp,
                discount_pct=discount_pct,
                in_stock=True,
                match_confidence=Decimal("1.00"),
                match_method="backfill_lightweight",
            )

            # 12. Inject price history
            injected = _inject_history(bp, listing, marketplace)

            # 13. Update BackfillProduct — link to listing
            bp.product_listing = listing
            bp.save(update_fields=["product_listing", "updated_at"])

            stats["created"] += 1
            stats["snapshots_injected"] += injected
            product_ids.append(str(product.id))

            if (i + 1) % 100 == 0:
                logger.info(
                    "  Lightweight: %d/%d — %d created, %d linked, "
                    "%d skipped, %d errors",
                    i + 1, len(candidates),
                    stats["created"], stats["linked"],
                    stats["skipped"], stats["errors"],
                )

        except Exception:
            logger.exception(
                "Error creating lightweight record for %s/%s",
                bp.marketplace_slug, bp.external_id,
            )
            stats["errors"] += 1

    # Queue Meilisearch sync for created products
    if product_ids:
        try:
            from apps.search.tasks import sync_products_to_meilisearch
            sync_products_to_meilisearch.delay(product_ids=product_ids)
            logger.info(
                "Queued Meilisearch sync for %d new lightweight products",
                len(product_ids),
            )
        except Exception:
            logger.warning(
                "Failed to queue Meilisearch sync — products still saved",
                exc_info=True,
            )

    logger.info("Lightweight creator complete: %s", stats)
    return stats


def _inject_history(
    bp: BackfillProduct,
    listing,
    marketplace,
) -> int:
    """Inject raw_price_data into price_snapshots via existing injector.

    Prices in raw_price_data are already in paisa (matching price_snapshots).
    No conversion needed.

    Returns:
        Number of rows injected.
    """
    if not bp.raw_price_data:
        return 0

    # Group by source for separate injection (dedup per source)
    by_source: dict[str, list[dict]] = {}
    for entry in bp.raw_price_data:
        source = entry.get("s", "backfill")
        by_source.setdefault(source, []).append({
            "time": entry["t"],
            "price": entry["p"],
        })

    total_injected = 0
    for source, points in by_source.items():
        count = inject_price_points(
            listing_id=str(listing.id),
            product_id=str(listing.product_id),
            marketplace_id=marketplace.id,
            price_points=points,
            source=source,
        )
        total_injected += count

    return total_injected
