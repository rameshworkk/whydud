"""Base Scrapy spider with anti-detection defaults and User-Agent rotation.

Provides comprehensive fingerprint randomization, viewport variance, and
realistic browser headers to minimize bot-detection signals.
"""
import random

import scrapy
from playwright_stealth import Stealth

# ---------------------------------------------------------------------------
# Expanded, realistic browser User-Agent strings — 2024-2026 versions.
# Rotated per request. Weighted toward Chrome (70%+ market share in India).
# ---------------------------------------------------------------------------
USER_AGENTS = [
    # Chrome on Windows (latest versions)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    # Chrome on Android (mobile traffic — India has high mobile usage)
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
]

# Realistic desktop viewport sizes — randomized per spider instance.
VIEWPORT_POOL = [
    {"width": 1920, "height": 1080},  # Full HD (most common)
    {"width": 1366, "height": 768},   # HD laptop (very common in India)
    {"width": 1536, "height": 864},   # Scaled FHD
    {"width": 1440, "height": 900},   # MacBook Air
    {"width": 1280, "height": 720},   # HD
    {"width": 1600, "height": 900},   # 16:9 variant
    {"width": 2560, "height": 1440},  # QHD
]

# Accept-Language header variants for Indian users
ACCEPT_LANGUAGES = [
    "en-IN,en;q=0.9,hi;q=0.8",
    "en-IN,en-GB;q=0.9,en;q=0.8",
    "en-IN,en;q=0.9,hi;q=0.8,en-US;q=0.7",
    "en-IN,en;q=0.9",
    "en-IN,en-US;q=0.9,en;q=0.8,hi;q=0.7",
]

# Sec-CH-UA header variants (Client Hints)
SEC_CH_UA_VARIANTS = [
    '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
    '"Chromium";v="130", "Not_A Brand";v="24", "Google Chrome";v="130"',
    '"Chromium";v="128", "Not_A Brand";v="24", "Google Chrome";v="128"',
    '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
]


class BaseWhydudSpider(scrapy.Spider):
    """Base spider all marketplace spiders inherit from.

    Provides:
    - User-Agent rotation (random per request) with 25+ UAs
    - Sec-CH-UA Client Hints rotation
    - Viewport randomization per spider instance
    - Download delay with jitter (2-5s)
    - Error counting for job stats
    - Respectful crawling defaults
    - Stealth configuration for Playwright
    """

    # Stealth config — hides common headless browser fingerprints.
    # Patches: navigator.webdriver, navigator.plugins, window.chrome,
    # WebGL vendor/renderer, and Permission API.
    # Stealth config — now applied via StealthPlaywrightHandler
    # (context-level init scripts injected before navigation).
    STEALTH = Stealth()

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 4,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "ROBOTSTXT_OBEY": True,
        "COOKIES_ENABLED": True,
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT": 4,
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-extensions",
                "--disable-gpu",
                "--lang=en-IN",
                "--window-size=1366,768",
            ],
        },
        # AutoThrottle — will ramp UP delay if server is stressed
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 3,
        "AUTOTHROTTLE_MAX_DELAY": 30,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 2.0,
        # Disable default UA middleware (we rotate manually) + proxy rotation.
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "apps.scraping.middlewares.BackoffRetryMiddleware": 350,
            "apps.scraping.middlewares.PlaywrightProxyMiddleware": 400,
        },
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.items_scraped: int = 0
        self.items_failed: int = 0
        # Pick a random viewport for this spider instance (consistency per session)
        self._viewport = random.choice(VIEWPORT_POOL)

    # ------------------------------------------------------------------
    # Request helpers
    # ------------------------------------------------------------------

    def _random_ua(self) -> str:
        """Return a random User-Agent string."""
        return random.choice(USER_AGENTS)

    def _make_headers(self) -> dict[str, str]:
        """Build realistic request headers with rotated User-Agent and Client Hints."""
        ua = self._random_ua()
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": random.choice(ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        # Add Client Hints for Chrome UAs
        if "Chrome" in ua and "Firefox" not in ua and "Safari/605" not in ua:
            headers["Sec-CH-UA"] = random.choice(SEC_CH_UA_VARIANTS)
            headers["Sec-CH-UA-Mobile"] = "?0"
            headers["Sec-CH-UA-Platform"] = random.choice(['"Windows"', '"macOS"', '"Linux"'])
        return headers

    def _extra_delay(self) -> float:
        """Random delay between 2-5 seconds (on top of DOWNLOAD_DELAY jitter)."""
        return random.uniform(2.0, 5.0)

    def get_viewport(self) -> dict:
        """Return the viewport for this spider instance."""
        return dict(self._viewport)

    # ------------------------------------------------------------------
    # Proxy session helpers
    # ------------------------------------------------------------------

    def _with_proxy_session(self, meta: dict, session_key: str) -> dict:
        """Add proxy session stickiness to request meta.

        All requests sharing the same session_key will be routed through
        the same proxy context (until that proxy is banned).
        """
        meta["proxy_session"] = session_key
        return meta

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def handle_error(self, failure) -> None:
        """Log Scrapy download errors and increment failure counter."""
        self.items_failed += 1
        self.logger.error(f"Request failed: {failure.request.url} — {failure.getErrorMessage()}")
