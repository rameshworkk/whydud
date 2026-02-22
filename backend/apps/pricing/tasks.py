from celery import shared_task

@shared_task(queue="alerts")
def check_price_alerts() -> None:
    """Run every 4 hours. Check all active price alerts and send notifications."""
    # TODO Sprint 3 Week 9
    pass

@shared_task(queue="scraping")
def snapshot_product_prices(product_id: str) -> None:
    """Record current price to price_snapshots hypertable."""
    # TODO Sprint 2 Week 5
    pass
