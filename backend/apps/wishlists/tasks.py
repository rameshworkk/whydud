from celery import shared_task

@shared_task(queue="alerts")
def update_wishlist_prices() -> None:
    """Refresh current_price and price_change_pct for all wishlist items."""
    # TODO Sprint 3 Week 9
    pass
