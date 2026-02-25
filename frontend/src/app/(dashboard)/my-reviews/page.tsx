"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { Pencil, Trash2 } from "lucide-react";
import { reviewsApi } from "@/lib/api/reviews";
import { formatDate } from "@/lib/utils/format";
import { cn } from "@/lib/utils/index";
import type { Review } from "@/types";

// Extended review type with product context from GET /api/v1/me/reviews
interface MyReview extends Review {
  productTitle: string;
  productSlug: string;
  productImage?: string | null;
  publishStatus: "published" | "pending";
  publishesAt?: string | null;
}

function Stars({ rating }: { rating: number }) {
  return (
    <span className="inline-flex gap-px" aria-label={`${rating} out of 5 stars`}>
      {Array.from({ length: 5 }, (_, i) => (
        <svg key={i} width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
          <path
            d="M6 1L7.545 4.13L11 4.635L8.5 7.07L9.09 10.51L6 8.885L2.91 10.51L3.5 7.07L1 4.635L4.455 4.13L6 1Z"
            fill={i < rating ? "#FBBF24" : "#E2E8F0"}
          />
        </svg>
      ))}
    </span>
  );
}

function publishLabel(review: MyReview): { text: string; color: string } {
  if (review.publishStatus === "published") {
    return { text: "Published", color: "bg-green-50 text-[#16A34A]" };
  }
  if (review.publishesAt) {
    const remaining = new Date(review.publishesAt).getTime() - Date.now();
    if (remaining <= 0) return { text: "Published", color: "bg-green-50 text-[#16A34A]" };
    const hours = Math.ceil(remaining / (1000 * 60 * 60));
    return { text: `Publishing in ${hours}h`, color: "bg-amber-50 text-amber-600" };
  }
  return { text: "Pending", color: "bg-amber-50 text-amber-600" };
}

function ReviewRowSkeleton() {
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-4 animate-pulse">
      <div className="w-10 h-10 rounded-lg bg-slate-200 shrink-0" />
      <div className="flex-1">
        <div className="w-40 h-3.5 rounded bg-slate-200 mb-2" />
        <div className="w-24 h-2.5 rounded bg-slate-200 mb-2" />
        <div className="w-32 h-2.5 rounded bg-slate-200" />
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <div className="w-20 h-5 rounded-full bg-slate-200" />
        <div className="w-7 h-7 rounded bg-slate-200" />
        <div className="w-7 h-7 rounded bg-slate-200" />
      </div>
    </div>
  );
}

export default function MyReviewsPage() {
  const [reviews, setReviews] = useState<MyReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReviews() {
      try {
        const res = await reviewsApi.getMyReviews();
        if (res.success && "data" in res) {
          setReviews(res.data as MyReview[]);
        } else if (!res.success && "error" in res) {
          setError(res.error.message);
        }
      } catch {
        setError("Failed to load your reviews.");
      } finally {
        setLoading(false);
      }
    }
    fetchReviews();
  }, []);

  async function handleDelete(id: string) {
    try {
      const res = await reviewsApi.delete(id);
      if (res.success) {
        setReviews((prev) => prev.filter((r) => r.id !== id));
      }
    } catch {
      // Silently fail
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-900">My Reviews</h1>
        <Link
          href="/search"
          className="rounded-lg bg-[#F97316] px-4 py-2 text-sm font-semibold text-white hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2"
        >
          Write a Review
        </Link>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center">
          <p className="text-sm font-medium text-slate-700 mb-2">
            Please log in to view your reviews.
          </p>
          <a
            href="/login"
            className="inline-block rounded-lg bg-[#F97316] px-5 py-2 text-sm font-semibold text-white hover:bg-[#EA580C] transition-colors"
          >
            Log In
          </a>
        </div>
      )}

      {/* Review list */}
      <div className="flex flex-col gap-3">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => <ReviewRowSkeleton key={i} />)
        ) : reviews.length === 0 && !error ? (
          <div className="rounded-xl border border-[#E2E8F0] bg-white p-12 text-center">
            <p className="text-2xl mb-2">{"\u270D\uFE0F"}</p>
            <p className="text-sm font-semibold text-slate-700">
              You haven&apos;t written any reviews yet
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Start reviewing!
            </p>
            <Link
              href="/search"
              className="inline-block mt-4 text-sm font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
            >
              Browse Products →
            </Link>
          </div>
        ) : (
          reviews.map((review) => {
            const status = publishLabel(review);
            const imageUrl = review.productImage ?? null;

            return (
              <div
                key={review.id}
                className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-start gap-4"
              >
                {/* Product thumbnail */}
                <div className="relative h-10 w-10 shrink-0 overflow-hidden rounded-lg border border-slate-100 bg-slate-50">
                  {imageUrl ? (
                    <Image
                      src={imageUrl}
                      alt={review.productTitle}
                      fill
                      className="object-contain p-0.5"
                      sizes="40px"
                      unoptimized
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-[8px] text-slate-400">
                      No img
                    </div>
                  )}
                </div>

                {/* Review info */}
                <div className="flex-1 min-w-0">
                  <Link
                    href={`/product/${review.productSlug}`}
                    className="text-sm font-semibold text-slate-800 hover:text-[#F97316] transition-colors line-clamp-1"
                  >
                    {review.productTitle}
                  </Link>

                  <div className="flex items-center gap-2 mt-1">
                    <Stars rating={review.rating} />
                    <span className="text-xs text-[#64748B]">
                      {review.rating}.0
                    </span>
                  </div>

                  {review.title && (
                    <p className="text-xs text-slate-600 mt-1 line-clamp-1">
                      {review.title}
                    </p>
                  )}

                  <p className="text-[10px] text-[#94A3B8] mt-1">
                    {formatDate(review.reviewDate)}
                  </p>
                </div>

                {/* Status + actions */}
                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={cn(
                      "text-[10px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap",
                      status.color
                    )}
                  >
                    {status.text}
                  </span>

                  <Link
                    href={`/product/${review.productSlug}/review`}
                    className={cn(
                      "flex h-7 w-7 items-center justify-center rounded-lg border border-[#E2E8F0]",
                      "text-[#64748B] hover:text-[#F97316] hover:border-[#F97316]",
                      "transition-colors",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
                    )}
                    title="Edit review"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Link>

                  <button
                    type="button"
                    onClick={() => handleDelete(review.id)}
                    className={cn(
                      "flex h-7 w-7 items-center justify-center rounded-lg border border-[#E2E8F0]",
                      "text-[#64748B] hover:text-[#DC2626] hover:border-red-300",
                      "transition-colors",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
                    )}
                    title="Delete review"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
