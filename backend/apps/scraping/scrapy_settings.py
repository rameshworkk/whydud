"""Scrapy settings for Whydud spiders.

These are loaded by the spider runner (apps/scraping/runner.py)
and merged with per-spider custom_settings.
"""
import random

BOT_NAME = "whydud_scraper"
SPIDER_MODULES = ["apps.scraping.spiders"]
NEWSPIDER_MODULE = "apps.scraping.spiders"

# ---------------------------------------------------------------------------
# Item pipelines (ordered by priority)
# ---------------------------------------------------------------------------
ITEM_PIPELINES = {
    "apps.scraping.pipelines.ValidationPipeline": 100,
    "apps.scraping.pipelines.ReviewValidationPipeline": 150,
    "apps.scraping.pipelines.NormalizationPipeline": 200,
    "apps.scraping.pipelines.ProductPipeline": 400,
    "apps.scraping.pipelines.ReviewPersistencePipeline": 450,
    "apps.scraping.pipelines.MeilisearchIndexPipeline": 500,
    "apps.scraping.pipelines.SpiderStatsUpdatePipeline": 600,
}

# ---------------------------------------------------------------------------
# Download & request settings
# ---------------------------------------------------------------------------
LOG_LEVEL = "INFO"
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 2048       # kill spider if using > 2GB RAM
MEMUSAGE_WARNING_MB = 1536     # warn at 1.5GB

DOWNLOAD_TIMEOUT = 90          # proxy connections need more time (DataImpulse adds latency)
DOWNLOAD_MAXSIZE = 10485760    # 10MB max response
RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# We rotate User-Agents in BaseWhydudSpider — disable Scrapy's built-in UA middleware.
# Replace default retry with BackoffRetryMiddleware for exponential backoff.
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
    "apps.scraping.middlewares.BackoffRetryMiddleware": 350,
    "apps.scraping.middlewares.PlaywrightProxyMiddleware": 400,
}

# ---------------------------------------------------------------------------
# AutoThrottle — dynamically adjusts request rate based on server latency
# ---------------------------------------------------------------------------
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3       # start at 3s, scales up dynamically
AUTOTHROTTLE_MAX_DELAY = 30        # back off up to 30s when server is stressed
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.5   # aim for 1.5 concurrent requests — be gentler

# ---------------------------------------------------------------------------
# Playwright (for JS-rendered pages)
# ---------------------------------------------------------------------------
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
DOWNLOAD_HANDLERS = {
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-infobars",
        "--disable-extensions",
        "--disable-gpu",
        "--lang=en-IN",
    ],
}
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 4
PLAYWRIGHT_MAX_CONTEXTS = 3            # limit memory — each context ≈ 150MB RAM

# Randomize viewport per spider run — reduces fingerprinting consistency.
_VIEWPORT_CHOICES = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
]
_VIEWPORT = random.choice(_VIEWPORT_CHOICES)

# Default context kwargs — mimic a real Indian Chrome user.
PLAYWRIGHT_CONTEXTS = {
    "default": {
        "locale": "en-IN",
        "timezone_id": "Asia/Kolkata",
        "viewport": _VIEWPORT,
        "java_script_enabled": True,
        "ignore_https_errors": True,
        "bypass_csp": True,
        "extra_http_headers": {
            "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
        },
    },
}


def get_scrapy_settings() -> dict:
    """Return all module-level uppercase variables as a dict.

    Used by the subprocess runner and Celery tasks to pass settings
    programmatically to CrawlerProcess.
    """
    return {k: v for k, v in globals().items() if k.isupper()}
