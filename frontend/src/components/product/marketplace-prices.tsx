import { formatPrice } from "@/lib/utils";
import type { ProductListing } from "@/types";

interface MarketplacePricesProps {
  listings: ProductListing[];
  bestPrice: number | null;
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

export function MarketplacePrices({ listings, bestPrice }: MarketplacePricesProps) {
  return (
    <div className="flex flex-col gap-2">
      {listings.map((listing) => {
        const isBest = listing.currentPrice !== null && listing.currentPrice === bestPrice;
        const diffPct =
          bestPrice && listing.currentPrice && !isBest
            ? ((listing.currentPrice - bestPrice) / bestPrice) * 100
            : null;
        const logoClass =
          MARKETPLACE_COLORS[listing.marketplace.slug] ?? "bg-slate-500 text-white";
        const logoLetter =
          MARKETPLACE_LOGOS[listing.marketplace.slug] ?? listing.marketplace.name[0];

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
                <a
                  href={listing.buyUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`text-xs px-3 py-1 rounded-full font-semibold transition-colors ${
                    isBest
                      ? "bg-[#F97316] text-white hover:bg-[#EA580C]"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  Buy
                </a>
              ) : (
                <span className="text-xs text-slate-400">Out of stock</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
