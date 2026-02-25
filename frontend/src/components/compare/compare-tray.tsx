"use client";

import { useRouter } from "next/navigation";
import Image from "next/image";
import { X } from "lucide-react";
import { useCompare } from "@/contexts/compare-context";
import { formatPrice } from "@/lib/utils/format";
import { cn } from "@/lib/utils/index";

export function CompareTray() {
  const router = useRouter();
  const { products, removeFromCompare, clearCompare, isFull } = useCompare();

  const visible = products.length > 0;

  function handleCompare() {
    if (products.length < 2) return;
    const slugs = products.map((p) => p.slug).join(",");
    router.push(`/compare?slugs=${slugs}`);
  }

  return (
    <div
      className={cn(
        "fixed bottom-0 left-0 right-0 z-50 transition-transform transition-opacity duration-300 ease-out",
        visible
          ? "translate-y-0 opacity-100"
          : "translate-y-full opacity-0 pointer-events-none"
      )}
    >
      <div className="border-t border-[#E2E8F0] bg-white shadow-[0_-4px_24px_rgba(0,0,0,0.08)]">
        <div className="mx-auto flex max-w-[1280px] items-center gap-4 px-4 py-3">
          {/* ── Product thumbnails (scrollable on mobile) ──────── */}
          <div className="flex flex-1 items-center gap-3 overflow-x-auto">
            {products.map((product) => {
              const imageUrl = product.images?.[0] ?? null;

              return (
                <div
                  key={product.slug}
                  className="group relative flex shrink-0 items-center gap-2.5 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] py-2 pl-2 pr-8"
                >
                  {/* Thumbnail */}
                  <div className="relative h-10 w-10 shrink-0 overflow-hidden rounded bg-white">
                    {imageUrl ? (
                      <Image
                        src={imageUrl}
                        alt={product.title}
                        fill
                        className="object-contain p-0.5"
                        sizes="40px"
                        unoptimized
                      />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center bg-slate-100 text-[8px] text-slate-400">
                        No img
                      </div>
                    )}
                  </div>

                  {/* Title + price */}
                  <div className="min-w-0">
                    <p className="truncate text-xs font-medium text-[#1E293B] max-w-[120px]">
                      {product.title}
                    </p>
                    <p className="text-xs font-semibold text-[#64748B]">
                      {formatPrice(product.currentBestPrice)}
                    </p>
                  </div>

                  {/* Remove button */}
                  <button
                    type="button"
                    onClick={() => removeFromCompare(product.slug)}
                    className={cn(
                      "absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full",
                      "text-[#94A3B8] hover:bg-red-50 hover:text-[#DC2626]",
                      "transition-colors duration-150",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
                    )}
                    aria-label={`Remove ${product.title} from compare`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              );
            })}

            {/* Empty slots */}
            {Array.from({ length: Math.max(0, 2 - products.length) }, (_, i) => (
              <div
                key={`empty-${i}`}
                className="flex h-14 w-[180px] shrink-0 items-center justify-center rounded-lg border border-dashed border-[#E2E8F0] text-xs text-[#94A3B8]"
              >
                + Add product
              </div>
            ))}
          </div>

          {/* ── Right actions ─────────────────────────────────── */}
          <div className="flex shrink-0 items-center gap-3">
            {isFull && (
              <span className="hidden text-[10px] font-medium text-[#94A3B8] sm:block">
                Max 4
              </span>
            )}

            <button
              type="button"
              onClick={clearCompare}
              className={cn(
                "text-xs font-medium text-[#64748B] hover:text-[#DC2626]",
                "transition-colors duration-150",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:rounded"
              )}
            >
              Clear
            </button>

            <button
              type="button"
              onClick={handleCompare}
              disabled={products.length < 2}
              className={cn(
                "rounded-lg px-5 py-2.5 text-sm font-semibold text-white",
                "bg-[#F97316] hover:bg-[#EA580C] active:bg-[#C2410C]",
                "transition-colors duration-150",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2",
                "disabled:cursor-not-allowed disabled:opacity-50"
              )}
            >
              Compare Now
              {products.length >= 2 && (
                <span className="ml-1.5 text-xs opacity-80">
                  ({products.length})
                </span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
