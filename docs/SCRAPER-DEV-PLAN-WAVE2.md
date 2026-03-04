# WHYDUD — Marketplace Scraper Development Plan
## Myntra, AJIO, FirstCry, Giva

> **For Claude Code.** Follow the prompt sequence exactly. Each prompt builds on the previous.
> Read `CLAUDE.md` and `PROGRESS.md` first. All spiders extend `BaseWhydudSpider`.

---

## SITE RECONNAISSANCE SUMMARY

### Myntra (myntra.com) — Flipkart Group
- **Anti-bot:** Flipkart-grade (hard). CAPTCHAs on suspicious traffic, IP blocking, fingerprinting.
- **Rendering:** Full SPA — React app. Listings are JS-rendered. Product pages are JS-rendered.
- **Data access strategy:** Playwright required for both listing + product pages. Myntra embeds product data in script tags or React hydration state inside the rendered HTML. After Playwright renders the page, parse `page_source` with BeautifulSoup to extract from known DOM classes (`product-brand`, `product-discountedPrice`, `product-strike`, `pdp-title`, `index-overallRating`). On product detail pages, look for `<script>` tags containing JSON product data (embedded pdpData/myx state).
- **URL patterns:**
  - Listings: `https://www.myntra.com/{category}?p={page}` (e.g., `men-tshirts?p=2`)
  - Products: `https://www.myntra.com/{product-slug}/{product-id}`
- **Key selectors (listing page):** `h3.product-brand`, `h4.product-product` (description), `span.product-discountedPrice`, `span.product-strike` (MRP), `div.product-ratingsContainer`
- **Key selectors (product page):** `h1.pdp-title`, `span.pdp-price > strong`, `div.pdp-product-description`, `div.index-overallRating`, `div.size-buttons-size-body`, images in `div.image-grid-image`
- **Difficulty:** 7/10
- **Phase approach:** Playwright listing → Playwright detail (both need JS rendering)

### AJIO (ajio.com) — Reliance Retail
- **Anti-bot:** Reliance infrastructure (hard). Akamai-level protection. Lazy-loading on listing pages with "Load More" button. Dynamic content.
- **Rendering:** SPA with lazy loading. Listing pages require scrolling/clicking "Load More". Product pages render server-side partially with JSON-LD structured data.
- **Data access strategy:** Two approaches: (1) Playwright for listing pages (handle lazy load). (2) On product detail pages, try plain HTTP first — AJIO sometimes serves SSR HTML with JSON-LD `<script type="application/ld+json">` containing product name, price, brand, description, images. If JSON-LD absent, fall back to Playwright.
- **URL patterns:**
  - Listings: `https://www.ajio.com/s/{query}?query=:relevance` or category URLs like `https://www.ajio.com/{brand}-{category}/c/{category-code}`
  - Products: `https://www.ajio.com/{brand}-{product-slug}/p/{product-code}_{color-code}`
- **Key data points:** brand, title, price (MRP + selling price), discount %, sizes, colors, product code, images, description, fabric/material specs
- **Difficulty:** 7/10
- **Phase approach:** Playwright listing (scroll/load more) → HTTP+JSON-LD detail, fallback Playwright detail

### FirstCry (firstcry.com)
- **Anti-bot:** Moderate. Standard Cloudflare protection. Not as aggressive as Flipkart/Reliance.
- **Rendering:** Mostly SSR with some dynamic elements. Listing pages render products server-side in initial HTML. Product pages have good SSR with structured data.
- **Data access strategy:** HTTP-first approach. Listing pages likely return product cards in SSR HTML — try plain HTTP + BeautifulSoup. Product detail pages should have JSON-LD or microdata. If Cloudflare blocks plain HTTP, use Playwright with stealth.
- **URL patterns:**
  - Listings: `https://www.firstcry.com/{category}` with pagination params
  - Products: `https://www.firstcry.com/{product-slug}/{product-id}.html`
- **Key data points:** product name, brand, price (MRP + selling price), age group, discount, images, description, material, product code, ratings/reviews
- **Special consideration:** Baby/kids products have age group as a critical attribute — must extract.
- **Difficulty:** 4/10
- **Phase approach:** HTTP listing → HTTP detail (+JSON-LD), fallback Playwright

### Giva (giva.co) — Shopify Store
- **Anti-bot:** Minimal. Shopify store = standard Shopify bot protection (very low).
- **Rendering:** Shopify stores serve SSR HTML and have a standardized JSON API.
- **Data access strategy:** EASIEST. Shopify stores have a built-in JSON API:
  - `https://www.giva.co/collections/{collection}.json` → full product list with pagination
  - `https://www.giva.co/products/{handle}.json` → full product detail as JSON
  - No Playwright needed. Pure HTTP requests with proper headers.
- **URL patterns:**
  - Collections: `/collections/{name}` → append `.json` for API
  - Products: `/products/{handle}` → append `.json` for API
  - Search: `/search/suggest.json?q={query}&resources[type]=product`
  - All products: `/products.json?page={n}&limit=250`
- **Key data points:** title, vendor (brand), price, compare_at_price (MRP), variants (with sizes/materials/stones), images, description (HTML), tags, product_type
- **Difficulty:** 1/10
- **Phase approach:** Pure HTTP JSON API. No rendering needed.

---

## BUILD ORDER

| Order | Spider | Difficulty | Rationale |
|-------|--------|-----------|-----------|
| 1 | **Giva** | 1/10 | Start with easiest. Validates pipeline integration. 30 min build. |
| 2 | **FirstCry** | 4/10 | Mostly SSR. HTTP-first. Validates the two-phase HTTP→Playwright fallback pattern. |
| 3 | **AJIO** | 7/10 | Hard but JSON-LD on PDPs makes detail phase easier. Listing phase hard (lazy load). |
| 4 | **Myntra** | 7/10 | Hardest. Full Playwright for both phases. Build last with all lessons learned. |

---

## COMMON SETUP (DO THIS FIRST)

### Prompt 0: Marketplace Seed Data

```
Add the following marketplaces to the seed data. If they already exist, skip them.
Do NOT delete any existing marketplace entries.

In the seed data command or fixture, add:

Marketplace: myntra
  name: Myntra
  base_url: https://www.myntra.com
  affiliate_tag: (leave empty for now)
  affiliate_param: (leave empty for now)
  scraper_status: development

Marketplace: ajio
  name: AJIO
  base_url: https://www.ajio.com
  affiliate_tag: (leave empty for now)
  affiliate_param: (leave empty for now)
  scraper_status: development

Marketplace: firstcry
  name: FirstCry
  base_url: https://www.firstcry.com
  affiliate_tag: (leave empty for now)
  affiliate_param: (leave empty for now)
  scraper_status: development

Marketplace: giva
  name: Giva
  base_url: https://www.giva.co
  affiliate_tag: (leave empty for now)
  affiliate_param: (leave empty for now)
  scraper_status: development

If using a seed data management command, add these. If using fixtures, add to the JSON.
If using Django admin, document the manual steps.

After adding, verify: python manage.py shell -c "from apps.products.models import Marketplace; print(Marketplace.objects.values_list('slug', flat=True))"
```

---

## SPIDER 1: GIVA (Shopify JSON API)

### Prompt 1A: Giva Spider — Product Scraper

```
Create the Giva product spider at apps/scraping/spiders/giva_spider.py

Giva (giva.co) is a Shopify store. Shopify stores have a built-in JSON API
that requires NO Playwright, NO proxy, just HTTP requests with proper headers.

## Architecture

This spider is DIFFERENT from Amazon/Flipkart. It does NOT use the two-phase
Playwright pattern. It uses pure HTTP requests to Shopify's JSON endpoints.

## Spider Class

class GivaSpider(BaseWhydudSpider):
    name = 'giva'
    marketplace_slug = 'giva'
    allowed_domains = ['giva.co']

    # Shopify JSON API endpoints
    PRODUCTS_API = 'https://www.giva.co/products.json'
    COLLECTION_API = 'https://www.giva.co/collections/{}.json'

    # Target collections to scrape
    COLLECTIONS = [
        'silver-rings', 'silver-earrings', 'silver-necklaces',
        'silver-bracelets', 'silver-pendants', 'gold-jewellery',
        'lab-grown-diamond-jewellery', 'men-jewellery',
    ]

## Listing Phase (start_requests)

For each collection in COLLECTIONS:
  URL: https://www.giva.co/collections/{collection}.json?page={n}&limit=50
  Method: Plain HTTP GET
  Headers: {
    'Accept': 'application/json',
    'User-Agent': (rotate from BaseWhydudSpider),
  }
  Parse response JSON:
    response_data = json.loads(response.text)
    products = response_data.get('products', [])
  For each product in products:
    Yield a Request to the product detail endpoint

  Pagination:
    If len(products) == 50, increment page and yield next listing request.
    If len(products) < 50, this is the last page.

## Detail Phase (parse_product)

URL: https://www.giva.co/products/{handle}.json
Parse the JSON response directly:

product_json = json.loads(response.text)['product']

Extract and map to ProductItem:
  title = product_json['title']
  brand = product_json.get('vendor', 'GIVA')
  description = product_json.get('body_html', '')  # HTML, strip tags for plain text
  external_id = str(product_json['id'])
  external_url = f"https://www.giva.co/products/{product_json['handle']}"

  # Price from first variant
  variants = product_json.get('variants', [])
  if variants:
      price = Decimal(variants[0].get('price', '0'))
      mrp = Decimal(variants[0].get('compare_at_price', '0') or variants[0].get('price', '0'))
  
  # Images
  images = [img['src'] for img in product_json.get('images', [])]

  # Specs from tags + options
  tags = product_json.get('tags', [])
  options = product_json.get('options', [])  # e.g., [{"name": "Size", "values": ["Free Size"]}]
  specs = {
      'material': next((t for t in tags if 'silver' in t.lower() or 'gold' in t.lower()), None),
      'product_type': product_json.get('product_type', ''),
      'options': {opt['name']: opt['values'] for opt in options},
  }

  # Rating/reviews — Shopify doesn't include in JSON API.
  # Set to None; can add review scraping later via page HTML or Judgeme widget API.
  rating = None
  review_count = 0

Yield ProductItem with all fields.

## Error Handling

- If HTTP 429 (rate limit): wait 30 seconds, retry. Max 3 retries.
- If HTTP 404 on a collection: skip, log warning.
- Shopify API rate limit is 2 requests/second for storefront. Add 0.5s delay between requests.

## Settings Override (in spider)

custom_settings = {
    'DOWNLOAD_DELAY': 0.5,
    'CONCURRENT_REQUESTS': 2,
    'RETRY_TIMES': 3,
    # No Playwright needed
    'PLAYWRIGHT_LAUNCH_OPTIONS': None,
}

## Test

Run: python manage.py run_spider giva --max-pages 1
Expected: 30-50 products scraped from first page of first collection.
Verify: Items in product_listings table with marketplace_id = giva.
```

---

## SPIDER 2: FIRSTCRY (HTTP-First with Playwright Fallback)

### Prompt 2A: FirstCry Spider — Reconnaissance Phase

```
Before building the FirstCry spider, I need you to do reconnaissance.

Create a test script at apps/scraping/spiders/test_firstcry_recon.py that:

1. Makes a plain HTTP GET request to https://www.firstcry.com/baby-care
   with realistic browser headers (User-Agent, Accept, Accept-Language, etc.)
   Use the headers from BaseWhydudSpider.

2. Check if the response is:
   a. 200 with product HTML → SSR works, HTTP-first approach viable
   b. 200 but empty/JS shell → needs Playwright
   c. 403/503/challenge page → Cloudflare blocking, needs Playwright + stealth

3. If response is 200 with HTML, search for:
   - <script type="application/ld+json"> → JSON-LD structured data
   - Product cards in HTML (look for common patterns: product-card, product-list, etc.)
   - Any embedded JSON in <script> tags (window.__INITIAL_STATE, etc.)

4. Make a plain HTTP GET to a product page:
   https://www.firstcry.com/fisher-price/fisher-price-laugh-and-learn-counting-and-colors-uno/15542060.html
   (or any other valid product URL — find one from the listing page)
   
   Check for JSON-LD, microdata, or embedded product JSON.

5. Print a report:
   - Listing page: SSR or SPA?
   - Listing page: any structured data?
   - Product page: SSR or SPA?
   - Product page: JSON-LD present?
   - Cloudflare challenge detected?
   - Recommended approach: HTTP-only / Playwright-listing-only / Full Playwright

Run this script and report findings BEFORE building the spider.
Do NOT proceed to spider construction until recon is complete.
```

### Prompt 2B: FirstCry Spider — Build (adapt based on recon)

```
Based on the reconnaissance results from Prompt 2A, build the FirstCry spider.

Create apps/scraping/spiders/firstcry_spider.py

## Spider Class

class FirstCrySpider(BaseWhydudSpider):
    name = 'firstcry'
    marketplace_slug = 'firstcry'
    allowed_domains = ['firstcry.com']

## Target Categories (baby/kids vertical)

CATEGORIES = [
    'baby-care',
    'baby-feeding',
    'baby-diapers',
    'toys',
    'baby-clothing',
    'kids-clothing',
    'baby-gear',
    'nursery',
    'kids-footwear',
    'school-supplies',
]

## Listing Phase

[If recon showed HTTP works for listings:]
  Use plain HTTP GET to https://www.firstcry.com/{category}?page={n}
  Parse HTML with BeautifulSoup/Scrapy selectors.
  Extract product URLs and basic info from listing cards.

[If recon showed Playwright needed for listings:]
  Use Playwright to load the page, wait for product cards to render.
  Extract from page_source after rendering.

For each product card, extract:
  - Product URL (href from card link)
  - Product ID (from URL or data attribute)
  - Quick data: brand, title, price, MRP, discount %, image URL

Pagination:
  Check for "next page" link or increment page number.
  Stop at --max-pages limit.

## Detail Phase

[If recon showed JSON-LD on product pages:]
  Make plain HTTP GET to product URL.
  Extract <script type="application/ld+json"> → parse JSON.
  Map JSON-LD fields to ProductItem:
    title = json_ld['name']
    brand = json_ld.get('brand', {}).get('name', '')
    price = json_ld.get('offers', {}).get('price', 0)
    mrp = json_ld.get('offers', {}).get('highPrice', price)
    images = json_ld.get('image', [])
    description = json_ld.get('description', '')
    rating = json_ld.get('aggregateRating', {}).get('ratingValue')
    review_count = json_ld.get('aggregateRating', {}).get('reviewCount', 0)

[If recon showed NO JSON-LD:]
  Use Playwright for product pages.
  Extract from rendered HTML using CSS selectors.

## CRITICAL: Age Group Extraction

FirstCry is a baby/kids platform. Every product has an age group (e.g., "0-6 Months",
"1-2 Years", "3-5 Years"). This MUST be extracted and stored in specs JSONB:

specs = {
    'age_group': '0-6 Months',
    'material': 'Cotton',
    'brand': 'Fisher-Price',
    # ... other product-specific specs
}

Look for age group in:
  - Product title (common pattern: "for 0-6 Months")
  - Dedicated field in product page HTML
  - Breadcrumb trail
  - JSON-LD or microdata

## Spider Settings

custom_settings = {
    'DOWNLOAD_DELAY': 1.5,  # conservative — Cloudflare
    'CONCURRENT_REQUESTS': 2,
    'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
    'RETRY_TIMES': 3,
}

## Test

Run: python manage.py run_spider firstcry --max-pages 1
Expected: 20-40 products from first listing page.
Report: success rate, any blocked requests, items stored.
```

---

## SPIDER 3: AJIO (Reliance — Hard)

### Prompt 3A: AJIO Spider — Reconnaissance Phase

```
Before building the AJIO spider, do reconnaissance.

Create apps/scraping/spiders/test_ajio_recon.py that:

1. Plain HTTP GET to https://www.ajio.com/men-t-shirts/c/830216001
   with full browser headers.
   Check: SSR or SPA? Blocked?

2. Plain HTTP GET to a product page:
   Try a URL like https://www.ajio.com/levis-slim-fit-crew-neck-t-shirt/p/460259543_blue
   Check: JSON-LD? SSR HTML with product data? SPA shell?

3. Check for internal API endpoints:
   AJIO may use internal APIs for search/listing. Check if these work:
   - https://www.ajio.com/api/category/830216001?fields=SITE&currentPage=0&pageSize=45
   - Or check network tab patterns: /api/search, /rilResponse, etc.
   - Try adding headers like 'X-Requested-With': 'XMLHttpRequest'

4. On the product page HTML, search for:
   - <script type="application/ld+json">
   - window.__PRELOADED_STATE__ or similar React state objects
   - Any <script> tag with JSON containing product price/title

5. Print report:
   - Listing page approach: HTTP API / Playwright
   - Product page approach: HTTP+JSON-LD / HTTP+embedded JSON / Playwright
   - Any anti-bot challenges observed
   - Internal API endpoints discovered (if any)

Run and report findings BEFORE building the spider.
```

### Prompt 3B: AJIO Spider — Build (adapt based on recon)

```
Based on AJIO reconnaissance results, build the spider.

Create apps/scraping/spiders/ajio_spider.py

## Spider Class

class AJIOSpider(BaseWhydudSpider):
    name = 'ajio'
    marketplace_slug = 'ajio'
    allowed_domains = ['ajio.com']

## Target Categories

CATEGORIES = [
    ('men-t-shirts', '830216001'),
    ('men-shirts', '830216003'),
    ('men-jeans', '830216009'),
    ('women-kurtas', '830318001'),
    ('women-tops', '830218001'),
    ('women-dresses', '830218010'),
    ('men-shoes', '830116001'),
    ('women-shoes', '830118001'),
    ('bags-wallets', '830416001'),
    ('watches', '830516001'),
]

## Listing Phase

[If recon discovered internal API:]
  Use the discovered API endpoint with plain HTTP.
  Parse JSON response for product list.
  This is the BEST approach if it works — no Playwright needed for listings.

[If no API, Playwright required:]
  AJIO listing pages use lazy loading / "Load More" button.
  Playwright approach:
    1. Navigate to category URL
    2. Wait for initial products to load (wait_for_selector on product cards)
    3. Scroll down to trigger lazy load
    4. Optionally click "Load More" button if present
    5. Extract product URLs from rendered HTML
  
  IMPORTANT: AJIO product cards typically have structure like:
    <div class="item rilrtl-products-list__item">
      <a href="/brand-product-slug/p/product_code_color">
      <div class="brand">Brand Name</div>
      <div class="nameCls">Product Title</div>
      <span class="price">₹999</span>
      <span class="orginal-price">₹1,999</span>
      <span class="discount">50% off</span>
    </a></div>

  Extract from each card: URL, brand, title, price, MRP, discount.

## Detail Phase

[If recon showed JSON-LD on product pages:]
  Plain HTTP GET + parse JSON-LD. Same pattern as Flipkart spider.

[If recon showed embedded JSON (window.__PRELOADED_STATE__):]
  Plain HTTP GET + regex extract JSON from script tag.
  Parse the state object for product data.

[If neither, Playwright:]
  Render with Playwright + extract from DOM:
    Brand: .brand-name or .prod-name
    Title: .prod-name or h1
    Price: .prod-sp (selling price)
    MRP: .prod-cp (cost price)
    Sizes: .size-variant-item (list of sizes)
    Colors: .color-variant-item
    Description: .prod-desc
    Images: .zoom-wrap img[src]
    Specs: .prod-desc table or .detail-list

  AJIO product codes look like: "460259543_blue"
  External ID = product code from URL.

## Specs Extraction

AJIO fashion products have detailed specs. Extract into JSONB:
specs = {
    'fabric': 'Cotton',
    'fit': 'Slim Fit',
    'pattern': 'Solid',
    'neck': 'Crew Neck',
    'sleeve': 'Short Sleeve',
    'wash_care': 'Machine Wash',
    'sizes_available': ['S', 'M', 'L', 'XL'],
    'colors_available': ['Blue', 'Black', 'White'],
}

## Spider Settings

custom_settings = {
    'DOWNLOAD_DELAY': 2.0,  # Reliance anti-bot is aggressive
    'CONCURRENT_REQUESTS': 1,
    'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    'RETRY_TIMES': 3,
    'PLAYWRIGHT_MAX_CONTEXTS': 2,
}

## Test

Run: python manage.py run_spider ajio --max-pages 1
Expected: 20-45 products from first page of first category.
Report: success rate, blocked requests, proxy usage, items stored.
```

---

## SPIDER 4: MYNTRA (Flipkart Group — Hardest)

### Prompt 4A: Myntra Spider — Reconnaissance Phase

```
Before building the Myntra spider, do thorough reconnaissance.
Myntra is Flipkart Group — expect aggressive anti-bot protection.

Create apps/scraping/spiders/test_myntra_recon.py that:

1. Plain HTTP GET to https://www.myntra.com/men-tshirts
   With full browser headers from BaseWhydudSpider.
   Check: what comes back? Full HTML? JS shell? Challenge page? Redirect?

2. Playwright (stealth) load of the same URL:
   - Use playwright stealth
   - Wait for product cards to render
   - Extract page_source
   - Check: do product cards appear?
   - What CSS classes are used for product cards?
   - Log: h3.product-brand, h4.product-product, span.product-discountedPrice

3. Plain HTTP GET to a product page:
   Example: https://www.myntra.com/tshirts/roadster/roadster-men-pure-cotton-tshirt/12345678
   (Get a real URL from step 2's listing page)
   Check: SSR or SPA shell?

4. Playwright load of product page:
   - Wait for h1.pdp-title or similar
   - Check for embedded JSON data in <script> tags
   - Specifically search page source for patterns:
     "pdpData" in script tags
     "__myx" in script tags
     "window.__INITIAL_STATE__" or similar
   - If found, this is the GOLDMINE — we can skip DOM parsing

5. Check pagination:
   - https://www.myntra.com/men-tshirts?p=2 — does page param work?
   - How many products per page?

6. Check Myntra's search API:
   - Try: https://www.myntra.com/gateway/v2/search/men-tshirts
   - With headers: 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json'
   - This might return JSON directly — huge win if it works

7. Print comprehensive report:
   - HTTP viability for listings: yes/no
   - HTTP viability for product pages: yes/no
   - Internal API discovered: yes/no (with URL)
   - Embedded JSON in product pages: yes/no (with key name)
   - CSS selectors for listing cards
   - CSS selectors for product detail
   - Pagination approach
   - Estimated difficulty: easy/medium/hard

IMPORTANT: Use existing ProxyPool from middlewares.py. Cycle through proxies.
Run and report findings BEFORE building the spider.
```

### Prompt 4B: Myntra Spider — Build (adapt based on recon)

```
Based on Myntra reconnaissance results, build the spider.

Create apps/scraping/spiders/myntra_spider.py

## Spider Class

class MyntraSpider(BaseWhydudSpider):
    name = 'myntra'
    marketplace_slug = 'myntra'
    allowed_domains = ['myntra.com']

## Target Categories

CATEGORIES = [
    'men-tshirts', 'men-shirts', 'men-jeans', 'men-trousers',
    'women-kurtas-kurtis', 'women-tops', 'women-dresses', 'women-jeans',
    'men-casual-shoes', 'women-heels', 'women-flats',
    'watches', 'bags-backpacks',
    'men-sunglasses', 'women-sunglasses',
]

## Listing Phase — Playwright Required

Myntra is a React SPA. Playwright is required for listing pages.

1. Navigate to https://www.myntra.com/{category}?p={page}
2. Wait for product cards to render:
   await page.wait_for_selector('.product-base', timeout=15000)
   OR
   await page.wait_for_selector('.search-searchProductsContainer', timeout=15000)
3. Extract product links and basic data:

For each product card in page (typically 50 per page):
  CSS selectors (verify with recon data, these are historically known):
    - Card container: .product-base
    - Link: a[data-refreshpage] or a[href*="/"] inside card
    - Brand: h3.product-brand
    - Product name: h4.product-product
    - Discounted price: span.product-discountedPrice or div.product-price span
    - MRP: span.product-strike
    - Rating: div.product-ratingsContainer span
    - Image: img.img-responsive inside .product-imageSliderContainer

  Extract product URL from href. It will be relative (/brand/product-name/12345678).
  Construct full URL: https://www.myntra.com{href}
  Extract product ID from URL (last numeric segment).

Yield request to detail page for each product.

Pagination:
  Myntra supports ?p={page_number} parameter.
  Check if current page returned products. If yes, increment page.
  Respect --max-pages limit.

## Detail Phase

[If recon found embedded JSON (pdpData or similar):]
  PREFERRED APPROACH:
  Use Playwright to load page, then extract JSON from page source.
  
  In page_source, search for:
    pattern = re.compile(r'pdpData\s*=\s*({.*?});', re.DOTALL)
    OR
    Look for <script> tags with "productDetails" or "__myx" keys
  
  Parse the JSON and extract:
    title, brand, mrp, price, discount, sizes, colors, images, description,
    rating, review_count, product_id, specs

[If no embedded JSON, parse DOM:]
  Playwright load + DOM extraction:
    Title: h1.pdp-title
    Brand: .pdp-title .pdp-name or separate brand element
    Price: span.pdp-price strong (selling price)
    MRP: span.pdp-mrp s (strikethrough MRP)
    Discount: span.pdp-discount
    Sizes: .size-buttons-size-body .size-buttons-unified-size
    Description: .pdp-product-description-content
    Images: .image-grid-image img[src] (multiple images)
    Rating: .index-overallRating div (star rating value)
    Review count: .index-ratingsCount
    Specs: .pdp-sizeFitDesc or .index-tableContainer table

## Specs Extraction

Fashion products on Myntra have rich specs:
specs = {
    'fabric': 'Cotton',
    'fit': 'Regular Fit',
    'pattern': 'Printed',
    'neck': 'Round Neck',
    'sleeve_length': 'Short Sleeves',
    'occasion': 'Casual',
    'brand_fit': 'Regular',
    'sizes_available': ['S', 'M', 'L', 'XL', 'XXL'],
    'colors_available': ['Blue', 'Red'],
    'wash_care': 'Machine Wash',
}

## Anti-Bot Handling

- ALWAYS use Playwright with stealth for Myntra
- ALWAYS use proxy rotation (from ProxyPool in middlewares.py)
- Max 2 concurrent Playwright contexts
- Download delay: 3 seconds minimum between requests
- If CAPTCHA detected (look for challenge page): log, skip product, continue
- If IP blocked (403): rotate proxy, retry once
- Random scroll on listing pages to appear human
- Random delay between 2-5 seconds on product pages

## Spider Settings

custom_settings = {
    'DOWNLOAD_DELAY': 3.0,
    'RANDOMIZE_DOWNLOAD_DELAY': True,
    'CONCURRENT_REQUESTS': 1,
    'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    'RETRY_TIMES': 2,
    'PLAYWRIGHT_MAX_CONTEXTS': 2,
    'PLAYWRIGHT_LAUNCH_OPTIONS': {
        'headless': True,
        'args': ['--disable-blink-features=AutomationControlled'],
    },
}

## Test

Run: python manage.py run_spider myntra --max-pages 1
Expected: 30-50 products from first page.
Report: success rate (aim >70%), blocked requests, CAPTCHA encounters, items stored.
```

---

## SPIDER REVIEW VARIANTS (Prompt for Later)

### Prompt 5: Review Spiders (All 4 Marketplaces)

```
After all 4 product spiders are working with >70% success rate,
build review spiders for each.

PRIORITY ORDER for review spiders:
1. Myntra (largest review corpus)
2. AJIO
3. FirstCry (parent reviews are gold)
4. Giva (small catalog, fewer reviews)

For each review spider, follow the same pattern as amazon_review_spider.py
and flipkart_review_spider.py:

- Extend BaseWhydudSpider
- Accept product_id or product_url as input
- Scrape paginated reviews
- Extract: reviewer_name, rating, title, body, date, verified_purchase, helpful_votes
- Yield ReviewItem
- Handle pagination (load more reviews)

Myntra reviews are inside the product page — scroll down to review section.
AJIO reviews may require clicking "View All Reviews" to load.
FirstCry reviews are typically on the product page.
Giva reviews may use Shopify's Judgeme or similar widget — check for widget API.

Build ONE review spider at a time. Test each before moving to next.
```

---

## PIPELINE INTEGRATION CHECKLIST

After each spider is built, verify these pipeline steps work:

```
[ ] Spider yields valid ProductItem (all required fields present)
[ ] ValidationPipeline passes (title, price, external_id not null)
[ ] NormalizationPipeline runs (brand name normalized, price in paisa)
[ ] ProductPipeline stores:
    - New product in products table (or matches existing canonical product)
    - New listing in product_listings table (marketplace + external_id unique)
    - Price snapshot in price_snapshots (TimescaleDB hypertable)
[ ] MeilisearchPipeline indexes the product (search works)
[ ] StatsPipeline logs item count at spider close
[ ] No duplicate listings created on re-run (upsert behavior)
[ ] External URL is correct (clicking it opens the real product page)
[ ] Images are stored as JSON array of URLs
[ ] Specs are stored as valid JSONB
```

---

## DEBUGGING PROMPTS

### If Spider Gets Blocked

```
The {marketplace} spider is getting blocked. Debug:

1. What HTTP status codes are you getting? Log the response status for every request.
2. Check response body: is it a Cloudflare challenge page? Look for:
   - "Just a moment..." text
   - cf-browser-verification
   - <form id="challenge-form">
3. Check response headers for: cf-ray, cf-cache-status, server: cloudflare
4. If Cloudflare detected:
   - Switch to Playwright with stealth if not already
   - Add random delays (2-5s)
   - Rotate user agents
   - Use residential proxies if available
5. If CAPTCHA detected:
   - Log the URL and skip
   - Do NOT try to solve CAPTCHAs
   - Reduce request rate
6. Check if the site returns different content for mobile vs desktop user agents
7. Try accessing via curl from the server to check if the IP itself is blocked

Report: status codes, block type, response samples (first 500 chars).
```

### If Product Data Is Missing Fields

```
The {marketplace} spider is yielding products with missing {field}.

1. Go to the actual website in a browser
2. Right-click → Inspect on the element containing {field}
3. What is the HTML tag and CSS class?
4. Is it loaded dynamically (via JS after initial page load)?
5. If dynamic: is Playwright waiting long enough? Try increasing timeout.
6. If static: is the CSS selector correct? Log what the selector returns.
7. For embedded JSON: is the key path correct? Print the JSON structure.

Fix the selector/parser, test on 5 different products, verify consistency.
```

---

## SUCCESS CRITERIA

| Spider | Success Rate Target | Products per Run | Test Categories |
|--------|-------------------|-----------------|----------------|
| Giva | >95% | All products (~500-1000) | All collections |
| FirstCry | >80% | 50+ per category page | baby-care, toys |
| AJIO | >70% | 30+ per category page | men-t-shirts, women-kurtas |
| Myntra | >70% | 30+ per category page | men-tshirts, women-dresses |

**Definition of "success":**
- Product stored in DB with: title, brand, price, external_url, at least 1 image
- No duplicate listings on re-run
- External URL opens the correct product page
- Price is reasonable (not 0, not absurdly high)

---

## TIMELINE

| Week | Task |
|------|------|
| 1 Day 1 | Prompt 0 (seed data) + Prompt 1A (Giva spider) — should be done in 1 session |
| 1 Day 2 | Prompt 2A (FirstCry recon) + Prompt 2B (FirstCry spider) |
| 1 Day 3-4 | Prompt 3A (AJIO recon) + Prompt 3B (AJIO spider) + debugging |
| 1 Day 5-7 | Prompt 4A (Myntra recon) + Prompt 4B (Myntra spider) + debugging |
| 2 | Review spiders + pipeline verification + fix flaky tests |

---

**This plan is the single source of truth for new marketplace spider development.**
