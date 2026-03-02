"""Custom Playwright download handler with stealth injection.

Subclasses scrapy-playwright's handler to add playwright-stealth init scripts
to every new browser context, preventing headless detection by anti-bot systems.
"""
from typing import Optional

from playwright_stealth import Stealth
from scrapy import Spider
from scrapy_playwright.handler import (
    ScrapyPlaywrightDownloadHandler,
    BrowserContextWrapper,
)

import logging

logger = logging.getLogger(__name__)

# Pre-generate stealth script payload once at import time.
_STEALTH = Stealth()
_STEALTH_SCRIPT = _STEALTH.script_payload


class StealthPlaywrightHandler(ScrapyPlaywrightDownloadHandler):
    """ScrapyPlaywrightDownloadHandler that auto-injects stealth patches."""

    async def _create_browser_context(
        self,
        name: str,
        context_kwargs: Optional[dict],
        spider: Optional[Spider] = None,
    ) -> BrowserContextWrapper:
        wrapper = await super()._create_browser_context(
            name=name, context_kwargs=context_kwargs, spider=spider
        )
        # Inject stealth init scripts into every new context.
        # This runs BEFORE any page navigations in that context.
        await wrapper.context.add_init_script(_STEALTH_SCRIPT)
        logger.debug("Stealth init script injected into context '%s'", name)
        return wrapper
