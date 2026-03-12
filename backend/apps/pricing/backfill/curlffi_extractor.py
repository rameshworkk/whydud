"""curl_cffi product data extractor for P2-P3 enrichment.

Uses Chrome TLS fingerprint impersonation (no browser) to fetch product
pages from Amazon.in and Flipkart, then extracts structured data via
JSON-LD and HTML parsing.

Marketplace support:
  - **Amazon.in**: Works ~55% through residential proxy (depends on IP
    reputation and time of day). Higher during off-peak IST midnight-6am.
  - **Flipkart**: Plain HTTP works for detail pages (same as the spider's
    Phase 2). May get 403 without session cookies — retry logic in
    enrichment.py handles escalation to Playwright after 3 failures.

What it gets (no JS needed):
  - Title, brand, price, MRP, rating, review count, images (up to 7)
  - Specs table, about/highlight bullets, seller name, stock status

What it CANNOT get (requires JS execution):
  - Full image gallery, variant matrix, bank offers, delivery estimates

BF-12 in BACKFILL.md.
"""
from __future__ import annotations

import json
import logging
import re
from decimal import Decimal, InvalidOperation

from curl_cffi.requests import Session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants / regex
# ---------------------------------------------------------------------------

PRICE_RE = re.compile(r"[\d,.]+")
RATING_RE = re.compile(r"([\d.]+)\s*out of\s*5")
RATING_NUM_RE = re.compile(r"([\d.]+)")
REVIEW_COUNT_RE = re.compile(r"([\d,]+)\s*(?:rating|review|customer)", re.IGNORECASE)
ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})")
FPID_RE = re.compile(r"/p/(itm[a-zA-Z0-9]+)")

# Block detection patterns (case-insensitive check on first 10KB)
BLOCK_SIGNALS = [
    b"captcha",
    b"robot",
    b"automated access",
    b"validatecaptcha",
    b"sorry, you have been blocked",
    b"api-services-support@amazon.com",
]

# Common headers to look like a real browser
_BASE_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_product_data(
    url: str,
    marketplace_slug: str,
    proxy_url: str | None = None,
) -> dict | None:
    """Fetch a product page via HTTP and extract structured data.

    Args:
        url: Full product URL (e.g. https://www.amazon.in/dp/B0CX23GFMV).
        marketplace_slug: ``"amazon-in"`` or ``"flipkart"``.
        proxy_url: Optional residential proxy URL for higher success rate.

    Returns:
        Dict with keys: title, brand, price (paisa), mrp (paisa), rating,
        review_count, images, in_stock, specs, about_bullets, seller_name,
        external_id.  Returns ``None`` if blocked or CAPTCHA detected.
    """
    html = _fetch_page(url, marketplace_slug, proxy_url)
    if html is None:
        return None

    if marketplace_slug in ("amazon-in", "amazon-com"):
        return _extract_amazon(html, url)
    elif marketplace_slug == "flipkart":
        return _extract_flipkart(html, url)
    else:
        logger.warning("Unsupported marketplace for curl_cffi: %s", marketplace_slug)
        return None


# ---------------------------------------------------------------------------
# HTTP fetch
# ---------------------------------------------------------------------------


def _fetch_page(
    url: str,
    marketplace_slug: str = "",
    proxy_url: str | None = None,
) -> str | None:
    """Fetch page HTML via curl_cffi with Chrome TLS impersonation.

    Adds marketplace-specific headers (Referer, etc.) to mimic a browser
    navigating from a listing/search page — same pattern as the Scrapy
    spiders' plain-HTTP detail page requests.

    Returns HTML string or None if blocked/error.
    """
    headers = {**_BASE_HEADERS}

    # Marketplace-specific headers — mimic navigation from listing page
    if marketplace_slug == "flipkart":
        headers["Referer"] = "https://www.flipkart.com/search?q=product"
    elif marketplace_slug in ("amazon-in", "amazon_in"):
        headers["Referer"] = "https://www.amazon.in/"
    elif marketplace_slug == "amazon-com":
        headers["Referer"] = "https://www.amazon.com/"

    try:
        session = Session(impersonate="chrome120")
        proxies = {"https": proxy_url, "http": proxy_url} if proxy_url else None
        resp = session.get(
            url,
            headers=headers,
            timeout=30,
            proxies=proxies,
            allow_redirects=True,
        )
    except Exception:
        logger.exception("curl_cffi request failed: %s", url)
        return None

    if resp.status_code != 200:
        logger.info("Non-200 status %d for %s", resp.status_code, url)
        return None

    # Check for blocks in first 10KB of raw bytes
    snippet = resp.content[:10240].lower()
    for signal in BLOCK_SIGNALS:
        if signal in snippet:
            logger.info("Block detected (%s) for %s", signal.decode(), url)
            return None

    # Amazon empty challenge page: <title>Amazon.in</title> or <title>Amazon.com</title> with tiny body
    if (b"<title>Amazon.in</title>" in snippet or b"<title>Amazon.com</title>" in snippet) and len(resp.content) < 30000:
        logger.info("Empty challenge page for %s", url)
        return None

    return resp.text


# ---------------------------------------------------------------------------
# Amazon.in extraction
# ---------------------------------------------------------------------------


def _extract_amazon(html: str, url: str) -> dict | None:
    """Extract product data from Amazon.in HTML."""
    from scrapy.http import HtmlResponse

    response = HtmlResponse(url=url, body=html, encoding="utf-8")

    # --- JSON-LD ---
    ld = _parse_json_ld(response)

    # --- External ID ---
    external_id = _amazon_asin(response)

    # --- Title ---
    title = None
    if ld:
        title = ld.get("name", "").strip() or None
    if not title:
        for sel in [
            "#productTitle::text",
            "#title span::text",
            "h1#title span.a-text-normal::text",
            "h1 span::text",
        ]:
            t = response.css(sel).get()
            if t and t.strip():
                title = t.strip()
                break
    if not title:
        title = response.css('meta[property="og:title"]::attr(content)').get()
        if title:
            title = title.strip()

    if not title:
        return None  # No title = nothing useful

    # --- Brand ---
    brand = None
    if ld:
        b = ld.get("brand")
        if isinstance(b, dict):
            brand = b.get("name", "").strip() or None
        elif isinstance(b, str):
            brand = b.strip() or None
    if not brand:
        raw = response.css("a#bylineInfo::text").get()
        if raw:
            # "Visit the Apple Store" → "Apple"
            brand = (
                raw.strip()
                .removeprefix("Visit the ")
                .removeprefix("Brand: ")
                .removesuffix(" Store")
                .strip()
            ) or None
    if not brand:
        for row in response.css("#productDetails_techSpec_section_1 tr"):
            label = row.css("th::text").get("").strip().lower()
            if label in ("brand", "manufacturer"):
                brand = row.css("td::text").get("").strip() or None
                if brand:
                    break

    # --- Price ---
    price = None
    if ld:
        offers = ld.get("offers")
        price = _json_ld_price(offers)
    if price is None:
        for sel in [
            "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen::text",
            "#dealprice_feature_div .a-price .a-offscreen::text",
            "#apex_desktop .a-price .a-offscreen::text",
            "span.a-price span.a-offscreen::text",
            "#priceblock_dealprice::text",
            "#priceblock_ourprice::text",
        ]:
            text = response.css(sel).get()
            price = _rupees_to_paisa(text)
            if price is not None:
                break

    # --- MRP ---
    mrp = None
    for sel in [
        ".basisPrice .a-text-price span.a-offscreen::text",
        "#corePriceDisplay_desktop_feature_div .a-text-price span.a-offscreen::text",
        "span.a-text-price span.a-offscreen::text",
        "#listPrice::text",
        "#priceblock_listprice::text",
    ]:
        text = response.css(sel).get()
        mrp = _rupees_to_paisa(text)
        if mrp is not None:
            break

    # --- Rating ---
    rating = None
    if ld:
        agg = ld.get("aggregateRating")
        if isinstance(agg, dict) and agg.get("ratingValue") is not None:
            try:
                rating = float(Decimal(str(agg["ratingValue"])))
            except (InvalidOperation, ValueError):
                pass
    if rating is None:
        for sel in [
            "#acrPopover span.a-icon-alt::text",
            'span[data-hook="rating-out-of-text"]::text',
            "#averageCustomerReviews .a-icon-alt::text",
        ]:
            text = response.css(sel).get()
            if text:
                m = RATING_RE.search(text)
                if m:
                    try:
                        rating = float(Decimal(m.group(1)))
                    except (InvalidOperation, ValueError):
                        pass
                    break

    # --- Review count ---
    review_count = None
    if ld:
        agg = ld.get("aggregateRating")
        if isinstance(agg, dict):
            for key in ("reviewCount", "ratingCount"):
                val = agg.get(key)
                if val is not None:
                    try:
                        review_count = int(val)
                    except (ValueError, TypeError):
                        pass
                    if review_count:
                        break
    if review_count is None:
        for sel in [
            "#acrCustomerReviewText::text",
            'span[data-hook="total-review-count"] span::text',
            "#acrCustomerReviewLink span::text",
        ]:
            text = response.css(sel).get()
            if text:
                m = REVIEW_COUNT_RE.search(text)
                if m:
                    review_count = int(m.group(1).replace(",", ""))
                    break

    # --- Images ---
    images = []
    if ld:
        img = ld.get("image")
        if isinstance(img, str) and img:
            images.append(img)
        elif isinstance(img, list):
            for i in img:
                if isinstance(i, str) and i:
                    images.append(i)
    if not images:
        main = response.css("#landingImage::attr(data-old-hires)").get()
        if not main:
            main = response.css("#landingImage::attr(src)").get()
        if not main:
            main = response.css("#imgBlkFront::attr(src)").get()
        if main:
            images.append(main)
    # Try dynamic image JSON for more images
    if len(images) <= 1:
        dynamic = response.css("#landingImage::attr(data-a-dynamic-image)").get()
        if dynamic:
            try:
                url_map = json.loads(dynamic)
                sorted_urls = sorted(
                    url_map.items(), key=lambda x: x[1][0], reverse=True,
                )
                for img_url, _ in sorted_urls[:6]:
                    if img_url not in images:
                        images.append(img_url)
            except (json.JSONDecodeError, TypeError, IndexError):
                pass

    # --- In stock ---
    in_stock = None
    if ld:
        offers = ld.get("offers")
        if isinstance(offers, dict):
            avail = offers.get("availability", "")
            if "InStock" in avail:
                in_stock = True
            elif "OutOfStock" in avail:
                in_stock = False
        elif isinstance(offers, list):
            for offer in offers:
                avail = offer.get("availability", "")
                if "InStock" in avail:
                    in_stock = True
                    break
                if "OutOfStock" in avail:
                    in_stock = False
    if in_stock is None:
        for sel in [
            "#availability span.a-size-medium::text",
            "#availability span::text",
        ]:
            text = response.css(sel).get()
            if text:
                lower = text.strip().lower()
                if "in stock" in lower:
                    in_stock = True
                    break
                if "currently unavailable" in lower or "out of stock" in lower:
                    in_stock = False
                    break
    if in_stock is None:
        in_stock = price is not None  # If we found a price, assume in stock

    # --- Specs ---
    specs = {}
    for row in response.css("#productDetails_techSpec_section_1 tr"):
        key = row.css("th::text").get("").strip()
        val = row.css("td::text").get("").strip()
        if key and val:
            specs[key] = val
    if not specs:
        for row in response.css("#productDetails_detailBullets_sections1 tr"):
            key = row.css("th::text").get("").strip()
            val = row.css("td::text").get("").strip()
            if key and val:
                specs[key] = val
    if not specs:
        for li in response.css("#detailBullets_feature_div li"):
            parts = [
                t.strip()
                for t in li.css("span.a-list-item::text").getall()
                if t.strip()
            ]
            if len(parts) >= 2:
                key = parts[0].rstrip(" :\u200f\u200e")
                val = parts[1].lstrip(" :\u200f\u200e")
                if key and val:
                    specs[key] = val

    # --- About bullets ---
    about_bullets = []
    for span in response.css(
        "#feature-bullets ul li span.a-list-item::text"
    ).getall():
        text = span.strip()
        if text and not text.startswith("\u203a"):  # ›
            about_bullets.append(text)

    # --- Description ---
    description = None
    if ld:
        desc = ld.get("description", "").strip()
        if desc:
            description = desc
    if not description:
        for sel in [
            "#productDescription p::text",
            "#productDescription span::text",
            "#productDescription::text",
        ]:
            texts = response.css(sel).getall()
            joined = " ".join(t.strip() for t in texts if t.strip())
            if joined:
                description = joined
                break

    # --- Seller name ---
    seller_name = None
    if ld:
        offers = ld.get("offers")
        if isinstance(offers, dict):
            seller = offers.get("seller")
            if isinstance(seller, dict) and seller.get("name"):
                seller_name = seller["name"].strip()
        elif isinstance(offers, list):
            for offer in offers:
                seller = offer.get("seller")
                if isinstance(seller, dict) and seller.get("name"):
                    seller_name = seller["name"].strip()
                    break
    if not seller_name:
        for sel in [
            "#sellerProfileTriggerId::text",
            "#merchant-info a::text",
            '#tabular-buybox .tabular-buybox-text[tabular-attribute-name="Sold by"] span::text',
        ]:
            text = response.css(sel).get()
            if text and text.strip():
                seller_name = text.strip()
                break

    return {
        "title": title,
        "brand": brand,
        "price": int(price) if price is not None else None,
        "mrp": int(mrp) if mrp is not None else None,
        "rating": rating,
        "review_count": review_count,
        "images": images[:10],
        "in_stock": in_stock,
        "specs": specs,
        "about_bullets": about_bullets,
        "description": description,
        "seller_name": seller_name,
        "external_id": external_id,
    }


# ---------------------------------------------------------------------------
# Flipkart extraction
# ---------------------------------------------------------------------------


def _extract_flipkart(html: str, url: str) -> dict | None:
    """Extract product data from Flipkart HTML."""
    from scrapy.http import HtmlResponse

    response = HtmlResponse(url=url, body=html, encoding="utf-8")

    # --- JSON-LD ---
    ld = _parse_json_ld(response)

    # --- Redux state ---
    initial_state = _parse_flipkart_initial_state(html)

    # --- External ID ---
    external_id = None
    m = FPID_RE.search(url)
    if m:
        external_id = m.group(1)
    elif "pid=" in url:
        external_id = url.split("pid=")[-1].split("&")[0] or None

    # --- Title ---
    title = None
    if ld:
        title = ld.get("name", "").strip() or None
    if not title:
        for sel in [
            "span.VU-ZEz::text",
            "h1._6EBuvT span::text",
            "h1 span.B_NuCI::text",
        ]:
            t = response.css(sel).get()
            if t and t.strip():
                title = t.strip()
                break
    if not title:
        return None

    # --- Brand ---
    brand = None
    if ld:
        b = ld.get("brand")
        if isinstance(b, dict):
            brand = b.get("name", "").strip() or None
        elif isinstance(b, str):
            brand = b.strip() or None
    if not brand and initial_state:
        bd = initial_state.get("bd")
        if bd:
            brand = str(bd).strip() or None
    if not brand:
        breadcrumbs = response.css(
            "div._1MR4o5 a::text, div._2whKao a::text"
        ).getall()
        if len(breadcrumbs) >= 3:
            brand = breadcrumbs[2].strip() or None

    # --- Price ---
    price = None
    if ld:
        price = _json_ld_price(ld.get("offers"))
    if price is None and initial_state:
        ppd = initial_state.get("ppd", {})
        for key in ("finalPrice", "fsp"):
            raw = ppd.get(key)
            if raw is not None:
                try:
                    rupees = Decimal(str(raw))
                    if rupees > 0:
                        price = int(rupees * 100)
                        break
                except (InvalidOperation, ValueError):
                    pass
    if price is None:
        for sel in [
            "div._30jeq3::text",
            "div._16Jk6d::text",
            "div.Nx9bqj::text",
            "div.hl05eU div.Nx9bqj::text",
        ]:
            text = response.css(sel).get()
            price = _rupees_to_paisa(text)
            if price is not None:
                break

    # --- MRP ---
    mrp = None
    if initial_state:
        ppd = initial_state.get("ppd", {})
        raw = ppd.get("mrp")
        if raw is not None:
            try:
                rupees = Decimal(str(raw))
                if rupees > 0:
                    mrp = int(rupees * 100)
            except (InvalidOperation, ValueError):
                pass
    if mrp is None:
        for sel in [
            "div._3I9_wc::text",
            "div._2p6lqe::text",
            "div.yRaY8j::text",
        ]:
            text = response.css(sel).get()
            mrp = _rupees_to_paisa(text)
            if mrp is not None:
                break

    # --- Rating ---
    rating = None
    if ld:
        agg = ld.get("aggregateRating")
        if isinstance(agg, dict) and agg.get("ratingValue") is not None:
            try:
                rating = float(Decimal(str(agg["ratingValue"])))
            except (InvalidOperation, ValueError):
                pass
    if rating is None:
        for sel in [
            "div._3LWZlK::text",
            "span._1lRcqv::text",
            "div.XQDdHH::text",
        ]:
            text = response.css(sel).get()
            if text:
                m = RATING_NUM_RE.search(text)
                if m:
                    try:
                        rating = float(Decimal(m.group(1)))
                    except (InvalidOperation, ValueError):
                        pass
                    break

    # --- Review count ---
    review_count = None
    if ld:
        agg = ld.get("aggregateRating")
        if isinstance(agg, dict):
            for key in ("reviewCount", "ratingCount"):
                val = agg.get(key)
                if val is not None:
                    try:
                        review_count = int(val)
                    except (ValueError, TypeError):
                        pass
                    if review_count:
                        break
    if review_count is None:
        for sel in [
            "span._2_R_DZ::text",
            "span._13vcW::text",
            'div[class*="row"] span._2_R_DZ span::text',
        ]:
            for text in response.css(sel).getall():
                m2 = REVIEW_COUNT_RE.search(text)
                if m2:
                    review_count = int(m2.group(1).replace(",", ""))
                    break
            if review_count is not None:
                break

    # --- Images ---
    images = []
    if ld:
        img = ld.get("image")
        if isinstance(img, str) and img:
            images.append(_flipkart_high_res(img))
        elif isinstance(img, list):
            for i in img:
                if isinstance(i, str) and i:
                    images.append(_flipkart_high_res(i))
    if not images:
        for img_url in response.css(
            'div._3kidJX img::attr(src), '
            'ul._1-n69S li img::attr(src), '
            'div._2E1FGS img::attr(src), '
            'div._1BweB8 img::attr(src)'
        ).getall():
            if "placeholder" in img_url:
                continue
            full = _flipkart_high_res(img_url)
            if full not in images:
                images.append(full)
    if not images:
        for img_url in response.css('img[src*="rukminim"]::attr(src)').getall():
            full = _flipkart_high_res(img_url)
            if full not in images:
                images.append(full)

    # --- In stock ---
    in_stock = None
    if ld:
        offers = ld.get("offers")
        if isinstance(offers, dict):
            avail = offers.get("availability", "")
            if "InStock" in avail:
                in_stock = True
            elif "OutOfStock" in avail:
                in_stock = False
        elif isinstance(offers, list):
            for offer in offers:
                avail = offer.get("availability", "")
                if "InStock" in avail:
                    in_stock = True
                    break
                if "OutOfStock" in avail:
                    in_stock = False
    if in_stock is None and initial_state:
        pls = initial_state.get("pls", {})
        status = pls.get("availabilityStatus", "")
        if status == "IN_STOCK":
            in_stock = True
        elif status in ("OUT_OF_STOCK", "UNAVAILABLE"):
            in_stock = False
        else:
            nb = initial_state.get("nb", {})
            if nb.get("isNonBuyable"):
                in_stock = False
    if in_stock is None:
        page_text = " ".join(
            response.css("div._16FRp0::text, div._1dVbu9::text").getall()
        ).lower()
        if "sold out" in page_text or "currently unavailable" in page_text:
            in_stock = False
    if in_stock is None:
        in_stock = price is not None

    # --- Specs ---
    specs = {}
    for row in response.css("div._14cfVK tr, table._14cfVK tr"):
        key = row.css("td:first-child::text").get("").strip()
        val = row.css("td:last-child li::text, td:last-child::text").get("").strip()
        if key and val and key != val:
            specs[key] = val
    if not specs:
        for row in response.css(
            "div._3k-BhJ tr, table.G4BRas tr, table._3npaEj tr"
        ):
            key = row.css("td:first-child::text").get("").strip()
            val = row.css("td:last-child::text").get("").strip()
            if key and val and key != val:
                specs[key] = val

    # --- Highlights / about bullets ---
    about_bullets = []
    for sel in [
        "div._2418kt li::text",
        "div.xFVion li::text",
        "div._3Rrcbo li::text",
    ]:
        items = response.css(sel).getall()
        if items:
            about_bullets = [b.strip() for b in items if b.strip()]
            break

    # --- Description ---
    description = None
    if ld:
        desc = ld.get("description", "").strip()
        if desc:
            description = desc
    if not description:
        for sel in [
            "div._1mXcCf::text",
            "div._1mXcCf p::text",
            "div._4gvKMe div::text",
        ]:
            texts = response.css(sel).getall()
            joined = " ".join(t.strip() for t in texts if t.strip())
            if joined:
                description = joined
                break

    # --- Seller name ---
    seller_name = None
    if ld:
        offers = ld.get("offers")
        if isinstance(offers, dict):
            seller = offers.get("seller")
            if isinstance(seller, dict) and seller.get("name"):
                seller_name = seller["name"].strip()
        elif isinstance(offers, list):
            for offer in offers:
                seller = offer.get("seller")
                if isinstance(seller, dict) and seller.get("name"):
                    seller_name = seller["name"].strip()
                    break
    if not seller_name and initial_state:
        pls = initial_state.get("pls", {})
        sid = pls.get("sellerId")
        if sid:
            seller_name = str(sid)
    if not seller_name:
        for sel in [
            "#sellerName span span::text",
            "div._3enH3G span span::text",
            'div[id="sellerName"] a span::text',
        ]:
            text = response.css(sel).get()
            if text and text.strip():
                seller_name = text.strip()
                break

    return {
        "title": title,
        "brand": brand,
        "price": int(price) if price is not None else None,
        "mrp": int(mrp) if mrp is not None else None,
        "rating": rating,
        "review_count": review_count,
        "images": images[:10],
        "in_stock": in_stock,
        "specs": specs,
        "about_bullets": about_bullets,
        "description": description,
        "seller_name": seller_name,
        "external_id": external_id,
    }


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _parse_json_ld(response) -> dict | None:
    """Extract the first schema.org Product JSON-LD block from the page."""
    for script in response.css(
        'script[type="application/ld+json"]::text'
    ).getall():
        try:
            data = json.loads(script)
        except (json.JSONDecodeError, ValueError):
            continue

        if isinstance(data, list):
            for obj in data:
                if isinstance(obj, dict) and obj.get("@type") == "Product":
                    return obj
        elif isinstance(data, dict):
            if data.get("@type") == "Product":
                return data
            for obj in data.get("@graph", []):
                if isinstance(obj, dict) and obj.get("@type") == "Product":
                    return obj
    return None


def _parse_flipkart_initial_state(html: str) -> dict | None:
    """Extract product summary (psi) from window.__INITIAL_STATE__."""
    marker = "window.__INITIAL_STATE__"
    idx = html.find(marker)
    if idx < 0:
        return None

    eq_idx = html.find("=", idx)
    if eq_idx < 0:
        return None
    json_start = html.find("{", eq_idx)
    if json_start < 0:
        return None

    try:
        decoder = json.JSONDecoder()
        state, _ = decoder.raw_decode(html, json_start)
        psi = (
            state.get("pageDataV4", {})
            .get("page", {})
            .get("pageData", {})
            .get("pageContext", {})
            .get("fdpEventTracking", {})
            .get("events", {})
            .get("psi", {})
        )
        if psi:
            return psi
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        pass

    return None


def _json_ld_price(offers) -> int | None:
    """Extract price in paisa from a JSON-LD offers field."""
    if isinstance(offers, dict):
        raw = offers.get("price")
        if raw is not None:
            try:
                rupees = Decimal(str(raw).replace(",", ""))
                if rupees > 0:
                    return int(rupees * 100)
            except (InvalidOperation, ValueError):
                pass
    elif isinstance(offers, list):
        for offer in offers:
            raw = offer.get("price")
            if raw is not None:
                try:
                    rupees = Decimal(str(raw).replace(",", ""))
                    if rupees > 0:
                        return int(rupees * 100)
                except (InvalidOperation, ValueError):
                    pass
    return None


def _rupees_to_paisa(text: str | None) -> int | None:
    """Parse price text like '₹24,999' or '₹1,24,999.00' to paisa integer."""
    if not text:
        return None
    text = text.strip()
    match = PRICE_RE.search(text)
    if not match:
        return None
    cleaned = match.group(0).replace(",", "")
    try:
        rupees = Decimal(cleaned)
        if rupees <= 0:
            return None
        return int(rupees * 100)
    except InvalidOperation:
        return None


def _amazon_asin(response) -> str | None:
    """Extract ASIN from Amazon URL or page."""
    m = ASIN_RE.search(response.url)
    if m:
        return m.group(1)
    asin = response.css('input[name="ASIN"]::attr(value)').get()
    if asin:
        return asin.strip()
    asin = response.css("#ASIN::attr(value)").get()
    return asin.strip() if asin else None


def _flipkart_high_res(url: str) -> str:
    """Upgrade Flipkart image URL to high resolution (832x832)."""
    return re.sub(r"/image/\d+/\d+/", "/image/832/832/", url)
