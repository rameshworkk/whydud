"""Celery tasks for pricing app."""
import logging
from decimal import Decimal

from celery import chain, shared_task
from django.db.models import Min
from django.utils import timezone

logger = logging.getLogger(__name__)


def _format_price(paisa: Decimal) -> str:
    """Format paisa value as ₹X,XX,XXX (Indian numbering)."""
    rupees = int(paisa / 100)
    s = str(rupees)
    if len(s) <= 3:
        return f"₹{s}"
    # Indian grouping: last 3 digits, then groups of 2
    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while rest:
        groups.append(rest[-2:])
        rest = rest[:-2]
    groups.reverse()
    return f"₹{','.join(groups)},{last3}"


@shared_task(queue="alerts")
def check_price_alerts() -> dict:
    """Check all active price alerts and trigger those whose target is met.

    For each active, un-triggered alert:
      1. Find the current best price (marketplace-specific or global)
      2. Update alert.current_price with latest price
      3. If current price <= target price: trigger the alert and send notification

    Returns a summary dict with counts.
    """
    from apps.accounts.tasks import create_notification
    from apps.pricing.models import PriceAlert
    from apps.products.models import ProductListing

    now = timezone.now()
    checked = 0
    triggered = 0
    errors = 0

    active_alerts = (
        PriceAlert.objects
        .filter(is_active=True, is_triggered=False)
        .select_related("product", "marketplace")
    )

    for alert in active_alerts.iterator(chunk_size=500):
        checked += 1
        try:
            # Build query for current best price
            listings_qs = ProductListing.objects.filter(
                product=alert.product,
                in_stock=True,
                current_price__isnull=False,
            )
            if alert.marketplace_id:
                listings_qs = listings_qs.filter(marketplace=alert.marketplace)

            best = listings_qs.aggregate(best_price=Min("current_price"))
            current_price = best["best_price"]

            if current_price is None:
                continue

            # Always update current_price on the alert for tracking
            alert.current_price = current_price
            update_fields = ["current_price", "updated_at"]

            if current_price <= alert.target_price:
                # Find which marketplace has this price
                best_listing = (
                    listings_qs
                    .filter(current_price=current_price)
                    .select_related("marketplace")
                    .first()
                )
                marketplace_name = (
                    best_listing.marketplace.name if best_listing else ""
                )
                marketplace_slug = (
                    best_listing.marketplace.slug if best_listing else ""
                )

                alert.is_triggered = True
                alert.triggered_at = now
                alert.triggered_price = current_price
                alert.triggered_marketplace = marketplace_slug
                alert.notification_sent = True
                alert.is_active = False
                update_fields += [
                    "is_triggered",
                    "triggered_at",
                    "triggered_price",
                    "triggered_marketplace",
                    "notification_sent",
                    "is_active",
                ]

                alert.save(update_fields=update_fields)
                triggered += 1

                # Build notification
                price_display = _format_price(current_price)
                marketplace_suffix = (
                    f" on {marketplace_name}" if marketplace_name else ""
                )

                create_notification.delay(
                    user_id=str(alert.user_id),
                    type="price_alert",
                    title=f"Price alert! {alert.product.title} is now {price_display}{marketplace_suffix}",
                    body=(
                        f"The price dropped to {price_display}, "
                        f"which is at or below your target of {_format_price(alert.target_price)}."
                    ),
                    action_url=f"/product/{alert.product.slug}",
                    action_label="Buy Now",
                    entity_type="product",
                    entity_id=str(alert.product_id),
                    metadata={
                        "alert_id": str(alert.pk),
                        "target_price": str(alert.target_price),
                        "triggered_price": str(current_price),
                        "marketplace": marketplace_slug,
                    },
                )
            else:
                alert.save(update_fields=update_fields)

        except Exception:
            errors += 1
            logger.exception(
                "check_price_alerts: error processing alert %s", alert.pk
            )

    summary = {"checked": checked, "triggered": triggered, "errors": errors}
    if triggered:
        logger.info("check_price_alerts: %s", summary)
    return summary


@shared_task(queue="scraping")
def snapshot_product_prices(product_id: str) -> None:
    """Record current price to price_snapshots hypertable."""
    # TODO Sprint 2 Week 5
    pass


# ── Backfill tasks ───────────────────────────────────────────────


@shared_task(queue="scraping", bind=True, max_retries=2, soft_time_limit=7200)
def backfill_existing_listings(
    self,
    marketplace_slug: str | None = None,
    limit: int = 2000,
) -> dict:
    """Phase 0: Backfill existing ProductListings via BuyHatke."""
    import asyncio

    from apps.pricing.backfill.phase0_existing import (
        backfill_existing_listings as _run,
    )

    return asyncio.run(_run(marketplace_slug=marketplace_slug, limit=limit))


@shared_task(queue="scraping", bind=True, max_retries=1, soft_time_limit=None, time_limit=None)
def run_phase1_discover(
    self,
    sitemap_start: int = 1,
    sitemap_end: int = 5,
    filter_electronics: bool = True,
    max_products: int | None = None,
    proxy_mode: str = "auto",
) -> dict:
    """Phase 1: Discover products from PH sitemaps."""
    import asyncio

    from apps.pricing.backfill.phase1_discover import discover_from_sitemaps

    return asyncio.run(
        discover_from_sitemaps(
            sitemap_start=sitemap_start,
            sitemap_end=sitemap_end,
            filter_electronics=filter_electronics,
            max_products=max_products,
            proxy_mode=proxy_mode,
        )
    )


@shared_task(queue="scraping", bind=True, max_retries=1, soft_time_limit=None, time_limit=None)
def run_phase2_buyhatke(
    self,
    batch_size: int = 5000,
    marketplace_slug: str | None = None,
    delay: float | None = None,
    repeat: bool = False,
    category_names: list[str] | None = None,
    proxy_mode: str = "auto",
) -> dict:
    """Phase 2: BuyHatke bulk price history fill for discovered products.

    Safe to dispatch multiple times concurrently — each task claims its own
    batch via SELECT ... FOR UPDATE SKIP LOCKED.

    If repeat=True, keeps claiming new batches until no items remain.
    If category_names provided, only processes products with matching category_name.
    proxy_mode: "auto" (default), "proxy" (always proxy), "direct" (no proxy).
    """
    import asyncio

    from apps.pricing.backfill.phase2_buyhatke import buyhatke_bulk_fill

    all_stats = {"total": 0, "filled": 0, "injected": 0, "empty": 0, "failed": 0, "points": 0, "rounds": 0}

    while True:
        result = asyncio.run(
            buyhatke_bulk_fill(
                batch_size=batch_size,
                marketplace_slug=marketplace_slug,
                delay=delay,
                category_names=category_names,
                proxy_mode=proxy_mode,
            )
        )
        all_stats["rounds"] += 1
        for key in ("total", "filled", "injected", "empty", "failed", "points"):
            all_stats[key] += result.get(key, 0)

        if not repeat or result.get("total", 0) == 0:
            break

        logger.info("Phase 2 repeat: round %d done (%d filled so far), claiming next batch...",
                     all_stats["rounds"], all_stats["filled"])

    return all_stats


@shared_task(queue="scraping", bind=True, max_retries=1, soft_time_limit=None, time_limit=None)
def run_phase3_extend(
    self,
    limit: int = 5000,
    marketplace_slug: str | None = None,
    delay: float | None = None,
    repeat: bool = False,
    category_names: list[str] | None = None,
    include_discovered: bool = False,
    proxy_mode: str = "auto",
) -> dict:
    """Phase 3: Extend top products with PH deep history.

    Safe to dispatch multiple times concurrently — each task claims its own
    batch via SELECT ... FOR UPDATE SKIP LOCKED.

    If repeat=True, keeps claiming new batches until no items remain.
    If category_names provided, only processes products with matching category_name.
    If include_discovered=True, also processes DISCOVERED products (skips bh-fill).
    proxy_mode: "auto" (default), "proxy" (always proxy), "direct" (no proxy).
    """
    import asyncio
    import secrets

    from apps.pricing.backfill.phase3_extend import extend_with_pricehistory

    # Generate a stable tag for this task so all rounds + waves share the same ID
    worker_tag = self.request.id[:6] if self.request.id else secrets.token_hex(3)

    all_stats = {
        "total": 0, "extended": 0, "injected": 0, "token_failed": 0,
        "api_failed": 0, "rate_limited": 0, "points": 0, "rounds": 0,
        "worker_tag": worker_tag,
    }

    while True:
        result = asyncio.run(
            extend_with_pricehistory(
                limit=limit,
                marketplace_slug=marketplace_slug,
                delay=delay,
                category_names=category_names,
                include_discovered=include_discovered,
                proxy_mode=proxy_mode,
                worker_tag=worker_tag,
            )
        )
        all_stats["rounds"] += 1
        for key in ("total", "extended", "injected", "token_failed", "api_failed", "rate_limited", "points"):
            all_stats[key] += result.get(key, 0)

        # Only stop repeat if the worker explicitly requested stop
        # (IP burned without proxy). Minor rate limiting with proxy is normal.
        if result.get("stop_requested", False):
            logger.warning("Phase 3 [W-%s]: stopping repeat — IP burned / stop requested "
                           "(%d rate-limited items)", worker_tag, result.get("rate_limited", 0))
            break

        if not repeat or result.get("total", 0) == 0:
            break

        logger.info("Phase 3 [W-%s] repeat: round %d done (%d extended so far), claiming next batch...",
                     worker_tag, all_stats["rounds"], all_stats["extended"])

    return all_stats


@shared_task(queue="scraping", soft_time_limit=None, time_limit=None)
def scrape_backfill_products_task(
    batch_size: int = 50,
    marketplace_slug: str | None = None,
    limit: int | None = None,
    auto_inject: bool = True,
) -> dict:
    """Targeted scrape of BackfillProduct ASINs/FPIDs via marketplace spiders."""
    from apps.pricing.backfill.targeted_scrape import scrape_backfill_products

    return scrape_backfill_products(
        batch_size=batch_size,
        marketplace_slug=marketplace_slug,
        limit=limit,
        auto_inject=auto_inject,
    )


@shared_task(queue="scraping", soft_time_limit=None, time_limit=None)
def run_phase4_inject(
    batch_size: int = 5000,
    marketplace_slug: str | None = None,
) -> dict:
    """Phase 4: Inject cached price data after spider enrichment."""
    from apps.pricing.backfill.phase4_inject import inject_cached_data

    return inject_cached_data(
        batch_size=batch_size,
        marketplace_slug=marketplace_slug,
    )


@shared_task(queue="default")
def refresh_price_daily_aggregate() -> dict:
    """Refresh the price_daily continuous aggregate after backfill."""
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("CALL refresh_continuous_aggregate('price_daily', NULL, NULL);")
    return {"success": True}


# ── Full pipeline ────────────────────────────────────────────────


@shared_task(queue="scraping", bind=True)
def run_full_backfill_pipeline(
    self,
    sitemap_start: int = 1,
    sitemap_end: int = 115,
    filter_electronics: bool = False,
    batch_size: int = 5000,
) -> dict:
    """Run the complete backfill pipeline as a Celery chain.

    Phase 1: Discover products from PH sitemaps
    Phase 2: BuyHatke bulk price history fill
    Phase 3: PH deep history extension for top products
    Phase 4: Inject cached price data
    Phase 5: Refresh price_daily aggregate

    Each phase runs sequentially. Monitor progress via Flower
    or `manage.py backfill_prices status`.
    """
    pipeline = chain(
        run_phase1_discover.si(
            sitemap_start=sitemap_start,
            sitemap_end=sitemap_end,
            filter_electronics=filter_electronics,
        ),
        run_phase2_buyhatke.si(batch_size=batch_size),
        run_phase3_extend.si(limit=batch_size),
        run_phase4_inject.si(batch_size=batch_size),
        refresh_price_daily_aggregate.si(),
    )
    result = pipeline.apply_async()
    logger.info(
        "Full backfill pipeline started: chain_id=%s, sitemaps=%d–%d",
        result.id,
        sitemap_start,
        sitemap_end,
    )
    return {
        "status": "pipeline_started",
        "chain_id": result.id,
        "phases": ["discover", "bh-fill", "ph-extend", "inject", "refresh-aggregate"],
        "sitemap_range": f"{sitemap_start}–{sitemap_end}",
        "filter_electronics": filter_electronics,
    }
