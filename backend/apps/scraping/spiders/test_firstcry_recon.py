#!/usr/bin/env python3
"""FirstCry reconnaissance script — probe site before building spider.

Tests HTTP viability, detects anti-bot protection, identifies data sources
(JSON-LD, embedded JSON, SSR HTML), and recommends the spider approach.

Usage:
    python backend/apps/scraping/spiders/test_firstcry_recon.py
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

# Multiple listing URL candidates — FirstCry may have changed URL patterns
LISTING_URLS = [
    ("Homepage", "https://www.firstcry.com/"),
    ("Baby Care category", "https://www.firstcry.com/baby-care"),
    ("Baby Care search", "https://www.firstcry.com/search?q=baby+care"),
    ("Toys category", "https://www.firstcry.com/toys"),
    ("Diapers category", "https://www.firstcry.com/diapers"),
    ("Brand page", "https://www.firstcry.com/brand/fisher-price"),
    ("Sitemap", "https://www.firstcry.com/sitemap.xml"),
    ("Robots.txt", "https://www.firstcry.com/robots.txt"),
]

FALLBACK_PRODUCT_URL = (
    "https://www.firstcry.com/fisher-price/"
    "fisher-price-laugh-and-learn-counting-and-colors-uno/15542060.html"
)

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
        "ak_bmsc" in str(headers),
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
    """Search for common embedded state patterns in <script> tags."""
    patterns = {
        "__INITIAL_STATE__": r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});",
        "__PRELOADED_STATE__": r"window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});",
        "__NEXT_DATA__": r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        "dataLayer": r"window\.dataLayer\s*=\s*(\[.*?\]);",
        "ssrData": r"window\.ssrData\s*=\s*(\{.*?\});",
        "pageData": r"window\.pageData\s*=\s*(\{.*?\});",
        "productData": r"window\.productData\s*=\s*(\{.*?\});",
        "__data__": r"window\.__data__\s*=\s*(\{.*?\});",
    }
    found = {}
    for name, pat in patterns.items():
        match = re.search(pat, html, re.DOTALL)
        if match:
            raw = match.group(1)
            found[name] = raw[:500]  # First 500 chars for inspection
    return found


def find_product_links(html: str) -> list[str]:
    """Extract product-like URLs from the HTML."""
    # FirstCry product URL pattern: /brand/slug/NUMERIC_ID.html
    pattern = re.compile(
        r'href="(https?://(?:www\.)?firstcry\.com/[^"]*?/\d+\.html)"',
        re.IGNORECASE,
    )
    links = list(set(pattern.findall(html)))
    # Also try relative URLs
    rel_pattern = re.compile(
        r'href="(/[^"]*?/\d+\.html)"',
        re.IGNORECASE,
    )
    for match in rel_pattern.findall(html):
        full = f"https://www.firstcry.com{match}"
        if full not in links:
            links.append(full)
    return links[:20]  # Cap at 20


def find_product_cards(html: str) -> dict:
    """Detect product card patterns in the HTML."""
    card_patterns = {
        "product-card": html.count("product-card"),
        "product-list": html.count("product-list"),
        "product-item": html.count("product-item"),
        "product_card": html.count("product_card"),
        "product_listing": html.count("product_listing"),
        "productCard": html.count("productCard"),
        "listing-card": html.count("listing-card"),
        "plp-card": html.count("plp-card"),
        "search-result": html.count("search-result"),
        "item-card": html.count("item-card"),
        'itemprop="product"': html.count('itemprop="product"'),
        'itemtype="http://schema.org/Product"': html.count(
            'itemtype="http://schema.org/Product"'
        ),
        "data-product": html.count("data-product"),
    }
    return {k: v for k, v in card_patterns.items() if v > 0}


def check_ssr_content(html: str) -> dict:
    """Check if the page has real SSR content or is a JS shell."""
    checks = {
        "has_price_rupee_symbol": "₹" in html,
        "has_price_rs": "Rs." in html.lower() or "rs " in html.lower(),
        "has_mrp": "mrp" in html.lower(),
        "has_add_to_cart": "add to cart" in html.lower() or "add to bag" in html.lower(),
        "has_product_image_tags": bool(re.search(r'<img[^>]*product', html, re.I)),
        "has_rating_stars": "rating" in html.lower() or "stars" in html.lower(),
        "html_length": len(html),
        "script_tag_count": html.count("<script"),
        "img_tag_count": html.count("<img"),
        "has_noscript": "<noscript>" in html.lower(),
    }
    return checks


def fetch_page(url: str, label: str) -> tuple[int, str, dict]:
    """Fetch a page using curl_cffi with Chrome TLS impersonation."""
    print(f"\n{SEPARATOR}")
    print(f"FETCHING: {label}")
    print(f"URL: {url}")
    print(SEPARATOR)

    try:
        resp = cffi_requests.get(
            url,
            headers=HEADERS,
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
        if resp.url != url:
            print(f"Redirected to: {resp.url}")

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
            if t in ("Product", "ItemList"):
                # Print a summary of this useful block
                print(f"\n  JSON-LD ({t}):")
                for key in ("name", "brand", "description", "sku"):
                    if key in block:
                        val = block[key]
                        if isinstance(val, dict):
                            val = val.get("name", val)
                        print(f"    {key}: {str(val)[:80]}")
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

    # Embedded JSON
    embedded = find_embedded_json(html)
    results["embedded_json"] = list(embedded.keys())
    if embedded:
        print(f"\n  Embedded JSON found: {list(embedded.keys())}")
        for name, preview in embedded.items():
            print(f"    {name}: {preview[:150]}...")

    # Product cards
    cards = find_product_cards(html)
    results["product_card_patterns"] = cards
    if cards:
        print(f"\n  Product card patterns: {cards}")

    # Product links
    links = find_product_links(html)
    results["product_links_count"] = len(links)
    if links:
        print(f"\n  Product links found: {len(links)}")
        for link in links[:5]:
            print(f"    {link}")

    return results


def print_report(listing_result: dict, product_result: dict) -> None:
    """Print the final reconnaissance report."""
    print(f"\n\n{'#' * 72}")
    print("FIRSTCRY RECONNAISSANCE REPORT")
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
    print(f"  Has INR prices:        {ssr.get('has_price_rupee_symbol', False)}")
    print(f"  Has Rs. prices:      {ssr.get('has_price_rs', False)}")
    print(f"  Has MRP:             {ssr.get('has_mrp', False)}")
    print(f"  Img tags:            {ssr.get('img_tag_count', 0)}")
    print(f"  Script tags:         {ssr.get('script_tag_count', 0)}")
    print(f"  JSON-LD blocks:      {listing_result.get('json_ld_count', 0)}")
    print(f"  JSON-LD types:       {listing_result.get('json_ld_types', [])}")
    print(f"  Embedded JSON:       {listing_result.get('embedded_json', [])}")
    print(f"  Product card hits:   {listing_result.get('product_card_patterns', {})}")
    print(f"  Product links found: {listing_result.get('product_links_count', 0)}")
    print(f"  Cloudflare blocked:  {listing_result.get('cloudflare_challenge', False)}")
    print(f"  Akamai blocked:      {listing_result.get('akamai_challenge', False)}")

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
    print(f"  Has INR prices:        {pssr.get('has_price_rupee_symbol', False)}")
    print(f"  Has Rs. prices:      {pssr.get('has_price_rs', False)}")
    print(f"  Has MRP:             {pssr.get('has_mrp', False)}")
    print(f"  Has Add-to-Cart:     {pssr.get('has_add_to_cart', False)}")
    print(f"  JSON-LD blocks:      {product_result.get('json_ld_count', 0)}")
    print(f"  JSON-LD types:       {product_result.get('json_ld_types', [])}")
    print(f"  Product JSON-LD:     {has_product_json_ld}")
    print(f"  Embedded JSON:       {product_result.get('embedded_json', [])}")
    print(f"  Cloudflare blocked:  {product_result.get('cloudflare_challenge', False)}")
    print(f"  Akamai blocked:      {product_result.get('akamai_challenge', False)}")

    # Recommendation
    print("\n--- RECOMMENDATION ---")
    listing_blocked = listing_result.get("cloudflare_challenge") or listing_result.get("akamai_challenge")
    product_blocked = product_result.get("cloudflare_challenge") or product_result.get("akamai_challenge")

    if listing_blocked and product_blocked:
        approach = "FULL PLAYWRIGHT — both listing and product pages blocked"
    elif listing_blocked:
        approach = "PLAYWRIGHT LISTING + HTTP DETAIL — listing blocked, product SSR accessible"
    elif not is_ssr:
        approach = "PLAYWRIGHT LISTING + HTTP DETAIL — listing is SPA, product may be SSR"
    elif is_ssr and has_product_json_ld:
        approach = "HTTP-ONLY — listing SSR + product JSON-LD. Best case!"
    elif is_ssr and is_product_ssr:
        approach = "HTTP-ONLY — both pages SSR. Parse HTML with selectors."
    else:
        approach = "HTTP LISTING + PLAYWRIGHT DETAIL — listing SSR but product needs JS"

    print(f"  Approach: {approach}")
    print(f"  Listing phase:  {'Playwright' if listing_blocked or not is_ssr else 'HTTP'}")
    print(f"  Detail phase:   {'Playwright' if product_blocked else 'HTTP' + (' + JSON-LD' if has_product_json_ld else ' + HTML parsing')}")
    print(f"  Proxy needed:   {'Yes' if listing_blocked or product_blocked else 'Probably not (test at volume)'}")
    print(f"  TLS bypass:     curl_cffi recommended (Cloudflare sites)")
    print()


def main() -> None:
    """Run FirstCry reconnaissance."""
    print("FirstCry Reconnaissance -- probing site structure and anti-bot\n")

    # Phase 1: Discovery — probe multiple URLs to find the real site structure
    print(f"\n{'#' * 72}")
    print("PHASE 1: URL DISCOVERY")
    print(f"{'#' * 72}")

    discovery_results = {}
    working_listing_url = None
    working_listing_html = ""
    working_listing_headers = {}

    for label, url in LISTING_URLS:
        status, html, headers = fetch_page(url, label)
        discovery_results[label] = {
            "url": url,
            "status": status,
            "length": len(html),
            "server": headers.get("server", "N/A"),
            "redirected_to": str(getattr(html, "url", "")),
        }

        if status == 200 and len(html) > 5000 and label not in ("Sitemap", "Robots.txt"):
            # Check if this has product-like content
            has_products = (
                find_product_links(html)
                or find_product_cards(html)
                or "product" in html.lower()[:5000]
            )
            if has_products and working_listing_url is None:
                working_listing_url = url
                working_listing_html = html
                working_listing_headers = headers
                print(f"  >>> Found working listing URL: {url}")

        # Print key info from robots.txt and sitemap
        if label == "Robots.txt" and status == 200:
            print(f"\n  robots.txt content (first 1500 chars):\n{html[:1500]}")
        if label == "Sitemap" and status == 200:
            print(f"\n  sitemap.xml content (first 1500 chars):\n{html[:1500]}")

        time.sleep(1.5)

    # Print discovery summary
    print(f"\n{SEPARATOR}")
    print("URL DISCOVERY SUMMARY:")
    for label, info in discovery_results.items():
        print(f"  [{info['status']}] {label}: {info['url']} ({info['length']:,} chars)")

    # Phase 2: Deep analysis of working listing page
    print(f"\n{'#' * 72}")
    print("PHASE 2: LISTING PAGE ANALYSIS")
    print(f"{'#' * 72}")

    listing_result = {}
    if working_listing_url:
        print(f"\nAnalyzing: {working_listing_url}")
        listing_result = analyze_page(working_listing_html, working_listing_headers, "listing")

        # Extract links from the page to understand URL structure
        all_links = re.findall(r'href="([^"]*firstcry\.com[^"]*)"', working_listing_html)
        if not all_links:
            all_links = re.findall(r'href="(/[^"]*)"', working_listing_html)
        unique_paths = sorted(set(all_links))[:30]
        print(f"\n  Sample URLs found on page ({len(unique_paths)}):")
        for link in unique_paths:
            print(f"    {link}")
    else:
        # Use homepage as fallback for analysis
        print("\nNo category page worked. Analyzing homepage...")
        status, html, headers = fetch_page("https://www.firstcry.com/", "Homepage (re-fetch)")
        if status == 200:
            listing_result = analyze_page(html, headers, "listing")
            working_listing_html = html
            working_listing_headers = headers

            # Extract ALL internal links to understand site structure
            all_links = re.findall(r'href="(https?://[^"]*firstcry\.com[^"]*)"', html)
            rel_links = re.findall(r'href="(/[^"]*)"', html)
            all_links += [f"https://www.firstcry.com{l}" for l in rel_links]
            unique_links = sorted(set(all_links))

            print(f"\n  Total unique links on homepage: {len(unique_links)}")
            # Group by path pattern
            category_links = [l for l in unique_links if "/c/" in l or "/category/" in l]
            product_links = [l for l in unique_links if ".html" in l or "/p/" in l or "/product/" in l]
            search_links = [l for l in unique_links if "search" in l.lower()]

            print(f"  Category-like links: {len(category_links)}")
            for l in category_links[:10]:
                print(f"    {l}")
            print(f"  Product-like links: {len(product_links)}")
            for l in product_links[:10]:
                print(f"    {l}")
            print(f"  Search-like links: {len(search_links)}")
            for l in search_links[:5]:
                print(f"    {l}")

            # Show unique path prefixes
            prefixes = set()
            for l in unique_links:
                parts = l.replace("https://www.firstcry.com", "").split("/")
                if len(parts) > 1 and parts[1]:
                    prefixes.add(f"/{parts[1]}/")
            print(f"\n  URL path prefixes: {sorted(prefixes)[:20]}")
        else:
            listing_result = {
                "cloudflare_challenge": False,
                "akamai_challenge": False,
                "ssr_content": {"html_length": 0},
                "json_ld_count": 0,
                "json_ld_types": [],
                "embedded_json": [],
                "product_card_patterns": {},
                "product_links_count": 0,
            }

    time.sleep(2)

    # Phase 3: Product page analysis
    print(f"\n{'#' * 72}")
    print("PHASE 3: PRODUCT PAGE ANALYSIS")
    print(f"{'#' * 72}")

    product_url = FALLBACK_PRODUCT_URL
    discovered_products = find_product_links(working_listing_html) if working_listing_html else []
    if discovered_products:
        product_url = discovered_products[0]
        print(f"  Using discovered product URL: {product_url}")
    else:
        print(f"  No product links found; using fallback URL")

    status2, html2, headers2 = fetch_page(product_url, "PRODUCT PAGE")
    product_result = {}
    if status2 == 200:
        product_result = analyze_page(html2, headers2, "product")

        # Dump a section of the body for manual inspection
        body_match = re.search(r"<body[^>]*>(.*)", html2, re.DOTALL | re.IGNORECASE)
        if body_match:
            body_preview = body_match.group(1)[:3000]
            print(f"\n  Product page body preview (first 3000 chars):\n{body_preview}")
    else:
        print(f"  Non-200 status: {status2}")
        product_result = {
            "cloudflare_challenge": is_cloudflare_challenge(html2, headers2),
            "akamai_challenge": is_akamai_challenge(html2, headers2),
            "ssr_content": {"html_length": len(html2)},
            "json_ld_count": 0,
            "json_ld_types": [],
            "embedded_json": [],
            "product_card_patterns": {},
            "product_links_count": 0,
        }
        if html2:
            print(f"  Response body preview:\n{html2[:1500]}")

    # Phase 4: Print final report
    print_report(listing_result, product_result)


if __name__ == "__main__":
    main()
