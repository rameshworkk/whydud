"""Tiered enrichment worker — routes products to Playwright or curl_cffi.

Three operating modes:
  1. **Batch** (Celery Beat every 15 min): ``enrich_batch`` processes N products
     by priority (P1 first, then P2, then P3).
  2. **On-demand** (user visits lightweight page): ``trigger_on_demand_enrichment``
     promotes to P0 and fires immediately.
  3. **Overnight** (management command): calls ``enrich_batch`` with large batch.

Enrichment routing:
  P0-P1 → Playwright via ``scrape_product_adhoc`` (existing spider infrastructure)
  P2-P3 → curl_cffi via ``enrich_via_http`` (uses curlffi_extractor)
         Falls back to Playwright after 3 curl_cffi failures.

Status lifecycle:
  pending → enriching → scraped (success) or failed (3 retries)

The ``_close_backfill_loop()`` hook in ProductPipeline handles the Playwright
path's status update. The curl_cffi path updates status directly here.
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.db.models import F
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core: single product enrichment (routes to Playwright or curl_cffi)
# ---------------------------------------------------------------------------

@shared_task(queue="scraping", rate_limit="30/m")
def enrich_single_product(backfill_product_id: str) -> dict:
    """Enrich a single BackfillProduct by routing to the appropriate method.

    P0-P1 → Playwright (full browser scrape via existing spider)
    P2-P3 → curl_cffi first (HTTP-only, 10x cheaper).
            After 3 curl_cffi failures, escalates to Playwright.

    Returns dict with status info for logging/monitoring.
    """
    from apps.pricing.models import BackfillProduct

    try:
        bp = BackfillProduct.objects.get(id=backfill_product_id)
    except BackfillProduct.DoesNotExist:
        return {"success": False, "error": "BackfillProduct not found"}

    if bp.scrape_status not in ("pending", "enriching"):
        return {"success": False, "error": f"Already {bp.scrape_status}"}

    if not bp.marketplace_url:
        bp.scrape_status = "failed"
        bp.error_message = "No marketplace URL"
        bp.save(update_fields=["scrape_status", "error_message"])
        return {"success": False, "error": "No marketplace URL"}

    # Mark as enriching
    bp.scrape_status = "enriching"
    bp.enrichment_queued_at = timezone.now()
    bp.save(update_fields=["scrape_status", "enrichment_queued_at"])

    if bp.enrichment_priority <= 1:
        # P0-P1: Always Playwright — need full data (images, variants, offers)
        return _dispatch_playwright(bp)
    else:
        # P2-P3: Try curl_cffi first (works for Amazon ~55%, Flipkart sometimes)
        # After 3 failures, escalates to Playwright automatically
        bp.enrichment_method = "curl_cffi"
        bp.save(update_fields=["enrichment_method"])

        enrich_via_http.delay(str(bp.id))

        logger.info(
            "Enrichment queued (curl_cffi): %s/%s",
            bp.marketplace_slug, bp.external_id,
        )
        return {
            "success": True,
            "method": "curl_cffi",
            "external_id": bp.external_id,
        }


def _dispatch_playwright(bp) -> dict:
    """Send a BackfillProduct to Playwright enrichment."""
    bp.enrichment_method = "playwright"
    bp.save(update_fields=["enrichment_method"])

    from apps.scraping.tasks import scrape_product_adhoc
    scrape_product_adhoc.delay(bp.marketplace_url, bp.marketplace_slug)

    logger.info(
        "Enrichment queued (Playwright): %s/%s",
        bp.marketplace_slug, bp.external_id,
    )
    return {
        "success": True,
        "method": "playwright",
        "external_id": bp.external_id,
    }


# ---------------------------------------------------------------------------
# curl_cffi enrichment (lightweight HTTP-only, no browser)
# ---------------------------------------------------------------------------

@shared_task(queue="scraping", rate_limit="60/m")
def enrich_via_http(backfill_product_id: str) -> dict:
    """Lightweight enrichment via curl_cffi — no browser needed.

    Calls the curl_cffi extractor (BF-12) to fetch product data from the
    marketplace page using TLS fingerprint impersonation. Updates the
    ProductListing and Product records directly.

    Uses the curl_cffi extractor (BF-12) to extract data via TLS
    fingerprint impersonation — no browser needed.
    """
    from apps.pricing.models import BackfillProduct
    from apps.products.models import Product, ProductListing

    try:
        bp = BackfillProduct.objects.select_related(
            "product_listing__product",
            "product_listing__marketplace",
        ).get(id=backfill_product_id)
    except BackfillProduct.DoesNotExist:
        return {"success": False, "error": "BackfillProduct not found"}

    try:
        from apps.pricing.backfill.curlffi_extractor import extract_product_data
    except ImportError:
        # BF-12 not built yet — mark as pending to retry later
        bp.scrape_status = "pending"
        bp.enrichment_method = "pending"
        bp.save(update_fields=["scrape_status", "enrichment_method"])
        return {"success": False, "error": "curlffi_extractor not available yet"}

    data = extract_product_data(bp.marketplace_url, bp.marketplace_slug)

    if not data or not data.get("title"):
        bp.retry_count = (bp.retry_count or 0) + 1
        if bp.retry_count >= 3:
            # Escalate to Playwright instead of giving up
            logger.info(
                "curl_cffi failed 3x, escalating to Playwright: %s/%s",
                bp.marketplace_slug, bp.external_id,
            )
            bp.scrape_status = "enriching"
            bp.error_message = ""
            bp.save(update_fields=["scrape_status", "error_message", "retry_count"])
            return _dispatch_playwright(bp)
        else:
            bp.scrape_status = "pending"
            bp.error_message = ""
        bp.save(update_fields=["scrape_status", "error_message", "retry_count"])
        return {
            "success": False,
            "error": "Extraction failed",
            "retry_count": bp.retry_count,
        }

    # Update ProductListing with extracted data
    listing = bp.product_listing
    if listing:
        listing_updates = {"last_scraped_at": timezone.now()}
        field_map = {
            "title": "title",
            "price": "current_price",
            "mrp": "mrp",
            "rating": "rating",
            "review_count": "review_count",
            "in_stock": "in_stock",
        }
        for data_key, model_field in field_map.items():
            if data.get(data_key) is not None:
                listing_updates[model_field] = data[data_key]

        # Extended listing fields from curl_cffi
        if data.get("about_bullets"):
            listing_updates["about_bullets"] = data["about_bullets"]

        ProductListing.objects.filter(id=listing.id).update(**listing_updates)

    # Update Product — upgrade from lightweight
    product = listing.product if listing else None
    if product:
        product_updates = {"is_lightweight": False}
        if data.get("rating") and not product.avg_rating:
            product_updates["avg_rating"] = data["rating"]
        if data.get("review_count") and not product.total_reviews:
            product_updates["total_reviews"] = data["review_count"]
        # Specs — merge new specs into existing
        if data.get("specs"):
            existing = product.specs or {}
            if not existing or len(data["specs"]) > len(existing):
                product_updates["specs"] = {**existing, **data["specs"]}
        # Description — fill if empty
        if data.get("description") and not product.description:
            product_updates["description"] = data["description"][:5000]
        # Images — update if we have more
        if data.get("images") and (
            not product.images or len(data["images"]) > len(product.images or [])
        ):
            product_updates["images"] = data["images"]
        # Physical fields — extract from specs if available
        specs = data.get("specs") or {}
        _spec_map = {
            "country_of_origin": (["Country of Origin", "country of origin"], 200),
            "manufacturer": (["Manufacturer", "manufacturer"], 500),
            "model_number": (["Item model number", "Model Number", "Model Name"], 200),
            "weight": (["Item Weight", "Product Weight", "Weight"], 100),
            "dimensions": (["Product Dimensions", "Item Dimensions", "Dimensions"], 200),
        }
        for field_name, (spec_keys, max_len) in _spec_map.items():
            if not getattr(product, field_name, ""):
                for key in spec_keys:
                    if specs.get(key):
                        product_updates[field_name] = specs[key][:max_len]
                        break

        # Category — assign from title if still uncategorized
        if not product.category_id or (
            product.category and product.category.slug == "uncategorized"
        ):
            from apps.products.category_mapper import match_by_keywords
            search_text = (data.get("title") or bp.title or "").lower()
            if data.get("breadcrumbs"):
                search_text = " ".join(data["breadcrumbs"]) + " " + search_text
            inferred_cat = match_by_keywords(search_text)
            if inferred_cat:
                product_updates["category_id"] = inferred_cat.id

        Product.objects.filter(id=product.id).update(**product_updates)

    # Mark enrichment complete
    bp.scrape_status = "scraped"
    bp.save(update_fields=["scrape_status"])

    logger.info(
        "curl_cffi enrichment complete: %s/%s",
        bp.marketplace_slug, bp.external_id,
    )

    # Chain review scraping if this product is in the top 100K
    if bp.review_status == "pending" and listing:
        queue_review_scraping.delay(
            listing_id=str(listing.id),
            marketplace_slug=bp.marketplace_slug,
            external_id=bp.external_id,
        )

    return {"success": True, "external_id": bp.external_id}


# ---------------------------------------------------------------------------
# Review completion handler + DudScore chain (BF-13)
# ---------------------------------------------------------------------------

@shared_task(queue="scoring")
def post_review_enrichment(product_id: str) -> dict:
    """Finalize review enrichment for a backfill product.

    Called after review spider finishes for this product:
      1. Count reviews, update Product aggregate fields
      2. Update BackfillProduct.review_status = 'scraped'
      3. Run fake review detection
      4. Trigger DudScore recalculation

    Returns summary dict.
    """
    from django.db.models import Avg, Count

    from apps.pricing.models import BackfillProduct
    from apps.products.models import Product
    from apps.reviews.models import Review

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        logger.error("post_review_enrichment: product %s not found", product_id)
        return {"success": False, "error": "Product not found"}

    # 1. Count and aggregate reviews
    review_stats = Review.objects.filter(product_id=product_id).aggregate(
        count=Count("id"),
        avg_rating=Avg("rating"),
    )
    review_count = review_stats["count"] or 0
    avg_rating = review_stats["avg_rating"]

    Product.objects.filter(id=product_id).update(
        total_reviews=review_count,
        avg_rating=avg_rating,
    )

    # 2. Update BackfillProduct
    listing = product.listings.select_related("marketplace").first()
    if listing:
        BackfillProduct.objects.filter(
            marketplace_slug=listing.marketplace.slug,
            external_id=listing.external_id,
            review_status="scraping",
        ).update(
            review_status="scraped",
            review_count_scraped=review_count,
        )

    # 3. Fake review detection
    try:
        from apps.reviews.tasks import detect_fake_reviews
        detect_fake_reviews.delay(str(product_id))
    except ImportError:
        logger.debug("detect_fake_reviews task not available")

    # 4. DudScore calculation
    try:
        from apps.scoring.tasks import compute_dudscore
        compute_dudscore.delay(str(product_id))
        logger.info(
            "post_review_enrichment: product=%s reviews=%d avg_rating=%s — DudScore triggered",
            product_id, review_count, avg_rating,
        )
    except ImportError:
        logger.warning("compute_dudscore task not found")

    return {
        "success": True,
        "product_id": str(product_id),
        "review_count": review_count,
        "avg_rating": float(avg_rating) if avg_rating else None,
    }


@shared_task(queue="default")
def check_review_completion() -> dict:
    """Find products where review spider has finished but status is still 'scraping'.

    Triggers ``post_review_enrichment`` for each completed product.
    Times out products stuck in 'scraping' for >3 hours.

    Scheduled via Celery Beat every 15 minutes.
    """
    from datetime import timedelta

    from apps.pricing.models import BackfillProduct
    from apps.reviews.models import Review

    scraping = BackfillProduct.objects.filter(
        review_status="scraping",
    ).select_related("product_listing")

    completed = 0
    timed_out = 0

    for bp in scraping:
        if not bp.product_listing:
            continue

        product_id = bp.product_listing.product_id
        review_count = Review.objects.filter(product_id=product_id).count()

        if review_count > 0:
            post_review_enrichment.delay(str(product_id))
            completed += 1
        elif bp.enrichment_queued_at:
            if timezone.now() - bp.enrichment_queued_at > timedelta(hours=3):
                bp.review_status = "failed"
                bp.error_message = "Review scraping timed out"
                bp.save(update_fields=["review_status", "error_message"])
                timed_out += 1

    if completed or timed_out:
        logger.info(
            "check_review_completion: %d completed, %d timed out",
            completed, timed_out,
        )

    return {"completed": completed, "timed_out": timed_out}


# ---------------------------------------------------------------------------
# Batch enrichment (Celery Beat entry point)
# ---------------------------------------------------------------------------

@shared_task(queue="scraping")
def enrich_batch(batch_size: int = 100) -> dict:
    """Process a batch of pending products by priority.

    Called by Celery Beat every 15 minutes. Dispatches individual
    ``enrich_single_product`` tasks for each product.

    Order: P0 first (on-demand), then P1, P2, P3, oldest first within tier.
    """
    from apps.pricing.models import BackfillProduct

    products = list(
        BackfillProduct.objects.filter(
            scrape_status="pending",
        )
        .exclude(marketplace_url="")
        .order_by("enrichment_priority", "created_at")
        .values_list("id", flat=True)[:batch_size]
    )

    for bp_id in products:
        enrich_single_product.delay(str(bp_id))

    logger.info("Enrichment batch dispatched: %d products", len(products))
    return {"dispatched": len(products), "batch_size": batch_size}


# ---------------------------------------------------------------------------
# On-demand enrichment (user visits lightweight product page)
# ---------------------------------------------------------------------------

def trigger_on_demand_enrichment(
    external_id: str, marketplace_slug: str
) -> bool:
    """Trigger immediate enrichment when a user visits a lightweight product.

    Called from ProductDetailView. Promotes the product to P0 (highest
    priority) and fires the enrichment task with Celery priority 9.

    Returns True if an enrichment was triggered, False otherwise.
    """
    from apps.pricing.models import BackfillProduct

    bp = BackfillProduct.objects.filter(
        external_id=external_id,
        marketplace_slug=marketplace_slug,
        scrape_status="pending",
    ).first()

    if not bp:
        return False

    bp.enrichment_priority = 0
    bp.save(update_fields=["enrichment_priority"])

    enrich_single_product.apply_async(
        args=[str(bp.id)],
        priority=9,  # highest Celery priority
    )

    logger.info(
        "On-demand enrichment triggered: %s/%s",
        marketplace_slug, external_id,
    )
    return True


# ---------------------------------------------------------------------------
# Review scraping chain (after enrichment completes)
# ---------------------------------------------------------------------------

@shared_task(queue="scraping", rate_limit="20/m")
def queue_review_scraping(
    listing_id: str, marketplace_slug: str, external_id: str
) -> dict:
    """Chain review scraping after detail enrichment completes.

    Uses existing review spider infrastructure. Called from:
    - ``_close_backfill_loop()`` in ProductPipeline (Playwright path)
    - ``enrich_via_http()`` (curl_cffi path)
    """
    from apps.pricing.models import BackfillProduct

    # Mark as scraping
    BackfillProduct.objects.filter(
        marketplace_slug=marketplace_slug,
        external_id=external_id,
        review_status="pending",
    ).update(review_status="scraping")

    if marketplace_slug in ("amazon-in", "amazon_in"):
        from apps.scraping.tasks import run_review_spider
        run_review_spider.delay("amazon-in", product_external_ids=[external_id])
        logger.info("Review spider queued for amazon-in: %s", external_id)
    elif marketplace_slug == "flipkart":
        from apps.scraping.tasks import run_review_spider
        run_review_spider.delay("flipkart", product_external_ids=[external_id])
        logger.info("Review spider queued for flipkart: %s", external_id)
    else:
        # No review spider for this marketplace — skip
        BackfillProduct.objects.filter(
            marketplace_slug=marketplace_slug,
            external_id=external_id,
        ).update(review_status="skip")
        return {
            "success": False,
            "error": f"No review spider for {marketplace_slug}",
        }

    return {
        "success": True,
        "marketplace": marketplace_slug,
        "external_id": external_id,
    }


# ---------------------------------------------------------------------------
# Stale enrichment cleanup (hourly)
# ---------------------------------------------------------------------------

@shared_task(queue="default")
def cleanup_stale_enrichments() -> dict:
    """Reset enrichments stuck in 'enriching' state for 2+ hours.

    Products with retry_count < 3 get reset to 'pending' for retry.
    Products with retry_count >= 3 are marked as 'failed'.

    Scheduled via Celery Beat hourly.
    """
    from datetime import timedelta

    from apps.pricing.models import BackfillProduct

    cutoff = timezone.now() - timedelta(hours=2)

    # Retry: reset to pending and increment retry count
    retried = BackfillProduct.objects.filter(
        scrape_status="enriching",
        enrichment_queued_at__lt=cutoff,
        retry_count__lt=3,
    ).update(
        scrape_status="pending",
        retry_count=F("retry_count") + 1,
    )

    # Exhausted: mark as failed
    failed = BackfillProduct.objects.filter(
        scrape_status="enriching",
        enrichment_queued_at__lt=cutoff,
        retry_count__gte=3,
    ).update(
        scrape_status="failed",
        error_message="Enrichment timed out after retries",
    )

    logger.info(
        "Stale enrichment cleanup: %d retried, %d failed", retried, failed
    )
    return {"retried": retried, "failed": failed}
