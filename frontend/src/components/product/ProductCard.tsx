import Link from "next/link";
import Image from "next/image";
import type { ProductSummary } from "@/types";
import { formatPrice, dudScoreColour, formatDudScore } from "@/lib/utils";

interface ProductCardProps {
  product: ProductSummary;
}

/** Compact product card for search results and category pages. */
export function ProductCard({ product }: ProductCardProps) {
  const imageUrl = product.images?.[0] ?? null;
  const scoreClass = dudScoreColour(product.dudScore);

  return (
    <Link
      href={`/product/${product.slug}`}
      className="group flex flex-col rounded-xl border bg-card p-3 hover:shadow-md transition-shadow"
    >
      {/* Image */}
      <div className="relative mb-3 aspect-square overflow-hidden rounded-lg bg-muted">
        {imageUrl ? (
          <Image
            src={imageUrl}
            alt={product.title}
            fill
            className="object-contain p-2 group-hover:scale-105 transition-transform"
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground text-xs">
            No image
          </div>
        )}

        {/* DudScore badge */}
        {product.dudScore != null && (
          <span className={`absolute top-1 right-1 rounded-full bg-background px-1.5 py-0.5 text-xs font-bold ${scoreClass}`}>
            {formatDudScore(product.dudScore)}
          </span>
        )}
      </div>

      {/* Info */}
      <p className="text-xs text-muted-foreground">{product.brand.name}</p>
      <h3 className="mt-0.5 line-clamp-2 text-sm font-medium leading-snug">{product.title}</h3>

      <div className="mt-auto pt-2 flex items-end justify-between gap-2">
        <div>
          <p className="text-base font-bold">{formatPrice(product.currentBestPrice)}</p>
          {product.lowestPriceEver != null && product.lowestPriceEver < (product.currentBestPrice ?? Infinity) && (
            <p className="text-xs text-muted-foreground">
              Lowest ever {formatPrice(product.lowestPriceEver)}
            </p>
          )}
        </div>
        {product.avgRating != null && (
          <span className="shrink-0 text-xs text-muted-foreground">
            ★ {product.avgRating.toFixed(1)} ({product.totalReviews})
          </span>
        )}
      </div>
    </Link>
  );
}

/** Skeleton placeholder while product card loads. */
export function ProductCardSkeleton() {
  return (
    <div className="flex flex-col rounded-xl border bg-card p-3 animate-pulse">
      <div className="mb-3 aspect-square rounded-lg bg-muted" />
      <div className="h-3 w-16 rounded bg-muted" />
      <div className="mt-1 h-4 w-full rounded bg-muted" />
      <div className="mt-0.5 h-4 w-3/4 rounded bg-muted" />
      <div className="mt-auto pt-2 h-5 w-20 rounded bg-muted" />
    </div>
  );
}
