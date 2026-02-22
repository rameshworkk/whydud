"""Flipkart spider — products, prices, reviews, offers.

Sprint 2, Week 5.
"""
from .base_spider import BaseWhydudSpider


class FlipkartSpider(BaseWhydudSpider):
    """Scrapes Flipkart product pages."""
    
    name = "flipkart"
    allowed_domains = ["flipkart.com", "www.flipkart.com"]

    def start_requests(self):
        # TODO Sprint 2 Week 5
        pass

    def parse(self, response):
        # TODO Sprint 2 Week 5
        pass
