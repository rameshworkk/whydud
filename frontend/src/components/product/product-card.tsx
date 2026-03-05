import Link from "next/link";
import Image from "next/image";
import type { ProductSummary } from "@/types";
import { formatPrice } from "@/lib/utils/format";
import { getMarketplace } from "@/config/marketplace";
import { AddToCompareButton } from "@/components/product/add-to-compare-button";

interface ProductCardProps {
  product: ProductSummary;
}

/** Render 5 stars with filled/half/empty based on a 0–5 rating. */
function StarRating({ rating }: { rating: number }) {
  return (
    <span className="flex items-center gap-px" aria-label={`${rating} out of 5 stars`}>
      {Array.from({ length: 5 }, (_, i) => {
        const filled = rating >= i + 1;
        const half = !filled && rating >= i + 0.5;
        return (
          <svg
            key={i}
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="none"
            aria-hidden="true"
          >
            {half ? (
              <>
                <defs>
                  <linearGradient id={`half-${i}`}>
                    <stop offset="50%" stopColor="#FBBF24" />
                    <stop offset="50%" stopColor="#E2E8F0" />
                  </linearGradient>
                </defs>
                <path
                  d="M6 1L7.545 4.13L11 4.635L8.5 7.07L9.09 10.51L6 8.885L2.91 10.51L3.5 7.07L1 4.635L4.455 4.13L6 1Z"
                  fill={`url(#half-${i})`}
                />
              </>
            ) : (
              <path
                d="M6 1L7.545 4.13L11 4.635L8.5 7.07L9.09 10.51L6 8.885L2.91 10.51L3.5 7.07L1 4.635L4.455 4.13L6 1Z"
                fill={filled ? "#FBBF24" : "#E2E8F0"}
              />
            )}
          </svg>
        );
      })}
    </span>
  );
}

/** Format review count compactly: 89432 → "89.4K" */
function formatReviewCount(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

/** Product card for grids — uses ProductSummary from API. */
export function ProductCard({ product }: ProductCardProps) {
  const marketplace = getMarketplace(product.currentBestMarketplace ?? "");
  const imageUrl = product.images?.[0] ?? null;
  const rating = product.avgRating ?? 0;
  const reviewCount = product.totalReviews ?? 0;

  return (
    <Link
      href={`/product/${product.slug}`}
      className="group relative flex flex-col rounded-lg border border-slate-200 bg-white shadow-sm hover:shadow-md transition-shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2"
    >
      {/* Image area */}
      <div className="relative overflow-hidden rounded-t-lg bg-slate-50 aspect-square">
        {imageUrl ? (
          <Image
            src={imageUrl}
            alt={product.title}
            fill
            className="object-contain p-4 group-hover:scale-105 transition-transform duration-300"
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            unoptimized
          />
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground text-xs">
            No image
          </div>
        )}

        {/* DudScore badge */}
        {product.dudScore != null && (
          <span className="absolute top-2 left-2 rounded-sm bg-[#F97316] px-1.5 py-0.5 text-[10px] font-semibold text-white leading-tight">
            DudScore {product.dudScore}
          </span>
        )}

        {/* Compare button overlay */}
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          <AddToCompareButton product={product} className="shadow-sm" />
        </div>
      </div>

      {/* Card body */}
      <div className="flex flex-col gap-1 p-3">
        {/* Brand */}
        <p className="text-xs font-medium text-[#4DB6AC] truncate">{product.brandName ?? ""}</p>

        {/* Title */}
        <h3 className="text-sm font-medium leading-snug text-slate-800 line-clamp-2 min-h-[2.5rem]">
          {product.title}
        </h3>

        {/* Stars + rating */}
        {rating > 0 && (
          <div className="flex items-center gap-1.5">
            <StarRating rating={rating} />
            <span className="text-xs text-slate-500">
              {rating.toFixed(1)}{" "}
              <span className="text-slate-400">({formatReviewCount(reviewCount)})</span>
            </span>
          </div>
        )}

        {/* Price row */}
        <div className="mt-1 flex items-end justify-between gap-2">
          <div>
            <p className="text-base font-bold text-slate-900 leading-tight">
              {formatPrice(product.currentBestPrice)}
            </p>
            {product.lowestPriceEver != null && product.lowestPriceEver < (product.currentBestPrice ?? Infinity) && (
              <p className="text-xs text-green-600 leading-tight">
                Lowest: {formatPrice(product.lowestPriceEver)}
              </p>
            )}
          </div>

          <div className="flex flex-col items-end gap-1 shrink-0">
            {/* Marketplace badge */}
            {marketplace && (
              <span
                className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[9px] font-bold text-white leading-none ${marketplace.badgeColor}`}
                title={marketplace.name}
                aria-label={marketplace.name}
              >
                {marketplace.badgeLabel}
              </span>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}

/** Skeleton placeholder while product card loads. */
export function ProductCardSkeleton() {
  return (
    <div className="flex flex-col rounded-lg border border-slate-200 bg-white shadow-sm animate-pulse">
      <div className="aspect-square rounded-t-lg bg-slate-100" />
      <div className="flex flex-col gap-2 p-3">
        <div className="h-3 w-16 rounded bg-slate-100" />
        <div className="h-4 w-full rounded bg-slate-100" />
        <div className="h-4 w-3/4 rounded bg-slate-100" />
        <div className="h-3 w-20 rounded bg-slate-100" />
        <div className="mt-1 flex justify-between">
          <div className="h-5 w-16 rounded bg-slate-100" />
          <div className="h-5 w-5 rounded-full bg-slate-100" />
        </div>
      </div>
    </div>
  );
}
