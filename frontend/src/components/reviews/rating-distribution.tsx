/** Star rating distribution — horizontal bars (5→1) with percentages. */

interface RatingDistributionProps {
  distribution: Record<1 | 2 | 3 | 4 | 5, number>; // star → percentage (0-100)
  avgRating: number;
  totalReviews: number;
}

export function RatingDistribution({
  distribution,
  avgRating,
  totalReviews,
}: RatingDistributionProps) {
  const stars = [5, 4, 3, 2, 1] as const;

  return (
    <div className="flex flex-col gap-3">
      {/* Summary row */}
      <div className="flex items-center gap-3 pb-2 border-b border-slate-200">
        <span className="text-3xl font-black text-slate-800">{avgRating.toFixed(1)}</span>
        <div>
          <div className="flex gap-0.5">
            {Array.from({ length: 5 }, (_, i) => (
              <span
                key={i}
                className={`text-base ${
                  i < Math.round(avgRating) ? "text-yellow-400" : "text-slate-200"
                }`}
              >
                ★
              </span>
            ))}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            {totalReviews.toLocaleString("en-IN")} reviews
          </p>
        </div>
      </div>

      {/* Bars */}
      {stars.map((star) => {
        const pct = distribution[star] ?? 0;
        return (
          <div key={star} className="flex items-center gap-2">
            <span className="text-xs text-slate-500 w-4 shrink-0 text-right">{star}</span>
            <span className="text-yellow-400 text-xs shrink-0">★</span>
            <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
              <div
                className="h-full bg-[#F97316] rounded-full transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs text-slate-500 w-8 shrink-0 text-right">{pct}%</span>
          </div>
        );
      })}
    </div>
  );
}
