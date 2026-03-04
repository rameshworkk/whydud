"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils/index";
import { productsApi } from "@/lib/api/products";
import { Header } from "@/components/layout/Header";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  VerifyPurchaseTab,
  type VerifyPurchaseData,
} from "@/components/review/verify-purchase-tab";
import {
  LeaveReviewTab,
  type LeaveReviewData,
} from "@/components/review/leave-review-tab";
import {
  RateFeaturesTab,
  type RateFeaturesData,
} from "@/components/review/rate-features-tab";
import {
  SellerFeedbackTab,
  type SellerFeedbackData,
} from "@/components/review/seller-feedback-tab";
import type { ProductDetail } from "@/types/product";

// ── Combined form state ───────────────────────────────────────────────────────

interface ReviewFormState {
  purchase: VerifyPurchaseData;
  review: LeaveReviewData;
  features: RateFeaturesData;
  seller: SellerFeedbackData;
}

const INITIAL_STATE: ReviewFormState = {
  purchase: {
    hasPurchaseProof: null,
    invoiceFile: null,
    platform: "",
    sellerName: "",
    deliveryDate: "",
    pricePaid: "",
  },
  review: {
    rating: 0,
    title: "",
    bodyPositive: "",
    bodyNegative: "",
    npsScore: null,
    mediaFiles: [],
  },
  features: {
    featureRatings: {},
  },
  seller: {
    deliveryRating: 0,
    packagingRating: 0,
    accuracyRating: 0,
    communicationRating: 0,
  },
};

// ── localStorage helpers ─────────────────────────────────────────────────────

function draftKey(slug: string): string {
  return `review_draft_${slug}`;
}

/** Serializable subset of ReviewFormState (File objects are not stored). */
interface SerializableDraft {
  purchase: Omit<VerifyPurchaseData, "invoiceFile">;
  review: Omit<LeaveReviewData, "mediaFiles">;
  features: RateFeaturesData;
  seller: SellerFeedbackData;
  activeTab: string;
}

function saveDraft(slug: string, form: ReviewFormState, activeTab: string): void {
  try {
    const draft: SerializableDraft = {
      purchase: {
        hasPurchaseProof: form.purchase.hasPurchaseProof,
        platform: form.purchase.platform,
        sellerName: form.purchase.sellerName,
        deliveryDate: form.purchase.deliveryDate,
        pricePaid: form.purchase.pricePaid,
      },
      review: {
        rating: form.review.rating,
        title: form.review.title,
        bodyPositive: form.review.bodyPositive,
        bodyNegative: form.review.bodyNegative,
        npsScore: form.review.npsScore,
      },
      features: form.features,
      seller: form.seller,
      activeTab,
    };
    localStorage.setItem(draftKey(slug), JSON.stringify(draft));
  } catch {
    // localStorage full or unavailable — silently ignore
  }
}

function loadDraft(slug: string): { form: ReviewFormState; activeTab: string } | null {
  try {
    const raw = localStorage.getItem(draftKey(slug));
    if (!raw) return null;
    const draft: SerializableDraft = JSON.parse(raw);
    return {
      form: {
        purchase: { ...draft.purchase, invoiceFile: null },
        review: { ...draft.review, mediaFiles: [] },
        features: draft.features,
        seller: draft.seller,
      },
      activeTab: draft.activeTab || "verify",
    };
  } catch {
    return null;
  }
}

function clearDraft(slug: string): void {
  try {
    localStorage.removeItem(draftKey(slug));
  } catch {
    // ignore
  }
}

// ── Tab config ────────────────────────────────────────────────────────────────

const REVIEW_TABS = [
  { value: "verify", label: "Verify purchase" },
  { value: "review", label: "Leave a review" },
  { value: "features", label: "Rate Features" },
  { value: "feedback", label: "Seller Feedback" },
] as const;

// ── Component ─────────────────────────────────────────────────────────────────

export default function WriteReviewPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [productLoading, setProductLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("verify");
  const [form, setForm] = useState<ReviewFormState>(INITIAL_STATE);
  const [submitMessage, setSubmitMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const draftLoaded = useRef(false);

  // ── Load draft from localStorage on mount ─────────────────
  useEffect(() => {
    if (draftLoaded.current) return;
    draftLoaded.current = true;
    const saved = loadDraft(slug);
    if (saved) {
      setForm(saved.form);
      setActiveTab(saved.activeTab);
    }
  }, [slug]);

  // ── Auth guard ──────────────────────────────────────────────
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace(`/login?next=/product/${slug}/review`);
    }
  }, [authLoading, isAuthenticated, router, slug]);

  // ── Fetch product ───────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setProductLoading(true);
      try {
        const res = await productsApi.getDetail(slug);
        if (!cancelled && res.success && res.data) {
          setProduct(res.data);
        }
      } catch {
        // Product not found — stay on empty state
      } finally {
        if (!cancelled) setProductLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [slug]);

  // ── Persist draft to localStorage on every change ──────────
  useEffect(() => {
    if (!draftLoaded.current) return; // don't save before initial load
    saveDraft(slug, form, activeTab);
  }, [slug, form, activeTab]);

  // ── Tab data updaters ───────────────────────────────────────
  const updatePurchase = useCallback(
    (update: Partial<VerifyPurchaseData>) =>
      setForm((prev) => ({
        ...prev,
        purchase: { ...prev.purchase, ...update },
      })),
    []
  );

  const updateReview = useCallback(
    (update: Partial<LeaveReviewData>) =>
      setForm((prev) => ({
        ...prev,
        review: { ...prev.review, ...update },
      })),
    []
  );

  const updateFeatures = useCallback(
    (update: Partial<RateFeaturesData>) =>
      setForm((prev) => ({
        ...prev,
        features: { ...prev.features, ...update },
      })),
    []
  );

  const updateSeller = useCallback(
    (update: Partial<SellerFeedbackData>) =>
      setForm((prev) => ({
        ...prev,
        seller: { ...prev.seller, ...update },
      })),
    []
  );

  // ── Tab navigation helpers ──────────────────────────────────
  function goToTab(tab: string) {
    setActiveTab(tab);
    setSubmitMessage(null);
  }

  // ── Handlers ────────────────────────────────────────────────
  function handleSubmitSuccess() {
    clearDraft(slug);
    setSubmitMessage({
      type: "success",
      text: "Your review has been submitted successfully!",
    });
    setTimeout(() => {
      router.push(`/product/${slug}`);
    }, 1500);
  }

  function handleSubmitError(message: string) {
    setSubmitMessage({ type: "error", text: message });
  }

  // ── Loading / auth states ───────────────────────────────────
  if (authLoading || (!isAuthenticated && !authLoading)) {
    return (
      <>
        <Header />
        <div className="flex h-[calc(100vh-64px)] items-center justify-center bg-[#F8FAFC]">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#E2E8F0] border-t-[#F97316]" />
        </div>
      </>
    );
  }

  const mainImage =
    product?.images?.[0] ??
    "https://placehold.co/400x400/f8fafc/94a3b8?text=No+Image";

  return (
    <>
      <Header />

      <div className="min-h-[calc(100vh-64px)] bg-[#F8FAFC]">
        <div
          className="mx-auto px-4 py-6 md:px-6 lg:py-8"
          style={{ maxWidth: "var(--max-width)" }}
        >
          {/* ── Back link ────────────────────────────────────── */}
          <Link
            href={`/product/${slug}`}
            className={cn(
              "mb-6 inline-flex items-center gap-1 text-sm text-[#64748B]",
              "hover:text-[#1E293B]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded",
              "transition-colors"
            )}
          >
            <ChevronLeft className="h-4 w-4" />
            Back to product
          </Link>

          {/* ── Success / error message ──────────────────────── */}
          {submitMessage && (
            <div
              className={cn(
                "mb-6 rounded-lg border px-4 py-3 text-sm",
                submitMessage.type === "success"
                  ? "border-green-200 bg-green-50 text-green-700"
                  : "border-red-200 bg-red-50 text-red-700"
              )}
            >
              {submitMessage.text}
            </div>
          )}

          {/* ── 2-column layout ──────────────────────────────── */}
          <div className="flex flex-col gap-6 lg:flex-row lg:gap-8">
            {/* ── Left: Product sidebar ─────────────────────── */}
            <aside className="w-full shrink-0 lg:w-[300px]">
              {productLoading ? (
                <div className="rounded-lg border border-[#E2E8F0] bg-white p-4 animate-pulse">
                  <div className="aspect-square w-full rounded-lg bg-[#F1F5F9]" />
                  <div className="mt-4 h-5 w-3/4 rounded bg-[#F1F5F9]" />
                  <div className="mt-2 h-4 w-1/2 rounded bg-[#F1F5F9]" />
                </div>
              ) : product ? (
                <div className="rounded-lg border border-[#E2E8F0] bg-white p-4 sticky top-20">
                  {/* Product image */}
                  <div className="relative aspect-square w-full overflow-hidden rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={mainImage}
                      alt={product.title}
                      className="h-full w-full object-contain p-4"
                    />
                  </div>

                  {/* Thumbnails */}
                  {product.images && product.images.length > 1 && (
                    <div className="mt-3 flex gap-2">
                      {product.images.slice(0, 4).map((img, i) => (
                        <div
                          key={i}
                          className={cn(
                            "h-14 w-14 shrink-0 overflow-hidden rounded-lg border-2",
                            i === 0
                              ? "border-[#F97316]"
                              : "border-[#E2E8F0]"
                          )}
                        >
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={img}
                            alt={`View ${i + 1}`}
                            className="h-full w-full object-contain p-1"
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Title */}
                  <h2 className="mt-4 text-sm font-semibold text-[#1E293B] leading-snug">
                    {product.title}
                  </h2>
                </div>
              ) : (
                <div className="rounded-lg border border-[#E2E8F0] bg-white p-6 text-center">
                  <p className="text-sm text-[#64748B]">
                    Product not found.
                  </p>
                </div>
              )}
            </aside>

            {/* ── Right: Tabbed form ───────────────────────── */}
            <main className="flex-1 min-w-0">
              <Tabs
                value={activeTab}
                onValueChange={(v) => goToTab(v)}
              >
                <TabsList
                  className={cn(
                    "h-auto w-full justify-start gap-0 rounded-none border-b-0 bg-transparent p-0",
                    "flex-wrap"
                  )}
                >
                  {REVIEW_TABS.map((tab) => (
                    <TabsTrigger
                      key={tab.value}
                      value={tab.value}
                      className={cn(
                        "rounded-lg border px-4 py-2 text-sm font-medium shadow-none transition-colors",
                        "data-[state=inactive]:border-[#E2E8F0] data-[state=inactive]:bg-white data-[state=inactive]:text-[#1E293B]",
                        "data-[state=inactive]:hover:bg-[#F8FAFC]",
                        "data-[state=active]:border-[#1E293B] data-[state=active]:bg-[#1E293B] data-[state=active]:text-white",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1"
                      )}
                    >
                      {tab.label}
                    </TabsTrigger>
                  ))}
                </TabsList>

                {/* ── Verify Purchase ─────────────────────── */}
                <TabsContent value="verify" className="mt-6">
                  <VerifyPurchaseTab
                    data={form.purchase}
                    onChange={updatePurchase}
                    onNext={() => goToTab("review")}
                    onSkip={() => goToTab("review")}
                  />
                </TabsContent>

                {/* ── Leave a Review ──────────────────────── */}
                <TabsContent value="review" className="mt-6">
                  <LeaveReviewTab
                    data={form.review}
                    onChange={updateReview}
                    onNext={() => goToTab("features")}
                    onRateFeatures={() => goToTab("features")}
                  />
                </TabsContent>

                {/* ── Rate Features ───────────────────────── */}
                <TabsContent value="features" className="mt-6">
                  <RateFeaturesTab
                    slug={slug}
                    data={form.features}
                    onChange={updateFeatures}
                    onNext={() => goToTab("feedback")}
                    onSkip={() => goToTab("feedback")}
                  />
                </TabsContent>

                {/* ── Seller Feedback ─────────────────────── */}
                <TabsContent value="feedback" className="mt-6">
                  <SellerFeedbackTab
                    slug={slug}
                    data={form.seller}
                    onChange={updateSeller}
                    purchaseData={form.purchase}
                    reviewData={form.review}
                    featuresData={form.features}
                    onSubmitSuccess={handleSubmitSuccess}
                    onSubmitError={handleSubmitError}
                  />
                </TabsContent>
              </Tabs>
            </main>
          </div>
        </div>
      </div>
    </>
  );
}
