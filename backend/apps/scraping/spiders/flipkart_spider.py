"""Flipkart spider — scrapes product listings, detail pages, prices, and offers.

Flipkart renders most content server-side, so Playwright is only used for
listing pages (lazy-loaded product cards). Product detail pages are fetched
via standard HTTP.

Strategy:
  1. JSON-LD structured data (``<script type="application/ld+json">``) is the
     primary source for title, price, brand, rating, images, availability, and
     seller.  Flipkart reliably includes schema.org Product markup.
  2. CSS/XPath fallbacks extract the same data when JSON-LD is absent.
  3. Specs, highlights, offers, MRP, and fulfilment info are CSS/XPath only.

Sprint 2, Week 5.
"""
import json
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import scrapy
from scrapy_playwright.page import PageMethod

from apps.scraping.items import ProductItem
from .base_spider import BaseWhydudSpider

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FPID_RE = re.compile(r"/p/(itm[a-zA-Z0-9]+)")
PRICE_RE = re.compile(r"[\d,.]+")
RATING_NUM_RE = re.compile(r"([\d.]+)")
REVIEW_COUNT_RE = re.compile(r"([\d,]+)\s*(?:rating|review)", re.IGNORECASE)

MARKETPLACE_SLUG = "flipkart"

# Flipkart search keyword → Whydud category slug mapping
KEYWORD_CATEGORY_MAP: dict[str, str] = {
    "smartphones": "smartphones",
    "laptops": "laptops",
    "headphones": "audio",
    "air purifiers": "appliances",
    "washing machines": "washing-machines",
    "refrigerators": "refrigerators",
    "televisions": "televisions",
    "cameras": "cameras",
}

# Seed search URLs — used when no ScraperJob provides URLs.
SEED_CATEGORY_URLS = [
    "https://www.flipkart.com/search?q=smartphones&sort=popularity",
    "https://www.flipkart.com/search?q=laptops&sort=popularity",
    "https://www.flipkart.com/search?q=headphones&sort=popularity",
    "https://www.flipkart.com/search?q=air+purifiers&sort=popularity",
    "https://www.flipkart.com/search?q=washing+machines&sort=popularity",
    "https://www.flipkart.com/search?q=refrigerators&sort=popularity",
    "https://www.flipkart.com/search?q=televisions&sort=popularity",
    "https://www.flipkart.com/search?q=cameras&sort=popularity",
]

MAX_LISTING_PAGES = 5


class FlipkartSpider(BaseWhydudSpider):
    """Scrapes Flipkart product pages.

    Flipkart renders most product detail content server-side, so Playwright
    is only activated for listing pages (product cards are lazy-loaded).

    Spider arguments (passed via ``-a``):
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES (default 5).
      save_html     — "1" to save raw HTML for debugging.
    """

    name = "flipkart"
    allowed_domains = ["flipkart.com", "www.flipkart.com"]

    # Playwright for both listing and product pages (Flipkart 403s plain HTTP).
    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_HANDLERS": {
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
    }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(
        self,
        job_id: str | None = None,
        category_urls: str | None = None,
        max_pages: str | None = None,
        save_html: str = "0",
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self._category_urls: list[str] = (
            [u.strip() for u in category_urls.split(",") if u.strip()]
            if category_urls
            else []
        )
        self._max_pages = int(max_pages) if max_pages else MAX_LISTING_PAGES
        self._save_html = save_html == "1"
        self._pages_followed: dict[str, int] = {}

    # ------------------------------------------------------------------
    # start_requests
    # ------------------------------------------------------------------

    def start_requests(self):
        """Emit initial requests from ScraperJob config or seed categories."""
        urls = self._load_urls()
        for url in urls:
            self.logger.info(f"Starting category: {url}")
            yield scrapy.Request(
                url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                # Listing pages need Playwright — cards are lazy-loaded.
                meta={"playwright": True},
                dont_filter=True,
            )

    def _load_urls(self) -> list[str]:
        """Resolve the list of search/category URLs to crawl."""
        if self._category_urls:
            return self._category_urls

        if self.job_id:
            try:
                from apps.scraping.models import ScraperJob

                job = ScraperJob.objects.get(id=self.job_id)
                self.logger.info(
                    f"Running for job {self.job_id}, marketplace: {job.marketplace.slug}"
                )
            except Exception as exc:
                self.logger.warning(f"Could not load ScraperJob {self.job_id}: {exc}")

        return list(SEED_CATEGORY_URLS)

    # ------------------------------------------------------------------
    # Listing page (search results / category pages)
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract product links from a Flipkart search/category page."""
        # Flipkart product links always contain /p/itm
        product_links = response.css('a[href*="/p/itm"]::attr(href)').getall()
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_links: list[str] = []
        for link in product_links:
            full = response.urljoin(link)
            # Normalise — strip query params and ref tags for dedup
            canon = full.split("?")[0]
            if canon not in seen:
                seen.add(canon)
                unique_links.append(full)

        if not unique_links:
            self.logger.warning(f"No product links found on {response.url}")
            return

        self.logger.info(f"Found {len(unique_links)} products on {response.url}")

        # Resolve category slug from the seed URL keyword
        category_slug = response.meta.get("category_slug") or self._resolve_category_from_url(response.url)

        for link in unique_links:
            yield scrapy.Request(
                link,
                callback=self.parse_product_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                # Flipkart returns 403 on plain HTTP — Playwright needed.
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "domcontentloaded"),
                    ],
                    "category_slug": category_slug,
                },
            )

        # Pagination
        base_url = re.sub(r"[&?]page=\d+", "", response.url)
        pages_so_far = self._pages_followed.get(base_url, 1)
        if pages_so_far < self._max_pages:
            next_link = self._find_next_page(response)
            if next_link:
                self._pages_followed[base_url] = pages_so_far + 1
                yield scrapy.Request(
                    response.urljoin(next_link),
                    callback=self.parse_listing_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={"playwright": True, "category_slug": category_slug},
                )

    @staticmethod
    def _find_next_page(response) -> str | None:
        """Locate the "Next" pagination link."""
        # Flipkart uses <nav> with numbered + next links
        for a in response.css("nav a"):
            text = a.css("::text").get("").strip().lower()
            if text == "next":
                return a.attrib.get("href")
        # Fallback: look for an anchor whose span contains "Next"
        nav_link = response.xpath(
            '//a[.//span[contains(text(),"Next")]]/@href'
        ).get()
        return nav_link

    # ------------------------------------------------------------------
    # Product detail page
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        """Extract all product data from a Flipkart product page.

        Primary source: JSON-LD structured data.
        Fallback: CSS selectors and XPath.
        """
        fpid = self._extract_fpid(response)
        if not fpid:
            self.logger.warning(f"Could not extract FPID from {response.url}")
            self.items_failed += 1
            return

        # Parse JSON-LD once — used by many extractors.
        ld_json = self._parse_json_ld(response)

        title = self._extract_title(response, ld_json)
        if not title:
            self.logger.warning(f"No title found for FPID {fpid}")
            self.items_failed += 1
            return

        raw_html_path = None
        if self._save_html:
            raw_html_path = self._save_raw_html(response, fpid)

        item = ProductItem()
        item["marketplace_slug"] = MARKETPLACE_SLUG
        item["external_id"] = fpid
        item["url"] = self._canonical_url(response.url, fpid)
        item["title"] = title
        item["brand"] = self._extract_brand(response, ld_json)
        item["price"] = self._extract_price(response, ld_json)
        item["mrp"] = self._extract_mrp(response)
        item["images"] = self._extract_images(response, ld_json)
        item["rating"] = self._extract_rating(response, ld_json)
        item["review_count"] = self._extract_review_count(response, ld_json)
        item["specs"] = self._extract_specs(response)
        item["seller_name"] = self._extract_seller(response, ld_json)
        item["seller_rating"] = self._extract_seller_rating(response)
        item["in_stock"] = self._extract_availability(response, ld_json)
        item["fulfilled_by"] = self._extract_fulfilled_by(response)
        item["category_slug"] = response.meta.get("category_slug")
        item["about_bullets"] = self._extract_highlights(response)
        item["offer_details"] = self._extract_offers(response)
        item["raw_html_path"] = raw_html_path

        self.items_scraped += 1
        yield item

    # ------------------------------------------------------------------
    # JSON-LD extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_ld(response) -> dict | None:
        """Extract the first schema.org Product JSON-LD block from the page."""
        for script in response.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(script)
            except (json.JSONDecodeError, ValueError):
                continue

            # Might be a single object or an array
            if isinstance(data, list):
                for obj in data:
                    if isinstance(obj, dict) and obj.get("@type") == "Product":
                        return obj
            elif isinstance(data, dict):
                if data.get("@type") == "Product":
                    return data
                # Sometimes nested inside @graph
                for obj in data.get("@graph", []):
                    if isinstance(obj, dict) and obj.get("@type") == "Product":
                        return obj
        return None

    # ------------------------------------------------------------------
    # Field extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_fpid(response) -> str | None:
        """Extract Flipkart Product ID (FPID) from URL."""
        match = FPID_RE.search(response.url)
        if match:
            return match.group(1)
        # Fallback: look for pid parameter in URL query
        pid = response.url.split("pid=")[-1].split("&")[0] if "pid=" in response.url else None
        return pid if pid else None

    @staticmethod
    def _extract_title(response, ld_json: dict | None) -> str | None:
        """Extract product title."""
        # JSON-LD
        if ld_json and ld_json.get("name"):
            return ld_json["name"].strip()
        # CSS fallbacks — Flipkart class names change, try multiple patterns
        for sel in [
            "span.VU-ZEz::text",       # Common product title class
            "h1._6EBuvT span::text",    # Alternative wrapper
            "h1 span.B_NuCI::text",     # Another variant
        ]:
            text = response.css(sel).get()
            if text and text.strip():
                return text.strip()
        # XPath: first h1 or large span in the product info column
        title = response.xpath(
            '//div[contains(@class,"aMaAEs") or contains(@class,"hGSR34")]'
            '//span[string-length(text()) > 10]/text()'
        ).get()
        return title.strip() if title else None

    @staticmethod
    def _extract_brand(response, ld_json: dict | None) -> str | None:
        """Extract brand name."""
        # JSON-LD
        if ld_json:
            brand_obj = ld_json.get("brand")
            if isinstance(brand_obj, dict) and brand_obj.get("name"):
                return brand_obj["name"].strip()
            if isinstance(brand_obj, str) and brand_obj.strip():
                return brand_obj.strip()
        # CSS: breadcrumb often contains brand
        breadcrumbs = response.css("div._1MR4o5 a::text, div._2whKao a::text").getall()
        if len(breadcrumbs) >= 3:
            # Breadcrumb pattern: Home > Category > Brand > ...
            return breadcrumbs[2].strip()
        # XPath: Specs table sometimes has "Brand"
        brand = response.xpath(
            '//td[text()="Brand" or text()="brand"]/following-sibling::td//text()'
        ).get()
        return brand.strip() if brand else None

    def _extract_price(self, response, ld_json: dict | None) -> Decimal | None:
        """Extract current sale price in paisa."""
        # JSON-LD offers
        if ld_json:
            offers = ld_json.get("offers")
            if isinstance(offers, dict):
                price = self._json_ld_price(offers)
                if price is not None:
                    return price
            elif isinstance(offers, list):
                for offer in offers:
                    price = self._json_ld_price(offer)
                    if price is not None:
                        return price

        # CSS fallbacks
        for sel in [
            "div._30jeq3::text",         # Common sale price class
            "div._16Jk6d::text",          # Alternative
            "div.Nx9bqj::text",           # Newer variant
            "div.hl05eU div.Nx9bqj::text",
        ]:
            text = response.css(sel).get()
            price = self._parse_price_text(text)
            if price is not None:
                return price

        # XPath: look for the first ₹ price near the buy button area
        price_text = response.xpath(
            '//div[contains(@class,"CEmi") or contains(@class,"_30jeq")]//text()'
        ).get()
        return self._parse_price_text(price_text)

    def _extract_mrp(self, response) -> Decimal | None:
        """Extract MRP (strike-through price) in paisa.

        JSON-LD only contains the sale price, so MRP is always from CSS.
        """
        for sel in [
            "div._3I9_wc::text",          # Common MRP class (strike-through)
            "div._2p6lqe::text",           # Alternative
            "div.yRaY8j::text",            # Newer variant
        ]:
            text = response.css(sel).get()
            price = self._parse_price_text(text)
            if price is not None:
                return price

        # XPath: strike-through or "M.R.P" text
        mrp_text = response.xpath(
            '//span[contains(@class,"_2p6lq") or contains(@style,"line-through")]//text()'
        ).get()
        return self._parse_price_text(mrp_text)

    def _extract_images(self, response, ld_json: dict | None) -> list[str]:
        """Extract all product image URLs (high resolution)."""
        images: list[str] = []

        # JSON-LD images
        if ld_json:
            img = ld_json.get("image")
            if isinstance(img, str) and img:
                images.append(self._high_res_image(img))
            elif isinstance(img, list):
                for i in img:
                    if isinstance(i, str) and i:
                        images.append(self._high_res_image(i))

        # CSS: image gallery thumbnails → upgrade to full size
        for img_url in response.css(
            'div._3kidJX img::attr(src), '
            'ul._1-n69S li img::attr(src), '
            'div._2E1FGS img::attr(src), '
            'div._1BweB8 img::attr(src)'
        ).getall():
            if "placeholder" in img_url:
                continue
            full = self._high_res_image(img_url)
            if full not in images:
                images.append(full)

        # Fallback: any large product image on the page
        if not images:
            for img_url in response.css('img[src*="rukminim"]::attr(src)').getall():
                full = self._high_res_image(img_url)
                if full not in images:
                    images.append(full)

        return images[:10]

    @staticmethod
    def _extract_rating(response, ld_json: dict | None) -> Decimal | None:
        """Extract average star rating (0-5)."""
        # JSON-LD
        if ld_json:
            agg = ld_json.get("aggregateRating")
            if isinstance(agg, dict):
                val = agg.get("ratingValue")
                if val is not None:
                    try:
                        return Decimal(str(val))
                    except InvalidOperation:
                        pass

        # CSS fallbacks
        for sel in [
            "div._3LWZlK::text",       # Common rating badge
            "span._1lRcqv::text",       # Alternative
            "div.XQDdHH::text",         # Newer variant
        ]:
            text = response.css(sel).get()
            if text:
                match = RATING_NUM_RE.search(text)
                if match:
                    try:
                        return Decimal(match.group(1))
                    except InvalidOperation:
                        pass
        return None

    @staticmethod
    def _extract_review_count(response, ld_json: dict | None) -> int | None:
        """Extract total number of ratings/reviews."""
        # JSON-LD
        if ld_json:
            agg = ld_json.get("aggregateRating")
            if isinstance(agg, dict):
                for key in ("reviewCount", "ratingCount"):
                    val = agg.get(key)
                    if val is not None:
                        try:
                            return int(val)
                        except (ValueError, TypeError):
                            pass

        # CSS: rating/review count text (e.g., "1,234 Ratings & 567 Reviews")
        for sel in [
            "span._2_R_DZ::text",
            "span._13vcW::text",
            'div[class*="row"] span._2_R_DZ span::text',
        ]:
            for text in response.css(sel).getall():
                match = REVIEW_COUNT_RE.search(text)
                if match:
                    return int(match.group(1).replace(",", ""))

        # XPath fallback
        count_text = response.xpath(
            '//*[contains(text(),"Rating") and contains(text(),"Review")]//text()'
        ).get()
        if count_text:
            match = REVIEW_COUNT_RE.search(count_text)
            if match:
                return int(match.group(1).replace(",", ""))
        return None

    @staticmethod
    def _extract_seller(response, ld_json: dict | None) -> str | None:
        """Extract seller name."""
        # JSON-LD offers.seller
        if ld_json:
            offers = ld_json.get("offers")
            if isinstance(offers, dict):
                seller = offers.get("seller")
                if isinstance(seller, dict) and seller.get("name"):
                    return seller["name"].strip()
            elif isinstance(offers, list):
                for offer in offers:
                    seller = offer.get("seller")
                    if isinstance(seller, dict) and seller.get("name"):
                        return seller["name"].strip()

        # CSS: seller info section
        for sel in [
            "#sellerName span span::text",
            "div._3enH3G span span::text",
            'div[id="sellerName"] a span::text',
        ]:
            text = response.css(sel).get()
            if text and text.strip():
                return text.strip()

        return None

    @staticmethod
    def _extract_seller_rating(response) -> Decimal | None:
        """Extract seller rating (shown next to seller name)."""
        # Seller rating is usually a small number like "4.5" near the seller name
        for sel in [
            "#sellerName div._3LWZlK::text",
            'div._3enH3G div._3LWZlK::text',
        ]:
            text = response.css(sel).get()
            if text:
                match = RATING_NUM_RE.search(text)
                if match:
                    try:
                        return Decimal(match.group(1))
                    except InvalidOperation:
                        pass
        return None

    @staticmethod
    def _extract_availability(response, ld_json: dict | None) -> bool:
        """Determine if product is in stock."""
        # JSON-LD
        if ld_json:
            offers = ld_json.get("offers")
            if isinstance(offers, dict):
                avail = offers.get("availability", "")
                if "InStock" in avail:
                    return True
                if "OutOfStock" in avail:
                    return False
            elif isinstance(offers, list):
                for offer in offers:
                    avail = offer.get("availability", "")
                    if "InStock" in avail:
                        return True

        # CSS: check for "Coming Soon" or "Sold Out" or "Currently Unavailable"
        page_text = " ".join(response.css("div._16FRp0::text, div._1dVbu9::text").getall()).lower()
        if "sold out" in page_text or "coming soon" in page_text or "currently unavailable" in page_text:
            return False

        # If there's an "Add to Cart" or "Buy Now" button, assume in stock
        buy_btn = response.css(
            'button._2KpZ6l::text, button.QqFHMw::text, '
            'button[class*="BUY"]::text, button[class*="add-to-cart"]::text'
        ).getall()
        for btn_text in buy_btn:
            lower = btn_text.strip().lower()
            if "buy now" in lower or "add to cart" in lower:
                return True

        # Default: if we found a price, assume in stock
        return bool(response.css("div._30jeq3, div.Nx9bqj"))

    @staticmethod
    def _extract_fulfilled_by(response) -> str | None:
        """Extract fulfilment info — Flipkart Assured or seller-fulfilled."""
        # Flipkart Assured badge
        assured = response.css(
            'img[src*="fa_62673a"]::attr(src), '  # Assured icon URL pattern
            'img[alt*="Assured"]::attr(alt), '
            'img[src*="fk-advantage"]::attr(src)'
        ).get()
        if assured:
            return "Flipkart"

        # XPath: look for "Flipkart Assured" text
        assured_text = response.xpath(
            '//*[contains(text(),"Flipkart Assured") or contains(text(),"F-Assured")]'
        ).get()
        if assured_text:
            return "Flipkart"

        return None

    @staticmethod
    def _extract_specs(response) -> dict[str, str]:
        """Extract technical specifications as key-value pairs.

        Flipkart organises specs in tables under a "Specifications" heading,
        grouped by category (General, Display, Performance, etc.).
        """
        specs: dict[str, str] = {}

        # Primary: specification tables (multiple grouped tables)
        for row in response.css("div._14cfVK tr, table._14cfVK tr"):
            key = row.css("td:first-child::text").get("").strip()
            val = row.css("td:last-child li::text, td:last-child::text").get("").strip()
            if key and val and key != val:
                specs[key] = val

        # Alternative class names
        if not specs:
            for row in response.css("div._3k-BhJ tr, table.G4BRas tr, table._3npaEj tr"):
                key = row.css("td:first-child::text").get("").strip()
                val = row.css("td:last-child::text").get("").strip()
                if key and val and key != val:
                    specs[key] = val

        # XPath fallback: look for the "Specifications" section
        if not specs:
            spec_rows = response.xpath(
                '//div[.//text()="Specifications" or .//text()="SPECIFICATIONS"]'
                '//following-sibling::div//table//tr'
            )
            for row in spec_rows:
                cells = row.xpath(".//td//text()").getall()
                cells = [c.strip() for c in cells if c.strip()]
                if len(cells) >= 2:
                    specs[cells[0]] = cells[-1]

        return specs

    @staticmethod
    def _extract_highlights(response) -> list[str]:
        """Extract product highlights / key features bullet points."""
        bullets: list[str] = []

        # Primary selectors
        for sel in [
            "div._2418kt li::text",
            "div.xFVion li::text",
            "div._3Rrcbo li::text",
        ]:
            items = response.css(sel).getall()
            if items:
                bullets = [b.strip() for b in items if b.strip()]
                break

        # XPath fallback: section headed "Highlights"
        if not bullets:
            items = response.xpath(
                '//div[.//text()="Highlights" or .//text()="HIGHLIGHTS"]'
                '//following-sibling::div[1]//li//text()'
            ).getall()
            bullets = [b.strip() for b in items if b.strip()]

        return bullets

    @staticmethod
    def _extract_offers(response) -> list[dict]:
        """Extract bank offers, exchange offers, and EMI details."""
        offers: list[dict] = []

        # Offer cards on Flipkart — usually in a specific section
        offer_selectors = [
            "div._3Ht4Hy li",      # Offer list items
            "div.DaXhCo li",       # Alternative
            "div._16eBzU li",      # Another variant
        ]

        offer_elements = []
        for sel in offer_selectors:
            offer_elements = response.css(sel)
            if offer_elements:
                break

        for elem in offer_elements:
            text_parts = elem.css("::text").getall()
            offer_text = " ".join(t.strip() for t in text_parts if t.strip())
            if not offer_text or len(offer_text) < 10:
                continue

            offer: dict = {"text": offer_text[:500]}
            lower = offer_text.lower()

            if "cashback" in lower:
                offer["type"] = "cashback"
            elif "no cost emi" in lower or "emi" in lower:
                offer["type"] = "emi"
            elif "exchange" in lower:
                offer["type"] = "exchange"
            elif "coupon" in lower:
                offer["type"] = "coupon"
            elif "bank" in lower or "card" in lower:
                offer["type"] = "bank_offer"
            elif "partner" in lower:
                offer["type"] = "partner_offer"
            else:
                offer["type"] = "other"

            offers.append(offer)

        # XPath fallback: look for "Available offers" section
        if not offers:
            offer_items = response.xpath(
                '//div[.//text()="Available offers" or .//text()="Available Offers"]'
                '//following-sibling::div[1]//li'
            )
            for li in offer_items:
                text_parts = li.xpath(".//text()").getall()
                offer_text = " ".join(t.strip() for t in text_parts if t.strip())
                if offer_text and len(offer_text) >= 10:
                    lower = offer_text.lower()
                    offer_type = "other"
                    if "cashback" in lower:
                        offer_type = "cashback"
                    elif "emi" in lower:
                        offer_type = "emi"
                    elif "exchange" in lower:
                        offer_type = "exchange"
                    elif "bank" in lower or "card" in lower:
                        offer_type = "bank_offer"
                    offers.append({"text": offer_text[:500], "type": offer_type})

        return offers[:10]

    # ------------------------------------------------------------------
    # Category resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_category_from_url(url: str) -> str | None:
        """Extract the Whydud category slug from a Flipkart search URL."""
        from urllib.parse import parse_qs, urlparse

        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            keyword = params.get("q", [None])[0]
            if keyword:
                normalised = keyword.replace("+", " ").strip().lower()
                return KEYWORD_CATEGORY_MAP.get(normalised)
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Parsing utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _json_ld_price(offer: dict) -> Decimal | None:
        """Extract price in paisa from a JSON-LD Offer object.

        JSON-LD prices are in rupees (e.g., ``"price": "24999"`` or ``24999``).
        """
        raw = offer.get("price")
        if raw is None:
            return None
        try:
            rupees = Decimal(str(raw).replace(",", ""))
            if rupees <= 0:
                return None
            return rupees * 100  # → paisa
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _parse_price_text(text: str | None) -> Decimal | None:
        """Parse price text like '₹24,999' to paisa Decimal."""
        if not text:
            return None
        text = text.strip()
        match = PRICE_RE.search(text)
        if not match:
            return None
        cleaned = match.group(0).replace(",", "")
        if not cleaned:
            return None
        try:
            rupees = Decimal(cleaned)
            if rupees <= 0:
                return None
            return rupees * 100
        except InvalidOperation:
            return None

    @staticmethod
    def _high_res_image(url: str) -> str:
        """Upgrade Flipkart image URL to high resolution.

        Flipkart image URLs (hosted on flixcart.com) contain a size segment
        like ``/image/312/312/`` — replace with ``/image/832/832/`` for
        higher resolution.
        """
        return re.sub(r"/image/\d+/\d+/", "/image/832/832/", url)

    @staticmethod
    def _canonical_url(response_url: str, fpid: str) -> str:
        """Build a clean canonical URL for the product.

        Strips tracking params but keeps the product path and FPID.
        """
        # Extract just the path up to and including the FPID
        match = re.search(r"(https://www\.flipkart\.com/.+/p/" + re.escape(fpid) + r")", response_url)
        if match:
            return match.group(1)
        return f"https://www.flipkart.com/product/p/{fpid}"

    def _save_raw_html(self, response, fpid: str) -> str | None:
        """Save response HTML to local filesystem for debugging."""
        try:
            raw_dir = Path(os.environ.get("SCRAPING_RAW_HTML_DIR", "data/raw_html"))
            raw_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"flipkart_{fpid}_{timestamp}.html"
            filepath = raw_dir / filename
            filepath.write_bytes(response.body)
            return str(filepath)
        except OSError as exc:
            self.logger.warning(f"Could not save raw HTML for {fpid}: {exc}")
            return None
