import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { ProductCard } from "@/components/product/product-card";
import { trendingApi } from "@/lib/api/trending";
import type { ProductSummary } from "@/types";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface TrendingSectionProps {
  /** Section heading text */
  title: string;
  /** Which trending endpoint to call */
  endpoint: "trending" | "rising" | "price-dropping";
  /** Max products to show (default 8) */
  limit?: number;
  /** "View all" link target — omit to hide the link */
  viewAllHref?: string;
}

// ---------------------------------------------------------------------------
// Endpoint → API call mapping
// ---------------------------------------------------------------------------

const API_MAP = {
  trending: () => trendingApi.getTrendingProducts(),
  rising: () => trendingApi.getRisingProducts(),
  "price-dropping": () => trendingApi.getPriceDropping(),
} as const;

// ---------------------------------------------------------------------------
// Component (async Server Component)
// ---------------------------------------------------------------------------

export async function TrendingSection({
  title,
  endpoint,
  limit = 8,
  viewAllHref,
}: TrendingSectionProps) {
  let products: ProductSummary[] = [];

  try {
    const res = await API_MAP[endpoint]();
    if (res.success && "data" in res) {
      products = Array.isArray(res.data) ? res.data.slice(0, limit) : [];
    }
  } catch {
    // API unavailable — render nothing
  }

  if (products.length === 0) return null;

  return (
    <section className="bg-white py-8 border-b border-[#E2E8F0]">
      <div className="mx-auto px-4 md:px-6 max-w-[1280px]">
        {/* Header row */}
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-[20px] font-bold text-[#1E293B]">{title}</h2>
          {viewAllHref && (
            <Link
              href={viewAllHref}
              className="flex items-center gap-1 text-[13px] font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
            >
              View all
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          )}
        </div>

        {/* Product grid: 2 cols mobile → 3 tablet → 4 desktop */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      </div>
    </section>
  );
}
