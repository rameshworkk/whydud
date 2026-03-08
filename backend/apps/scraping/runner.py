"""Standalone Scrapy spider runner — invoked via subprocess from Celery tasks.

This avoids Twisted reactor restart issues when running Scrapy from within
a Celery worker process.

Usage:
    python -m apps.scraping.runner <spider_name> [--job-id UUID] [--urls url1,url2]
"""
import argparse
import os
import sys

# Ensure backend/ is on sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Whydud Scrapy spider")
    parser.add_argument("spider_name", help="Spider name (e.g., amazon_in)")
    parser.add_argument("--job-id", default=None, help="ScraperJob UUID")
    parser.add_argument("--urls", default=None, help="Comma-separated category URLs")
    parser.add_argument("--max-pages", default=None, help="Max listing pages per category")
    parser.add_argument("--save-html", action="store_true", help="Save raw HTML for debugging")
    parser.add_argument("--max-review-pages", default=None, help="Max review pages per product (review spiders)")
    parser.add_argument("--external-ids", default=None, help="Comma-separated external IDs to filter (review spiders)")
    parser.add_argument("--proxy-list", default=None, help="Comma-separated proxy URLs (overrides SCRAPING_PROXY_LIST env var)")
    args = parser.parse_args()

    # Load .env so DB credentials etc. are available in subprocess context.
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BACKEND_DIR, ".env"))

    # Initialise Django before importing anything that touches models.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "whydud.settings.dev")
    # Allow synchronous ORM calls from Scrapy's async Playwright reactor.
    # Safe here because the runner is a standalone subprocess, not a web server.
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    import django
    django.setup()

    from scrapy.crawler import CrawlerProcess
    from apps.scraping.scrapy_settings import get_scrapy_settings

    settings = get_scrapy_settings()

    # CLI proxy list override — passed to middleware via Scrapy settings
    if args.proxy_list:
        settings["PROXY_LIST_OVERRIDE"] = args.proxy_list

    process = CrawlerProcess(settings)

    spider_kwargs: dict[str, str] = {}
    if args.job_id:
        spider_kwargs["job_id"] = args.job_id
    if args.urls:
        spider_kwargs["category_urls"] = args.urls
    if args.max_pages:
        spider_kwargs["max_pages"] = args.max_pages
    if args.save_html:
        spider_kwargs["save_html"] = "1"
    if args.max_review_pages:
        spider_kwargs["max_review_pages"] = args.max_review_pages
    if args.external_ids:
        spider_kwargs["external_ids"] = args.external_ids

    process.crawl(args.spider_name, **spider_kwargs)
    process.start()  # blocks until all spiders finish


if __name__ == "__main__":
    main()
