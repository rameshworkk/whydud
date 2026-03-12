"""Phase 1: Discover products from PriceHistory.app sitemaps.

Flow:
  1. Parse sitemap XML files concurrently → get product URLs + ph_codes
  2. Filter by keyword (electronics/tech only)
  3. Fetch each product's HTML page concurrently (semaphore-limited)
  4. Extract ASIN/FSID + marketplace from JSON-LD
  5. Bulk-create BackfillProduct records with status='discovered'

This gives us a catalog of products with their marketplace IDs,
ready for Phase 2 (BuyHatke bulk fill).

Usage::

    python manage.py backfill_prices discover --start 1 --end 5
    python manage.py backfill_prices discover --start 1 --end 1 --limit 50
"""
from __future__ import annotations

import asyncio
import logging

from asgiref.sync import sync_to_async

from apps.pricing.backfill.config import BackfillConfig
from apps.pricing.backfill.ph_client import PHClient
from apps.pricing.models import BackfillProduct

logger = logging.getLogger(__name__)


def _get_existing_codes(ph_codes: list[str]) -> set[str]:
    """Synchronous ORM query for existing ph_codes."""
    return set(
        BackfillProduct.objects.filter(
            ph_code__in=ph_codes
        ).values_list("ph_code", flat=True)
    )


def _bulk_create_backfill_products(records: list[dict]) -> int:
    """Bulk-create BackfillProduct records. Returns count created."""
    from apps.pricing.backfill.prioritizer import infer_category_from_title

    objects = []
    for r in records:
        title = r["title"][:1000]
        objects.append(BackfillProduct(
            ph_code=r["ph_code"],
            ph_url=r["ph_url"],
            marketplace_slug=r["marketplace_slug"],
            external_id=r["external_id"],
            title=title,
            brand_name=r["brand_name"][:200],
            image_url=r["image_url"][:500],
            current_price=r["current_price"] or None,
            category_name=infer_category_from_title(title),
            status=BackfillProduct.Status.DISCOVERED,
        ))

    created = BackfillProduct.objects.bulk_create(objects, ignore_conflicts=True)
    return len(created)


async def discover_from_sitemaps(
    sitemap_start: int = 1,
    sitemap_end: int = 5,
    filter_electronics: bool = False,
    max_products: int | None = None,
    delay: float | None = None,
    proxy_mode: str = "auto",
) -> dict:
    """Phase 1: Parse sitemaps → fetch HTML → extract ASINs.

    Sitemaps are parsed concurrently, and HTML pages are fetched
    concurrently via asyncio.gather() with semaphore-based rate limiting.

    Args:
        sitemap_start: First sitemap index (1-based, out of 343).
        sitemap_end: Last sitemap index (inclusive).
        filter_electronics: Only keep products matching electronics keywords.
        max_products: Cap total products to process (None = unlimited).
        delay: Override PH HTML request delay.
    """
    stats = {
        "sitemaps_parsed": 0,
        "urls_found": 0,
        "after_filter": 0,
        "html_fetched": 0,
        "asin_extracted": 0,
        "created": 0,
        "skipped_dupe": 0,
        "failed": 0,
    }

    async with PHClient(delay=delay, proxy_mode=proxy_mode) as client:
        # Step 1: Get sitemap index
        all_sitemaps = await client.fetch_sitemap_index()
        target_sitemaps = all_sitemaps[sitemap_start - 1 : sitemap_end]
        logger.info(
            "Phase 1: processing sitemaps %d–%d (%d files)",
            sitemap_start,
            sitemap_end,
            len(target_sitemaps),
        )

        # Step 2: Parse sitemaps concurrently → collect product URLs
        all_products: list[dict] = []

        async def _parse_one_sitemap(sitemap_url):
            products = await client.parse_sitemap(sitemap_url)
            logger.info("  Parsed %s: %d products", sitemap_url, len(products))
            return products

        sitemap_results = await asyncio.gather(
            *[_parse_one_sitemap(url) for url in target_sitemaps]
        )
        for products in sitemap_results:
            stats["sitemaps_parsed"] += 1
            stats["urls_found"] += len(products)
            all_products.extend(products)

        # Step 3: Filter by keywords
        if filter_electronics:
            keywords = BackfillConfig.electronics_keywords()
            filtered = []
            for p in all_products:
                slug_lower = p["slug"].lower()
                if any(kw in slug_lower for kw in keywords):
                    filtered.append(p)
            logger.info(
                "  Filtered: %d → %d electronics products",
                len(all_products),
                len(filtered),
            )
            all_products = filtered

        stats["after_filter"] = len(all_products)

        if max_products and len(all_products) > max_products:
            all_products = all_products[:max_products]

        # Step 4: Check which ph_codes already exist (skip dupes)
        existing_codes = await sync_to_async(_get_existing_codes)(
            [p["ph_code"] for p in all_products]
        )
        new_products = [p for p in all_products if p["ph_code"] not in existing_codes]
        stats["skipped_dupe"] = len(all_products) - len(new_products)
        logger.info(
            "  New products: %d (skipping %d existing)",
            len(new_products),
            stats["skipped_dupe"],
        )

        # Step 5: Fetch HTML concurrently for each new product → extract ASIN/FSID
        pending_records: list[dict] = []
        _done_count = 0

        async def _fetch_one(product):
            nonlocal _done_count
            code = product["ph_code"]
            try:
                meta = await client.fetch_page_metadata(code)
                stats["html_fetched"] += 1

                external_id = meta.get("external_id", "")
                marketplace_slug = meta.get("marketplace_slug", "")

                if not external_id or not marketplace_slug:
                    stats["failed"] += 1
                else:
                    stats["asin_extracted"] += 1
                    pending_records.append({
                        "ph_code": code,
                        "ph_url": product.get("ph_url", ""),
                        "marketplace_slug": marketplace_slug,
                        "external_id": external_id,
                        "title": meta.get("title", ""),
                        "brand_name": meta.get("brand_name", ""),
                        "image_url": meta.get("image_url", ""),
                        "current_price": meta.get("current_price"),
                    })

            except Exception as e:
                stats["failed"] += 1
                logger.debug("  %s: %s", code, e)

            _done_count += 1
            if _done_count % 200 == 0:
                logger.info(
                    "  Progress: %d/%d — %d ASINs extracted, %d failed",
                    _done_count, len(new_products),
                    stats["asin_extracted"], stats["failed"],
                )

        # Fire all HTML fetches concurrently — PHClient semaphore limits in-flight
        await asyncio.gather(*[_fetch_one(p) for p in new_products])

        # Step 6: Bulk-create records in batches of 1000
        if pending_records:
            total_created = 0
            for i in range(0, len(pending_records), 1000):
                batch = pending_records[i : i + 1000]
                count = await sync_to_async(_bulk_create_backfill_products)(batch)
                total_created += count
            stats["created"] = total_created
            logger.info("  Created %d BackfillProduct records", total_created)

    logger.info("Phase 1 complete: %s", stats)
    return stats
