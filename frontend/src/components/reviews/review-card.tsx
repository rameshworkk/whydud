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

export function ReviewCard({ review }: ReviewCardProps) {
  const avatarColor = nameToColor(review.reviewerName);
  const dateLabel = relativeDate(review.reviewDate);

  return (
    <div className="flex flex-col gap-2 border-b border-slate-100 py-4 last:border-b-0">
      {/* Header: avatar + name + date */}
      <div className="flex items-center gap-3">
        <span
          className="inline-flex items-center justify-center w-8 h-8 rounded-full text-white text-sm font-bold shrink-0"
          style={{ backgroundColor: avatarColor }}
        >
          {review.reviewerName.charAt(0)}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-slate-800 truncate">{review.reviewerName}</p>
          <p className="text-xs text-slate-400">{dateLabel}</p>
        </div>
      </div>

      {/* Stars */}
      <div className="flex items-center gap-1">
        {Array.from({ length: 5 }, (_, i) => (
          <span
            key={i}
            className={`text-sm ${i < review.rating ? "text-yellow-400" : "text-slate-200"}`}
          >
            ★
          </span>
        ))}
        {review.isVerifiedPurchase && (
          <span className="ml-1 text-xs text-green-600 font-medium">Verified</span>
        )}
        {review.isFlagged && (
          <span className="ml-1 text-xs text-red-500 font-medium">Flagged</span>
        )}
      </div>

      {/* Title */}
      <p className="text-sm font-semibold text-slate-800 leading-snug">{review.title}</p>

      {/* Body */}
      <p className="text-sm text-slate-600 leading-relaxed line-clamp-3">{review.body}</p>

      {/* Helpful */}
      <div className="flex items-center gap-3 pt-1">
        <span className="text-xs text-slate-400">Helpful?</span>
        <button className="flex items-center gap-1 text-xs text-slate-500 hover:text-[#F97316] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
          <span>👍</span>
          <span>{review.upvotes}</span>
        </button>
        <button className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-300 rounded">
          <span>👎</span>
          <span>{review.downvotes}</span>
        </button>
      </div>
    </div>
  );
}

/**
 * @deprecated Use ReviewCard with the real Review type instead.
 * Kept temporarily for backward compatibility during migration.
 */
export { ReviewCard as MockReviewCard };
