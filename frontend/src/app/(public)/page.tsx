import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import {
  Search,
  ChevronDown,
  ArrowRight,
  Star,
  SlidersHorizontal,
  ChevronRight,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { ProductCard } from "@/components/product/product-card";
import { TrendingSection } from "@/components/product/trending-section";
import { RecentlyViewedSection } from "@/components/product/recently-viewed-section";
import { productsApi, dealsApi } from "@/lib/api/products";
import { formatPrice } from "@/lib/utils/format";
import type { ProductSummary, Deal } from "@/types";

export const metadata: Metadata = {
  title: "Whydud — Discover Product Truth. Shop Smarter.",
  description:
    "India's product intelligence platform. Check DudScore, price history, and fake review detection before you buy.",
};

// ── Category data ─────────────────────────────────────────────────────────────

const CATEGORY_IMAGES = [
  { label: "Mobiles",      slug: "Smartphones",                 img: "https://placehold.co/100x100/dbeafe/1d4ed8?text=📱", color: "#dbeafe" },
  { label: "Laptops",      slug: "Laptops+%26+Computers",       img: "https://placehold.co/100x100/ede9fe/6d28d9?text=💻", color: "#ede9fe" },
  { label: "Audio",        slug: "Earphones+%26+Headphones",    img: "https://placehold.co/100x100/fce7f3/be185d?text=🎧", color: "#fce7f3" },
  { label: "Smartwatches", slug: "Smartwatches",                img: "https://placehold.co/100x100/d1fae5/065f46?text=⌚", color: "#d1fae5" },
  { label: "Home",         slug: "Home+Appliances",             img: "https://placehold.co/100x100/fef3c7/92400e?text=🏠", color: "#fef3c7" },
  { label: "Kitchen",      slug: "Kitchen+Appliances",          img: "https://placehold.co/100x100/ffedd5/9a3412?text=🍳", color: "#ffedd5" },
  { label: "Fashion",      slug: "Fashion",                     img: "https://placehold.co/100x100/fce7f3/9d174d?text=👗", color: "#fce7f3" },
  { label: "Beauty",       slug: "Beauty+%26+Personal+Care",    img: "https://placehold.co/100x100/fdf2f8/86198f?text=💄", color: "#fdf2f8" },
  { label: "Sports",       slug: "Sports",                      img: "https://placehold.co/100x100/ecfdf5/047857?text=⚽", color: "#ecfdf5" },
  { label: "Toys",         slug: "Toys",                        img: "https://placehold.co/100x100/fff7ed/c2410c?text=🧸", color: "#fff7ed" },
  { label: "TVs",          slug: "TVs",                         img: "https://placehold.co/100x100/f0fdf4/166534?text=📺", color: "#f0fdf4" },
  { label: "Grocery",      slug: "Grocery",                     img: "https://placehold.co/100x100/fefce8/713f12?text=🛒", color: "#fefce8" },
];

const FILTER_CHIPS = [
  { label: "All", slug: "" },
  { label: "Mobiles", slug: "Smartphones" },
  { label: "Laptops", slug: "Laptops+%26+Computers" },
  { label: "Audio", slug: "Earphones+%26+Headphones" },
  { label: "Smartwatches", slug: "Smartwatches" },
  { label: "Home Appliances", slug: "Home+Appliances" },
  { label: "Kitchen", slug: "Kitchen+Appliances" },
  { label: "Fashion", slug: "Fashion" },
  { label: "Beauty", slug: "Beauty+%26+Personal+Care" },
];

// ── Deal type config ──────────────────────────────────────────────────────────

const DEAL_TYPE_CONFIG: Record<string, { label: string; bg: string; emoji: string }> = {
  error_price: { label: "Error Price", bg: "bg-[#DC2626]", emoji: "🔥" },
  lowest_ever: { label: "Lowest Ever", bg: "bg-[#4DB6AC]", emoji: "📉" },
  genuine_discount: { label: "Big Discount", bg: "bg-[#F97316]", emoji: "💥" },
  flash_sale: { label: "Flash Sale", bg: "bg-[#7C3AED]", emoji: "⚡" },
};

// ── Deal card ─────────────────────────────────────────────────────────────────

function DealCard({ deal }: { deal: Deal }) {
  const fallback = { label: "Deal", bg: "bg-[#F97316]", emoji: "💥" };
  const config = DEAL_TYPE_CONFIG[deal.dealType] ?? fallback;
  const savedPaisa = (deal.referencePrice ?? 0) - deal.currentPrice;
  const imageUrl = deal.product?.images?.[0] ?? "https://placehold.co/72x72/f8fafc/94a3b8?text=?";

  return (
    <div className="flex flex-col rounded-xl border border-[#E2E8F0] bg-white shadow-sm hover:shadow-md transition-shadow">
      <div className={`${config.bg} rounded-t-xl px-3 py-1.5 flex items-center gap-1.5`}>
        <span className="text-sm">{config.emoji}</span>
        <span className="text-[11px] font-bold text-white uppercase tracking-wider">
          {config.label}
        </span>
      </div>
      <div className="flex gap-3 p-3">
        <div className="relative h-[72px] w-[72px] shrink-0 rounded-lg overflow-hidden bg-[#F8FAFC]">
          <Image
            src={imageUrl}
            alt={deal.product?.title ?? "Deal"}
            fill
            sizes="72px"
            className="object-contain p-1.5"
            unoptimized
          />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[11px] text-[#4DB6AC] font-medium truncate">{deal.product?.brandName ?? ""}</p>
          <Link
            href={`/product/${deal.product?.slug ?? ""}`}
            className="text-sm font-medium text-[#1E293B] line-clamp-2 leading-snug hover:text-[#F97316] transition-colors"
          >
            {deal.product?.title ?? "Unknown Product"}
          </Link>
        </div>
      </div>
      <div className="px-3 pb-3 flex items-end justify-between gap-2">
        <div>
          <p className="text-xl font-black text-[#16A34A] leading-none">
            {formatPrice(deal.currentPrice)}
          </p>
          {deal.referencePrice != null && (
            <p className="mt-0.5 text-xs text-[#94A3B8] line-through">
              {formatPrice(deal.referencePrice)}
            </p>
          )}
          {savedPaisa > 0 && (
            <p className="text-[11px] font-semibold text-[#16A34A]">
              Save {formatPrice(savedPaisa)}
            </p>
          )}
        </div>
        <div className="flex flex-col items-end gap-2 shrink-0">
          {deal.discountPct != null && deal.discountPct > 0 && (
            <span className="rounded-full bg-[#DC2626] px-2 py-0.5 text-[11px] font-black text-white">
              -{Math.round(deal.discountPct)}%
            </span>
          )}
          <Link
            href={`/product/${deal.product?.slug ?? ""}`}
            className="rounded-full bg-[#F97316] px-3 py-1 text-xs font-semibold text-white hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors"
          >
            View Deal
          </Link>
        </div>
      </div>
    </div>
  );
}

// ── Horizontal product row ────────────────────────────────────────────────────

function ProductRow({ products }: { products: ProductSummary[] }) {
  return (
    <div className="flex gap-3 overflow-x-auto pb-1 -mx-4 px-4 md:-mx-0 md:px-0 snap-x snap-mandatory no-scrollbar">
      {products.map((product) => (
        <div key={product.id} className="snap-start shrink-0 w-[180px] md:w-[200px]">
          <ProductCard product={product} />
        </div>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default async function HomePage() {
  // Fetch products and deals from the real API
  let products: ProductSummary[] = [];
  let deals: Deal[] = [];

  try {
    const productsRes = await productsApi.list();
    if (productsRes.success && "data" in productsRes) {
      products = Array.isArray(productsRes.data) ? productsRes.data : [];
    }
  } catch {
    // API unavailable — render empty
  }

  try {
    const dealsRes = await dealsApi.list();
    if (dealsRes.success && "data" in dealsRes) {
      deals = Array.isArray(dealsRes.data) ? dealsRes.data : [];
    }
  } catch {
    // API unavailable — render empty
  }

  const trendingProducts = products.slice(0, 8);
  const topRatedProducts = [...products].sort((a, b) => (b.avgRating ?? 0) - (a.avgRating ?? 0)).slice(0, 6);
  const bestsellers = [...products].sort((a, b) => (b.totalReviews ?? 0) - (a.totalReviews ?? 0)).slice(0, 6);
  const reviewProducts = products.slice(0, 3);

  return (
    <>
      <Header />

      <main>

        {/* ── Category image strip ──────────────────────────────────────────── */}
        <section className="bg-white border-b border-[#E2E8F0]">
          <div className="mx-auto px-4 md:px-6 max-w-[1280px]">
            <div className="flex gap-2 overflow-x-auto py-3 no-scrollbar justify-center">
              {CATEGORY_IMAGES.map((cat) => (
                <Link
                  key={cat.label}
                  href={`/search?category=${cat.slug}`}
                  className="shrink-0 flex flex-col items-center gap-1.5 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded-lg p-1"
                >
                  <div
                    className="h-[72px] w-[88px] rounded-xl overflow-hidden relative transition-transform group-hover:scale-105"
                    style={{ backgroundColor: cat.color }}
                  >
                    <Image
                      src={cat.img}
                      alt={cat.label}
                      fill
                      className="object-contain p-2"
                      unoptimized
                    />
                  </div>
                  <span className="text-[11px] font-medium text-[#64748B] group-hover:text-[#F97316] transition-colors whitespace-nowrap">
                    {cat.label}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* ── Hero ─────────────────────────────────────────────────────────── */}
        <section className="bg-white border-b border-[#E2E8F0]">
          <div className="mx-auto px-4 md:px-6 max-w-[1280px]">
            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-0 md:gap-8 items-center py-10 md:py-12">

              {/* Left: title + description + search */}
              <div className="max-w-[630px]">
                <h1 className="text-[36px] md:text-[44px] font-bold text-[#1E293B] leading-[1.15] tracking-tight">
                  Discover product truth.{" "}
                  <span className="block">Shop smarter.</span>
                </h1>
                <p className="mt-3 text-[18px] text-[#64748B] leading-relaxed">
                  Read real reviews. Share your honest experience.
                </p>

                {/* Search bar */}
                <form
                  action="/search"
                  method="GET"
                  className="mt-6 flex items-center h-[60px] max-w-[570px] rounded-full bg-[#fbfbfb] border border-[#E2E8F0] shadow-[0px_2px_6px_rgba(0,0,0,0.08)] focus-within:border-[#F97316] focus-within:ring-2 focus-within:ring-[#F97316]/20 transition-all overflow-hidden"
                >
                  {/* Category selector */}
                  <button
                    type="button"
                    className="flex items-center gap-1.5 pl-5 pr-3 shrink-0 h-full text-[#64748B] text-[14px] font-normal whitespace-nowrap hover:text-[#1E293B] transition-colors"
                  >
                    All Categories
                    <ChevronDown className="h-3.5 w-3.5 shrink-0" />
                  </button>

                  {/* Divider */}
                  <div className="w-px h-[36px] bg-[#E2E8F0] shrink-0" />

                  {/* Input */}
                  <input
                    type="search"
                    name="q"
                    placeholder="Search for products, brands, services, category..."
                    className="flex-1 min-w-0 bg-transparent px-3 text-[14px] text-[#1E293B] placeholder:text-[#94A3B8] outline-none"
                  />

                  {/* Search button */}
                  <button
                    type="submit"
                    aria-label="Search"
                    className="m-[6px] h-[48px] w-[48px] shrink-0 rounded-full bg-[#F97316] flex items-center justify-center hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
                  >
                    <Search className="h-5 w-5 text-white" />
                  </button>
                </form>
              </div>

              {/* Right: floating product visuals */}
              <div className="hidden md:block relative w-[460px] h-[270px] shrink-0">
                {/* Product card 1 - top left of right section */}
                <div className="absolute left-[30px] top-[20px] w-[110px] bg-white rounded-xl shadow-[0px_4px_16px_rgba(0,0,0,0.12)] border border-[#E2E8F0] overflow-hidden">
                  <div className="h-[80px] relative bg-[#dbeafe]">
                    <Image
                      src="https://placehold.co/110x80/dbeafe/1d4ed8?text=Phone"
                      alt="Mobile"
                      fill
                      className="object-contain p-2"
                      unoptimized
                    />
                  </div>
                  <div className="px-2 py-1.5">
                    <p className="text-[10px] font-semibold text-[#1E293B] truncate">Galaxy S24 FE</p>
                    <p className="text-[10px] text-[#16A34A] font-bold">₹42,999</p>
                  </div>
                </div>

                {/* Product card 2 - top right */}
                <div className="absolute right-[10px] top-[10px] w-[110px] bg-white rounded-xl shadow-[0px_4px_16px_rgba(0,0,0,0.12)] border border-[#E2E8F0] overflow-hidden">
                  <div className="h-[80px] relative bg-[#ede9fe]">
                    <Image
                      src="https://placehold.co/110x80/ede9fe/6d28d9?text=Laptop"
                      alt="Laptop"
                      fill
                      className="object-contain p-2"
                      unoptimized
                    />
                  </div>
                  <div className="px-2 py-1.5">
                    <p className="text-[10px] font-semibold text-[#1E293B] truncate">MacBook Air M2</p>
                    <p className="text-[10px] text-[#16A34A] font-bold">₹89,990</p>
                  </div>
                </div>

                {/* Product card 3 - bottom center */}
                <div className="absolute left-[140px] bottom-[20px] w-[115px] bg-white rounded-xl shadow-[0px_4px_16px_rgba(0,0,0,0.12)] border border-[#E2E8F0] overflow-hidden">
                  <div className="h-[80px] relative bg-[#fce7f3]">
                    <Image
                      src="https://placehold.co/115x80/fce7f3/be185d?text=Earbuds"
                      alt="Earbuds"
                      fill
                      className="object-contain p-2"
                      unoptimized
                    />
                  </div>
                  <div className="px-2 py-1.5">
                    <p className="text-[10px] font-semibold text-[#1E293B] truncate">boAt Airdopes</p>
                    <p className="text-[10px] text-[#16A34A] font-bold">₹599</p>
                  </div>
                </div>

                {/* Floating label pills */}
                <div className="absolute left-[0px] top-[130px] bg-white rounded-full px-3 py-1.5 shadow-[0px_2px_10px_rgba(0,0,0,0.10)] border border-[#E2E8F0]">
                  <span className="text-[12px] font-semibold text-[#1E293B]">Find trusted reviews</span>
                </div>
                <div className="absolute right-[0px] top-[170px] bg-white rounded-full px-3 py-1.5 shadow-[0px_2px_10px_rgba(0,0,0,0.10)] border border-[#E2E8F0]">
                  <span className="text-[12px] font-semibold text-[#1E293B]">Share your Experience</span>
                </div>
                <div className="absolute left-[20px] bottom-[15px] bg-white rounded-full px-3 py-1.5 shadow-[0px_2px_10px_rgba(0,0,0,0.10)] border border-[#E2E8F0]">
                  <span className="text-[12px] font-semibold text-[#1E293B]">Compare before you buy</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── Review CTA strip ─────────────────────────────────────────────── */}
        <section className="bg-white py-3 border-b border-[#E2E8F0]">
          <div className="mx-auto px-4 md:px-6 max-w-[1280px]">
            <div className="bg-[#fff5ef] rounded-[12px] flex items-center justify-between px-5 py-3 gap-4">

              {/* Left: stars visual + text */}
              <div className="flex items-center gap-4">
                <div className="relative w-[72px] h-[54px] shrink-0">
                  {/* Gift card mockup */}
                  <div className="absolute left-[8px] top-[4px] w-[46px] h-[34px] bg-[#F97316] rounded-md flex items-center justify-center shadow-md rotate-[-6deg]">
                    <span className="text-white text-xl leading-none">🎁</span>
                  </div>
                  {/* Stars around it */}
                  <Star className="absolute bottom-0 left-0 h-3.5 w-3.5 text-[#FBBF24] fill-[#FBBF24]" />
                  <Star className="absolute bottom-0 right-0 h-3.5 w-3.5 text-[#FBBF24] fill-[#FBBF24]" />
                  <Star className="absolute top-0 right-[4px] h-3 w-3 text-[#FBBF24] fill-[#FBBF24]" />
                </div>
                <div>
                  <p className="font-semibold text-[#262626] text-[15px] leading-snug">
                    Get an ₹500 instant gift card for a platform of your choice.
                  </p>
                  <p className="text-[#585858] text-[13px] mt-0.5">
                    Bought something recently? Tell us how it went and earn rewards.
                  </p>
                </div>
              </div>

              {/* Right: CTA button */}
              <Link
                href="/reviews/new"
                className="shrink-0 border-[1.4px] border-[#ffbfb8] rounded-full px-5 py-2 text-[13px] font-semibold text-[#574c4c] hover:bg-[#fff0eb] transition-colors whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
              >
                Write a review now
              </Link>
            </div>
          </div>
        </section>

        {/* ── Trending right now ────────────────────────────────────────────── */}
        <section className="bg-white pt-6 pb-8 border-b border-[#E2E8F0]">
          <div className="mx-auto px-4 md:px-6 max-w-[1280px]">
            {/* Header */}
            <h2 className="text-[20px] font-bold text-[#1E293B] mb-4">Trending right now</h2>

            {/* Filter chips row */}
            <div className="flex items-center gap-2 mb-5 overflow-x-auto pb-1 no-scrollbar">
              {FILTER_CHIPS.map((chip, i) => (
                <Link
                  key={chip.label}
                  href={chip.slug ? `/search?category=${chip.slug}` : "/search"}
                  className={`shrink-0 rounded-full border px-4 py-1.5 text-[13px] font-medium whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] ${
                    i === 0
                      ? "bg-[#F97316] border-[#F97316] text-white"
                      : "border-[#E2E8F0] bg-white text-[#64748B] hover:border-[#F97316] hover:text-[#F97316]"
                  }`}
                >
                  {chip.label}
                </Link>
              ))}
              <button className="shrink-0 ml-1 flex items-center gap-1.5 rounded-full border border-[#E2E8F0] bg-white px-4 py-1.5 text-[13px] font-medium text-[#64748B] hover:border-[#F97316] hover:text-[#F97316] transition-colors">
                <SlidersHorizontal className="h-3.5 w-3.5" />
                Filters
              </button>
            </div>

            {/* Product scroll row */}
            <div className="flex gap-3 overflow-x-auto pb-1 -mx-4 px-4 md:-mx-0 md:px-0 snap-x snap-mandatory no-scrollbar">
              {trendingProducts.map((product) => (
                <div key={product.id} className="snap-start shrink-0 w-[180px] md:w-[200px]">
                  <ProductCard product={product} />
                </div>
              ))}
            </div>

            {/* View all */}
            <div className="flex justify-center mt-5">
              <Link
                href="/search"
                className="flex items-center gap-1 text-[13px] font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors"
              >
                View all
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </section>

        {/* ── Recently Viewed (logged-in users only) ─────────────────────────── */}
        <RecentlyViewedSection />

        {/* ── Buyer's Zone / Reviewer's Zone ───────────────────────────────── */}
        <section className="bg-[#F8FAFC] py-5">
          <div className="mx-auto px-4 md:px-6 max-w-[1280px]">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

              {/* Buyer's Zone */}
              <div className="bg-[#fff0e0] rounded-2xl shadow-[0px_1px_4px_rgba(0,0,0,0.12)] overflow-hidden flex h-[206px]">
                <div className="flex-1 flex flex-col justify-between pl-[22px] pr-4 py-[18px]">
                  <div className="flex flex-col gap-2.5">
                    <span className="self-start bg-[#ffbd76] text-[#2a2a2a] text-[13px] font-semibold rounded-full px-4 py-1.5">
                      Buyer&apos;s Zone
                    </span>
                    <h3 className="text-[#333535] text-[18px] font-semibold leading-[1.3]">
                      Read honest reviews, shop smarter
                    </h3>
                    <p className="text-[#373838] text-[14px] leading-relaxed">
                      Discover unbiased opinions from real buyers before you spend your money.
                    </p>
                  </div>
                  <Link
                    href="/search"
                    className="flex items-center gap-1 text-[#cb6900] text-[14px] font-semibold hover:underline mt-2"
                  >
                    Explore reviews
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                </div>
                <div className="w-[224px] shrink-0 relative">
                  <Image
                    src="https://placehold.co/224x206/e8d5b7/7c4a00?text=Shop+Smarter"
                    alt="Buyer shopping online"
                    fill
                    className="object-cover"
                    unoptimized
                  />
                </div>
              </div>

              {/* Reviewer's Zone */}
              <div className="bg-[#ffe0dd] rounded-2xl shadow-[0px_1px_4px_rgba(0,0,0,0.12)] overflow-hidden flex h-[206px]">
                <div className="flex-1 flex flex-col justify-between pl-[22px] pr-4 py-[18px]">
                  <div className="flex flex-col gap-2.5">
                    <span className="self-start bg-[#ff9991] text-[#2a2a2a] text-[13px] font-medium rounded-full px-4 py-1.5">
                      Reviewer&apos;s Zone
                    </span>
                    <h3 className="text-[#333535] text-[18px] font-semibold leading-[1.3]">
                      Write honest reviews, help others
                    </h3>
                    <p className="text-[#373838] text-[14px] leading-relaxed">
                      Share your real experiences, earn trust, and guide smarter choices for others.
                    </p>
                  </div>
                  <Link
                    href="/reviews/new"
                    className="flex items-center gap-1 text-[#832542] text-[14px] font-semibold hover:underline mt-2"
                  >
                    Write a review
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                </div>
                <div className="w-[224px] shrink-0 relative">
                  <Image
                    src="https://placehold.co/224x206/f5b8b0/7a1a2e?text=Share+Experience"
                    alt="Reviewer sharing experience"
                    fill
                    className="object-cover"
                    unoptimized
                  />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── Blockbuster deals for you ─────────────────────────────────────── */}
        {deals.length > 0 && (
          <section className="bg-[#1E293B] py-8">
            <div className="mx-auto px-4 md:px-6 max-w-[1280px]">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-[20px] font-bold text-white">Blockbuster deals for you</h2>
                <Link
                  href="/deals"
                  className="flex items-center gap-1 text-sm font-medium text-[#4DB6AC] hover:text-teal-300 transition-colors"
                >
                  View all <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 md:gap-4">
                {deals.slice(0, 5).map((deal) => (
                  <DealCard key={deal.id} deal={deal} />
                ))}
              </div>
            </div>
          </section>
        )}

        {/* ── Rate and review your products ────────────────────────────────── */}
        {reviewProducts.length > 0 && (
          <section className="bg-white py-8 border-b border-[#E2E8F0]">
            <div className="mx-auto px-4 md:px-6 max-w-[1280px]">

              {/* User header */}
              <div className="flex items-start gap-4 mb-5">
                <div className="h-[60px] w-[60px] shrink-0 rounded-full overflow-hidden relative border-2 border-[#E2E8F0]">
                  <Image
                    src="https://placehold.co/60x60/fef3c7/92400e?text=You"
                    alt="Profile"
                    fill
                    className="object-cover"
                    unoptimized
                  />
                </div>
                <div>
                  <p className="text-[#1E293B] text-[18px] font-semibold leading-snug">
                    Rate and review your products
                  </p>
                  <p className="text-[#64748B] text-[13px] mt-1 flex flex-wrap items-center gap-1.5">
                    Get{" "}
                    <span className="inline-block bg-[#FFF7ED] border border-[#FED7AA] text-[#F97316] text-[11px] font-semibold rounded-full px-2.5 py-0.5">
                      Rewards
                    </span>{" "}
                    by{" "}
                    <span className="inline-block bg-[#FFF7ED] border border-[#FED7AA] text-[#F97316] text-[11px] font-semibold rounded-full px-2.5 py-0.5">
                      reviewing
                    </span>{" "}
                    any product below
                  </p>
                </div>
              </div>

              {/* Products to review + view all */}
              <div className="flex gap-4 overflow-x-auto pb-1 no-scrollbar">
                {reviewProducts.map((product) => {
                  const imgUrl = product.images?.[0] ?? "https://placehold.co/90x90/f8fafc/94a3b8?text=?";
                  return (
                    <div key={product.id} className="shrink-0 w-[300px] md:w-[350px]">
                      <div className="flex gap-3 rounded-xl border border-[#E2E8F0] bg-white p-3 shadow-sm hover:shadow-md transition-shadow">
                        <div className="relative h-[90px] w-[90px] shrink-0 rounded-lg overflow-hidden bg-[#F8FAFC]">
                          <Image
                            src={imgUrl}
                            alt={product.title}
                            fill
                            sizes="90px"
                            className="object-contain p-2"
                            unoptimized
                          />
                        </div>
                        <div className="flex-1 min-w-0 flex flex-col justify-between py-0.5">
                          <div>
                            <p className="text-[11px] text-[#4DB6AC] font-medium">{product.brandName}</p>
                            <p className="text-[13px] font-medium text-[#1E293B] line-clamp-2 leading-snug mt-0.5">
                              {product.title}
                            </p>
                          </div>
                          <Link
                            href={`/product/${product.slug}`}
                            className="mt-2 self-start inline-flex items-center justify-center rounded-full bg-[#F97316] px-3 py-1.5 text-[11px] font-semibold text-white hover:bg-[#EA580C] transition-colors"
                          >
                            Write a review
                          </Link>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* View all tile */}
                <div className="shrink-0 w-[80px] flex items-center justify-center">
                  <Link
                    href="/reviews/new"
                    className="flex flex-col items-center gap-1.5 text-[#F97316] hover:text-[#EA580C] transition-colors"
                  >
                    <div className="h-10 w-10 rounded-full border-2 border-[#F97316] flex items-center justify-center">
                      <ChevronRight className="h-5 w-5" />
                    </div>
                    <span className="text-[11px] font-semibold whitespace-nowrap">View All</span>
                  </Link>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ── Top Rated + Bestsellers ───────────────────────────────────────── */}
        {products.length > 0 && (
          <section className="bg-[#F8FAFC] py-8">
            <div className="mx-auto px-4 md:px-6 max-w-[1280px]">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-[20px] font-bold text-[#1E293B]">Top Rated</h2>
                    <Link href="/search?sort=rating" className="text-[13px] font-medium text-[#F97316] hover:text-[#EA580C] flex items-center gap-0.5">
                      View all <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                  <ProductRow products={topRatedProducts} />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-[20px] font-bold text-[#1E293B]">Bestsellers</h2>
                    <Link href="/search?sort=bestsellers" className="text-[13px] font-medium text-[#F97316] hover:text-[#EA580C] flex items-center gap-0.5">
                      View all <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                  <ProductRow products={bestsellers} />
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ── Trending Products (from real trending API) ────────────────── */}
        <TrendingSection
          title="Trending Products"
          endpoint="trending"
          limit={8}
          viewAllHref="/search?sort=trending"
        />

        {/* ── Price Dropping ─────────────────────────────────────────────── */}
        <TrendingSection
          title="Price Dropping"
          endpoint="price-dropping"
          limit={8}
          viewAllHref="/search?sort=price_drop"
        />

      </main>

      <Footer />
    </>
  );
}
