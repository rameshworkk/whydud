"""Standalone test runner for the Meesho spider.

Runs the spider WITHOUT Django/DB — outputs scraped items to JSON file.
Usage: python test_spider.py [--urls url1,url2] [--max-pages N]
"""
import argparse
import json
import os
import sys
import time

# ---------------------------------------------------------------------------
# Mock Django so imports don't break (spider code lives under apps.scraping)
# ---------------------------------------------------------------------------
# The spider imports base_spider which imports playwright_stealth — that's fine.
# But scrapy_settings references pipelines that import Django models.
# We avoid loading scrapy_settings entirely and configure Scrapy manually.

def main():
    parser = argparse.ArgumentParser(description="Test Meesho spider (no Django)")
    parser.add_argument(
        "--urls",
        default=None,
        help="Comma-separated Meesho product or search URLs",
    )
    parser.add_argument(
        "--max-pages",
        default="1",
        help="Max search pages per query (default 1)",
    )
    parser.add_argument(
        "--output",
        default="/app/output/meesho_test_results.jsonl",
        help="Output JSONL file path",
    )
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    from scrapy.crawler import CrawlerProcess

    # Import the spider
    from apps.scraping.spiders.meesho_spider import MeeshoSpider

    # Minimal Scrapy settings — NO Django pipelines, just JSON output
    settings = {
        "BOT_NAME": "whydud_meesho_test",
        "SPIDER_MODULES": [],  # Don't auto-discover — we import MeeshoSpider directly
        "LOG_LEVEL": "INFO",
        "MEMUSAGE_ENABLED": False,
        "DOWNLOAD_TIMEOUT": 90,
        "DOWNLOAD_MAXSIZE": 10485760,
        # Twisted reactor for async
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        # Override download handlers to plain HTTP (spider's custom_settings
        # already does this, but be explicit)
        "DOWNLOAD_HANDLERS": {
            "https": "scrapy.core.downloader.handlers.http11.HTTP11DownloadHandler",
            "http": "scrapy.core.downloader.handlers.http11.HTTP11DownloadHandler",
        },
        # NO pipelines — just feed export to JSONL
        "ITEM_PIPELINES": {},
        "FEEDS": {
            args.output: {
                "format": "jsonlines",
                "encoding": "utf-8",
                "overwrite": True,
            },
        },
        # AutoThrottle
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 3,
        "AUTOTHROTTLE_MAX_DELAY": 20,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        # Cookies
        "COOKIES_ENABLED": True,
        "ROBOTSTXT_OBEY": False,
    }

    # Build spider kwargs
    spider_kwargs = {"max_pages": args.max_pages}
    if args.urls:
        spider_kwargs["urls"] = args.urls

    print("=" * 70)
    print("MEESHO SPIDER TEST")
    print("=" * 70)
    print(f"URLs:       {args.urls or '(seed queries — first 4)'}")
    print(f"Max pages:  {args.max_pages}")
    print(f"Output:     {args.output}")
    print("=" * 70)
    print()

    start_time = time.time()

    process = CrawlerProcess(settings)
    process.crawl(MeeshoSpider, **spider_kwargs)
    process.start()

    elapsed = time.time() - start_time

    # Print results summary
    print()
    print("=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    print(f"Duration: {elapsed:.1f}s")

    if os.path.exists(args.output):
        with open(args.output, "r", encoding="utf-8") as f:
            lines = f.readlines()

        print(f"Items scraped: {len(lines)}")
        print()

        for i, line in enumerate(lines):
            try:
                item = json.loads(line)
                print(f"--- Item {i + 1} ---")
                print(f"  Title:       {item.get('title', 'N/A')[:80]}")
                print(f"  External ID: {item.get('external_id', 'N/A')}")
                print(f"  Price:       {item.get('price', 'N/A')} paisa")
                print(f"  MRP:         {item.get('mrp', 'N/A')} paisa")
                print(f"  Seller:      {item.get('seller_name', 'N/A')}")
                print(f"  Rating:      {item.get('rating', 'N/A')}")
                print(f"  Reviews:     {item.get('review_count', 'N/A')}")
                print(f"  Images:      {len(item.get('images', []))} images")
                print(f"  In stock:    {item.get('in_stock', 'N/A')}")
                print(f"  Category:    {item.get('category_slug', 'N/A')}")
                print(f"  URL:         {item.get('url', 'N/A')[:100]}")
                specs = item.get("specs", {})
                if specs:
                    print(f"  Specs:       {len(specs)} fields")
                print()
            except json.JSONDecodeError:
                print(f"  [Invalid JSON line {i + 1}]")

        if not lines:
            print("WARNING: No items were scraped!")
            print("This could mean:")
            print("  - Akamai blocked camoufox (check logs above for 403/503)")
            print("  - Page structure changed (check for empty __NEXT_DATA__)")
            print("  - Network issue inside container")
    else:
        print("WARNING: Output file not created — spider may have failed to start")

    print("=" * 70)


if __name__ == "__main__":
    main()
