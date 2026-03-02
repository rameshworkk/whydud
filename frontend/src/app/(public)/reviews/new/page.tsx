"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Search, PenSquare, Star, ArrowRight, Package } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { cn } from "@/lib/utils/index";
import { productsApi } from "@/lib/api/products";
import { searchApi } from "@/lib/api/search";
import { reviewsApi } from "@/lib/api/reviews";
import { formatPrice } from "@/lib/utils/format";
import type { ProductSummary, Review } from "@/types";

// GET /api/v1/me/reviews returns Review with product context
interface MyReviewResponse extends Review {
  productTitle: string;
  productSlug: string;
  productImage?: string | null;
}

export default function WriteReviewPickerPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<ProductSummary[]>([]);
  const [searching, setSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const [myReviews, setMyReviews] = useState<MyReviewResponse[]>([]);
  const [recentProducts, setRecentProducts] = useState<ProductSummary[]>([]);
  const [loadingRecent, setLoadingRecent] = useState(true);

  // Fetch popular products on mount
  useEffect(() => {
    let cancelled = false;
    async function loadRecent() {
      try {
        const res = await productsApi.list();
        if (!cancelled && res.success && "data" in res) {
          const items = Array.isArray(res.data) ? res.data : [];
          setRecentProducts(items.slice(0, 8));
        }
      } catch {
        // API unavailable
      } finally {
        if (!cancelled) setLoadingRecent(false);
      }
    }
    loadRecent();
    return () => { cancelled = true; };
  }, []);

  // Fetch user's existing reviews if authenticated
  useEffect(() => {
    if (!isAuthenticated || authLoading) return;
    let cancelled = false;
    async function loadMyReviews() {
      try {
        const res = await reviewsApi.getMyReviews();
        if (!cancelled && res.success && "data" in res) {
          const items = Array.isArray(res.data) ? res.data : [];
          setMyReviews(items as MyReviewResponse[]);
        }
      } catch {
        // No reviews or not authenticated
      }
    }
    loadMyReviews();
    return () => { cancelled = true; };
  }, [isAuthenticated, authLoading]);

  // Search handler
  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;

    setSearching(true);
    setHasSearched(true);
    try {
      const res = await searchApi.search(q, { limit: 20 });
      if (res.success && "data" in res) {
        const data = res.data as { results?: ProductSummary[] };
        setSearchResults(Array.isArray(data.results) ? data.results : []);
      } else {
        setSearchResults([]);
      }
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }

  // Set of product slugs user already reviewed
  const reviewedSlugs = new Set(myReviews.map((r) => r.productSlug));

  return (
    <>
      <Header />

      <main className="min-h-[calc(100vh-64px)] bg-[#F8FAFC]">
        <div className="mx-auto px-4 md:px-6 py-8 lg:py-12" style={{ maxWidth: "var(--max-width)" }}>
          {/* Hero */}
          <div className="text-center mb-8">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[#FFF7ED]">
              <PenSquare className="h-6 w-6 text-[#F97316]" />
            </div>
            <h1 className="text-2xl md:text-3xl font-bold text-[#1E293B] tracking-tight">
              Write a Review
            </h1>
            <p className="mt-2 text-[#64748B] text-sm md:text-base max-w-md mx-auto">
              Search for the product you want to review. Earn rewards for every honest review.
            </p>
          </div>

          {/* Search bar */}
          <form
            onSubmit={handleSearch}
            className="mx-auto max-w-xl flex items-center h-12 rounded-full border border-[#E2E8F0] bg-white shadow-sm focus-within:border-[#F97316] focus-within:ring-2 focus-within:ring-[#F97316]/20 transition-all overflow-hidden mb-8"
          >
            <Search className="ml-4 h-4 w-4 text-[#94A3B8] shrink-0" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by product name, brand, or category..."
              className="flex-1 min-w-0 bg-transparent px-3 text-sm text-[#1E293B] placeholder:text-[#94A3B8] outline-none"
            />
            <button
              type="submit"
              disabled={searching}
              className={cn(
                "m-1.5 h-9 shrink-0 rounded-full bg-[#F97316] px-5 text-sm font-semibold text-white",
                "hover:bg-[#EA580C] active:bg-[#C2410C]",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1",
                "transition-colors disabled:opacity-50"
              )}
            >
              {searching ? "Searching..." : "Search"}
            </button>
          </form>

          {/* Search results */}
          {hasSearched && (
            <section className="mb-10">
              <h2 className="text-sm font-semibold text-[#1E293B] mb-3">
                {searching
                  ? "Searching..."
                  : searchResults.length > 0
                    ? `Found ${searchResults.length} product${searchResults.length === 1 ? "" : "s"}`
                    : "No products found. Try a different search term."}
              </h2>

              {!searching && searchResults.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {searchResults.map((product) => (
                    <ProductReviewCard
                      key={product.id}
                      product={product}
                      alreadyReviewed={reviewedSlugs.has(product.slug)}
                    />
                  ))}
                </div>
              )}
            </section>
          )}

          {/* My existing reviews */}
          {isAuthenticated && myReviews.length > 0 && !hasSearched && (
            <section className="mb-10">
              <h2 className="text-sm font-semibold text-[#1E293B] mb-3">Your Reviews</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {myReviews.map((review) => (
                  <Link
                    key={review.id}
                    href={`/product/${review.productSlug}/review`}
                    className="flex items-center gap-3 rounded-lg border border-[#E2E8F0] bg-white p-3 shadow-sm hover:shadow-md transition-shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
                  >
                    <div className="h-14 w-14 shrink-0 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] overflow-hidden flex items-center justify-center">
                      {review.productImage ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img
                          src={review.productImage}
                          alt=""
                          className="h-full w-full object-contain p-1"
                        />
                      ) : (
                        <Package className="h-5 w-5 text-[#94A3B8]" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-[#1E293B] line-clamp-1">
                        {review.productTitle}
                      </p>
                      <div className="flex items-center gap-1 mt-0.5">
                        {Array.from({ length: 5 }, (_, i) => (
                          <Star
                            key={i}
                            className={cn(
                              "h-3 w-3",
                              i < review.rating
                                ? "text-[#FBBF24] fill-[#FBBF24]"
                                : "text-[#E2E8F0]"
                            )}
                          />
                        ))}
                        <span className="text-xs text-[#64748B] ml-1">Edit review</span>
                      </div>
                    </div>
                    <ArrowRight className="h-4 w-4 text-[#94A3B8] shrink-0" />
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Popular products to review */}
          {!hasSearched && (
            <section>
              <h2 className="text-sm font-semibold text-[#1E293B] mb-3">
                Popular Products to Review
              </h2>
              {loadingRecent ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {Array.from({ length: 8 }, (_, i) => (
                    <div
                      key={i}
                      className="animate-pulse rounded-lg border border-[#E2E8F0] bg-white p-3"
                    >
                      <div className="h-32 rounded-lg bg-[#F1F5F9]" />
                      <div className="mt-3 h-4 w-3/4 rounded bg-[#F1F5F9]" />
                      <div className="mt-2 h-3 w-1/2 rounded bg-[#F1F5F9]" />
                    </div>
                  ))}
                </div>
              ) : recentProducts.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {recentProducts.map((product) => (
                    <ProductReviewCard
                      key={product.id}
                      product={product}
                      alreadyReviewed={reviewedSlugs.has(product.slug)}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-[#64748B] text-sm">
                  No products available right now.
                </div>
              )}
            </section>
          )}
        </div>
      </main>

      <Footer />
    </>
  );
}

// ── Product card for review picker ───────────────────────────────────────────

function ProductReviewCard({
  product,
  alreadyReviewed,
}: {
  product: ProductSummary;
  alreadyReviewed: boolean;
}) {
  const imgUrl =
    product.images?.[0] ?? "https://placehold.co/200x200/f8fafc/94a3b8?text=No+Image";

  return (
    <div className="flex flex-col rounded-lg border border-[#E2E8F0] bg-white shadow-sm hover:shadow-md transition-shadow overflow-hidden">
      {/* Image */}
      <div className="relative h-36 bg-[#F8FAFC] flex items-center justify-center border-b border-[#E2E8F0]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={imgUrl}
          alt={product.title}
          className="h-full w-full object-contain p-4"
        />
      </div>

      {/* Content */}
      <div className="flex-1 p-3 flex flex-col">
        {product.brandName && (
          <p className="text-[11px] font-medium text-[#4DB6AC]">{product.brandName}</p>
        )}
        <p className="text-sm font-medium text-[#1E293B] line-clamp-2 leading-snug mt-0.5">
          {product.title}
        </p>

        {/* Rating + price */}
        <div className="flex items-center gap-2 mt-2">
          {product.avgRating != null && (
            <div className="flex items-center gap-0.5">
              <Star className="h-3 w-3 text-[#FBBF24] fill-[#FBBF24]" />
              <span className="text-xs font-medium text-[#1E293B]">
                {product.avgRating.toFixed(1)}
              </span>
            </div>
          )}
          {product.currentBestPrice != null && (
            <span className="text-xs font-semibold text-[#16A34A]">
              {formatPrice(product.currentBestPrice)}
            </span>
          )}
        </div>

        {/* CTA */}
        <Link
          href={`/product/${product.slug}/review`}
          className={cn(
            "mt-3 inline-flex items-center justify-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1",
            alreadyReviewed
              ? "border border-[#E2E8F0] bg-white text-[#64748B] hover:bg-[#F8FAFC]"
              : "bg-[#F97316] text-white hover:bg-[#EA580C] active:bg-[#C2410C]"
          )}
        >
          <PenSquare className="h-3 w-3" />
          {alreadyReviewed ? "Edit Your Review" : "Write a Review"}
        </Link>
      </div>
    </div>
  );
}
