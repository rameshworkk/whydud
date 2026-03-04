#!/usr/bin/env python3
"""Myntra reconnaissance script — probe site before building spider.

Myntra is Flipkart Group — expect aggressive anti-bot protection.
Tests HTTP viability for listing + product pages, probes internal search API,
checks for embedded JSON (pdpData, __myx), detects anti-bot protection,
and recommends the spider approach.

Usage:
    python backend/apps/scraping/spiders/test_myntra_recon.py
"""
import json
import os
import re
import sys
import time

# Fix Windows console encoding for Unicode (rupee symbol etc.)
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from curl_cffi import requests as cffi_requests

# ---------------------------------------------------------------------------
# Headers — realistic Chrome/131 with full Sec-Fetch set
# ---------------------------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-CH-UA": '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
}

# XHR/API headers for internal API probes
API_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-CH-UA": '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Referer": "https://www.myntra.com/",
}

# URLs to probe
LISTING_URL = "https://www.myntra.com/men-tshirts"
LISTING_URL_PAGE2 = "https://www.myntra.com/men-tshirts?p=2"

# Fallback product URL (will prefer discovered URLs from listing page)
FALLBACK_PRODUCT_URL = "https://www.myntra.com/tshirts/roadster/roadster-men-pure-cotton-tshirt/12345678"

# Internal API endpoint candidates (Myntra patterns)
API_ENDPOINTS = [
    (
        "Search API v2",
        "https://www.myntra.com/gateway/v2/search/men-tshirts",
    ),
    (
        "Search API v1",
        "https://www.myntra.com/gateway/v1/search/men-tshirts",
    ),
    (
        "Search API (query param)",
        "https://www.myntra.com/gateway/v2/search?q=men-tshirts&p=1&rows=50",
    ),
    (
        "Browse API",
        "https://www.myntra.com/gateway/v2/browse/men-tshirts",
    ),
    (
        "Category API",
        "https://www.myntra.com/gateway/v2/category/men-tshirts?p=1&rows=50",
    ),
    (
        "Product list API",
        "https://www.myntra.com/gateway/v2/product?q=men-tshirts&p=1&rows=50",
    ),
    (
        "Myntraweb search",
        "https://www.myntra.com/myntraweb/v2/search?q=men+tshirts&p=1&rows=50",
    ),
    (
        "Web API search",
        "https://www.myntra.com/web/v2/search?q=men+tshirts&p=1&rows=50",
    ),
]

SEPARATOR = "=" * 72


def is_cloudflare_challenge(text: str, headers: dict) -> bool:
    """Detect Cloudflare challenge / Turnstile / JS challenge page."""
    signals = [
        "Just a moment..." in text,
        "cf-browser-verification" in text,
        'id="challenge-form"' in text,
        "challenges.cloudflare.com" in text,
        "_cf_chl" in text,
        "Checking if the site connection is secure" in text,
    ]
    header_signals = [
        "cloudflare" in headers.get("server", "").lower(),
        headers.get("cf-ray") is not None,
    ]
    return any(signals) or all(header_signals)


def is_akamai_challenge(text: str, headers: dict) -> bool:
    """Detect Akamai Bot Manager challenge."""
    signals = [
        "_abck" in text,
        "akamaighost" in headers.get("server", "").lower(),
        "akamai" in headers.get("server", "").lower(),
        "ak_bmsc" in str(headers),
        "akam/" in headers.get("server", "").lower(),
    ]
    return any(signals)


def is_perimeterx_challenge(text: str, headers: dict) -> bool:
    """Detect PerimeterX / HUMAN bot protection (used by Flipkart group)."""
    signals = [
        "perimeterx" in text.lower(),
        "px-captcha" in text.lower(),
        "_pxhd" in str(headers),
        "px-block" in text.lower(),
        "human challenge" in text.lower(),
        "Press & Hold" in text,
        "window._pxAppId" in text,
        "window._pxUuid" in text,
    ]
    return any(signals)


def find_json_ld(html: str) -> list[dict]:
    """Extract all JSON-LD blocks from HTML."""
    blocks = []
    pattern = re.compile(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(html):
        try:
            data = json.loads(match.group(1).strip())
            blocks.append(data)
        except json.JSONDecodeError:
            blocks.append({"_raw_error": match.group(1)[:200]})
    return blocks


def find_embedded_json(html: str) -> dict[str, str]:
    """Search for common embedded state patterns in <script> tags.

    Myntra-specific patterns: pdpData, __myx, searchData, etc.
    """
    patterns = {
        # Myntra-specific patterns
        "pdpData": r"pdpData\s*=\s*(\{.*?\});",
        "__myx": r"window\.__myx\s*=\s*(\{.*?\});",
        "searchData": r"searchData\s*=\s*(\{.*?\});",
        "productDetails": r"productDetails\s*=\s*(\{.*?\});",
        # Generic React/SPA state patterns
        "__INITIAL_STATE__": r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});",
        "__PRELOADED_STATE__": r"window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});",
        "__NEXT_DATA__": r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        "dataLayer": r"window\.dataLayer\s*=\s*(\[.*?\]);",
        # Other common Flipkart group patterns
        "ssrData": r"window\.ssrData\s*=\s*(\{.*?\});",
        "pageData": r"window\.pageData\s*=\s*(\{.*?\});",
        "__data__": r"window\.__data__\s*=\s*(\{.*?\});",
        "__STORE__": r"window\.__STORE__\s*=\s*(\{.*?\});",
        "APP_STATE": r"window\.APP_STATE\s*=\s*(\{.*?\});",
    }
    found = {}
    for name, pat in patterns.items():
        match = re.search(pat, html, re.DOTALL)
        if match:
            raw = match.group(1)
            found[name] = raw[:500]  # First 500 chars for inspection
    return found


def find_product_links(html: str) -> list[str]:
    """Extract Myntra product-like URLs from the HTML.

    Myntra product URL pattern: /brand/product-name/NUMERIC_ID
    """
    # Absolute URLs
    pattern = re.compile(
        r'href="((?:https?://(?:www\.)?myntra\.com)?/[^"]*?/\d{6,})"',
        re.IGNORECASE,
    )
    links = []
    for match in pattern.findall(html):
        url = match if match.startswith("http") else f"https://www.myntra.com{match}"
        # Filter out non-product links (e.g., policy pages, etc.)
        # Product URLs typically have a numeric ID at the end
        if re.search(r"/\d{6,}$", url):
            if url not in links:
                links.append(url)
    return links[:20]


def find_product_cards(html: str) -> dict:
    """Detect Myntra product card patterns in the HTML."""
    card_patterns = {
        "product-base": html.count("product-base"),
        "product-brand": html.count("product-brand"),
        "product-product": html.count("product-product"),
        "product-discountedPrice": html.count("product-discountedPrice"),
        "product-strike": html.count("product-strike"),
        "product-ratingsContainer": html.count("product-ratingsContainer"),
        "product-imageSliderContainer": html.count("product-imageSliderContainer"),
        "product-price": html.count("product-price"),
        "product-card": html.count("product-card"),
        "search-searchProductsContainer": html.count("search-searchProductsContainer"),
        "product-sliderContainer": html.count("product-sliderContainer"),
        "data-refreshpage": html.count("data-refreshpage"),
        'itemtype="http://schema.org/Product"': html.count(
            'itemtype="http://schema.org/Product"'
        ),
    }
    return {k: v for k, v in card_patterns.items() if v > 0}


def find_pdp_selectors(html: str) -> dict:
    """Detect Myntra product detail page (PDP) selectors in HTML."""
    pdp_patterns = {
        "pdp-title": html.count("pdp-title"),
        "pdp-name": html.count("pdp-name"),
        "pdp-price": html.count("pdp-price"),
        "pdp-mrp": html.count("pdp-mrp"),
        "pdp-discount": html.count("pdp-discount"),
        "pdp-product-description": html.count("pdp-product-description"),
        "index-overallRating": html.count("index-overallRating"),
        "index-ratingsCount": html.count("index-ratingsCount"),
        "size-buttons-size-body": html.count("size-buttons-size-body"),
        "size-buttons-unified-size": html.count("size-buttons-unified-size"),
        "image-grid-image": html.count("image-grid-image"),
        "pdp-sizeFitDesc": html.count("pdp-sizeFitDesc"),
        "index-tableContainer": html.count("index-tableContainer"),
    }
    return {k: v for k, v in pdp_patterns.items() if v > 0}


def check_ssr_content(html: str) -> dict:
    """Check if the page has real SSR content or is a JS shell."""
    checks = {
        "has_price_rupee_symbol": "\u20b9" in html,
        "has_price_rs": "Rs." in html or "rs " in html.lower(),
        "has_mrp": "mrp" in html.lower(),
        "has_add_to_cart": "add to cart" in html.lower() or "add to bag" in html.lower(),
        "has_product_image_tags": bool(re.search(r"<img[^>]*product", html, re.I)),
        "has_rating_stars": "rating" in html.lower() or "stars" in html.lower(),
        "html_length": len(html),
        "script_tag_count": html.count("<script"),
        "img_tag_count": html.count("<img"),
        "has_noscript": "<noscript>" in html.lower(),
    }
    return checks


def fetch_page(url: str, label: str, headers: dict | None = None) -> tuple[int, str, dict]:
    """Fetch a page using curl_cffi with Chrome TLS impersonation."""
    print(f"\n{SEPARATOR}")
    print(f"FETCHING: {label}")
    print(f"URL: {url}")
    print(SEPARATOR)

    use_headers = headers or HEADERS

    try:
        resp = cffi_requests.get(
            url,
            headers=use_headers,
            impersonate="chrome131",
            timeout=30,
            allow_redirects=True,
        )
        status = resp.status_code
        text = resp.text
        resp_headers = dict(resp.headers)

        print(f"Status: {status}")
        print(f"Content-Length: {len(text)} chars")
        print(f"Content-Type: {resp_headers.get('content-type', 'N/A')}")
        print(f"Server: {resp_headers.get('server', 'N/A')}")

        # Check for redirects
        if str(resp.url) != url:
            print(f"Redirected to: {resp.url}")

        # Check for set-cookie headers (bot detection tokens)
        cookies = resp_headers.get("set-cookie", "")
        if "_abck" in cookies or "ak_bmsc" in cookies:
            print("  [!] Akamai bot manager cookies detected")
        if "bm_sv" in cookies:
            print("  [!] Akamai bot manager session cookie detected")
        if "_pxhd" in cookies or "_pxvid" in cookies:
            print("  [!] PerimeterX cookies detected")

        return status, text, resp_headers

    except Exception as e:
        print(f"ERROR: {e}")
        return 0, "", {}


def analyze_page(html: str, headers: dict, label: str) -> dict:
    """Run all analysis checks on a fetched page."""
    results = {"label": label}

    # Anti-bot detection
    results["cloudflare_challenge"] = is_cloudflare_challenge(html, headers)
    results["akamai_challenge"] = is_akamai_challenge(html, headers)
    results["perimeterx_challenge"] = is_perimeterx_challenge(html, headers)

    # SSR content check
    results["ssr_content"] = check_ssr_content(html)

    # JSON-LD
    json_ld = find_json_ld(html)
    results["json_ld_count"] = len(json_ld)
    results["json_ld_types"] = []
    for block in json_ld:
        if isinstance(block, dict):
            t = block.get("@type", "unknown")
            results["json_ld_types"].append(t)
            if t in ("Product", "ItemList", "BreadcrumbList"):
                print(f"\n  JSON-LD ({t}):")
                for key in ("name", "brand", "description", "sku", "productID"):
                    if key in block:
                        val = block[key]
                        if isinstance(val, dict):
                            val = val.get("name", val)
                        print(f"    {key}: {str(val)[:100]}")
                if "offers" in block:
                    offers = block["offers"]
                    if isinstance(offers, dict):
                        print(f"    price: {offers.get('price', 'N/A')}")
                        print(f"    priceCurrency: {offers.get('priceCurrency', 'N/A')}")
                    elif isinstance(offers, list) and offers:
                        print(f"    offers[0].price: {offers[0].get('price', 'N/A')}")
                if "aggregateRating" in block:
                    ar = block["aggregateRating"]
                    print(f"    rating: {ar.get('ratingValue', 'N/A')}")
                    print(f"    reviewCount: {ar.get('reviewCount', 'N/A')}")
    results["json_ld_data"] = json_ld

    # Embedded JSON (Myntra-specific patterns)
    embedded = find_embedded_json(html)
    results["embedded_json"] = list(embedded.keys())
    if embedded:
        print(f"\n  Embedded JSON found: {list(embedded.keys())}")
        for name, preview in embedded.items():
            print(f"    {name}: {preview[:200]}...")

    # Product cards (listing page selectors)
    cards = find_product_cards(html)
    results["product_card_patterns"] = cards
    if cards:
        print(f"\n  Product card patterns: {cards}")

    # PDP selectors (product detail page)
    pdp = find_pdp_selectors(html)
    results["pdp_selectors"] = pdp
    if pdp:
        print(f"\n  PDP selectors found: {pdp}")

    # Product links
    links = find_product_links(html)
    results["product_links_count"] = len(links)
    results["product_links"] = links
    if links:
        print(f"\n  Product links found: {len(links)}")
        for link in links[:5]:
            print(f"    {link}")

    return results


def probe_internal_apis() -> dict:
    """Probe potential internal API endpoints."""
    print(f"\n{'#' * 72}")
    print("PHASE 4: INTERNAL API PROBING")
    print(f"{'#' * 72}")

    api_results = {}
    for label, url in API_ENDPOINTS:
        print(f"\n{SEPARATOR}")
        print(f"API PROBE: {label}")
        print(f"URL: {url}")
        print(SEPARATOR)

        try:
            resp = cffi_requests.get(
                url,
                headers=API_HEADERS,
                impersonate="chrome131",
                timeout=15,
                allow_redirects=True,
            )
            status = resp.status_code
            text = resp.text
            content_type = resp.headers.get("content-type", "")

            print(f"Status: {status}")
            print(f"Content-Type: {content_type}")
            print(f"Content-Length: {len(text)} chars")

            is_json = False
            if "json" in content_type or text.strip().startswith("{") or text.strip().startswith("["):
                try:
                    data = json.loads(text)
                    is_json = True
                    print(f"  Valid JSON: YES")

                    # Inspect structure
                    if isinstance(data, dict):
                        top_keys = list(data.keys())[:15]
                        print(f"  Top-level keys: {top_keys}")

                        # Look for product data
                        for key in (
                            "products", "items", "results", "data", "searchResults",
                            "searchData", "response", "totalCount", "totalPages",
                        ):
                            if key in data:
                                items = data[key]
                                if isinstance(items, list):
                                    print(f"  '{key}' array: {len(items)} items")
                                    if items:
                                        first = items[0]
                                        if isinstance(first, dict):
                                            print(f"  First item keys: {list(first.keys())[:15]}")
                                            for fk in ("name", "title", "brand", "price", "productId",
                                                        "productName", "brandName", "mrp", "discountedPrice"):
                                                if fk in first:
                                                    print(f"    {fk}: {str(first[fk])[:100]}")
                                elif isinstance(items, dict):
                                    print(f"  '{key}' is dict with keys: {list(items.keys())[:10]}")
                                elif isinstance(items, (int, float)):
                                    print(f"  '{key}': {items}")

                    print(f"\n  Response preview (first 500 chars):")
                    print(f"  {text[:500]}")
                except json.JSONDecodeError:
                    print(f"  Valid JSON: NO (parse error)")
                    print(f"  Response preview: {text[:300]}")
            else:
                # Check if it's an HTML page (redirect to challenge/login)
                if "<html" in text.lower()[:500]:
                    print(f"  Got HTML instead of JSON (likely redirect/challenge)")
                    print(f"  Preview: {text[:300]}")
                else:
                    print(f"  Not JSON. Preview: {text[:300]}")

            api_results[label] = {
                "url": url,
                "status": status,
                "is_json": is_json,
                "content_type": content_type,
                "length": len(text),
            }

        except Exception as e:
            print(f"  ERROR: {e}")
            api_results[label] = {"url": url, "status": 0, "error": str(e)}

        time.sleep(1.5)

    return api_results


def check_pagination(html1: str) -> dict:
    """Check if pagination via ?p=2 works and how many products per page."""
    print(f"\n{'#' * 72}")
    print("PHASE 5: PAGINATION CHECK")
    print(f"{'#' * 72}")

    result = {}

    # Fetch page 2
    status2, html2, headers2 = fetch_page(LISTING_URL_PAGE2, "LISTING PAGE 2 (?p=2)")

    if status2 == 200:
        # Check if page 2 content differs from page 1
        result["page2_status"] = status2
        result["page2_length"] = len(html2)
        result["page1_length"] = len(html1)
        result["content_differs"] = html1[:5000] != html2[:5000]

        cards2 = find_product_cards(html2)
        result["page2_cards"] = cards2
        links2 = find_product_links(html2)
        result["page2_product_links"] = len(links2)

        # Check for pagination controls in HTML
        pagination_patterns = {
            "pagination": html2.lower().count("pagination"),
            "next-page": html2.lower().count("next-page"),
            "page-controller": html2.lower().count("page-controller"),
            "search-paginationContainer": html2.count("search-paginationContainer"),
        }
        result["pagination_controls"] = {k: v for k, v in pagination_patterns.items() if v > 0}

        print(f"\n  Page 2 content differs from Page 1: {result['content_differs']}")
        print(f"  Page 2 product cards: {cards2}")
        print(f"  Page 2 product links: {len(links2)}")
        print(f"  Pagination controls: {result['pagination_controls']}")
    else:
        result["page2_status"] = status2
        print(f"  Page 2 returned status {status2}")

    return result


def print_report(
    listing_result: dict,
    product_result: dict,
    api_results: dict,
    pagination_result: dict,
) -> None:
    """Print the final Myntra reconnaissance report."""
    print(f"\n\n{'#' * 72}")
    print("MYNTRA RECONNAISSANCE REPORT")
    print(f"{'#' * 72}")

    # Listing page analysis
    print("\n--- LISTING PAGE ---")
    ssr = listing_result.get("ssr_content", {})
    is_ssr = (
        ssr.get("has_price_rupee_symbol", False)
        or ssr.get("has_price_rs", False)
    ) and ssr.get("html_length", 0) > 10000

    print(f"  SSR or SPA?          {'SSR (server-rendered)' if is_ssr else 'SPA / JS shell'}")
    print(f"  HTML length:         {ssr.get('html_length', 0):,} chars")
    print(f"  Has INR prices:      {ssr.get('has_price_rupee_symbol', False)}")
    print(f"  Has Rs. prices:      {ssr.get('has_price_rs', False)}")
    print(f"  Has MRP:             {ssr.get('has_mrp', False)}")
    print(f"  Img tags:            {ssr.get('img_tag_count', 0)}")
    print(f"  Script tags:         {ssr.get('script_tag_count', 0)}")
    print(f"  JSON-LD blocks:      {listing_result.get('json_ld_count', 0)}")
    print(f"  JSON-LD types:       {listing_result.get('json_ld_types', [])}")
    print(f"  Embedded JSON:       {listing_result.get('embedded_json', [])}")
    print(f"  Product card hits:   {listing_result.get('product_card_patterns', {})}")
    print(f"  PDP selectors:       {listing_result.get('pdp_selectors', {})}")
    print(f"  Product links found: {listing_result.get('product_links_count', 0)}")
    print(f"  Cloudflare blocked:  {listing_result.get('cloudflare_challenge', False)}")
    print(f"  Akamai blocked:      {listing_result.get('akamai_challenge', False)}")
    print(f"  PerimeterX blocked:  {listing_result.get('perimeterx_challenge', False)}")

    # Product page analysis
    print("\n--- PRODUCT PAGE ---")
    pssr = product_result.get("ssr_content", {})
    is_product_ssr = (
        pssr.get("has_price_rupee_symbol", False)
        or pssr.get("has_price_rs", False)
    ) and pssr.get("html_length", 0) > 5000

    has_product_json_ld = "Product" in product_result.get("json_ld_types", [])

    print(f"  SSR or SPA?          {'SSR (server-rendered)' if is_product_ssr else 'SPA / JS shell'}")
    print(f"  HTML length:         {pssr.get('html_length', 0):,} chars")
    print(f"  Has INR prices:      {pssr.get('has_price_rupee_symbol', False)}")
    print(f"  Has Rs. prices:      {pssr.get('has_price_rs', False)}")
    print(f"  Has MRP:             {pssr.get('has_mrp', False)}")
    print(f"  Has Add-to-Cart:     {pssr.get('has_add_to_cart', False)}")
    print(f"  JSON-LD blocks:      {product_result.get('json_ld_count', 0)}")
    print(f"  JSON-LD types:       {product_result.get('json_ld_types', [])}")
    print(f"  Product JSON-LD:     {has_product_json_ld}")
    print(f"  Embedded JSON:       {product_result.get('embedded_json', [])}")
    print(f"  PDP selectors:       {product_result.get('pdp_selectors', {})}")
    print(f"  Cloudflare blocked:  {product_result.get('cloudflare_challenge', False)}")
    print(f"  Akamai blocked:      {product_result.get('akamai_challenge', False)}")
    print(f"  PerimeterX blocked:  {product_result.get('perimeterx_challenge', False)}")

    # Internal API analysis
    print("\n--- INTERNAL APIs ---")
    working_apis = []
    for label, info in api_results.items():
        status = info.get("status", 0)
        is_json = info.get("is_json", False)
        marker = "OK+JSON" if status == 200 and is_json else f"[{status}]"
        print(f"  {marker:10s} {label}: {info.get('url', 'N/A')}")
        if status == 200 and is_json:
            working_apis.append(label)

    # Pagination analysis
    print("\n--- PAGINATION ---")
    if pagination_result:
        print(f"  Page 2 status:       {pagination_result.get('page2_status', 'N/A')}")
        print(f"  Content differs:     {pagination_result.get('content_differs', 'N/A')}")
        print(f"  Page 2 cards:        {pagination_result.get('page2_cards', {})}")
        print(f"  Page 2 links:        {pagination_result.get('page2_product_links', 0)}")
        print(f"  Pagination controls: {pagination_result.get('pagination_controls', {})}")
    else:
        print("  Not tested")

    # Recommendation
    print("\n--- RECOMMENDATION ---")
    listing_blocked = (
        listing_result.get("cloudflare_challenge")
        or listing_result.get("akamai_challenge")
        or listing_result.get("perimeterx_challenge")
    )
    product_blocked = (
        product_result.get("cloudflare_challenge")
        or product_result.get("akamai_challenge")
        or product_result.get("perimeterx_challenge")
    )

    # Determine listing approach
    if working_apis:
        listing_approach = f"HTTP API ({', '.join(working_apis)})"
        print(f"  >>> BEST: Working internal APIs found: {working_apis}")
    elif listing_blocked:
        listing_approach = "Playwright + stealth + proxy (BLOCKED)"
    elif not is_ssr:
        listing_approach = "Playwright + stealth (SPA, no SSR)"
    else:
        listing_approach = "HTTP (SSR content available)"

    # Determine detail approach
    has_embedded = bool(product_result.get("embedded_json"))
    if has_product_json_ld and not product_blocked:
        detail_approach = "HTTP + JSON-LD (best case)"
    elif has_embedded and not product_blocked:
        embedded_keys = product_result.get("embedded_json", [])
        detail_approach = f"HTTP + embedded JSON ({', '.join(embedded_keys)})"
    elif is_product_ssr and not product_blocked:
        detail_approach = "HTTP + HTML parsing"
    elif product_blocked:
        detail_approach = "Playwright + stealth + proxy (BLOCKED)"
    else:
        detail_approach = "Playwright + stealth (SPA, no SSR)"

    print(f"  Listing phase:   {listing_approach}")
    print(f"  Detail phase:    {detail_approach}")
    print(f"  Proxy needed:    {'Yes — anti-bot detected' if listing_blocked or product_blocked else 'Probably (Flipkart group = aggressive anti-bot)'}")
    print(f"  TLS bypass:      curl_cffi with chrome131 impersonation")

    # Estimate difficulty
    if working_apis and (has_product_json_ld or has_embedded):
        difficulty = "MEDIUM (API + embedded data = minimal Playwright)"
    elif working_apis:
        difficulty = "MEDIUM-HARD (API for listings, Playwright for detail)"
    elif listing_blocked or product_blocked:
        difficulty = "HARD (anti-bot blocking, full Playwright + proxy required)"
    elif not is_ssr:
        difficulty = "HARD (SPA, Playwright for both phases)"
    else:
        difficulty = "MEDIUM (SSR available, HTTP-first approach)"

    print(f"  Difficulty:      {difficulty}")
    print()


def main() -> None:
    """Run Myntra reconnaissance."""
    print("Myntra Reconnaissance -- probing site structure and anti-bot")
    print("(Myntra = Flipkart Group, expect aggressive anti-bot)\n")

    # Phase 1: Listing page
    print(f"\n{'#' * 72}")
    print("PHASE 1: LISTING PAGE ANALYSIS (men-tshirts)")
    print(f"{'#' * 72}")

    status1, html1, headers1 = fetch_page(LISTING_URL, "LISTING PAGE (men-tshirts)")
    listing_result = {}
    if status1 == 200:
        listing_result = analyze_page(html1, headers1, "listing")

        # Extract sample URLs to understand URL patterns
        all_links = re.findall(r'href="([^"]*myntra\.com[^"]*)"', html1)
        if not all_links:
            all_links = re.findall(r'href="(/[^"]*)"', html1)
        product_urls = [l for l in all_links if re.search(r"/\d{6,}", l)]
        print(f"\n  Total links on page: {len(all_links)}")
        print(f"  Product links (numeric ID): {len(product_urls)}")
        for link in product_urls[:5]:
            print(f"    {link}")
    else:
        print(f"  Non-200 status: {status1}")
        listing_result = {
            "cloudflare_challenge": is_cloudflare_challenge(html1, headers1),
            "akamai_challenge": is_akamai_challenge(html1, headers1),
            "perimeterx_challenge": is_perimeterx_challenge(html1, headers1),
            "ssr_content": {"html_length": len(html1)},
            "json_ld_count": 0,
            "json_ld_types": [],
            "embedded_json": [],
            "product_card_patterns": {},
            "pdp_selectors": {},
            "product_links_count": 0,
            "product_links": [],
        }
        if html1:
            print(f"  Response preview:\n{html1[:2000]}")

    time.sleep(2)

    # Phase 2: Product page
    print(f"\n{'#' * 72}")
    print("PHASE 2: PRODUCT PAGE ANALYSIS")
    print(f"{'#' * 72}")

    # Try to use a real product URL from the listing page
    discovered = listing_result.get("product_links", [])
    if not discovered:
        discovered = find_product_links(html1) if html1 else []
    product_url = discovered[0] if discovered else FALLBACK_PRODUCT_URL
    if discovered:
        print(f"  Using discovered product URL: {product_url}")
    else:
        print(f"  No product links found on listing; using fallback URL")

    status2, html2, headers2 = fetch_page(product_url, "PRODUCT PAGE")
    product_result = {}
    if status2 == 200:
        product_result = analyze_page(html2, headers2, "product")

        # Dump body preview for manual inspection
        body_match = re.search(r"<body[^>]*>(.*)", html2, re.DOTALL | re.IGNORECASE)
        if body_match:
            body_preview = body_match.group(1)[:3000]
            print(f"\n  Product page body preview (first 3000 chars):\n{body_preview}")

        # Also search specifically for <script> tags with product data
        script_pattern = re.compile(r"<script[^>]*>(.*?)</script>", re.DOTALL)
        for i, match in enumerate(script_pattern.finditer(html2)):
            content = match.group(1).strip()
            # Look for product-related keywords in script content
            if any(kw in content.lower() for kw in ("pdpdata", "productdetails", "productid", "productname", "mrp")):
                print(f"\n  [!] Script tag #{i} contains product-related data:")
                print(f"      Preview: {content[:500]}...")
                break
    else:
        print(f"  Non-200 status: {status2}")
        product_result = {
            "cloudflare_challenge": is_cloudflare_challenge(html2, headers2),
            "akamai_challenge": is_akamai_challenge(html2, headers2),
            "perimeterx_challenge": is_perimeterx_challenge(html2, headers2),
            "ssr_content": {"html_length": len(html2)},
            "json_ld_count": 0,
            "json_ld_types": [],
            "embedded_json": [],
            "product_card_patterns": {},
            "pdp_selectors": {},
            "product_links_count": 0,
        }
        if html2:
            print(f"  Response preview:\n{html2[:2000]}")

    time.sleep(2)

    # Phase 3: Check for Myntra's mobile site / alternative endpoints
    print(f"\n{'#' * 72}")
    print("PHASE 3: MOBILE SITE / ALTERNATE ENDPOINTS")
    print(f"{'#' * 72}")

    mobile_headers = dict(HEADERS)
    mobile_headers["User-Agent"] = (
        "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
    )
    mobile_headers.pop("Sec-CH-UA-Platform", None)
    mobile_headers["Sec-CH-UA-Mobile"] = "?1"

    status_m, html_m, headers_m = fetch_page(
        LISTING_URL, "MOBILE LISTING PAGE", headers=mobile_headers
    )
    if status_m == 200:
        m_ssr = check_ssr_content(html_m)
        m_cards = find_product_cards(html_m)
        m_links = find_product_links(html_m)
        print(f"  Mobile SSR content: {m_ssr}")
        print(f"  Mobile product cards: {m_cards}")
        print(f"  Mobile product links: {len(m_links)}")
        if m_links:
            for link in m_links[:3]:
                print(f"    {link}")
    else:
        print(f"  Mobile listing returned status {status_m}")

    time.sleep(2)

    # Phase 4: Internal API probing
    api_results = probe_internal_apis()

    time.sleep(1)

    # Phase 5: Pagination
    pagination_result = check_pagination(html1) if html1 else {}

    # Phase 6: Print final report
    print_report(listing_result, product_result, api_results, pagination_result)


if __name__ == "__main__":
    main()
