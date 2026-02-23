import type { Metadata } from "next";
import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { DudScoreGauge } from "@/components/product/dud-score-gauge";
import { MarketplacePrices } from "@/components/product/marketplace-prices";
import { CategoryScoreBars } from "@/components/product/category-score-bars";
import { PriceChart } from "@/components/product/price-chart";
import { RatingDistribution } from "@/components/reviews/rating-distribution";
import { MockReviewCard } from "@/components/reviews/review-card";
import { MOCK_PRODUCT_DETAIL } from "@/lib/mock-product-detail";
import { formatPrice } from "@/lib/utils";

interface ProductPageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: ProductPageProps): Promise<Metadata> {
  const { slug } = await params;
  void slug; // slug used for future API lookup
  const p = MOCK_PRODUCT_DETAIL;
  return {
    title: `${p.title} — Whydud`,
    description: `DudScore ${p.dudScore} · Best price ${formatPrice(p.bestPrice)} on ${p.bestMarketplace}`,
  };
}

export default async function ProductPage({ params }: ProductPageProps) {
  const { slug } = await params;
  void slug; // future: look up product by slug from API

  const p = MOCK_PRODUCT_DETAIL;
  const discountPct = Math.round(((p.mrp - p.bestPrice) / p.mrp) * 100);

  return (
    <>
      <Header />

      {/* Three-column dashboard — each column scrolls independently */}
      <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-[#F8FAFC]">

        {/* ── Left Sidebar: Product image + Key Specs ─────────────────────── */}
        <aside className="w-[260px] shrink-0 overflow-y-auto no-scrollbar border-r border-slate-200 bg-white flex flex-col">
          {/* Product image */}
          <div className="p-4 border-b border-slate-100">
            <div className="relative aspect-square w-full rounded-xl overflow-hidden bg-slate-50 border border-slate-100 flex items-center justify-center">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={p.image}
                alt={p.title}
                className="object-contain p-4 w-full h-full"
              />
            </div>
            {/* Thumbnail strip */}
            <div className="flex gap-2 mt-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className={`w-14 h-14 rounded-lg border-2 overflow-hidden cursor-pointer ${
                    i === 1 ? "border-[#F97316]" : "border-slate-200"
                  }`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={p.image}
                    alt={`View ${i}`}
                    className="object-contain p-1 w-full h-full"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Key Specs */}
          <div className="p-4 flex flex-col gap-0.5 flex-1">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">
              Key Specs
            </h3>
            {p.specs.map((spec) => (
              <div
                key={spec.label}
                className="flex items-start justify-between gap-2 py-2 border-b border-slate-50 last:border-b-0"
              >
                <span className="text-xs text-slate-500 shrink-0 w-[95px]">{spec.label}</span>
                <span className="text-xs font-medium text-slate-800 text-right leading-snug">
                  {spec.value}
                </span>
              </div>
            ))}
            <button className="mt-3 text-xs font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
              View all specifications →
            </button>
          </div>
        </aside>

        {/* ── Center: Title, price, DudScore, marketplace prices, chart ────── */}
        <main className="flex-1 overflow-y-auto no-scrollbar px-6 py-5">
          {/* Breadcrumb */}
          <nav className="flex items-center gap-1.5 text-xs text-slate-400 mb-4 flex-wrap">
            {p.breadcrumb.map((crumb, i) => (
              <span key={crumb} className="flex items-center gap-1.5">
                {i > 0 && <span>›</span>}
                {i < p.breadcrumb.length - 1 ? (
                  <Link href="/" className="hover:text-[#F97316] transition-colors">
                    {crumb}
                  </Link>
                ) : (
                  <span className="text-slate-600 font-medium">{crumb}</span>
                )}
              </span>
            ))}
          </nav>

          {/* Brand + category */}
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
            {p.brand} · {p.category}
          </p>

          {/* Title */}
          <h1 className="text-xl font-bold text-slate-900 leading-snug mb-2">{p.title}</h1>

          {/* Rating summary */}
          <div className="flex items-center gap-2 mb-4">
            <div className="flex gap-0.5">
              {Array.from({ length: 5 }, (_, i) => (
                <span
                  key={i}
                  className={`text-base ${
                    i < Math.round(p.avgRating) ? "text-yellow-400" : "text-slate-200"
                  }`}
                >
                  ★
                </span>
              ))}
            </div>
            <span className="text-sm font-semibold text-slate-700">{p.avgRating.toFixed(1)}</span>
            <span className="text-xs text-slate-400">
              ({p.totalReviews.toLocaleString("en-IN")} reviews)
            </span>
          </div>

          {/* Price block */}
          <div className="flex items-baseline gap-3 mb-2">
            <span className="text-3xl font-black text-slate-900">
              {formatPrice(p.bestPrice)}
            </span>
            <span className="text-base text-slate-400 line-through">
              {formatPrice(p.mrp)}
            </span>
            <span className="bg-green-100 text-green-700 text-xs font-bold px-2 py-0.5 rounded-full">
              {discountPct}% off
            </span>
          </div>

          {/* Best price source + lowest ever */}
          <p className="text-xs text-slate-500 mb-5">
            Best price on{" "}
            <span className="font-semibold text-slate-700">{p.bestMarketplace}</span>
            {" · "}
            <span className="text-green-600 font-medium">
              Lowest ever: {formatPrice(p.lowestEver)}
            </span>
          </p>

          {/* ── DudScore section ─────────────────────────────────────── */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 mb-5">
            <div className="flex items-start gap-4">
              {/* Gauge */}
              <div className="w-[160px] shrink-0">
                <DudScoreGauge score={p.dudScore} label={p.dudScoreLabel} />
              </div>

              {/* Score breakdown */}
              <div className="flex-1 min-w-0 pt-1">
                <div className="flex items-center gap-2 mb-3">
                  <h2 className="text-sm font-semibold text-slate-700">DudScore Breakdown</h2>
                  <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full capitalize">
                    {p.dudScoreConfidence}
                  </span>
                </div>
                <CategoryScoreBars components={p.dudScoreComponents} />
                <button className="mt-3 text-xs font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
                  View all reviews →
                </button>
              </div>
            </div>
          </div>

          {/* ── Compare all available options ────────────────────────── */}
          <div className="mb-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-3">
              Compare all available options
            </h2>
            <MarketplacePrices listings={p.listings} />
          </div>

          {/* ── Price History ─────────────────────────────────────────── */}
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <h2 className="text-sm font-semibold text-slate-700 mb-1">Price History</h2>
            <PriceChart data={p.priceHistory} />
          </div>
        </main>

        {/* ── Right Sidebar: Reviews ───────────────────────────────────────── */}
        <aside className="w-[340px] shrink-0 overflow-y-auto no-scrollbar border-l border-slate-200 bg-white">
          {/* Sticky header */}
          <div className="p-4 border-b border-slate-100 sticky top-0 bg-white z-10">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900">
                Reviews
                <span className="ml-2 text-sm font-normal text-slate-400">
                  ({p.totalReviews.toLocaleString("en-IN")})
                </span>
              </h2>
              <button className="text-xs font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
                Post a review
              </button>
            </div>
          </div>

          {/* Rating distribution */}
          <div className="p-4 border-b border-slate-100">
            <RatingDistribution
              distribution={p.ratingDistribution}
              avgRating={p.avgRating}
              totalReviews={p.totalReviews}
            />
          </div>

          {/* Review filter tabs */}
          <div className="px-4 py-3 border-b border-slate-100 flex gap-2 overflow-x-auto no-scrollbar">
            {["All", "Positive", "Critical", "Verified"].map((tab, i) => (
              <button
                key={tab}
                className={`shrink-0 px-3 py-1 rounded-full text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] ${
                  i === 0
                    ? "bg-[#F97316] text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Review cards */}
          <div className="px-4">
            {p.reviews.map((review) => (
              <MockReviewCard key={review.id} review={review} />
            ))}
            <button className="w-full py-4 text-sm font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
              Load more reviews
            </button>
          </div>
        </aside>
      </div>
    </>
  );
}
