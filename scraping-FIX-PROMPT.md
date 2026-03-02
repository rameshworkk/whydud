# FIX — Stop Context Cycling + Spider Must Check Middleware Flag

## Problem 1: Context cycling kills performance

The `_process_rotating` method creates 5 rotating contexts (rotating_0 through
rotating_4) with RANDOM viewports on every request. Each unique context_name +
viewport combo makes Playwright spin up a BRAND NEW browser context. That takes
5-10 seconds PLUS the DataImpulse connection time. With Amazon pages taking
10-20s to load through a proxy, you hit the 30s Playwright timeout constantly.

**Fix:** Use ONE single context for the rotating proxy. DataImpulse already
rotates IPs at their gateway level — you don't need to force new connections
by cycling contexts. One context, one persistent tunnel, DataImpulse handles
the IP rotation on their end.

In `apps/scraping/middlewares.py`, replace the entire `_process_rotating` method:

```python
def _process_rotating(self, request):
    """For rotating proxies: use a single persistent context.

    DataImpulse/SmartProxy rotate IPs at the gateway level.
    We don't need multiple contexts — one context, one tunnel.
    The gateway assigns different IPs per request internally.
    Creating multiple contexts just wastes memory and startup time.
    """
    context_name = "rotating_0"

    proxy_state = self.pool.all_states[0]
    proxy_dict = _parse_proxy_url(proxy_state.url)

    request.meta["playwright_context"] = context_name
    request.meta["_proxy_context_name"] = context_name
    request.meta["playwright_context_kwargs"] = {
        **_BASE_CONTEXT_KWARGS,
        "proxy": proxy_dict,
    }

    return None
```

This uses one context. No viewport randomization. No context cycling.
Fast, stable, reuses the existing browser context for every request.

## Problem 2: Spider doesn't check middleware's CAPTCHA flag

The middleware sets `response.meta["_is_captcha"] = True` on CAPTCHA.
But the Amazon spider's `parse_product_page` uses its OWN `_is_captcha_page()`
method which checks the HTML body independently. It then retries 3 times
(CAPTCHA_MAX_RETRIES = 3), each retry going through the same proxy context,
wasting 30+ seconds each.

**Fix:** In `apps/scraping/spiders/amazon_spider.py`, at the TOP of
`parse_product_page`, BEFORE the existing CAPTCHA check, add:

```python
# Check middleware's CAPTCHA flag first (rotating proxy already detected it)
if response.meta.get("_is_captcha"):
    self._captcha_count = getattr(self, "_captcha_count", 0) + 1
    self.items_failed += 1
    self.logger.debug(f"CAPTCHA flagged by proxy middleware — skipping {response.url[:60]}")
    return
```

This skips instantly (0 seconds) instead of retrying 3 times (90+ seconds).

Do the same in `apps/scraping/spiders/flipkart_spider.py` parse_product_page.

## Problem 3: Playwright default timeout is 30s — too short for proxy

DataImpulse adds latency. Amazon pages are heavy. 30 seconds is tight.

In `apps/scraping/spiders/base_spider.py`, in the `_apply_stealth` method,
add timeout increases:

```python
async def _apply_stealth(self, page, request):
    """Apply playwright-stealth scripts to a page before navigation."""
    try:
        await self.STEALTH.apply_stealth_async(page)
        # Increase timeouts for proxy connections (DataImpulse adds latency)
        page.set_default_navigation_timeout(60000)  # 60s instead of 30s
        page.set_default_timeout(45000)  # 45s for other operations
    except Exception as e:
        self.logger.warning(f"Stealth setup issue: {e}")
```

Also in `apps/scraping/scrapy_settings.py`, increase DOWNLOAD_TIMEOUT:

```python
DOWNLOAD_TIMEOUT = 90  # was 45 — proxy connections need more time
```

## Problem 4: PageMethod wait_for_load_state too strict

In the Amazon spider, product page requests use:
```python
PageMethod("wait_for_load_state", "domcontentloaded"),
```

But the Playwright handler also waits for "load" by default (line from
the traceback: `waiting until "load"`). The "load" event waits for ALL
resources (images, scripts, fonts). Through a proxy this can easily
take 30+ seconds.

In the Amazon spider's product page request meta, change the Playwright
page goto wait_until to "domcontentloaded" (faster, we don't need images to
load — we parse HTML):

Find where product page requests are made (in parse_listing_page) and
ensure the meta includes:
```python
"playwright_page_goto_kwargs": {"wait_until": "domcontentloaded"},
```

This tells Playwright to consider the page "loaded" once the HTML is parsed,
not waiting for every image and script to finish loading. Much faster through
a proxy.

Add this to ALL scrapy.Request calls for product pages in both Amazon and
Flipkart spiders. For example:

```python
meta = {
    "playwright": True,
    "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded"},
    "playwright_page_methods": [
        PageMethod("wait_for_load_state", "domcontentloaded"),
        PageMethod("wait_for_timeout", random.randint(2000, 4000)),
    ],
    "category_slug": category_slug,
}
```

## Summary of all changes

1. middlewares.py — Replace `_process_rotating` with single-context version
2. amazon_spider.py — Add `_is_captcha` meta check at top of parse_product_page
3. flipkart_spider.py — Same `_is_captcha` meta check
4. base_spider.py — Increase Playwright timeouts in _apply_stealth
5. scrapy_settings.py — DOWNLOAD_TIMEOUT = 90
6. amazon_spider.py — Add `playwright_page_goto_kwargs: {"wait_until": "domcontentloaded"}` to product page request meta
7. flipkart_spider.py — Same wait_until change

Test with:
```
python -m apps.scraping.runner amazon_in --max-pages 1 --save-html
```

Expected: 50-150 products in 10-15 minutes instead of 1 product then stall.
