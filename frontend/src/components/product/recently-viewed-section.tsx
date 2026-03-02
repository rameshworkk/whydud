"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useRecentlyViewed } from "@/hooks/use-recently-viewed";
import { ProductCard } from "@/components/product/product-card";

/**
 * "Recently Viewed" horizontal row — only renders for logged-in users
 * who have at least one recently viewed product.
 */
export function RecentlyViewedSection() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { products, isLoading } = useRecentlyViewed(8);

  // Don't render anything for logged-out users or while auth is loading
  if (authLoading || !isAuthenticated) return null;
  // Still loading recently viewed data — show skeleton
  if (isLoading) {
    return (
      <section className="bg-white py-8 border-b border-[#E2E8F0]">
        <div className="mx-auto px-4 md:px-6 max-w-[1280px]">
          <h2 className="text-[20px] font-bold text-[#1E293B] mb-4">Recently Viewed</h2>
          <div className="flex gap-3 overflow-x-auto pb-1 no-scrollbar">
            {Array.from({ length: 4 }, (_, i) => (
              <div
                key={i}
                className="shrink-0 w-[180px] md:w-[200px] h-[260px] rounded-xl bg-slate-100 animate-pulse"
              />
            ))}
          </div>
        </div>
      </section>
    );
  }

  // No recently viewed products — don't render the section
  if (products.length === 0) return null;

  return (
    <section className="bg-white py-8 border-b border-[#E2E8F0]">
      <div className="mx-auto px-4 md:px-6 max-w-[1280px]">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[20px] font-bold text-[#1E293B]">Recently Viewed</h2>
          <Link
            href="/search"
            className="flex items-center gap-1 text-[13px] font-medium text-[#F97316] hover:text-[#EA580C] transition-colors"
          >
            View all <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
        <div className="flex gap-3 overflow-x-auto pb-1 -mx-4 px-4 md:-mx-0 md:px-0 snap-x snap-mandatory no-scrollbar">
          {products.map((product) => (
            <div key={product.id} className="snap-start shrink-0 w-[180px] md:w-[200px]">
              <ProductCard product={product} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
