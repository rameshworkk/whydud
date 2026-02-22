import Link from "next/link";
import type { Deal } from "@/types";
import { formatPrice, formatRelative } from "@/lib/utils";

interface DealCardProps {
  deal: Deal;
}

const DEAL_TYPE_LABELS: Record<Deal["dealType"], string> = {
  error_price: "Error Price",
  lowest_ever: "Lowest Ever",
  genuine_discount: "Genuine Discount",
  flash_sale: "Flash Sale",
};

const CONFIDENCE_COLOURS: Record<Deal["confidence"], string> = {
  high: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-gray-100 text-gray-600",
};

/** Deal card for the Blockbuster Deals page. */
export function DealCard({ deal }: DealCardProps) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-card p-4">
      <div className="flex items-start justify-between gap-2">
        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${CONFIDENCE_COLOURS[deal.confidence]}`}>
          {deal.confidence} confidence
        </span>
        <span className="text-xs text-muted-foreground">{formatRelative(deal.detectedAt)}</span>
      </div>

      <div>
        <p className="text-xs text-muted-foreground">{DEAL_TYPE_LABELS[deal.dealType]}</p>
        <Link href={`/product/${deal.productSlug}`} className="mt-0.5 font-semibold hover:underline line-clamp-2">
          {deal.productTitle}
        </Link>
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-black text-green-700">{formatPrice(deal.currentPrice)}</span>
        {deal.referencePrice != null && (
          <span className="text-sm text-muted-foreground line-through">
            {formatPrice(deal.referencePrice)}
          </span>
        )}
        {deal.discountPct != null && (
          <span className="text-sm font-semibold text-green-700">
            -{Math.round(deal.discountPct)}%
          </span>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{deal.marketplaceName}</span>
        {deal.expiresAt && <span>Expires {formatRelative(deal.expiresAt)}</span>}
      </div>

      <Link
        href={`/product/${deal.productSlug}`}
        className="mt-auto rounded-lg bg-primary py-2 text-center text-sm font-medium text-primary-foreground hover:opacity-90"
      >
        View Deal
      </Link>
    </div>
  );
}
