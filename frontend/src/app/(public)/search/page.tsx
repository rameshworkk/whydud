import type { Metadata } from "next";
import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { ProductCard } from "@/components/product/product-card";
import { MOCK_PRODUCTS } from "@/lib/mock-data";
import { MOCK_SELLER_SIDEBAR } from "@/lib/mock-pages-data";
import { formatPrice } from "@/lib/utils/format";

interface SearchPageProps {
  searchParams: Promise<{ q?: string; cursor?: string; sortBy?: string }>;
}

export function generateMetadata(): Metadata {
  return { title: "Search Results — Whydud" };
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;
  const query = params.q ?? "Uppercase bags";
  const seller = MOCK_SELLER_SIDEBAR;

  return (
    <>
      <Header />
      <main className="mx-auto max-w-[1280px] px-4 py-6">
        {/* Results header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-lg font-bold text-slate-900">
              Results for <span className="text-slate-700">{query}</span>
            </h1>
          </div>
          <div className="flex items-center gap-4">
            {/* Sort dropdown */}
            <div className="flex items-center gap-2 text-sm">
              <span className="text-slate-500">Sort by:</span>
              <select className="border border-slate-200 rounded-md px-2 py-1 text-sm text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-[#F97316]">
                <option>Relevance</option>
                <option>Price: Low to High</option>
                <option>Price: High to Low</option>
                <option>Rating</option>
                <option>DudScore</option>
              </select>
            </div>
            {/* Results only toggle */}
            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                className="rounded border-slate-300 text-[#F97316] focus:ring-[#F97316]"
              />
              Results only
            </label>
          </div>
        </div>

        <div className="flex gap-6">
          {/* ── Product grid (4 cols) ──────────────────────────────── */}
          <div className="flex-1 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {MOCK_PRODUCTS.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>

          {/* ── Right sidebar: Seller Details ──────────────────────── */}
          <aside className="w-[280px] shrink-0 hidden lg:flex flex-col gap-4">
            {/* Seller card */}
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-bold text-slate-800 mb-3">
                Seller Details
              </h2>
              <div className="flex items-start gap-3 mb-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={seller.avatar}
                  alt={seller.name}
                  className="w-10 h-10 rounded-lg shrink-0"
                />
                <div className="min-w-0">
                  <Link
                    href={`/seller/${seller.slug}`}
                    className="text-sm font-semibold text-slate-800 hover:text-[#F97316] transition-colors leading-snug block"
                  >
                    {seller.name}
                  </Link>
                  {seller.verified && (
                    <span className="text-xs text-green-600 font-medium">
                      ✓ Verified seller
                    </span>
                  )}
                </div>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed mb-3">
                {seller.description}
              </p>
              {/* Stars */}
              <div className="flex items-center gap-1.5">
                <div className="flex gap-0.5">
                  {Array.from({ length: 5 }, (_, i) => (
                    <span
                      key={i}
                      className={`text-sm ${
                        i < Math.round(seller.rating)
                          ? "text-yellow-400"
                          : "text-slate-200"
                      }`}
                    >
                      ★
                    </span>
                  ))}
                </div>
                <span className="text-xs text-slate-500">
                  {seller.rating} ({seller.reviewCount.toLocaleString("en-IN")})
                </span>
              </div>
            </div>

            {/* Top reviews */}
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h3 className="text-sm font-bold text-slate-800 mb-3">
                Top reviews from{" "}
                <span className="lowercase">{query.split(" ")[0]}</span>
              </h3>
              <div className="flex flex-col gap-3">
                {seller.reviews.map((r) => (
                  <div key={r.reviewer} className="flex items-start gap-2.5">
                    <span
                      className="inline-flex items-center justify-center w-7 h-7 rounded-full text-white text-xs font-bold shrink-0"
                      style={{ backgroundColor: r.avatarColor }}
                    >
                      {r.reviewer.charAt(0)}
                    </span>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-slate-700">
                        {r.reviewer}
                      </p>
                      <div className="flex gap-0.5 my-0.5">
                        {Array.from({ length: 5 }, (_, i) => (
                          <span
                            key={i}
                            className={`text-[10px] ${
                              i < r.rating
                                ? "text-yellow-400"
                                : "text-slate-200"
                            }`}
                          >
                            ★
                          </span>
                        ))}
                      </div>
                      <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">
                        {r.text}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Related products */}
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h3 className="text-sm font-bold text-slate-800 mb-3">
                Related products
              </h3>
              <div className="flex flex-col gap-3">
                {seller.relatedProducts.map((rp) => (
                  <Link
                    key={rp.slug}
                    href={`/product/${rp.slug}`}
                    className="flex items-center gap-3 group"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={rp.image}
                      alt={rp.title}
                      className="w-14 h-14 rounded-md border border-slate-100 object-contain shrink-0"
                    />
                    <div className="min-w-0">
                      <p className="text-xs text-slate-700 group-hover:text-[#F97316] transition-colors line-clamp-2 leading-snug">
                        {rp.title}
                      </p>
                      <p className="text-sm font-bold text-slate-900 mt-0.5">
                        {formatPrice(rp.price)}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </main>
      <Footer />
    </>
  );
}
