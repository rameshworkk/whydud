"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { X, Scale, ChevronUp, ChevronDown } from "lucide-react";
import { useCompare } from "@/contexts/compare-context";
import { formatPrice } from "@/lib/utils/format";
import { cn } from "@/lib/utils/index";

export function CompareTray() {
  const router = useRouter();
  const { products, removeFromCompare, clearCompare } = useCompare();
  const [mobileExpanded, setMobileExpanded] = useState(false);

  const visible = products.length > 0;

  function handleCompare() {
    if (products.length < 2) return;
    const slugs = products.map((p) => p.slug).join(",");
    router.push(`/compare?slugs=${slugs}`);
  }

  return (
    <div
      className={cn(
        "fixed bottom-0 left-0 right-0 z-50 transition-transform duration-300 ease-out",
        visible
          ? "translate-y-0"
          : "translate-y-full pointer-events-none"
      )}
    >
      <div className="border-t border-[#E2E8F0] bg-white shadow-[0_-4px_24px_rgba(0,0,0,0.08)]">
        {/* ── Mobile collapsed bar ────────────────────────── */}
        <button
          type="button"
          onClick={() => setMobileExpanded((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-3 md:hidden"
        >
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-[#F97316]" />
            <span className="text-sm font-semibold text-[#1E293B]">
              Compare
            </span>
            <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-[#F97316] px-1.5 text-[10px] font-bold text-white">
              {products.length}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {products.length >= 2 && (
              <span
                onClick={(e) => {
                  e.stopPropagation();
                  handleCompare();
                }}
                className="rounded-lg bg-[#F97316] px-4 py-1.5 text-xs font-semibold text-white active:bg-[#EA580C]"
                role="button"
                tabIndex={0}
              >
                Compare Now
              </span>
            )}
            {mobileExpanded ? (
              <ChevronDown className="h-4 w-4 text-[#94A3B8]" />
            ) : (
              <ChevronUp className="h-4 w-4 text-[#94A3B8]" />
            )}
          </div>
        </button>

        {/* ── Mobile expanded product list ─────────────────── */}
        <div
          className={cn(
            "overflow-hidden transition-all duration-200 ease-out md:hidden",
            mobileExpanded ? "max-h-[300px]" : "max-h-0"
          )}
        >
          <div className="border-t border-[#E2E8F0] px-4 py-2 space-y-2">
            {products.map((product) => {
              const imageUrl = product.images?.[0] ?? null;
              return (
                <div
                  key={product.slug}
                  className="flex items-center gap-3 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-2"
                >
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
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium text-[#1E293B]">
                      {product.title}
                    </p>
                    <p className="text-xs font-semibold text-[#64748B]">
                      {formatPrice(product.currentBestPrice)}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeFromCompare(product.slug)}
                    className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[#94A3B8] hover:bg-red-50 hover:text-[#DC2626] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
                    aria-label={`Remove ${product.title} from compare`}
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              );
            })}
            <button
              type="button"
              onClick={clearCompare}
              className="w-full py-1 text-xs font-medium text-[#64748B] hover:text-[#DC2626] transition-colors"
            >
              Clear all
            </button>
          </div>
        </div>

        {/* ── Desktop bar ──────────────────────────────────── */}
        <div className="mx-auto hidden max-w-[1280px] items-center gap-4 px-4 py-3 md:flex">
          {/* Product thumbnails */}
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

            {/* Empty slots (show up to min 2) */}
            {Array.from({ length: Math.max(0, 2 - products.length) }, (_, i) => (
              <div
                key={`empty-${i}`}
                className="flex h-14 w-[180px] shrink-0 items-center justify-center rounded-lg border border-dashed border-[#E2E8F0] text-xs text-[#94A3B8]"
              >
                + Add product
              </div>
            ))}
          </div>

          {/* Right actions */}
          <div className="flex shrink-0 items-center gap-3">
            {products.length >= 4 && (
              <span className="text-[10px] font-medium text-[#94A3B8]">
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
