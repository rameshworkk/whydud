"use client";

import { useState } from "react";
import { formatPrice } from "@/lib/utils";
import { clicksApi } from "@/lib/api/products";
import type { ProductListing } from "@/types";

interface MarketplacePricesProps {
  listings: ProductListing[];
  bestPrice: number | null;
  filteredBestPrice?: number | null;
  marketplaceFilterActive?: boolean;
  totalListings?: number;
  referrerPage?: string;
  onToggleFilter?: (showAll: boolean) => void;
}

const MARKETPLACE_LOGOS: Record<string, string> = {
  amazon_in: "A",
  flipkart: "F",
  croma: "C",
  myntra: "M",
  meesho: "Me",
  reliance_digital: "RD",
};

const MARKETPLACE_COLORS: Record<string, string> = {
  amazon_in: "bg-[#FF9900] text-white",
  flipkart: "bg-[#2874F0] text-white",
  croma: "bg-[#1A1A1A] text-white",
  myntra: "bg-[#FF3F6C] text-white",
  meesho: "bg-[#9B2335] text-white",
  reliance_digital: "bg-[#3366CC] text-white",
};

export function MarketplacePrices({
  listings,
  bestPrice,
  filteredBestPrice,
  marketplaceFilterActive = false,
  totalListings,
  referrerPage = "product_page",
  onToggleFilter,
}: MarketplacePricesProps) {
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const effectiveBestPrice = marketplaceFilterActive && filteredBestPrice != null
    ? filteredBestPrice
    : bestPrice;

  async function handleBuyClick(listing: ProductListing) {
    setLoadingId(listing.id);
    try {
      const res = await clicksApi.track(
        listing.id,
        referrerPage,
        "marketplace_prices",
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

  return (
    <div className="flex flex-col gap-2">
      {/* Filter info badge */}
      {marketplaceFilterActive && (
        <div className="flex items-center justify-between rounded-lg bg-[#FFF7ED] border border-[#F97316]/20 px-3 py-2">
          <span className="text-xs text-[#F97316] font-medium">
            Showing {listings.length} of {totalListings ?? "all"} marketplaces
          </span>
          {onToggleFilter && (
            <button
              type="button"
              onClick={() => onToggleFilter(true)}
              className="text-xs font-medium text-[#F97316] hover:text-[#EA580C] underline transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
            >
              Show all
            </button>
          )}
        </div>
      )}

      {listings.map((listing) => {
        const isBest = listing.currentPrice !== null && listing.currentPrice === effectiveBestPrice;
        const diffPct =
          effectiveBestPrice && listing.currentPrice && !isBest
            ? ((listing.currentPrice - effectiveBestPrice) / effectiveBestPrice) * 100
            : null;
        const logoClass =
          MARKETPLACE_COLORS[listing.marketplace.slug] ?? "bg-slate-500 text-white";
        const logoLetter =
          MARKETPLACE_LOGOS[listing.marketplace.slug] ?? listing.marketplace.name[0];
        const isLoading = loadingId === listing.id;

        return (
          <div
            key={listing.id}
            className={`flex items-center justify-between rounded-lg px-4 py-3 border ${
              isBest
                ? "bg-green-50 border-green-200"
                : "bg-white border-slate-200"
            }`}
          >
            {/* Left: logo + name */}
            <div className="flex items-center gap-3">
              <span
                className={`inline-flex items-center justify-center w-8 h-8 rounded-md text-xs font-bold shrink-0 ${logoClass}`}
              >
                {logoLetter}
              </span>
              <div>
                <p className="text-sm font-semibold text-slate-800">
                  {listing.marketplace.name}
                </p>
                {isBest && (
                  <p className="text-xs text-green-700 font-medium">Best Price</p>
                )}
                {diffPct !== null && (
                  <p className="text-xs text-slate-500">
                    {diffPct.toFixed(1)}% higher
                  </p>
                )}
              </div>
            </div>

            {/* Right: price + buy button */}
            <div className="flex flex-col items-end gap-1">
              <span
                className={`text-base font-bold ${
                  isBest ? "text-green-700" : "text-slate-800"
                }`}
              >
                {formatPrice(listing.currentPrice)}
              </span>
              {listing.inStock ? (
                <button
                  type="button"
                  onClick={() => handleBuyClick(listing)}
                  disabled={isLoading}
                  className={`text-xs px-3 py-1 rounded-full font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1 ${
                    isBest
                      ? "bg-[#F97316] text-white hover:bg-[#EA580C] active:bg-[#C2410C]"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200 active:bg-slate-300"
                  } ${isLoading ? "opacity-60 cursor-wait" : ""}`}
                >
                  {isLoading ? "..." : "Buy"}
                </button>
              ) : (
                <span className="text-xs text-slate-400">Out of stock</span>
              )}
            </div>
          </div>
        );
      })}

      {listings.length === 0 && (
        <div className="rounded-lg border border-dashed border-[#E2E8F0] bg-white p-6 text-center">
          <p className="text-sm text-slate-500">No listings from your preferred marketplaces.</p>
          {onToggleFilter && (
            <button
              type="button"
              onClick={() => onToggleFilter(true)}
              className="mt-2 text-xs font-medium text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
            >
              Show all marketplaces
            </button>
          )}
        </div>
      )}
    </div>
  );
}
