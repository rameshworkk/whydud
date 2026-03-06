"""Price history backfill pipeline.

Multi-phase pipeline combining BuyHatke (fast, zero-auth) and
PriceHistory.app (deep, token-auth) to populate price_snapshots.
"""
