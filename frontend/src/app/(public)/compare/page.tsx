import type { Metadata } from "next";
import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { productsApi } from "@/lib/api/products";
import { formatPrice, formatDudScore } from "@/lib/utils/format";
import type { ProductDetail } from "@/types/product";

export const metadata: Metadata = { title: "Compare Products — Whydud" };

function ScoreDots({ filled, total = 5 }: { filled: number; total?: number }) {
  const color =
    filled >= 4
      ? "bg-green-500"
      : filled >= 3
      ? "bg-lime-400"
      : filled >= 2
      ? "bg-yellow-400"
      : "bg-orange-400";
  return (
    <div className="flex gap-1">
      {Array.from({ length: total }, (_, i) => (
        <span
          key={i}
          className={`inline-block w-3 h-3 rounded-full ${
            i < filled ? color : "bg-slate-200"
          }`}
        />
      ))}
    </div>
  );
}

function Stars({ rating }: { rating: number }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: 5 }, (_, i) => (
        <span
          key={i}
          className={`text-sm ${
            i < Math.round(rating) ? "text-yellow-400" : "text-slate-200"
          }`}
        >
          ★
        </span>
      ))}
    </div>
  );
}

/** Convert a DudScore (0-100) to a 0-5 dots scale. */
function scoreToDots(score: number | null): number {
  if (score == null) return 0;
  return Math.round((score / 100) * 5);
}

/** Determine which product index has the "best" value for a numeric spec (higher = better). */
function bestIndex(values: (string | number | boolean | null | undefined)[]): number | null {
  let best = -Infinity;
  let idx: number | null = null;
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    const n = typeof v === "number" ? v : typeof v === "string" ? parseFloat(v) : NaN;
    if (!isNaN(n) && n > best) {
      best = n;
      idx = i;
    }
  }
  return idx;
}

/** Build highlight cards from product comparison. */
function buildHighlights(products: ProductDetail[]): {
  badge: string;
  badgeColor: string;
  productTitle: string;
  description: string;
}[] {
  const highlights: {
    badge: string;
    badgeColor: string;
    productTitle: string;
    description: string;
  }[] = [];

  // Best Price
  let bestPriceIdx = -1;
  let bestPrice = Infinity;
  for (let i = 0; i < products.length; i++) {
    const p = products[i]!;
    if (p.currentBestPrice != null && p.currentBestPrice < bestPrice) {
      bestPrice = p.currentBestPrice;
      bestPriceIdx = i;
    }
  }
  const bestPriceProduct = bestPriceIdx >= 0 ? products[bestPriceIdx] : undefined;
  if (bestPriceProduct) {
    highlights.push({
      badge: "Best Price",
      badgeColor: "bg-[#F97316] text-white",
      productTitle: bestPriceProduct.title,
      description: `Lowest current price at ${formatPrice(bestPrice)} on ${bestPriceProduct.currentBestMarketplace}.`,
    });
  }

  // Best Rating
  let bestRatingIdx = -1;
  let bestRating = -1;
  for (let i = 0; i < products.length; i++) {
    const p = products[i]!;
    if (p.avgRating != null && p.avgRating > bestRating) {
      bestRating = p.avgRating;
      bestRatingIdx = i;
    }
  }
  const bestRatingProduct = bestRatingIdx >= 0 ? products[bestRatingIdx] : undefined;
  if (bestRatingProduct) {
    highlights.push({
      badge: "Highest Rated",
      badgeColor: "bg-[#F97316] text-white",
      productTitle: bestRatingProduct.title,
      description: `Top customer rating of ${bestRating.toFixed(1)} across ${bestRatingProduct.totalReviews.toLocaleString("en-IN")} reviews.`,
    });
  }

  // Best DudScore
  let bestDudIdx = -1;
  let bestDud = -1;
  for (let i = 0; i < products.length; i++) {
    const p = products[i]!;
    if (p.dudScore != null && p.dudScore > bestDud) {
      bestDud = p.dudScore;
      bestDudIdx = i;
    }
  }
  const bestDudProduct = bestDudIdx >= 0 ? products[bestDudIdx] : undefined;
  if (bestDudProduct) {
    highlights.push({
      badge: "Best DudScore",
      badgeColor: "bg-[#F97316] text-white",
      productTitle: bestDudProduct.title,
      description: `Highest trust score of ${formatDudScore(bestDud)}/100 based on review credibility and price stability.`,
    });
  }

  return highlights;
}

/** Collect all spec keys across products and group them into sections. */
function buildSpecRows(products: ProductDetail[]): {
  section: string;
  rows: { label: string; values: { text: string; detail?: string; isBest?: boolean }[] }[];
}[] {
  // Gather all unique spec keys
  const allKeys = new Set<string>();
  for (const p of products) {
    if (p.specs) {
      for (const key of Object.keys(p.specs)) {
        allKeys.add(key);
      }
    }
  }

  if (allKeys.size === 0) return [];

  const rows: { label: string; values: { text: string; detail?: string; isBest?: boolean }[] }[] = [];

  for (const key of allKeys) {
    const rawValues = products.map((p) => p.specs?.[key] ?? null);
    const bestIdx = bestIndex(rawValues);

    const values = rawValues.map((v, i) => ({
      text: v == null ? "—" : String(v),
      isBest: bestIdx === i,
    }));

    rows.push({ label: key, values });
  }

  // Return as a single "Specifications" section
  return [{ section: "Specifications", rows }];
}

/** Build detailed spec rows (all specs, flat string values). */
function buildDetailedRows(products: ProductDetail[]): {
  section: string;
  rows: { label: string; values: string[] }[];
}[] {
  const allKeys = new Set<string>();
  for (const p of products) {
    if (p.specs) {
      for (const key of Object.keys(p.specs)) {
        allKeys.add(key);
      }
    }
  }

  if (allKeys.size === 0) return [];

  const rows: { label: string; values: string[] }[] = [];
  for (const key of allKeys) {
    const values = products.map((p) => {
      const v = p.specs?.[key];
      return v == null ? "" : String(v);
    });
    rows.push({ label: key, values });
  }

  return [{ section: "All Specifications", rows }];
}

interface ComparePageProps {
  searchParams: Promise<{ slugs?: string }>;
}

export default async function ComparePage({ searchParams }: ComparePageProps) {
  const { slugs: slugsParam } = await searchParams;
  const slugs = slugsParam
    ? slugsParam.split(",").map((s) => s.trim()).filter(Boolean)
    : [];

  // No slugs provided
  if (slugs.length === 0) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-[1280px] px-4 py-20 text-center">
          <h1 className="text-xl font-bold text-slate-900 mb-2">Compare Products</h1>
          <p className="text-sm text-slate-500">
            Select products to compare. Add <code className="bg-slate-100 px-1 rounded">?slugs=slug1,slug2</code> to the URL.
          </p>
          <Link
            href="/search"
            className="inline-block mt-6 text-sm font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
          >
            Browse Products →
          </Link>
        </main>
        <Footer />
      </>
    );
  }

  // Fetch comparison data
  const response = await productsApi.compare(slugs);

  if (!response.success) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-[1280px] px-4 py-20 text-center">
          <h1 className="text-xl font-bold text-slate-900 mb-2">Compare Products</h1>
          <p className="text-sm text-slate-500">
            Could not load comparison data. Please try again or select different products.
          </p>
          <Link
            href="/search"
            className="inline-block mt-6 text-sm font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
          >
            Browse Products →
          </Link>
        </main>
        <Footer />
      </>
    );
  }

  const products = response.data;

  if (products.length === 0) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-[1280px] px-4 py-20 text-center">
          <h1 className="text-xl font-bold text-slate-900 mb-2">Compare Products</h1>
          <p className="text-sm text-slate-500">
            No matching products found for the given slugs.
          </p>
          <Link
            href="/search"
            className="inline-block mt-6 text-sm font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
          >
            Browse Products →
          </Link>
        </main>
        <Footer />
      </>
    );
  }

  const colCount = products.length;

  // Determine which product has the best price
  let bestPriceIdx = -1;
  let bestPriceVal = Infinity;
  for (let i = 0; i < products.length; i++) {
    const p = products[i]!;
    if (p.currentBestPrice != null && p.currentBestPrice < bestPriceVal) {
      bestPriceVal = p.currentBestPrice;
      bestPriceIdx = i;
    }
  }

  // Build derived data
  const highlights = buildHighlights(products);
  const keySpecs = buildSpecRows(products);
  const detailedSummary = buildDetailedRows(products);

  // Category scores from DudScore components
  // Show category scores section if any product has a DudScore
  const hasDudComponents = products.some(
    (p) => p.dudScore != null
  );

  return (
    <>
      <Header />

      {/* Sticky tab bar */}
      <div className="sticky top-16 z-20 bg-white border-b border-slate-200">
        <div className="mx-auto max-w-[1280px] px-4">
          <nav className="flex gap-6 overflow-x-auto no-scrollbar">
            {[
              { label: "Highlights", id: "highlights" },
              { label: "Comparison Summary", id: "summary" },
              { label: "Detailed Comparison", id: "detailed" },
              { label: "Total cost of ownership", id: "tco" },
            ].map((tab) => (
              <a
                key={tab.id}
                href={`#${tab.id}`}
                className="shrink-0 py-3 text-sm font-medium text-slate-500 hover:text-[#F97316] border-b-2 border-transparent hover:border-[#F97316] transition-colors"
              >
                {tab.label}
              </a>
            ))}
          </nav>
        </div>
      </div>

      <main className="mx-auto max-w-[1280px] px-4 py-6">
        {/* ── Header: Compare Models ─────────────────────────────── */}
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Compare Models</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Each product treats differently — pick what matters
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button className="text-sm text-slate-600 hover:text-[#F97316] transition-colors font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
              Save Comparison
            </button>
            <button className="text-sm text-slate-600 hover:text-[#F97316] transition-colors font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
              Share ↗
            </button>
          </div>
        </div>

        {/* ── Product header row ─────────────────────────────────── */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 mb-4">
          <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${colCount}, 1fr)` }}>
            {products.map((p, i) => (
              <div key={p.slug} className="flex flex-col items-center text-center relative">
                {/* VS marker between products */}
                {i > 0 && (
                  <span className="absolute -left-2 top-1/3 -translate-x-1/2 bg-slate-100 text-slate-500 text-xs font-bold px-2 py-1 rounded-full">
                    VS
                  </span>
                )}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={p.images?.[0] ?? `https://placehold.co/160x200/f0f0f0/1a1a1a?text=${encodeURIComponent(p.title)}`}
                  alt={p.title}
                  className="w-28 h-36 object-contain mb-3"
                />
                <Link
                  href={`/product/${p.slug}`}
                  className="text-sm font-semibold text-slate-800 hover:text-[#F97316] transition-colors"
                >
                  {p.title}
                </Link>
                <p className="text-base font-bold text-slate-900 mt-1">
                  {formatPrice(p.currentBestPrice)}
                </p>
                {i === bestPriceIdx && (
                  <span className="text-xs font-semibold text-[#F97316] mt-1">
                    ★ Best Buy
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Show only differences toggle */}
        <label className="flex items-center gap-2 text-sm text-slate-600 mb-6 cursor-pointer">
          <input
            type="checkbox"
            className="rounded border-slate-300 text-[#F97316] focus:ring-[#F97316]"
          />
          Show only differences
        </label>

        {/* ── Comparison Summary ─────────────────────────────────── */}
        <section id="summary" className="scroll-mt-28 mb-8">
          <h2 className="text-lg font-bold text-slate-900 mb-4">
            Comparison Summary
          </h2>

          {/* Highlights */}
          <div id="highlights" className="scroll-mt-28 mb-6">
            <div className="flex items-center gap-2 mb-3">
              <h3 className="text-sm font-semibold text-slate-700">
                Highlights
              </h3>
              <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">
                {highlights.length} Key differences
              </span>
            </div>
            <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${Math.min(highlights.length, colCount)}, 1fr)` }}>
              {highlights.map((h) => (
                <div
                  key={h.badge}
                  className="rounded-lg border border-slate-200 bg-white p-4"
                >
                  <span
                    className={`inline-block text-xs font-bold px-2 py-0.5 rounded-full mb-2 ${h.badgeColor}`}
                  >
                    {h.badge}
                  </span>
                  <p className="text-sm font-semibold text-slate-800">
                    {h.productTitle}
                  </p>
                  <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                    {h.description}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Category Scores — derived from DudScore components if available */}
          {hasDudComponents && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">
                Category Scores
              </h3>
              <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
                {/* Column headers */}
                <div
                  className="grid gap-4 px-4 py-3 border-b border-slate-100 bg-slate-50"
                  style={{ gridTemplateColumns: `160px repeat(${colCount}, 1fr)` }}
                >
                  <span />
                  {products.map((p) => (
                    <span
                      key={p.slug}
                      className="text-xs font-semibold text-slate-600"
                    >
                      {p.title}
                    </span>
                  ))}
                </div>

                {/* DudScore overall row */}
                <div
                  className="grid gap-4 px-4 py-3 border-b border-slate-50"
                  style={{ gridTemplateColumns: `160px repeat(${colCount}, 1fr)` }}
                >
                  <span className="text-sm text-slate-600">Overall Trust</span>
                  {products.map((p, i) => (
                    <ScoreDots key={i} filled={scoreToDots(p.dudScore)} />
                  ))}
                </div>

                {/* Review Credibility row from reviewSummary */}
                <div
                  className="grid gap-4 px-4 py-3 border-b border-slate-50"
                  style={{ gridTemplateColumns: `160px repeat(${colCount}, 1fr)` }}
                >
                  <span className="text-sm text-slate-600">Review Credibility</span>
                  {products.map((p, i) => (
                    <ScoreDots
                      key={i}
                      filled={scoreToDots(
                        p.reviewSummary.avgCredibilityScore != null
                          ? p.reviewSummary.avgCredibilityScore * 100
                          : null
                      )}
                    />
                  ))}
                </div>

                {/* Verified Purchases */}
                <div
                  className="grid gap-4 px-4 py-3 border-b border-slate-50 last:border-b-0"
                  style={{ gridTemplateColumns: `160px repeat(${colCount}, 1fr)` }}
                >
                  <span className="text-sm text-slate-600">Verified Purchases</span>
                  {products.map((p, i) => (
                    <ScoreDots
                      key={i}
                      filled={scoreToDots(
                        p.reviewSummary.verifiedPurchasePct != null
                          ? p.reviewSummary.verifiedPurchasePct
                          : null
                      )}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Ratings */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">
              Ratings
            </h3>
            <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
              {/* Customer Ratings */}
              <div
                className="grid gap-4 px-4 py-3 border-b border-slate-50"
                style={{ gridTemplateColumns: `160px repeat(${colCount}, 1fr)` }}
              >
                <span className="text-sm text-slate-600">Customer Ratings</span>
                {products.map((p, i) => (
                  <div key={i} className="flex flex-col gap-1">
                    <Stars rating={p.avgRating ?? 0} />
                    <span className="text-xs text-slate-500">
                      {p.avgRating?.toFixed(1) ?? "—"} out of{" "}
                      {p.totalReviews >= 1000
                        ? `${(p.totalReviews / 1000).toFixed(1)}K`
                        : p.totalReviews}{" "}
                      Reviews
                    </span>
                  </div>
                ))}
              </div>
              {/* DudScore */}
              <div
                className="grid gap-4 px-4 py-3"
                style={{ gridTemplateColumns: `160px repeat(${colCount}, 1fr)` }}
              >
                <span className="text-sm text-slate-600">DudScore</span>
                {products.map((p, i) => (
                  <span key={i} className="text-sm font-semibold text-slate-800">
                    {formatDudScore(p.dudScore)} out of 100
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Key Specs */}
          {keySpecs.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">
                Key Specs
              </h3>
              {keySpecs.map((section) => (
                <div key={section.section} className="mb-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                    {section.section}
                  </p>
                  <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
                    {section.rows.map((row) => (
                      <div
                        key={row.label}
                        className="grid gap-4 px-4 py-3 border-b border-slate-50 last:border-b-0"
                        style={{ gridTemplateColumns: `160px repeat(${colCount}, 1fr)` }}
                      >
                        <span className="text-sm text-slate-600">
                          {row.label}
                        </span>
                        {row.values.map((v, i) => (
                          <div key={i}>
                            <p className="text-sm font-medium text-slate-800">
                              {v.text}
                            </p>
                            {v.detail && (
                              <p className="text-xs text-slate-400">{v.detail}</p>
                            )}
                            {v.isBest && (
                              <span className="inline-block mt-1 text-[10px] font-bold text-[#F97316] bg-orange-50 px-1.5 py-0.5 rounded">
                                Best
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ── Detailed Summary ───────────────────────────────────── */}
        {detailedSummary.length > 0 && (
          <section id="detailed" className="scroll-mt-28 mb-8">
            <h2 className="text-lg font-bold text-slate-900 mb-4">
              Detailed Summary
            </h2>
            {detailedSummary.map((section) => (
              <div key={section.section} className="mb-6">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  {section.section}
                </p>
                <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
                  {section.rows.map((row) => (
                    <div
                      key={row.label}
                      className="grid gap-4 px-4 py-3 border-b border-slate-50 last:border-b-0"
                      style={{ gridTemplateColumns: `160px repeat(${colCount}, 1fr)` }}
                    >
                      <span className="text-sm text-slate-600">{row.label}</span>
                      {row.values.map((v, i) => (
                        <span
                          key={i}
                          className={`text-sm ${
                            v === "" ? "text-slate-300" : "text-slate-800"
                          }`}
                        >
                          {v || "—"}
                        </span>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </section>
        )}

        {/* ── Quick TCO — Coming Soon ─────────────────────────────── */}
        <section id="tco" className="scroll-mt-28 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-slate-900">Quick TCO</h2>
            <span className="text-xs text-slate-400">⊙ 3 years</span>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
            <div className="px-4 py-8 text-center">
              <p className="text-sm font-medium text-slate-500">
                Total Cost of Ownership comparison coming soon
              </p>
              <p className="text-xs text-slate-400 mt-1">
                We are building detailed TCO models for this category
              </p>
            </div>
          </div>

          {/* Legend + CTA */}
          <div className="flex items-center justify-between mt-4">
            <div className="flex items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-[#F97316]" /> Purchase
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500" /> Ongoing
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500" /> Resale
              </span>
            </div>
            <button className="text-sm font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
              View Breakdown
            </button>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
