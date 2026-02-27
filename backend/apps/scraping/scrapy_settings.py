"""Scrapy settings for Whydud spiders.

These are loaded by the spider runner (apps/scraping/runner.py)
and merged with per-spider custom_settings.
"""

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
}

# ---------------------------------------------------------------------------
# Download & request settings
# ---------------------------------------------------------------------------
LOG_LEVEL = "INFO"
DOWNLOAD_TIMEOUT = 30
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# We rotate User-Agents in BaseWhydudSpider — disable Scrapy's built-in UA middleware.
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    # TODO Sprint 3: Add proxy rotation middleware
}

# Playwright (for JS-rendered pages)
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
DOWNLOAD_HANDLERS = {
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
}


def get_scrapy_settings() -> dict:
    """Return all module-level uppercase variables as a dict.

    Used by the subprocess runner and Celery tasks to pass settings
    programmatically to CrawlerProcess.
    """
    return {k: v for k, v in globals().items() if k.isupper()}
