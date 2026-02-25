"""Scrapy Item definitions for marketplace scrapers."""
import scrapy


class ProductItem(scrapy.Item):
    """Structured product data yielded by marketplace spiders.

    Prices are stored in paisa (Indian currency subunit).
    E.g., ₹24,999 → 2499900 paisa.
    """

    marketplace_slug = scrapy.Field()   # str — e.g., "amazon-in"
    external_id = scrapy.Field()        # str — ASIN for Amazon, product ID for others
    url = scrapy.Field()                # str — canonical product URL
    title = scrapy.Field()              # str
    brand = scrapy.Field()              # str | None
    price = scrapy.Field()              # Decimal (paisa) | None — current sale price
    mrp = scrapy.Field()                # Decimal (paisa) | None — maximum retail price
    images = scrapy.Field()             # list[str] — image URLs
    rating = scrapy.Field()             # Decimal (0-5) | None
    review_count = scrapy.Field()       # int | None
    specs = scrapy.Field()              # dict[str, str] — specifications key-value pairs
    seller_name = scrapy.Field()        # str | None
    seller_rating = scrapy.Field()      # Decimal (0-5) | None
    in_stock = scrapy.Field()           # bool
    fulfilled_by = scrapy.Field()       # str | None — "Amazon" or seller name
    about_bullets = scrapy.Field()      # list[str] — "About this item" bullet points
    offer_details = scrapy.Field()      # list[dict] — bank offers, coupons, EMI
    raw_html_path = scrapy.Field()      # str | None — local path to saved HTML
