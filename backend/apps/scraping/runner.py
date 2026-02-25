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
    args = parser.parse_args()

    # Initialise Django before importing anything that touches models.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "whydud.settings.dev")
    import django
    django.setup()

    from scrapy.crawler import CrawlerProcess
    from apps.scraping.scrapy_settings import get_scrapy_settings

    settings = get_scrapy_settings()
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

    process.crawl(args.spider_name, **spider_kwargs)
    process.start()  # blocks until all spiders finish


if __name__ == "__main__":
    main()
