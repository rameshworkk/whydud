"""Base Scrapy spider with anti-detection middleware configured."""
import scrapy


class BaseWhydudSpider(scrapy.Spider):
    """Base spider all marketplace spiders inherit from.
    
    Implements:
    - User-agent rotation
    - Request rate limiting
    - Error handling and job stats reporting
    """
    
    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "ROBOTSTXT_OBEY": False,
        "COOKIES_ENABLED": True,
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.items_scraped = 0
        self.items_failed = 0

    def handle_error(self, failure) -> None:
        """Log Scrapy download errors."""
        self.items_failed += 1
        self.logger.error(f"Request failed: {failure.request.url}")
