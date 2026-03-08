"""Flipkart review spider — scrapes customer reviews for existing product listings.

Targets Flipkart's review listing pages (/product-reviews/<FPID>/?page=N),
sorted by helpfulness.  Only scrapes products that already have a ProductListing
in our DB with fewer than 10 scraped Flipkart reviews.

Flipkart uses React Native Web with obfuscated utility CSS classes that change
frequently.  Rather than chasing class names, this spider uses Playwright's
page.evaluate() to extract review data via JavaScript directly from the rendered
DOM, then injects structured JSON into the page for Scrapy to consume.

Sprint 2.
"""
import json
import re

import scrapy
from scrapy_playwright.page import PageMethod

from apps.scraping.items import ReviewItem
from .base_spider import BaseWhydudSpider

MARKETPLACE_SLUG = "flipkart"

# JS script injected via PageMethod to extract reviews from the rendered DOM
# and write them as a JSON blob into a hidden element Scrapy can read.
EXTRACT_REVIEWS_JS = r"""
() => {
    const reviews = [];
    // Find review containers by walking up from 'Verified Purchase' anchors
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const vpElements = [];
    while (walker.nextNode()) {
        const txt = walker.currentNode.textContent.trim();
        if (txt === 'Verified Purchase' || txt === 'Certified Buyer') {
            vpElements.push(walker.currentNode.parentElement);
        }
    }

    const seen = new Set();
    for (const vpEl of vpElements) {
        // Walk up to find the review container — a div starting with "N.0"
        let container = vpEl;
        for (let i = 0; i < 12; i++) {
            if (!container.parentElement) break;
            container = container.parentElement;
            const text = container.innerText.trim();
            if (text.length > 40 && text.length < 5000 && /^[1-5]\.0/.test(text)) {
                break;
            }
        }

        // Dedup (same container can be found via multiple VP elements)
        const key = container.innerText.substring(0, 100);
        if (seen.has(key)) continue;
        seen.add(key);

        const text = container.innerText;
        const lines = text.split('\n').map(l => l.trim()).filter(l => l);

        // Rating (first line: "5.0" or "4.0")
        const ratingMatch = text.match(/^([1-5])\.0/);
        const rating = ratingMatch ? parseInt(ratingMatch[1]) : null;
        if (!rating) continue;

        // Title — first meaningful line after rating, before "Review for:"
        let title = '';
        let titleIdx = -1;
        for (let i = 0; i < lines.length; i++) {
            const l = lines[i];
            if (/^[1-5]\.0$/.test(l)) continue;
            if (l === '\u2605' || l.length < 2) continue;
            if (/^Review for:/.test(l)) break;
            if (l.length >= 3 && l.length < 200 && !/^Helpful/.test(l) && !/Verified Purchase/.test(l) && !/Certified Buyer/.test(l)) {
                title = l;
                titleIdx = i;
                break;
            }
        }

        // Variant — "Review for: Color Iris Black..."
        let variant = '';
        const variantMatch = text.match(/Review for:\s*(.+?)(?:\n|$)/);
        if (variantMatch) variant = variantMatch[1].trim();

        // Body — text inside <span> elements (the actual review content)
        const spans = container.querySelectorAll('span');
        let body = '';
        for (const sp of spans) {
            const spText = sp.textContent.trim();
            if (spText.length > body.length && spText.length > 10) {
                body = spText;
            }
        }
        if (!body) {
            // Fallback: lines > 20 chars that aren't metadata
            const bodyLines = lines.filter(l =>
                l.length > 15 &&
                !/^[1-5]\.0/.test(l) &&
                !/^Review for:/.test(l) &&
                !/^Helpful/.test(l) &&
                !/Verified Purchase/.test(l) &&
                !/Certified Buyer/.test(l) &&
                l !== title &&
                !/Reviewer$/.test(l) &&
                !/months? ago$/.test(l)
            );
            body = bodyLines.join(' ');
        }

        // Reviewer name — look for text near location pattern ", CityName"
        let reviewerName = '';
        for (let i = 0; i < lines.length; i++) {
            // Name is typically followed by ", Location"
            if (i + 1 < lines.length && /^,\s/.test(lines[i + 1])) {
                reviewerName = lines[i];
                break;
            }
        }

        // Helpful votes — "Helpful for N" or just a number near helpful
        let helpful = 0;
        const helpfulMatch = text.match(/Helpful for (\d[\d,]*)/);
        if (helpfulMatch) {
            helpful = parseInt(helpfulMatch[1].replace(/,/g, ''));
        }

        // Verified purchase
        const isVerified = text.includes('Verified Purchase') || text.includes('Certified Buyer');

        // Date — "Feb, 2024" or "8 months ago"
        let reviewDate = '';
        const dateMatch = text.match(/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*,?\s*\d{4}/i);
        if (dateMatch) {
            reviewDate = dateMatch[0];
        } else {
            const agoMatch = text.match(/\d+\s+months?\s+ago/i);
            if (agoMatch) reviewDate = agoMatch[0];
        }

        // Images
        const images = [];
        const imgs = container.querySelectorAll('img[src*="rukminim"]');
        for (const img of imgs) {
            if (img.src && !img.src.includes('placeholder')) {
                images.push(img.src.replace(/\/image\/\d+\/\d+\//, '/image/832/832/'));
            }
        }

        reviews.push({
            rating, title, body, reviewerName, helpful,
            isVerified, reviewDate, variant, images
        });
    }

    // Inject as JSON for Scrapy to read
    const el = document.createElement('script');
    el.id = 'whydud-reviews';
    el.type = 'application/json';
    el.textContent = JSON.stringify(reviews);
    document.head.appendChild(el);
}
"""


class FlipkartReviewSpider(BaseWhydudSpider):
    """Scrapes Flipkart customer reviews for products we already track.

    Spider arguments (passed via ``-a``):
      max_review_pages — pages per product (default 3; ~10 reviews/page).
    """

    name = "flipkart_reviews"
    allowed_domains = ["flipkart.com", "www.flipkart.com"]

    # No DOWNLOAD_HANDLERS override needed — scrapy_settings.py has it globally.
    # No other overrides needed beyond base spider defaults.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_review_pages = int(kwargs.get("max_review_pages", 3))

        # Optional: only scrape reviews for these specific external IDs
        # Passed as comma-separated string from runner CLI
        raw_ids = kwargs.get("external_ids", "")
        self.external_ids: list[str] = [
            eid.strip() for eid in raw_ids.split(",") if eid.strip()
        ] if raw_ids else []

        # Stats
        self._reviews_scraped: int = 0
        self._products_processed: int = 0
        self._empty_pages: int = 0
        self._js_extraction_failures: int = 0

    # ------------------------------------------------------------------
    # Stealth
    # ------------------------------------------------------------------

    async def _apply_stealth(self, page, request):
        """Apply playwright-stealth scripts to a page before navigation."""
        await self.STEALTH.apply_stealth_async(page)

    # ------------------------------------------------------------------
    # start_requests
    # ------------------------------------------------------------------

    def start_requests(self):
        """Get Flipkart ProductListings to scrape reviews for.

        When ``external_ids`` is set (passed by enrichment worker), only
        scrape those specific products.  Otherwise use the default batch
        (products with < 10 reviews, ordered by popularity, max 200).
        """
        from django.db.models import Count, Q

        from apps.products.models import ProductListing

        if self.external_ids:
            # Targeted mode: only specific products from enrichment pipeline
            listings = ProductListing.objects.filter(
                marketplace__slug="flipkart",
                external_id__in=self.external_ids,
            )
        else:
            # Default batch mode: products needing reviews
            listings = (
                ProductListing.objects.filter(
                    marketplace__slug="flipkart",
                    in_stock=True,
                )
                .annotate(
                    db_review_count=Count(
                        "product__reviews",
                        filter=Q(product__reviews__marketplace__slug="flipkart"),
                    )
                )
                .filter(db_review_count__lt=10)
                .order_by("-product__total_reviews")[:200]
            )

        for listing in listings:
            fpid = listing.external_id
            self._products_processed += 1
            review_url = self._build_review_url(listing.external_url, fpid)
            yield scrapy.Request(
                review_url,
                callback=self.parse_review_page,
                errback=self.handle_error,
                meta={
                    "fpid": fpid,
                    "page": 1,
                    "playwright": True,
                    "playwright_page_init_callback": self._apply_stealth,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                        PageMethod("evaluate", EXTRACT_REVIEWS_JS),
                    ],
                },
                headers=self._make_headers(),
            )

    @staticmethod
    def _build_review_url(external_url: str, fpid: str) -> str:
        """Convert a Flipkart product URL to its review listing page URL."""
        if external_url and "/p/" in external_url:
            base = external_url.split("/p/")[0]
            return f"{base}/product-reviews/{fpid}?page=1&sortOrder=MOST_HELPFUL"
        return (
            f"https://www.flipkart.com/product/product-reviews/{fpid}"
            f"?page=1&sortOrder=MOST_HELPFUL"
        )

    # ------------------------------------------------------------------
    # Review page parsing
    # ------------------------------------------------------------------

    def parse_review_page(self, response):
        """Parse reviews extracted by the JS PageMethod."""
        fpid = response.meta["fpid"]
        page = response.meta["page"]

        # Read the JSON blob injected by EXTRACT_REVIEWS_JS
        json_text = response.css("script#whydud-reviews::text").get("")
        if not json_text:
            self._empty_pages += 1
            self.logger.info(
                f"No reviews found on page {page} for FPID {fpid} "
                f"(JS extraction produced no output — possible DOM structure change)"
            )
            return

        try:
            reviews_data = json.loads(json_text)
        except (json.JSONDecodeError, TypeError) as exc:
            self._js_extraction_failures += 1
            self.logger.warning(
                f"Failed to parse review JSON on page {page} for FPID {fpid}: {exc}"
            )
            return

        if not isinstance(reviews_data, list):
            self._js_extraction_failures += 1
            self.logger.warning(
                f"EXTRACT_REVIEWS_JS returned non-list type on page {page} for FPID {fpid}"
            )
            return

        self.logger.info(
            f"Found {len(reviews_data)} reviews on page {page} for FPID {fpid}"
        )

        # DOM structure change detection: if we got entries but all bodies are
        # empty or very short, the JS extraction logic is probably broken.
        if reviews_data:
            bodies = [rev.get("body", "") for rev in reviews_data]
            non_empty_bodies = [b for b in bodies if len(b) >= 10]
            if not non_empty_bodies:
                self.logger.warning(
                    f"DOM structure change detected: {len(reviews_data)} reviews found "
                    f"on page {page} for FPID {fpid} but ALL bodies are empty or < 10 chars. "
                    f"EXTRACT_REVIEWS_JS may need updating."
                )

        for rev in reviews_data:
            if not rev.get("rating") or not rev.get("body"):
                continue

            item = ReviewItem()
            item["marketplace_slug"] = MARKETPLACE_SLUG
            item["product_external_id"] = fpid
            item["review_id"] = ""  # Pipeline generates content hash
            item["rating"] = rev["rating"]
            item["title"] = rev.get("title", "")
            item["body"] = rev.get("body", "")
            item["reviewer_name"] = rev.get("reviewerName", "")
            item["review_date"] = rev.get("reviewDate", "")
            item["is_verified_purchase"] = rev.get("isVerified", False)
            item["helpful_votes"] = rev.get("helpful", 0)
            item["images"] = rev.get("images", [])
            item["variant"] = rev.get("variant", "")
            item["country"] = "India"
            item["review_url"] = response.url

            yield item
            self._reviews_scraped += 1

        # Pagination
        if page < self.max_review_pages and len(reviews_data) >= 8:
            next_page = page + 1
            next_url = self._build_next_page_url(response.url, next_page)
            yield scrapy.Request(
                next_url,
                callback=self.parse_review_page,
                errback=self.handle_error,
                meta={
                    "fpid": fpid,
                    "page": next_page,
                    "playwright": True,
                    "playwright_page_init_callback": self._apply_stealth,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                        PageMethod("evaluate", EXTRACT_REVIEWS_JS),
                    ],
                },
                headers=self._make_headers(),
            )

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    @staticmethod
    def _build_next_page_url(current_url: str, next_page: int) -> str:
        """Replace or append page number in the review URL."""
        if "page=" in current_url:
            return re.sub(r"page=\d+", f"page={next_page}", current_url)
        separator = "&" if "?" in current_url else "?"
        return f"{current_url}{separator}page={next_page}"

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def closed(self, reason):
        """Log final scrape statistics."""
        self.logger.info(
            f"Spider stats: products_processed={self._products_processed}, "
            f"reviews_scraped={self._reviews_scraped}, "
            f"empty_pages={self._empty_pages}, "
            f"js_extraction_failures={self._js_extraction_failures}, "
            f"failed={self.items_failed}"
        )
