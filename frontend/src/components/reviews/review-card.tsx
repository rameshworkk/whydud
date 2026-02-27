import type { Review } from "@/types";

interface ReviewCardProps {
  review: Review;
}

/** Generate a deterministic color from a string (reviewer name). */
function nameToColor(name: string): string {
  const COLORS = ["#4DB6AC", "#F97316", "#1E293B", "#DC2626", "#16A34A", "#7C3AED", "#0891B2"];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return COLORS[Math.abs(hash) % COLORS.length]!;
}

/** Format an ISO date string into a relative label like "7 days ago". */
function relativeDate(dateStr: string | null): string {
  if (!dateStr) return "";
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 1) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return weeks === 1 ? "1 week ago" : `${weeks} weeks ago`;
  }
  if (diffDays < 365) {
    const months = Math.floor(diffDays / 30);
    return months === 1 ? "1 month ago" : `${months} months ago`;
  }
  const years = Math.floor(diffDays / 365);
  return years === 1 ? "1 year ago" : `${years} years ago`;
}

/** Marketplace slug → badge config */
const MARKETPLACE_BADGE: Record<string, { label: string; bg: string; text: string }> = {
  "amazon-in": { label: "Amazon.in", bg: "bg-orange-50", text: "text-[#F97316]" },
  flipkart: { label: "Flipkart", bg: "bg-blue-50", text: "text-blue-600" },
};

export function ReviewCard({ review }: ReviewCardProps) {
  const displayName = review.isScraped
    ? review.externalReviewerName || review.reviewerName
    : review.reviewerName;
  const avatarColor = nameToColor(displayName);
  const dateLabel = relativeDate(review.reviewDate);
  const badge = review.marketplaceSlug ? MARKETPLACE_BADGE[review.marketplaceSlug] : null;

  return (
    <div className="flex flex-col gap-2 border-b border-slate-100 py-4 last:border-b-0">
      {/* Header: avatar + name + badge + date */}
      <div className="flex items-center gap-3">
        <span
          className="inline-flex items-center justify-center w-8 h-8 rounded-full text-white text-sm font-bold shrink-0"
          style={{ backgroundColor: avatarColor }}
        >
          {displayName.charAt(0)}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-slate-800 truncate">{displayName}</p>
            {/* Source badge */}
            {review.isScraped && badge ? (
              <span className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] font-semibold ${badge.bg} ${badge.text}`}>
                {badge.label}
              </span>
            ) : !review.isScraped ? (
              <span className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-green-50 text-green-600">
                Whydud
              </span>
            ) : null}
          </div>
          <p className="text-xs text-slate-400">{dateLabel}</p>
        </div>
      </div>

      {/* Stars + verified */}
      <div className="flex items-center gap-1 flex-wrap">
        {Array.from({ length: 5 }, (_, i) => (
          <span
            key={i}
            className={`text-sm ${i < review.rating ? "text-yellow-400" : "text-slate-200"}`}
          >
            ★
          </span>
        ))}
        {review.isVerifiedPurchase && (
          <span className="ml-1 text-xs text-green-600 font-medium">Verified Purchase</span>
        )}
        {review.isFlagged && (
          <span className="ml-1 text-xs text-red-500 font-medium">Flagged</span>
        )}
      </div>

      {/* Variant info chip */}
      {review.variantInfo && (
        <span className="inline-block self-start px-2 py-0.5 rounded bg-slate-100 text-xs text-slate-500">
          {review.variantInfo}
        </span>
      )}

      {/* Title */}
      {review.title && (
        <p className="text-sm font-semibold text-slate-800 leading-snug">{review.title}</p>
      )}

      {/* Body */}
      {review.body && (
        <p className="text-sm text-slate-600 leading-relaxed line-clamp-3">{review.body}</p>
      )}

      {/* Review images mini gallery */}
      {review.media && review.media.length > 0 && (
        <div className="flex gap-2 overflow-x-auto no-scrollbar pt-1">
          {review.media.slice(0, 4).map((url, i) => (
            <img
              key={i}
              src={url}
              alt={`Review image ${i + 1}`}
              className="w-14 h-14 rounded object-cover border border-slate-200 shrink-0"
              loading="lazy"
            />
          ))}
          {review.media.length > 4 && (
            <span className="inline-flex items-center justify-center w-14 h-14 rounded bg-slate-100 text-xs text-slate-500 font-semibold shrink-0">
              +{review.media.length - 4}
            </span>
          )}
        </div>
      )}

      {/* Footer: helpful + vote buttons + external link */}
      <div className="flex items-center gap-3 pt-1 flex-wrap">
        {/* Scraped helpful count */}
        {review.isScraped && review.helpfulVoteCount > 0 && (
          <span className="text-xs text-slate-500">
            {review.helpfulVoteCount.toLocaleString("en-IN")} found helpful
          </span>
        )}

        {/* Whydud vote buttons */}
        {!review.isScraped && (
          <>
            <span className="text-xs text-slate-400">Helpful?</span>
            <button className="flex items-center gap-1 text-xs text-slate-500 hover:text-[#F97316] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
              <span>&#x1F44D;</span>
              <span>{review.upvotes}</span>
            </button>
            <button className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-300 rounded">
              <span>&#x1F44E;</span>
              <span>{review.downvotes}</span>
            </button>
          </>
        )}

        {/* External review link */}
        {review.isScraped && review.externalReviewUrl && badge && (
          <a
            href={review.externalReviewUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={`ml-auto text-xs font-semibold ${badge.text} hover:underline transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded`}
          >
            Read on {badge.label} &rarr;
          </a>
        )}
      </div>
    </div>
  );
}
