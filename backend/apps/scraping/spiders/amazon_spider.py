"""Amazon.in spider — products, prices, reviews, offers.

Sprint 2, Week 4.
"""
from .base_spider import BaseWhydudSpider


class AmazonINSpider(BaseWhydudSpider):
    """Scrapes Amazon.in product pages using Playwright for JS rendering."""
    
    name = "amazon_in"
    allowed_domains = ["amazon.in", "www.amazon.in"]
    
    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_HANDLERS": {
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
    }

    def start_requests(self):
        # TODO Sprint 2 Week 4: load product URLs from DB and start crawling
        pass

    def parse(self, response):
        # TODO Sprint 2 Week 4: extract product data
        pass

    def parse_product_detail(self, response):
        # TODO Sprint 2 Week 4
        pass

    def parse_reviews(self, response):
        # TODO Sprint 2 Week 6
        pass
