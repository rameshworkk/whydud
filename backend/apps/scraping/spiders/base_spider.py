"""Base Scrapy spider with anti-detection defaults and User-Agent rotation."""
import random

import scrapy

# Realistic browser User-Agent strings — rotated per request.
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


class BaseWhydudSpider(scrapy.Spider):
    """Base spider all marketplace spiders inherit from.

    Provides:
    - User-Agent rotation (random per request)
    - Download delay with jitter (2-5s)
    - Error counting for job stats
    - Respectful crawling defaults
    """

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "ROBOTSTXT_OBEY": True,
        "COOKIES_ENABLED": True,
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        # Disable default UA middleware — we rotate manually.
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
        },
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.items_scraped: int = 0
        self.items_failed: int = 0

    # ------------------------------------------------------------------
    # Request helpers
    # ------------------------------------------------------------------

    def _random_ua(self) -> str:
        """Return a random User-Agent string."""
        return random.choice(USER_AGENTS)

    def _make_headers(self) -> dict[str, str]:
        """Build request headers with a rotated User-Agent."""
        return {
            "User-Agent": self._random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
        }

    def _extra_delay(self) -> float:
        """Random delay between 2-5 seconds (on top of DOWNLOAD_DELAY jitter)."""
        return random.uniform(2.0, 5.0)

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def handle_error(self, failure) -> None:
        """Log Scrapy download errors and increment failure counter."""
        self.items_failed += 1
        self.logger.error(f"Request failed: {failure.request.url} — {failure.getErrorMessage()}")
