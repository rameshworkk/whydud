"use client";

import { useState } from "react";
import { formatPrice } from "@/lib/utils";
import { clicksApi } from "@/lib/api/products";
import { getMarketplace } from "@/config/marketplace";
import { PriceAlertButton } from "@/components/product/price-alert-button";
import type { ProductListing } from "@/types";

/* ── Props ────────────────────────────────────────────────────────────────── */

interface CrossPlatformPricePanelProps {
  listings: ProductListing[];
  lowestPriceEver: number | null;
  productId: string;
  referrerPage?: string;
}

/* ── Helpers ──────────────────────────────────────────────────────────────── */

function getBestPrice(listings: ProductListing[]): number | null {
  const prices = listings
    .filter((l) => l.inStock && l.currentPrice !== null)
    .map((l) => l.currentPrice as number);
  return prices.length > 0 ? Math.min(...prices) : null;
}

/* ── Component ────────────────────────────────────────────────────────────── */

export function CrossPlatformPricePanel({
  listings,
  lowestPriceEver,
  productId,
  referrerPage = "product_page",
}: CrossPlatformPricePanelProps) {
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const bestPrice = getBestPrice(listings);

  // Derive marketplaces for PriceAlertButton
  const alertMarketplaces = [...new Map(
    listings.map((l) => [l.marketplace.slug, { slug: l.marketplace.slug, name: l.marketplace.name }])
  ).values()];

  // Sort: in-stock first (by price asc), then out-of-stock
  const sorted = [...listings].sort((a, b) => {
    if (a.inStock !== b.inStock) return a.inStock ? -1 : 1;
    return (a.currentPrice ?? Infinity) - (b.currentPrice ?? Infinity);
  });

  async function handleBuyClick(listing: ProductListing) {
    setLoadingId(listing.id);
    try {
      const res = await clicksApi.track(
        listing.id,
        referrerPage,
        "cross_platform_prices",
      );
      if (res.success && res.data) {
        window.open(res.data.affiliateUrl, "_blank", "noopener,noreferrer");
      } else {
        window.open(listing.buyUrl, "_blank", "noopener,noreferrer");
      }
    } catch {
      window.open(listing.buyUrl, "_blank", "noopener,noreferrer");
    } finally {
      setLoadingId(null);
    }
  }

  if (sorted.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 text-center">
        <p className="text-sm text-slate-400">No marketplace listings available.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {sorted.map((listing) => {
        const isBest =
          listing.inStock &&
          listing.currentPrice !== null &&
          listing.currentPrice === bestPrice;
        const isLowestEver =
          lowestPriceEver !== null &&
          listing.currentPrice !== null &&
          listing.currentPrice <= lowestPriceEver &&
          listing.inStock;
        const isLoading = loadingId === listing.id;
        const mp = getMarketplace(listing.marketplace.slug);
        const badgeLabel = mp?.badgeLabel ?? listing.marketplace.name[0];
        const badgeColor = mp?.badgeColor ?? "bg-slate-500";

        return (
          <div
            key={listing.id}
            role={listing.inStock ? "button" : undefined}
            tabIndex={listing.inStock ? 0 : undefined}
            onClick={() => listing.inStock && !isLoading && handleBuyClick(listing)}
            onKeyDown={(e) => {
              if (listing.inStock && !isLoading && (e.key === "Enter" || e.key === " ")) {
                e.preventDefault();
                handleBuyClick(listing);
              }
            }}
            className={`flex items-center gap-3 rounded-lg px-4 py-3 border transition-colors
              ${listing.inStock ? "cursor-pointer" : "cursor-default opacity-60"}
              ${
                isBest
                  ? "bg-[#DCFCE7]/60 border-green-200 hover:bg-[#DCFCE7]"
                  : listing.inStock
                    ? "bg-white border-slate-200 hover:bg-slate-50"
                    : "bg-slate-50/40 border-slate-100"
              }
              ${isLoading ? "opacity-60 cursor-wait" : ""}
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]`}
          >
            {/* Marketplace badge */}
            <span
              className={`inline-flex items-center justify-center w-8 h-8 rounded-md text-xs font-bold text-white shrink-0 ${badgeColor}`}
            >
              {badgeLabel}
            </span>

            {/* Name + badges */}
            <div className="flex-1 min-w-0 text-left">
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-semibold text-slate-800 truncate">
                  {mp?.shortName ?? listing.marketplace.name}
                </span>
                {isBest && (
                  <span className="shrink-0 text-[10px] font-bold text-[#16A34A] bg-[#DCFCE7] px-1.5 py-0.5 rounded">
                    BEST
                  </span>
                )}
                {isLowestEver && !isBest && (
                  <span className="shrink-0 text-[10px] font-bold text-[#F97316] bg-[#FFF7ED] px-1.5 py-0.5 rounded">
                    LOWEST
                  </span>
                )}
              </div>
              {!listing.inStock && (
                <p className="text-[11px] text-slate-400 mt-0.5">Out of stock</p>
              )}
            </div>

            {/* Price */}
            <span
              className={`text-sm font-bold tabular-nums shrink-0 ${
                isBest ? "text-[#16A34A]" : listing.inStock ? "text-slate-800" : "text-slate-400"
              }`}
            >
              {formatPrice(listing.currentPrice)}
            </span>

            {/* Arrow indicator */}
            {listing.inStock && (
              <svg
                className="w-4 h-4 text-slate-400 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            )}
          </div>
        );
      })}

      {/* Price alert */}
      <div className="flex justify-center mt-2">
        <PriceAlertButton
          productId={productId}
          currentPrice={bestPrice ?? listings[0]?.currentPrice ?? 0}
          marketplaces={alertMarketplaces}
        />
      </div>
    </div>
  );
}
