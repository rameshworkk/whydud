import type { Review } from "@/types";
import { formatDate } from "@/lib/utils";

interface ReviewCardProps {
  review: Review;
}

/** Individual review card with credibility badge and vote controls. */
export function ReviewCard({ review }: ReviewCardProps) {
  const stars = Array.from({ length: 5 }, (_, i) => i < review.rating);

  return (
    <div className="flex flex-col gap-2 rounded-xl border p-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-2">
            <span className="flex">
              {stars.map((filled, i) => (
                <span key={i} className={filled ? "text-amber-400" : "text-muted"}>
                  ★
                </span>
              ))}
            </span>
            {review.isVerifiedPurchase && (
              <span className="rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                Verified Purchase
              </span>
            )}
            {review.isFlagged && (
              <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                Flagged
              </span>
            )}
          </div>
          <span className="text-sm font-medium">{review.reviewerName}</span>
          <span className="text-xs text-muted-foreground">{formatDate(review.reviewDate)}</span>
        </div>

        {review.credibilityScore != null && (
          <span className="shrink-0 text-xs text-muted-foreground">
            Credibility {Math.round(review.credibilityScore * 100)}%
          </span>
        )}
      </div>

      {/* Body */}
      {review.title && <p className="font-semibold text-sm">{review.title}</p>}
      <p className="text-sm text-muted-foreground line-clamp-4">{review.body}</p>

      {/* Pros / Cons */}
      {(review.extractedPros.length > 0 || review.extractedCons.length > 0) && (
        <div className="flex gap-4 text-xs">
          {review.extractedPros.length > 0 && (
            <div>
              <p className="font-semibold text-green-700 mb-0.5">Pros</p>
              <ul className="list-disc list-inside text-muted-foreground space-y-0.5">
                {review.extractedPros.map((p) => <li key={p}>{p}</li>)}
              </ul>
            </div>
          )}
          {review.extractedCons.length > 0 && (
            <div>
              <p className="font-semibold text-red-700 mb-0.5">Cons</p>
              <ul className="list-disc list-inside text-muted-foreground space-y-0.5">
                {review.extractedCons.map((c) => <li key={c}>{c}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Votes — TODO Sprint 2: wire to API */}
      <div className="flex items-center gap-3 text-xs text-muted-foreground pt-1">
        <button className="hover:text-foreground">▲ {review.upvotes}</button>
        <button className="hover:text-foreground">▼ {review.downvotes}</button>
      </div>
    </div>
  );
}

export function ReviewCardSkeleton() {
  return (
    <div className="flex flex-col gap-2 rounded-xl border p-4 animate-pulse">
      <div className="h-4 w-32 rounded bg-muted" />
      <div className="h-3 w-48 rounded bg-muted" />
      <div className="h-16 w-full rounded bg-muted" />
    </div>
  );
}
