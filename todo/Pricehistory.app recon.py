=== TASK: Reverse-engineer PriceHistory.app's internal API ===

We need to discover:
1. The API endpoint that serves price chart/graph data for a product
2. The API endpoint (or HTML pattern) for browsing/listing products by category
3. The sitemap structure (for bulk product discovery)
4. How to search products by ASIN or Flipkart URL

Do these steps IN ORDER. Save all findings to /home/user/RECON-RESULTS.md
(create the file at the start, append to it after each step).

Find all vulnerable points of pricehistory which may enhance our pricehistory backfill meachanism
=== Step 1: Check Sitemap ===

Fetch and analyze sitemap files:

  curl -s https://pricehistory.app/robots.txt > /tmp/ph_robots.txt
  cat /tmp/ph_robots.txt
  # Look for "Sitemap:" lines

  curl -s https://pricehistory.app/sitemap.xml > /tmp/ph_sitemap.xml
  head -100 /tmp/ph_sitemap.xml
  # Check if it's a sitemap index (has <sitemap> tags) or direct URL list

  # If sitemap index, fetch the first sub-sitemap:
  # curl -s <first_sitemap_url> | head -100

  # Count total product URLs (matching /p/):
  # grep -c '/p/' /tmp/ph_sitemap*.xml

Record in RECON-RESULTS.md:
- Does sitemap exist? What structure?
- How many product URLs are listed?
- Sample product URLs (first 10)


=== Step 2: Inspect Product Page HTML ===

Fetch a product page and look for embedded API data or JavaScript endpoints:

  curl -s 'https://pricehistory.app/p/apple-iphone-16-pink-128-gb-sy9uDEyp' \
    -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' \
    > /tmp/ph_product.html

Analyze the HTML:
  # Look for inline JSON data (common in Next.js/Nuxt apps)
  grep -oP '__NEXT_DATA__.*?</script>' /tmp/ph_product.html | head -1 | python3 -c "
  import sys, json
  raw = sys.stdin.read()
  # Extract JSON between > and </script>
  start = raw.find('>')
  end = raw.rfind('</script>')
  if start > 0 and end > 0:
      data = json.loads(raw[start+1:end])
      print(json.dumps(data, indent=2)[:5000])
  "

  # Look for __NUXT_DATA__ or similar SSR hydration data
  grep -oP '__NUXT|__INITIAL_STATE__|__APP_DATA__|window\.__' /tmp/ph_product.html

  # Look for API base URLs in script tags
  grep -oP 'https?://[^"'\''> ]*api[^"'\''> ]*' /tmp/ph_product.html | sort -u

  # Look for fetch/axios calls in inline scripts
  grep -oP 'fetch\([^)]+\)|axios\.[a-z]+\([^)]+\)' /tmp/ph_product.html

  # Look for any JSON-LD or embedded product data
  grep -oP '<script type="application/ld\+json">.*?</script>' /tmp/ph_product.html

  # Check for chart library data attributes (Highcharts, Chart.js, ApexCharts)
  grep -oiP 'highcharts|chart\.js|apexcharts|recharts|plotly|d3' /tmp/ph_product.html

  # Find all script src URLs (the JS bundles that contain API calls)
  grep -oP 'src="(/[^"]*\.js[^"]*)"' /tmp/ph_product.html | sort -u

Record findings in RECON-RESULTS.md.


=== Step 3: Inspect JavaScript Bundles ===

Download the main JS bundle(s) and search for API endpoints:

  # Get all JS bundle URLs from the page
  JS_URLS=$(grep -oP 'src="(/[^"]*\.js[^"]*)"' /tmp/ph_product.html | sed 's/src="//' | sed 's/"//')

  for js_path in $JS_URLS; do
    echo "=== Fetching: $js_path ==="
    curl -s "https://pricehistory.app${js_path}" > /tmp/ph_bundle.js 2>/dev/null
    
    # Search for API patterns
    echo "--- API endpoints ---"
    grep -oP '"/api/[^"]*"' /tmp/ph_bundle.js 2>/dev/null | sort -u | head -20
    grep -oP '"https?://[^"]*api[^"]*"' /tmp/ph_bundle.js 2>/dev/null | sort -u | head -20
    
    # Search for fetch/axios patterns  
    echo "--- Fetch patterns ---"
    grep -oP 'fetch\("[^"]*"' /tmp/ph_bundle.js 2>/dev/null | head -20
    grep -oP 'axios\.[a-z]+\("[^"]*"' /tmp/ph_bundle.js 2>/dev/null | head -20
    
    # Search for chart/graph/price/history related endpoints
    echo "--- Price/chart patterns ---"
    grep -oiP '[^a-z](price|chart|graph|history|timeseries)[^a-z][^"'\'']{0,100}' /tmp/ph_bundle.js 2>/dev/null | head -20
    
    echo ""
  done

Also search for any Next.js/Nuxt API route patterns:
  grep -oP '/api/[a-zA-Z0-9/_-]+' /tmp/ph_bundle.js 2>/dev/null | sort -u

Record all discovered endpoints in RECON-RESULTS.md.


=== Step 4: Playwright Network Interception ===

Use Playwright to load the product page and capture ALL XHR/fetch requests:

Create a Python script /tmp/recon_ph.py:
```python
import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    captured_requests = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1366, 'height': 768},
            locale='en-IN',
            timezone_id='Asia/Kolkata',
        )
        page = await context.new_page()

        # Intercept all requests
        async def on_request(request):
            if request.resource_type in ('xhr', 'fetch', 'document'):
                captured_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'resource_type': request.resource_type,
                    'headers': dict(request.headers),
                    'post_data': request.post_data,
                })

        # Intercept all responses
        captured_responses = []
        async def on_response(response):
            url = response.url
            content_type = response.headers.get('content-type', '')
            if 'json' in content_type or 'api' in url.lower() or 'price' in url.lower() or 'chart' in url.lower() or 'graph' in url.lower() or 'history' in url.lower():
                try:
                    body = await response.text()
                    captured_responses.append({
                        'url': url,
                        'status': response.status,
                        'content_type': content_type,
                        'body_preview': body[:2000],
                        'body_length': len(body),
                    })
                except:
                    captured_responses.append({
                        'url': url,
                        'status': response.status,
                        'content_type': content_type,
                        'body_preview': '<failed to read>',
                    })

        page.on('request', on_request)
        page.on('response', on_response)

        # Load product page
        print("Loading PriceHistory.app product page...")
        await page.goto(
            'https://pricehistory.app/p/apple-iphone-16-pink-128-gb-sy9uDEyp',
            wait_until='networkidle',
            timeout=30000,
        )

        # Wait extra for lazy-loaded chart data
        await asyncio.sleep(5)
        
        # Try scrolling to trigger lazy-loaded chart
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
        await asyncio.sleep(3)
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(3)

        # Try clicking chart period buttons if they exist
        for selector in ['[data-period]', '.chart-period', '.time-range', 'button:has-text("1Y")', 'button:has-text("All")', 'button:has-text("Max")']:
            try:
                el = await page.query_selector(selector)
                if el:
                    await el.click()
                    await asyncio.sleep(2)
                    print(f"Clicked: {selector}")
            except:
                pass

        await browser.close()

    # Report findings
    print("\n" + "="*80)
    print("CAPTURED XHR/FETCH REQUESTS")
    print("="*80)
    
    for req in captured_requests:
        if req['resource_type'] in ('xhr', 'fetch'):
            print(f"\n{req['method']} {req['url']}")
            if req['post_data']:
                print(f"  POST data: {req['post_data'][:200]}")

    print("\n" + "="*80)
    print("CAPTURED JSON RESPONSES (likely API endpoints)")
    print("="*80)
    
    for resp in captured_responses:
        print(f"\n[{resp['status']}] {resp['url']}")
        print(f"  Content-Type: {resp['content_type']}")
        print(f"  Body length: {resp.get('body_length', '?')}")
        print(f"  Preview: {resp['body_preview'][:500]}")

    # Save full results
    with open('/tmp/ph_recon_results.json', 'w') as f:
        json.dump({
            'requests': captured_requests,
            'responses': captured_responses,
        }, f, indent=2)
    
    print(f"\nFull results saved to /tmp/ph_recon_results.json")
    print(f"Total requests: {len(captured_requests)}")
    print(f"JSON responses: {len(captured_responses)}")

asyncio.run(main())
```

Run it:
  cd /home/user
  python /tmp/recon_ph.py

Analyze the output:
- Which URLs returned JSON with price data?
- What headers were sent?
- What does the response look like?

Record THE KEY FINDING in RECON-RESULTS.md:
- The exact URL that returns chart/price data
- Request headers needed
- Response format (paste first 500 chars of JSON)


=== Step 5: Test the discovered endpoint independently ===

Once you identify the chart data endpoint from Step 4, test it with curl:

  # Replace with actual URL found in Step 4
  curl -s 'https://pricehistory.app/api/DISCOVERED_ENDPOINT' \
    -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' \
    -H 'Accept: application/json' \
    -H 'Referer: https://pricehistory.app/' \
    | python3 -m json.tool | head -50

Test without cookies (to see if auth is required):
  curl -s 'https://pricehistory.app/api/DISCOVERED_ENDPOINT' \
    -H 'User-Agent: Mozilla/5.0' \
    | head -200

Test with a different product:
  # Change the product ID in the URL and see if it still works

Record in RECON-RESULTS.md:
- Does endpoint work without cookies? YES/NO
- What are the minimum required headers?
- Full response format with field descriptions


=== Step 6: Discover Browse/Category/Search endpoints ===

Use the same Playwright interception on browse pages:
```python
# Same script but navigate to these URLs instead:
urls_to_check = [
    'https://pricehistory.app/amazon-price-tracker',
    'https://pricehistory.app/flipkart-price-tracker',
    'https://pricehistory.app/price-drop',
    'https://pricehistory.app/amazon-price-drop',
    'https://pricehistory.app/search?q=iphone',
]
```

For each: capture XHR requests that return product lists.
We need an endpoint that returns a paginated list of products with their
marketplace URLs (Amazon/Flipkart links).

Record in RECON-RESULTS.md.

Commit: "docs: PriceHistory.app API recon results"