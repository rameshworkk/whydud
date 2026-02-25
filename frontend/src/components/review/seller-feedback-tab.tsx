"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils/index";
import { StarRatingInput } from "@/components/reviews/star-rating-input";
import { reviewsApi } from "@/lib/api/reviews";
import type { WriteReviewPayload } from "@/lib/api/types";
import type { VerifyPurchaseData } from "./verify-purchase-tab";
import type { LeaveReviewData } from "./leave-review-tab";
import type { RateFeaturesData } from "./rate-features-tab";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface SellerFeedbackData {
  deliveryRating: number;
  packagingRating: number;
  accuracyRating: number;
  communicationRating: number;
}

interface SellerFeedbackTabProps {
  slug: string;
  data: SellerFeedbackData;
  onChange: (update: Partial<SellerFeedbackData>) => void;
  /** All data from previous tabs, used to build the final payload. */
  purchaseData: VerifyPurchaseData;
  reviewData: LeaveReviewData;
  featuresData: RateFeaturesData;
  onSubmitSuccess?: (reviewId: string) => void;
  onSubmitError?: (message: string) => void;
}

// ── Seller rating fields ──────────────────────────────────────────────────────

const SELLER_RATINGS: { key: keyof SellerFeedbackData; label: string }[] = [
  { key: "deliveryRating", label: "Delivery Speed" },
  { key: "packagingRating", label: "Packaging Quality" },
  { key: "accuracyRating", label: "Product Accuracy" },
  { key: "communicationRating", label: "Communication" },
];

// ── Component ─────────────────────────────────────────────────────────────────

export function SellerFeedbackTab({
  slug,
  data,
  onChange,
  purchaseData,
  reviewData,
  featuresData,
  onSubmitSuccess,
  onSubmitError,
}: SellerFeedbackTabProps) {
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    if (reviewData.rating === 0) {
      onSubmitError?.("Please provide an overall rating before submitting.");
      return;
    }

    // ── Build payload from all tabs ─────────────────────────────
    const payload: WriteReviewPayload = {
      // Leave a review tab
      rating: reviewData.rating,
      title: reviewData.title || undefined,
      bodyPositive: reviewData.bodyPositive || undefined,
      bodyNegative: reviewData.bodyNegative || undefined,
      npsScore: reviewData.npsScore ?? undefined,

      // Rate features tab
      featureRatings:
        Object.keys(featuresData.featureRatings).length > 0
          ? featuresData.featureRatings
          : undefined,

      // Verify purchase tab
      purchasePlatform: purchaseData.platform || undefined,
      purchaseSeller: purchaseData.sellerName || undefined,
      purchaseDeliveryDate: purchaseData.deliveryDate || undefined,
      purchasePricePaid: purchaseData.pricePaid
        ? Number(purchaseData.pricePaid) * 100 // Convert ₹ to paisa
        : undefined,

      // Seller feedback tab
      sellerDeliveryRating: data.deliveryRating || undefined,
      sellerPackagingRating: data.packagingRating || undefined,
      sellerAccuracyRating: data.accuracyRating || undefined,
      sellerCommunicationRating: data.communicationRating || undefined,
    };

    setSubmitting(true);
    try {
      const res = await reviewsApi.submit(slug, payload);

      if (!res.success) {
        onSubmitError?.("Failed to submit review. Please try again.");
        return;
      }

      // Upload purchase proof if provided
      const reviewId = res.data?.id;
      if (reviewId && purchaseData.invoiceFile) {
        try {
          await reviewsApi.uploadPurchaseProof(
            String(reviewId),
            purchaseData.invoiceFile
          );
        } catch {
          // Non-blocking — review was already saved
        }
      }

      onSubmitSuccess?.(String(reviewId ?? ""));
    } catch {
      onSubmitError?.("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* ── Seller ratings ─────────────────────────────────────── */}
      <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-6">
        <h3 className="text-base font-semibold text-[#1E293B]">
          Rate the Seller
        </h3>

        <div className="mt-5 grid grid-cols-1 gap-x-8 gap-y-5 sm:grid-cols-2">
          {SELLER_RATINGS.map(({ key, label }) => (
            <div key={key} className="space-y-1.5">
              <p className="text-sm text-[#1E293B]">{label}</p>
              <StarRatingInput
                value={data[key]}
                onChange={(rating) => onChange({ [key]: rating })}
                size="md"
              />
            </div>
          ))}
        </div>
      </div>

      {/* ── Submit button ──────────────────────────────────────── */}
      <div className="pt-2">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={submitting}
          className={cn(
            "flex w-full items-center justify-center gap-2 rounded-lg px-6 py-3 text-sm font-semibold",
            "bg-[#1E293B] text-white",
            "hover:bg-[#0F172A] active:bg-black",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2",
            "transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          {submitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Submitting…
            </>
          ) : (
            "Submit Review"
          )}
        </button>
      </div>
    </div>
  );
}
