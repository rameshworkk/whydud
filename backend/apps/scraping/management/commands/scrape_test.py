"""Management command: test scraping health without a full run.

Fetches one product page per marketplace and reports detailed diagnostics.

Usage:
    python manage.py scrape_test
    python manage.py scrape_test --test-proxies
    python manage.py scrape_test --save-html
    python manage.py scrape_test --amazon-url "https://www.amazon.in/dp/XXXXXXXXXX"
"""
import os
import random
import time

from django.core.management.base import BaseCommand

from apps.scraping.spiders.base_spider import USER_AGENTS


def _random_headers() -> dict[str, str]:
    """Realistic browser headers for plain HTTP tests."""
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": ua,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }
    if "Chrome" in ua and "Firefox" not in ua:
        headers["Sec-CH-UA-Mobile"] = "?0"
        headers["Sec-CH-UA-Platform"] = random.choice(
            ['"Windows"', '"macOS"', '"Linux"']
        )
    return headers


class Command(BaseCommand):
    help = (
        "Test scraping health — fetches 1 product from each marketplace "
        "and reports results"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--amazon-url",
            default="https://www.amazon.in/dp/B0DGJLLX6T",
            help="Amazon product URL to test",
        )
        parser.add_argument(
            "--flipkart-url",
            default=(
                "https://www.flipkart.com/samsung-galaxy-s24-fe-blue-256-gb"
                "/p/itm07c2e7d44e621"
            ),
            help="Flipkart product URL to test",
        )
        parser.add_argument(
            "--save-html",
            action="store_true",
            help="Save response HTML for debugging",
        )
        parser.add_argument(
            "--test-proxies",
            action="store_true",
            help="Test proxy connectivity",
        )

    def handle(self, *args, **options):
        self.save_html = options["save_html"]
        self.stdout.write("\n=== Whydud Scraping Health Check ===\n")

        # Test 1: Proxy connectivity
        if options["test_proxies"]:
            self.stdout.write(self.style.MIGRATE_HEADING("\n[1] Proxy Connectivity"))
            self._test_proxies()

        # Test 2: Amazon listing page (plain HTTP)
        self.stdout.write(self.style.MIGRATE_HEADING("\n[2] Amazon Listing (HTTP)"))
        self._test_http(
            "https://www.amazon.in/s?k=smartphones&page=1",
            "Amazon listing (HTTP)",
        )

        # Test 3: Amazon product page (Playwright)
        self.stdout.write(self.style.MIGRATE_HEADING("\n[3] Amazon Product (Playwright)"))
        self._test_playwright(
            options["amazon_url"], "Amazon product (Playwright)"
        )

        # Test 4: Flipkart listing page (Playwright)
        self.stdout.write(self.style.MIGRATE_HEADING("\n[4] Flipkart Listing (Playwright)"))
        self._test_playwright(
            "https://www.flipkart.com/search?q=smartphones",
            "Flipkart listing (Playwright)",
        )

        # Test 5: Flipkart product page (HTTP — JSON-LD check)
        self.stdout.write(self.style.MIGRATE_HEADING("\n[5] Flipkart Product (HTTP)"))
        self._test_http(options["flipkart_url"], "Flipkart product (HTTP)")

        # Test 6: Database connectivity
        self.stdout.write(self.style.MIGRATE_HEADING("\n[6] Database"))
        self._test_db()

        # Test 7: Meilisearch connectivity
        self.stdout.write(self.style.MIGRATE_HEADING("\n[7] Meilisearch"))
        self._test_meilisearch()

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Done ===\n"))

    # ------------------------------------------------------------------
    # Proxy test
    # ------------------------------------------------------------------

    def _test_proxies(self):
        import requests

        proxy_list = os.environ.get("SCRAPING_PROXY_LIST", "")
        if not proxy_list:
            self.stdout.write(
                self.style.WARNING(
                    "  No proxies configured (SCRAPING_PROXY_LIST empty)"
                )
            )
            return

        proxies = [p.strip() for p in proxy_list.split(",") if p.strip()]
        self.stdout.write(f"  Testing {len(proxies)} proxies...")

        for i, proxy in enumerate(proxies):
            start = time.monotonic()
            try:
                r = requests.get(
                    "https://httpbin.org/ip",
                    proxies={"https": proxy, "http": proxy},
                    timeout=10,
                )
                elapsed = time.monotonic() - start
                ip = r.json().get("origin", "unknown")
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  proxy_{i}: OK — IP: {ip} ({elapsed:.1f}s)"
                    )
                )
            except Exception as e:
                elapsed = time.monotonic() - start
                self.stdout.write(
                    self.style.ERROR(
                        f"  proxy_{i}: FAILED — {e} ({elapsed:.1f}s)"
                    )
                )

    # ------------------------------------------------------------------
    # Plain HTTP test
    # ------------------------------------------------------------------

    def _test_http(self, url, label):
        """Test plain HTTP request with realistic headers."""
        import requests

        start = time.monotonic()
        try:
            r = requests.get(url, headers=_random_headers(), timeout=15)
            elapsed = time.monotonic() - start
            body = r.text
            body_lower = body[:5000].lower()
            has_title = "<title" in body_lower
            has_captcha = (
                "captcha" in body_lower or "robot check" in body_lower
            )
            has_json_ld = '"@type"' in body[:10000]
            size_kb = len(r.content) / 1024

            status_style = (
                self.style.SUCCESS if 200 <= r.status_code < 300
                else self.style.ERROR
            )
            self.stdout.write(
                f"  {label}: {status_style(f'HTTP {r.status_code}')} | "
                f"{size_kb:.0f}KB | {elapsed:.1f}s | "
                f"title={'yes' if has_title else 'NO'} | "
                f"json-ld={'yes' if has_json_ld else 'no'} | "
                f"captcha={'DETECTED' if has_captcha else 'clean'}"
            )
            if has_captcha:
                self.stdout.write(
                    self.style.WARNING(
                        f"    CAPTCHA detected — need proxies for {label}"
                    )
                )

            if self.save_html:
                self._save_html(label, r.text)

        except Exception as e:
            elapsed = time.monotonic() - start
            self.stdout.write(
                self.style.ERROR(
                    f"  {label}: FAILED — {e} ({elapsed:.1f}s)"
                )
            )

    # ------------------------------------------------------------------
    # Playwright test
    # ------------------------------------------------------------------

    def _test_playwright(self, url, label):
        """Test a page with Playwright (headless Chromium)."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.stdout.write(
                self.style.WARNING(
                    f"  {label}: SKIPPED — playwright not installed "
                    "(pip install playwright && playwright install chromium)"
                )
            )
            return

        start = time.monotonic()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport={"width": 1366, "height": 768},
                    locale="en-IN",
                    timezone_id="Asia/Kolkata",
                )
                page = context.new_page()
                resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                status = resp.status if resp else 0

                # Wait a moment for JS rendering
                page.wait_for_timeout(2000)

                content = page.content()
                content_lower = content[:5000].lower()
                has_title = "<title" in content_lower
                has_captcha = (
                    "captcha" in content_lower
                    or "robot check" in content_lower
                )
                has_json_ld = '"@type"' in content[:10000]
                size_kb = len(content.encode()) / 1024
                elapsed = time.monotonic() - start

                status_style = (
                    self.style.SUCCESS if 200 <= status < 300
                    else self.style.ERROR
                )
                self.stdout.write(
                    f"  {label}: {status_style(f'HTTP {status}')} | "
                    f"{size_kb:.0f}KB | {elapsed:.1f}s | "
                    f"title={'yes' if has_title else 'NO'} | "
                    f"json-ld={'yes' if has_json_ld else 'no'} | "
                    f"captcha={'DETECTED' if has_captcha else 'clean'}"
                )
                if has_captcha:
                    self.stdout.write(
                        self.style.WARNING(
                            f"    CAPTCHA detected — this marketplace "
                            f"may need proxies"
                        )
                    )

                if self.save_html:
                    self._save_html(label, content)

                browser.close()

        except Exception as e:
            elapsed = time.monotonic() - start
            self.stdout.write(
                self.style.ERROR(
                    f"  {label}: FAILED — {e} ({elapsed:.1f}s)"
                )
            )

    # ------------------------------------------------------------------
    # Database test
    # ------------------------------------------------------------------

    def _test_db(self):
        try:
            from apps.products.models import Marketplace, Product, ProductListing
            from apps.reviews.models import Review

            self.stdout.write(
                f"  Marketplaces: {Marketplace.objects.count()}, "
                f"Products: {Product.objects.count()}, "
                f"Listings: {ProductListing.objects.count()}, "
                f"Reviews: {Review.objects.count()}"
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  DB: FAILED — {e}"))

    # ------------------------------------------------------------------
    # Meilisearch test
    # ------------------------------------------------------------------

    def _test_meilisearch(self):
        import requests

        host = os.environ.get("MEILISEARCH_HOST", "http://localhost:7700")
        try:
            r = requests.get(f"{host}/health", timeout=5)
            status = r.json().get("status", "unknown")
            self.stdout.write(
                self.style.SUCCESS(f"  Meilisearch: OK — status={status}")
            )
        except Exception:
            self.stdout.write(
                self.style.WARNING(
                    f"  Meilisearch: NOT REACHABLE at {host}"
                )
            )

    # ------------------------------------------------------------------
    # HTML save helper
    # ------------------------------------------------------------------

    def _save_html(self, label, html):
        """Save HTML to data/raw_html/ for debugging."""
        from common.app_settings import ScrapingConfig

        out_dir = ScrapingConfig.raw_html_dir()
        os.makedirs(out_dir, exist_ok=True)
        safe_label = label.lower().replace(" ", "_").replace("(", "").replace(")", "")
        ts = int(time.time())
        path = os.path.join(out_dir, f"test_{safe_label}_{ts}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        self.stdout.write(f"    Saved HTML: {path}")
