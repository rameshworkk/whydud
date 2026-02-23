import type { MockReviewDetail } from "@/lib/mock-product-detail";

interface ReviewCardProps {
  review: MockReviewDetail;
}

export function MockReviewCard({ review }: ReviewCardProps) {
  return (
    <div className="flex flex-col gap-2 border-b border-slate-100 py-4 last:border-b-0">
      {/* Header: avatar + name + date */}
      <div className="flex items-center gap-3">
        <span
          className="inline-flex items-center justify-center w-8 h-8 rounded-full text-white text-sm font-bold shrink-0"
          style={{ backgroundColor: review.avatarColor }}
        >
          {review.reviewerName.charAt(0)}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-slate-800 truncate">{review.reviewerName}</p>
          <p className="text-xs text-slate-400">{review.dateLabel}</p>
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
      </div>

      {/* Title */}
      <p className="text-sm font-semibold text-slate-800 leading-snug">{review.title}</p>

      {/* Body */}
      <p className="text-sm text-slate-600 leading-relaxed line-clamp-4">{review.body}</p>

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
