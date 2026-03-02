"""Affiliate click tracking — URL generation and event recording.

Affiliate tags are injected at redirect time (not stored in DB) per Architecture §6.
Sub-tags encode user + product + click for attribution matching against parsed emails.
"""
from __future__ import annotations

import hashlib
import uuid
from typing import TYPE_CHECKING

from common.app_settings import ClickTrackingConfig

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.products.models import ProductListing


def generate_affiliate_url(
    listing: ProductListing,
    user: User | None = None,
    referrer_page: str = "product_page",
) -> str:
    """Generate tracked affiliate URL for a marketplace listing.

    Appends the marketplace's affiliate param + tag to the raw external URL.
    Also builds a sub_tag for click attribution (user/product/session).
    """
    base_url = listing.external_url
    marketplace = listing.marketplace

    # Build affiliate URL using marketplace-configured param/tag
    if marketplace.affiliate_tag and marketplace.affiliate_param:
        sep = "&" if "?" in base_url else "?"
        affiliate_url = (
            f"{base_url}{sep}{marketplace.affiliate_param}={marketplace.affiliate_tag}"
        )
    elif listing.affiliate_url:
        # Fall back to pre-built affiliate URL if stored on listing
        affiliate_url = listing.affiliate_url
    else:
        affiliate_url = base_url

    # Append sub-tag for attribution tracking (where supported)
    sub_tag = _build_sub_tag(listing, user, referrer_page)
    if sub_tag and marketplace.slug in ClickTrackingConfig.sub_tag_marketplaces():
        sep = "&" if "?" in affiliate_url else "?"
        sub_param = ClickTrackingConfig.sub_tag_param(marketplace.slug)
        if sub_param:
            affiliate_url = f"{affiliate_url}{sep}{sub_param}={sub_tag}"

    return affiliate_url


def _build_sub_tag(
    listing: ProductListing,
    user: User | None,
    referrer_page: str,
) -> str:
    """Build a sub-tag string for click attribution.

    Format: u{user_hash}_p{product_id_short}_{referrer}
    Keeps it short enough for URL params (~50 chars).
    """
    user_part = "anon"
    if user and user.pk:
        user_part = f"u{hashlib.sha256(str(user.pk).encode()).hexdigest()[:8]}"

    product_part = str(listing.product_id).replace("-", "")[:8]
    ref_short = referrer_page[:12]

    return f"{user_part}_p{product_part}_{ref_short}"


def hash_ip(ip: str) -> str:
    """One-way hash of IP address for analytics without storing raw IPs."""
    return hashlib.sha256(ip.encode()).hexdigest()


def hash_user_agent(ua: str) -> str:
    """One-way hash of User-Agent string."""
    return hashlib.sha256(ua.encode()).hexdigest()


def detect_device_type(user_agent: str) -> str:
    """Simple device type detection from User-Agent string."""
    ua_lower = user_agent.lower()
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        return "mobile"
    if "tablet" in ua_lower or "ipad" in ua_lower:
        return "tablet"
    return "desktop"
