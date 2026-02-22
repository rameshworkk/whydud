from celery import shared_task

@shared_task(queue="scraping")
def run_spider(marketplace_slug: str, spider_name: str, job_id: str) -> None:
    """Launch a Scrapy spider via subprocess for a marketplace."""
    # TODO Sprint 2 Week 4
    pass

@shared_task(queue="scraping")
def scrape_product_adhoc(url: str, marketplace_slug: str) -> None:
    """On-demand scrape triggered by user search."""
    # TODO Sprint 2 (P1)
    pass

@shared_task(queue="scraping")
def scrape_daily_prices() -> None:
    """Daily: scrape prices for all active listings."""
    # TODO Sprint 2 Week 4
    pass
