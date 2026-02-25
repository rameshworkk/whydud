"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils/index";
import { StarRatingInput } from "@/components/reviews/star-rating-input";
import { reviewsApi } from "@/lib/api/reviews";
import type { ReviewFeature } from "@/lib/api/types";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface RateFeaturesData {
  featureRatings: Record<string, number>;
}

interface RateFeaturesTabProps {
  slug: string;
  data: RateFeaturesData;
  onChange: (update: Partial<RateFeaturesData>) => void;
  onNext: () => void;
  onSkip: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function RateFeaturesTab({
  slug,
  data,
  onChange,
  onNext,
  onSkip,
}: RateFeaturesTabProps) {
  const [features, setFeatures] = useState<ReviewFeature[]>([]);
  const [loading, setLoading] = useState(true);

  // ── Fetch feature keys from API ─────────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const res = await reviewsApi.getFeatures(slug);
        if (!cancelled && res.success && res.data) {
          setFeatures(res.data);
        }
      } catch {
        // Silently fail — features are optional
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [slug]);

  function setRating(key: string, rating: number) {
    onChange({
      featureRatings: { ...data.featureRatings, [key]: rating },
    });
  }

  return (
    <div className="space-y-6">
      {/* ── Feature ratings grid ───────────────────────────────── */}
      <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-6">
        <h3 className="text-base font-semibold text-[#1E293B]">
          Rate features
        </h3>

        {loading ? (
          <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 w-28 rounded bg-[#E2E8F0] animate-pulse" />
                <div className="h-5 w-32 rounded bg-[#E2E8F0] animate-pulse" />
              </div>
            ))}
          </div>
        ) : features.length === 0 ? (
          <p className="mt-3 text-sm text-[#64748B]">
            No feature ratings available for this product category.
          </p>
        ) : (
          <div className="mt-5 grid grid-cols-1 gap-x-8 gap-y-5 sm:grid-cols-2">
            {features.map((feature) => (
              <div key={feature.key} className="space-y-1.5">
                <p className="text-sm text-[#1E293B]">{feature.label}</p>
                <StarRatingInput
                  value={data.featureRatings[feature.key] ?? 0}
                  onChange={(rating) => setRating(feature.key, rating)}
                  size="md"
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Footer buttons ─────────────────────────────────────── */}
      <div className="flex items-center justify-end gap-4 pt-2">
        <button
          type="button"
          onClick={onSkip}
          className={cn(
            "px-5 py-2.5 text-sm font-medium text-[#1E293B]",
            "hover:text-[#64748B]",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded-lg",
            "transition-colors"
          )}
        >
          Skip
        </button>
        <button
          type="button"
          onClick={onNext}
          className={cn(
            "rounded-lg px-8 py-2.5 text-sm font-medium",
            "bg-[#E2E8F0] text-[#1E293B]",
            "hover:bg-[#CBD5E1] active:bg-[#94A3B8]",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1",
            "transition-colors"
          )}
        >
          Next
        </button>
      </div>
    </div>
  );
}
