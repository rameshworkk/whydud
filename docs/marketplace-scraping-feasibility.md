# Marketplace Scraping Feasibility Report

> Investigated 2026-03-03. Each site probed via curl for public APIs, SSR data patterns, anti-bot systems, and framework detection.

---

Marketplace Scraping Feasibility Report
Summary Table
Site	Has Public API?	Data Format	Anti-Bot	Framework	Difficulty	Recommended Approach
Reliance Digital	YES — /ext/raven-api/catalog/v1.0/products	JSON API (no auth!)	Akamai (API unprotected)	Vue.js (Fynd Commerce)	Easy (2/10)	HTTP + JSON API
Vijay Sales	YES — Unbxd Search API	JSON API (public key, open CORS)	Akamai CDN + Fastly (minimal)	Adobe AEM + Magento	Easy (2/10)	HTTP + JSON API
Snapdeal	No (old API deprecated)	SSR HTML + schema.org microdata	None (AWS CloudFront only)	Java/Tomcat + jQuery	Easy (3/10)	HTTP + HTML parsing
Nykaa	No (gateway-api returns 403)	SSR HTML + __PRELOADED_STATE__ + JSON-LD	Akamai (bypassed with headers)	React SSR (custom, not Next.js)	Medium (4/10)	HTTP + HTML parsing (with Sec-Fetch headers)
JioMart	No (internal APIs return 503)	Hybrid — SSR on PDP, CSR on listings	Akamai WAF (header-sensitive)	jQuery + Vue.js	Medium (5/10)	Sitemap discovery + HTTP for PDPs
Tata CLiQ	No (APIs broken/protected)	Pure CSR SPA (<div id="root">)	Cloudflare Bot Management	React + Redux SPA	Hard (7/10)	Playwright required (all pages)
Croma	No (Hybris APIs blocked)	React SSR (no NEXT_DATA)	Akamai Bot Manager (aggressive)	React SSR (custom)	Hard (8/10)	Playwright + stealth + proxy
Meesho	No (APIs return 403)	CSR via Next.js (empty __next)	Akamai Bot Manager (aggressive)	Next.js Pages Router	Hard (8/10)	Playwright + stealth + proxy
Tier 1 — Easy (HTTP-only, no Playwright)
Reliance Digital
API: GET /ext/raven-api/catalog/v1.0/products?q={query}&page={n}&pageSize=24 — zero auth required
Backup: /ext/raven-api/catalog//v1.0/collections/{slug}/items (note double slash)
Data: Rich JSON — name, brand, prices (rupees), specs, EAN, images, stock, country of origin
Platform: Fynd Commerce (same as JioMart backend) — x-fynd-trace-id in responses
Watch out: Prices in rupees (not paisa), rating data is sparse (external review widget), pagination quirks on search API
Vijay Sales
API: Unbxd Search at search.unbxd.io/{api_key}/{site_key}/search?q={query}&rows=50&start={offset}
API Key: bb8ef7667d38c04e8a81c80f4a43a998 (public, embedded in HTML)
Data: 5,124 products total. Rich fields: title, brand, SKU, price/MRP/offerPrice, images, warranty, city-specific pricing
Unique: Per-city pricing (e.g., cityId_10_price for Delhi). No reviews in API — need HTML for those
Filtering: &filter=brand_uFilter:"Samsung" works. Field selection: &fields=field1,field2
Snapdeal
Approach: HTTP + HTML parsing (fully SSR, zero anti-bot)
Search: /search?keyword={term}&noOfResults=20&offset={N} — products in .product-tuple-listing elements
Detail: /product/{slug}/{pogId} — rich itemprop microdata (name, price, brand, rating, reviews, seller)
Watch out: /honeybot honeypot link — spider must NOT follow it. Slug is required in product URLs
Tier 2 — Medium (HTTP with proper headers)
Nykaa
Approach: HTTP + HTML parsing with full browser headers (Sec-Fetch-*, sec-ch-ua required)
Data sources (3 complementary):
window.__PRELOADED_STATE__ — richest: name, SKU, MRP, offerPrice, rating, reviewCount, variants, stock
JSON-LD Product schema on PDPs — clean structured data
window.dataLayer — analytics data with product summary
Quirk: Search URLs redirect 302 to category pages. Use category URLs directly
Headers: Must include Sec-Fetch-Dest: document, sec-ch-ua, Upgrade-Insecure-Requests: 1
JioMart
Approach: Sitemap-based discovery + HTTP for product detail pages
Discovery: jiomart.com/sitemap.xml → 6 sub-sitemaps (electronics, fashion, etc.) with product URLs
PDPs: URL /p/{vertical}/{slug}/{sku_id} returns full SSR HTML with prices, specs, seller info
Watch out: Listing pages are 100% client-rendered (Algolia). Prices are pincode-dependent (defaults to Mumbai 400020)
robots.txt: Explicitly disallows /search and /*? — but sitemaps are open
Tier 3 — Hard (Playwright mandatory)
Tata CLiQ
Problem: Pure client-rendered SPA. Every URL returns identical empty <div id="root"></div>. Zero SSR data.
APIs: All return errors — searchProducts gives E0000, prodsearch.tatacliq.com gives 500. Require runtime tokens.
Anti-bot: Cloudflare Bot Management (__cf_bm cookie)
Strategy: Playwright for all pages. Intercept Redux store via window.getState() for structured data extraction
Croma
Problem: Akamai Bot Manager blocks ALL content pages (403) including search, product, and category
APIs: SAP Hybris REST endpoints exist but blocked without valid _abck sensor cookie
Anti-bot: Akamai sensor challenge. Homepage rate-limited after ~5 requests/minute
Strategy: Playwright + playwright-stealth + proxy rotation mandatory. Intercept XHR for JSON data from Hybris APIs
Meesho
Problem: Next.js shell with empty __next div. All product data client-rendered ("catalogs" terminology)
APIs: Both REST (/api/v1/products/search) and GraphQL (/graphql) return 403
Anti-bot: Akamai blocks even robots.txt without full Sec-Fetch headers. Search pages have noindex meta
Strategy: Playwright + proxy rotation. Intercept internal API calls via page.on('response') for catalog JSON
Build Priority Recommendation
Priority	Site	Reason
P0 (build first)	Reliance Digital	Open JSON API, richest data, zero friction, ~1,800+ mobiles alone
P0	Vijay Sales	Open Unbxd JSON API, 5,100+ products, city-specific pricing is unique value
P1	Snapdeal	Zero anti-bot, full SSR + microdata, simple HTML parsing
P1	Nykaa	HTTP-only with headers, triple data sources, strong beauty/lifestyle vertical
P2	JioMart	Sitemap approach viable, SSR PDPs, but needs careful rate limiting
P3 (build last)	Tata CLiQ	Playwright required, Cloudflare, but manageable difficulty
P3	Croma	Aggressive Akamai, needs stealth+proxy, but SAP Hybris JSON is clean once past WAF
P4 (optional)	Meesho	Hardest to scrape, budget marketplace, lower value per product
Key Technical Notes for Pipeline Integration
Price format: All sites return prices in rupees (not paisa). Pipeline must multiply by 100 for storage.
Marketplace slugs needed: reliance-digital, vijay-sales, snapdeal, nykaa, jiomart, tata-cliq, croma, meesho
Review data: Only Snapdeal and Nykaa provide reviews in SSR. Others use external widgets (Bazaarvoice, Jio reviews widget, etc.) requiring separate scraping.
Shared infrastructure: Reliance Digital and JioMart both run on Fynd Commerce — similar API patterns may apply.


## Summary Table

| Site | Has Public API? | Data Format | Anti-Bot | Framework | Difficulty | Recommended Approach |
|---|---|---|---|---|---|---|
| **Reliance Digital** | **YES** — `/ext/raven-api/catalog/v1.0/products` | JSON API (no auth!) | Akamai (API unprotected) | Vue.js (Fynd Commerce) | **Easy** (2/10) | HTTP + JSON API |
| **Vijay Sales** | **YES** — Unbxd Search API | JSON API (public key, open CORS) | Akamai CDN + Fastly (minimal) | Adobe AEM + Magento | **Easy** (2/10) | HTTP + JSON API |
| **Snapdeal** | No (old API deprecated) | SSR HTML + schema.org microdata | **None** (AWS CloudFront only) | Java/Tomcat + jQuery | **Easy** (3/10) | HTTP + HTML parsing |
| **Nykaa** | No (gateway-api returns 403) | SSR HTML + `__PRELOADED_STATE__` + JSON-LD | Akamai (bypassed with headers) | React SSR (custom, not Next.js) | **Medium** (4/10) | HTTP + HTML parsing (with Sec-Fetch headers) |
| **JioMart** | No (internal APIs return 503) | Hybrid — SSR on PDP, CSR on listings | Akamai WAF (header-sensitive) | jQuery + Vue.js | **Medium** (5/10) | Sitemap discovery + HTTP for PDPs |
| **Tata CLiQ** | No (APIs broken/protected) | Pure CSR SPA (`<div id="root">`) | Cloudflare Bot Management | React + Redux SPA | **Hard** (7/10) | Playwright required (all pages) |
| **Croma** | No (Hybris APIs blocked) | React SSR (no __NEXT_DATA__) | **Akamai Bot Manager (aggressive)** | React SSR (custom) | **Hard** (8/10) | Playwright + stealth + proxy |
| **Meesho** | No (APIs return 403) | CSR via Next.js (empty `__next`) | **Akamai Bot Manager (aggressive)** | Next.js Pages Router | **Hard** (8/10) | Playwright + stealth + proxy |

---

## Build Priority

| Priority | Site | Reason |
|---|---|---|
| **P0** (build first) | **Reliance Digital** | Open JSON API, richest data, zero friction, ~1,800+ mobiles alone |
| **P0** | **Vijay Sales** | Open Unbxd JSON API, 5,100+ products, city-specific pricing is unique value |
| **P1** | **Snapdeal** | Zero anti-bot, full SSR + microdata, simple HTML parsing |
| **P1** | **Nykaa** | HTTP-only with headers, triple data sources, strong beauty/lifestyle vertical |
| **P2** | **JioMart** | Sitemap approach viable, SSR PDPs, but needs careful rate limiting |
| **P3** (build last) | **Tata CLiQ** | Playwright required, Cloudflare, but manageable difficulty |
| **P3** | **Croma** | Aggressive Akamai, needs stealth+proxy, but SAP Hybris JSON is clean once past WAF |
| **P4** (optional) | **Meesho** | Hardest to scrape, budget marketplace, lower value per product |

---

## Tier 1 — Easy (HTTP-only, no Playwright)

### Reliance Digital

- **API**: `GET /ext/raven-api/catalog/v1.0/products?q={query}&page={n}&pageSize=24` — **zero auth required**
- **Backup**: `/ext/raven-api/catalog//v1.0/collections/{slug}/items` (note double slash)
- **Data**: Rich JSON — name, brand, prices (rupees), specs, EAN, images, stock, country of origin
- **Platform**: Fynd Commerce (same as JioMart backend) — `x-fynd-trace-id` in responses

**Available fields per product:**

| Field | Example |
|---|---|
| `name` | `OnePlus Nord 5 5G 256 GB, 8 GB RAM, Phantom Grey, Mobile Phone` |
| `slug` | `oneplus-nord-5-256-gb-8-gb-ram-phantom-grey-mobile-phone-mcor07-9278286` |
| `uid` | `9278286` |
| `item_code` | `494582110` |
| `brand.name` | `One Plus` |
| `price.effective.min` | `33999` (INR, rupees not paisa) |
| `price.marked.min` | `34999` (MRP) |
| `discount` | `3% OFF` |
| `categories[].name` | `Smart Phones` |
| `medias[]` | Array of image URLs (CDN: `cdn.jiostore.online`) |
| `country_of_origin` | `China` |

**Nested attributes:** `brand_name`, `model-name`, `series`, `colour`, `key-features` (HTML), `ean`, `internal-storage`, `battery_capacity`, `processor`, `operating_system`, `screen_size_diagonal`, `warranty`, `in-the-box`, `net-weight`, `store_ids`, `sellable_quantity`

**Pagination:** `page.current`, `page.has_next`, `page.item_total`. 19 filter facets available.

**Watch out:**
- Prices in rupees (not paisa) — pipeline must multiply by 100
- Rating data is sparse (external review widget at `reviews-ratings-widget.jio.com`)
- Collection API uses double slash: `/ext/raven-api/catalog//v1.0/collections/{slug}/items`
- `Cache-Control: no-cache, no-store` — every request hits origin. Use 1–2s delays.

**Recommended spider architecture:**
```
Approach:     HTTP + JSON (no Playwright needed)
Primary API:  /ext/raven-api/catalog/v1.0/products?q={query}&page={n}&pageSize=24
Backup API:   /ext/raven-api/catalog//v1.0/collections/{slug}/items
Rate limit:   1-2 seconds between requests
Proxy:        Not required, but recommended for sustained scraping
Headers:      Minimal — even bare requests work
```

---

### Vijay Sales

- **API**: Unbxd Search at `search.unbxd.io/{api_key}/{site_key}/search?q={query}&rows=50&start={offset}`
- **API Key**: `bb8ef7667d38c04e8a81c80f4a43a998` (public, embedded in HTML)
- **Site Key**: `ss-unbxd-aapac-prod-vijaysales-magento33881704883825`
- **Data**: 5,124 products total. Rich fields including city-specific pricing.
- **Platform**: Adobe AEM frontend + Magento commerce backend

**Available fields per product:**
- `title`, `brand`, `sku`, `uniqueId`, `modelName`
- `price`, `mrp`, `offerPrice`, `discountPercentage`
- `productUrl`, `imageUrl`, `smallImage`, `thumbnailImage`
- `description`, `categories`, `categoryPath`
- `color`, `ean`
- `deliveryType`, `gstPercentage`, `loyaltyValue`
- `manufacturingWarranty`, `servicesWarranty`, `additionalBrandWarranty`, `warrantyDescription`, `totalWarranty`
- `isCod`, `isExchange`, `isCashify`, `isFastSelling`, `isExclusivelyAvailable`
- `createdAt`, `updatedAt`

**City-specific pricing (unique discovery):**
- `cityId_10_price_unx_d: 49999` (MRP for Delhi)
- `cityId_10_offerPrice_unx_d: 39999` (offer price for Delhi)
- `cityId_10_sellingPrice_unx_d: 39999` (selling price for Delhi)
- `cityId_10_specialTag_unx_ts: "No Cost EMI,₹3000 Bank Offer,Price Drop"`
- `cityId_10_couponLabel_unx_ts: "DLXOF1000"`
- City IDs need mapping (e.g., 10 = Delhi).

**API features:**
- Pagination: `start` (offset) + `rows` (page size). Total in `response.numberOfProducts`.
- Filtering: `&filter=brand_uFilter:"Samsung"` works correctly.
- Field selection: `&fields=field1,field2,...` reduces payload size.
- CORS: `Access-Control-Allow-Origin: *` (fully open).
- No rate limit headers observed.

**Not available via Unbxd API:**
- Customer reviews/ratings — loaded via separate service
- Detailed product specifications — need HTML parsing for those
- Stock/inventory levels — only `productStatus` (1 = available)

**Recommended spider architecture:**
```
Phase 1 (Listing): HTTP + JSON via Unbxd API
  - URL: search.unbxd.io/{key}/{site}/search?q={query}&rows=50&start={offset}
  - Extract: all product fields directly from JSON
  - Use &fields= to select only needed fields

Phase 2 (Detail): HTTP + HTML parsing (for specs/reviews not in API)
  - URL: vijaysales.com/p/{parent_id}/{variant_id}/{slug}
  - Parse: JSON-LD + SSR HTML for specs tables and reviews

No Playwright needed. No proxy needed.
```

---

### Snapdeal

- **Approach**: HTTP + HTML parsing (fully SSR, zero anti-bot)
- **CDN**: AWS CloudFront (caching only, no WAF)
- **Server**: Apache-Coyote/1.1 (Java/Tomcat backend)

**Search results page (`/search?keyword=...`):**
- Returns HTTP 200 with ~295KB of SSR HTML
- ~20 product tuples per page
- Each product has: `id="{pogId}"`, `data-price="{price}"`, `.product-title`, `.product-price`, full product URL
- Pagination via `offset` and `noOfResults` query params
- JSON-LD present but only `WebSite` schema (not product data)

**Product detail page (`/product/{slug}/{pogId}`):**
- Rich schema.org microdata (`itemprop` attributes):
  - `name`, `price`, `priceCurrency` (INR), `brand`, `ratingValue`, `reviewCount`, `ratingCount`
  - `description`, `image`, `availability`, `seller`, `aggregateRating`
- Slug is required in URL (pogId alone returns 404)

**URL patterns:**
- Search: `https://www.snapdeal.com/search?keyword={term}&noOfResults=20`
- Product: `https://www.snapdeal.com/product/{slug}/{pogId}`

**Watch out:**
- `/honeybot` honeypot link on page — spider must NOT follow it
- Product slug is required in URL — pogId alone returns 404
- Images served from CDN: `i1.sdlcdn.com` through `i4.sdlcdn.com`
- Mobile API at `mobileapi.snapdeal.com` exists (not tested)

**Recommended spider architecture:**
```
Phase 1 (Listing): HTTP only, parse SSR HTML
  - URL: /search?keyword={term}&noOfResults=20&offset={N}
  - Extract: pogId, slug, price, title from .product-tuple-listing elements

Phase 2 (Detail): HTTP only, parse SSR HTML with microdata
  - URL: /product/{slug}/{pogId}
  - Extract: full product data via itemprop attributes

No Playwright needed. No proxy needed (unless high volume).
```

---

## Tier 2 — Medium (HTTP with proper headers)

### Nykaa

- **Approach**: HTTP + HTML parsing with full browser headers
- **Anti-bot**: Akamai Bot Manager — bypassed with correct `Sec-Fetch-*` and `sec-ch-ua` headers
- **Framework**: Custom React SSR (NOT Next.js) — `id="app"`, `window.__PRELOADED_STATE__`

**Required headers (minimum to bypass Akamai):**
```
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8
Accept-Language: en-IN,en;q=0.9
Sec-Fetch-Dest: document
Sec-Fetch-Mode: navigate
Sec-Fetch-Site: none
Sec-Fetch-User: ?1
sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120"
sec-ch-ua-mobile: ?0
sec-ch-ua-platform: "Windows"
Upgrade-Insecure-Requests: 1
```

**Three complementary data sources per page:**

1. **`window.__PRELOADED_STATE__`** (richest):
   - Category pages: `appReducer`, `dataLayer`, full Redux state, `totalFound` count
   - Product pages: `productPage` with name, SKU, MRP, offerPrice, discount, rating, reviewCount, variants, stock

2. **JSON-LD** (`application/ld+json`):
   - Category pages: `ItemList` schema with product names and URLs
   - Product pages: Full `Product` schema with offers, brand, review rating

3. **`window.dataLayer`** (analytics):
   - Product summary: id, name, mrp, offerPrice, sku, brand, category, discount, rating, reviewCount

**Quirks:**
- Search URLs redirect 302 to category pages (e.g., `?q=lipstick` → `/makeup/lips/c/15`)
- Use category URLs directly for predictable results
- Prices in rupees (not paisa)
- Image CDN: `images-static.nykaa.com` with transformation params

**Recommended spider architecture:**
```
Phase 1 (Listing): HTTP GET to category URLs
  - Parse window.__PRELOADED_STATE__ for product URLs and basic data
  - Parse JSON-LD ItemList for product URLs
  - Follow pagination

Phase 2 (Detail): HTTP GET to product URLs
  - URL: /{product-slug}/p/{product-id}
  - Parse JSON-LD Product schema for structured data
  - Parse window.__PRELOADED_STATE__.productPage for extended fields

No Playwright needed. Conservative rate limiting (2-3s delays).
```

---

### JioMart

- **Approach**: Sitemap-based product discovery + HTTP for product detail pages
- **Anti-bot**: Akamai WAF — requires `Sec-Fetch-*` headers (bare UA gets 403)
- **Framework**: jQuery + Vue.js (custom SSR, not a SPA framework)

**Search/listing pages:**
- 100% client-rendered via Algolia InstantSearch.js + Google Retail API
- Cannot be scraped without Playwright
- `robots.txt` explicitly disallows `/search` and `/*?`

**Sitemap (preferred discovery method):**
- `https://www.jiomart.com/sitemap.xml` → 6 sub-sitemaps:
  - `electronics.xml`, `fashion.xml`, `gm-sitemap.xml`, `fmcg-sitemap.xml`, `cdit-sitemap.xml`, `website.xml`
- Product URL pattern: `https://www.jiomart.com/p/{vertical}/{slug}/{sku_id}`
- Sitemaps dated 2023-12 to 2024-04 (may be stale)

**Product detail pages (SSR):**
- Full SSR HTML with: product name, SKU, manufacturer, category, seller, specs table
- Selling price and MRP in HTML (e.g., `₹200` selling, `₹3,499` MRP)
- JSON-LD: `BreadcrumbList` only (no `Product` schema)
- Prices are pincode-dependent — defaults to Mumbai (400020)

**Product verticals:** GROCERIES, ELECTRONICS, FASHION, JEWELLERY, BEAUTY, WELLNESS, HOMEANDKITCHEN, HOMEIMPROVEMENT, PREMIUMFRUITS

**Watch out:**
- Listing pages need Playwright — avoid by using sitemaps
- Prices depend on pincode (default: Mumbai 400020)
- Sitemaps may be stale (last updated 2024)
- HEAD requests return 403 even with full headers — only GET works

**Recommended spider architecture:**
```
Phase 1 (Discovery): HTTP, parse sitemap XML files
  - URL: /sitemap.xml → sub-sitemaps → product URLs
  - No Playwright needed

Phase 2 (Detail): HTTP + HTML parsing with Sec-Fetch headers
  - URL: /p/{vertical}/{slug}/{sku_id}
  - Parse: product name, prices, brand, specs, seller, images

Playwright only needed for supplemental search-based discovery.
```

---

## Tier 3 — Hard (Playwright mandatory)

### Tata CLiQ

- **Problem**: Pure client-rendered SPA. Every URL returns identical empty `<div id="root"></div>`.
- **Anti-bot**: Cloudflare Bot Management (`__cf_bm` cookie)
- **Framework**: React + Redux SPA (Create React App style)

**API investigation results:**
- `marketplacewebservices/v2/mpl/products/searchProducts` — always returns `E0000` system error
- `prodsearch.tatacliq.com/products/mpl/searchAndSuggest/` — returns HTTP 500
- APIs require runtime tokens/session state generated by client-side JS

**JSON-LD:** Two blocks found but site-level only (`WebSite` + `Organization`). No product data.

**Recommended spider architecture:**
```
Approach:     Playwright for ALL pages (listing + detail)
Data source:  Intercept Redux store or XHR responses
Anti-bot:     Cloudflare — playwright-stealth recommended
Rate:         Conservative delays (3-5s between pages)
Proxy:        Recommended for sustained scraping
```

---

### Croma

- **Problem**: Akamai Bot Manager blocks ALL content pages (403) even on first request
- **Anti-bot**: Akamai sensor challenge (`_abck` cookie with `-1` values = unsolved)
- **Framework**: React SSR (custom, not Next.js) with `react-helmet`
- **Backend**: SAP Commerce Cloud (Hybris) — `/rest/v2/croma/products/search` exists but blocked

**Akamai evidence:**
- Server: `AkamaiGHost`
- Bot Manager cookies: `_abck`, `bm_sz`
- Homepage rate-limited after ~5 requests/minute
- Search/product pages: 403 outright even on first request

**Recommended spider architecture:**
```
Approach:     Playwright + playwright-stealth + proxy rotation (mandatory)
Strategy:     Load pages, let Akamai sensor execute, intercept XHR for Hybris JSON
Contexts:     Max 2-3 concurrent browser contexts
Rate:         Minimum 5-10s delay between page loads
Proxies:      Indian residential proxies recommended (datacenter IPs flagged)
```

---

### Meesho

- **Problem**: Next.js Pages Router with empty `__next` div. All product data client-rendered.
- **Anti-bot**: Akamai Bot Manager — blocks even `robots.txt` without full browser headers
- **Framework**: Next.js Pages Router + styled-components v6

**Key observations:**
- Without `Sec-Fetch-*` headers: every URL returns 403 (including homepage)
- With full headers: HTML shell served (200) but no product data — only skeleton loaders
- `__NEXT_DATA__` exists but contains only shell data, no products
- Search pages have `<meta name="robots" content="noindex"/>` — not meant to be crawled
- Products called "catalogs" internally

**Recommended spider architecture:**
```
Approach:     Playwright + proxy rotation
Strategy:     page.on('response') to intercept internal catalog API calls
Headers:      Must include full Sec-Fetch-*, sec-ch-ua* headers
Proxies:      Strongly recommended — Akamai fingerprints IPs
Priority:     Lower — budget marketplace, lower value per product
```

---

## Pipeline Integration Notes

### Price Format
All 8 sites return prices in **rupees** (not paisa). Pipeline must multiply by 100 for storage.

### Marketplace Slugs Needed
Add to `Marketplace` model: `reliance-digital`, `vijay-sales`, `snapdeal`, `nykaa`, `jiomart`, `tata-cliq`, `croma`, `meesho`

### Review Data Availability
| Site | Reviews in SSR? | External Widget |
|---|---|---|
| Snapdeal | Yes (microdata) | No |
| Nykaa | Yes (`__PRELOADED_STATE__`) | No |
| Reliance Digital | No | `reviews-ratings-widget.jio.com` |
| Vijay Sales | No | Unknown (separate service) |
| JioMart | No | Unknown |
| Tata CLiQ | No | Loaded via JS |
| Croma | No | Loaded via JS |
| Meesho | No | Loaded via JS |

### Shared Infrastructure
- **Reliance Digital + JioMart**: Both run on Fynd Commerce (`x-fynd-trace-id`, `cdn.jiostore.online`). Similar API patterns may apply.
- **Croma + Tata CLiQ**: Both part of Tata Digital ecosystem (shared SSO at `accounts.tatadigital.com`).
