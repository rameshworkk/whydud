"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { RatingDistribution } from "@/components/reviews/rating-distribution";
import { ReviewCard } from "@/components/reviews/review-card";
import { productsApi } from "@/lib/api/products";
import type { Review } from "@/types";

// ── Sort / filter config ────────────────────────────────────────────────────

const SORT_OPTIONS = [
  { value: "helpful", label: "Most Helpful" },
  { value: "recent", label: "Newest" },
  { value: "rating_desc", label: "Highest Rating" },
  { value: "rating_asc", label: "Lowest Rating" },
] as const;

const SOURCE_FILTERS = [
  { value: "", label: "All Reviews" },
  { value: "amazon-in", label: "Amazon.in" },
  { value: "flipkart", label: "Flipkart" },
  { value: "whydud", label: "Whydud" },
] as const;

// ── Props ───────────────────────────────────────────────────────────────────

interface ReviewSidebarProps {
  slug: string;
  totalReviews: number;
  avgRating: number;
  ratingDistribution: Record<1 | 2 | 3 | 4 | 5, number>;
  initialReviews: Review[];
}

export function ReviewSidebar({
  slug,
  totalReviews,
  avgRating,
  ratingDistribution,
  initialReviews,
}: ReviewSidebarProps) {
  const [reviews, setReviews] = useState<Review[]>(initialReviews);
  const [sort, setSort] = useState("helpful");
  const [source, setSource] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchReviews = useCallback(
    async (newSort: string, newSource: string) => {
      setLoading(true);
      try {
        const params: Record<string, string> = { sort: newSort };
        if (newSource) params.source = newSource;
        const res = await productsApi.getReviews(slug, params);
        if (res.success) {
          setReviews(res.data);
        }
      } finally {
        setLoading(false);
      }
    },
    [slug],
  );

  const handleSortChange = (newSort: string) => {
    setSort(newSort);
    fetchReviews(newSort, source);
  };

  const handleSourceChange = (newSource: string) => {
    setSource(newSource);
    fetchReviews(sort, newSource);
  };

  return (
    <aside className="w-[340px] shrink-0 overflow-y-auto no-scrollbar border-l border-slate-200 bg-white">
      {/* Sticky header */}
      <div className="p-4 border-b border-slate-100 sticky top-0 bg-white z-10">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">
            Reviews
            <span className="ml-2 text-sm font-normal text-slate-400">
              ({totalReviews.toLocaleString("en-IN")})
            </span>
          </h2>
          <Link
            href={`/product/${slug}/review`}
            className="text-xs font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
          >
            Post a review
          </Link>
        </div>
      </div>

      {/* Rating distribution */}
      <div className="p-4 border-b border-slate-100">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">
          Community rating
        </h3>
        <RatingDistribution
          distribution={ratingDistribution}
          avgRating={avgRating}
          totalReviews={totalReviews}
        />
      </div>

      {/* Source filter tabs */}
      <div className="px-4 py-3 border-b border-slate-100 flex gap-2 overflow-x-auto no-scrollbar">
        {SOURCE_FILTERS.map((filter) => (
          <button
            key={filter.value}
            onClick={() => handleSourceChange(filter.value)}
            className={`shrink-0 px-3 py-1 rounded-full text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] ${
              source === filter.value
                ? "bg-[#F97316] text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {/* Sort dropdown */}
      <div className="px-4 py-2 border-b border-slate-100 flex items-center justify-between">
        <span className="text-xs text-slate-400">Sort by</span>
        <select
          value={sort}
          onChange={(e) => handleSortChange(e.target.value)}
          className="text-xs font-semibold text-slate-700 bg-transparent border-none cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded pr-5"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Review cards */}
      <div className="px-4">
        {loading ? (
          <div className="py-8 flex justify-center">
            <span className="w-5 h-5 border-2 border-slate-200 border-t-[#F97316] rounded-full animate-spin" />
          </div>
        ) : reviews.length > 0 ? (
          reviews.map((review) => <ReviewCard key={review.id} review={review} />)
        ) : (
          <p className="py-6 text-sm text-slate-400 text-center">No reviews yet.</p>
        )}
        {!loading && reviews.length > 0 && (
          <button className="w-full py-4 text-sm font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
            Load more reviews
          </button>
        )}
      </div>
    </aside>
  );
}
