"""Scrapy settings for Whydud spiders.

Loaded by scrapy.cfg — not Django settings.
"""
BOT_NAME = "whydud_scraper"
SPIDER_MODULES = ["apps.scraping.spiders"]

ITEM_PIPELINES = {
    "apps.scraping.pipelines.ValidationPipeline": 100,
    "apps.scraping.pipelines.NormalizationPipeline": 200,
    "apps.scraping.pipelines.DeduplicationPipeline": 300,
    "apps.scraping.pipelines.PersistencePipeline": 400,
    "apps.scraping.pipelines.MeilisearchIndexPipeline": 500,
}

DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    # TODO Sprint 2: Add proxy rotation middleware
    # TODO Sprint 2: Add anti-detection middleware
}

LOG_LEVEL = "INFO"
DOWNLOAD_TIMEOUT = 30
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
