import type { Metadata } from "next";
import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { MOCK_COMPARE } from "@/lib/mock-pages-data";
import { formatPrice } from "@/lib/utils/format";

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

interface ComparePageProps {
  searchParams: Promise<{ slugs?: string }>;
}

export default async function ComparePage({ searchParams }: ComparePageProps) {
  const { slugs } = await searchParams;
  void slugs;
  const data = MOCK_COMPARE;
  const colCount = data.products.length;

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
            {data.products.map((p, i) => (
              <div key={p.slug} className="flex flex-col items-center text-center relative">
                {/* VS marker between products */}
                {i > 0 && (
                  <span className="absolute -left-2 top-1/3 -translate-x-1/2 bg-slate-100 text-slate-500 text-xs font-bold px-2 py-1 rounded-full">
                    VS
                  </span>
                )}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={p.image}
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
                  {formatPrice(p.price)}
                </p>
                {p.bestBuy && (
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
                0 Key differences
              </span>
            </div>
            <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${colCount}, 1fr)` }}>
              {data.highlights.map((h) => (
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

          {/* Category Scores */}
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
                {data.products.map((p) => (
                  <span
                    key={p.slug}
                    className="text-xs font-semibold text-slate-600"
                  >
                    {p.title}
                  </span>
                ))}
              </div>
              {data.categoryScores.map((row) => (
                <div
                  key={row.label}
                  className="grid gap-4 px-4 py-3 border-b border-slate-50 last:border-b-0"
                  style={{ gridTemplateColumns: `160px repeat(${colCount}, 1fr)` }}
                >
                  <span className="text-sm text-slate-600">{row.label}</span>
                  {row.scores.map((s, i) => (
                    <ScoreDots key={i} filled={s} />
                  ))}
                </div>
              ))}
            </div>
          </div>

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
                {data.ratings.customerRatings.map((r, i) => (
                  <div key={i} className="flex flex-col gap-1">
                    <Stars rating={r.stars} />
                    <span className="text-xs text-slate-500">
                      {r.stars} out of {(r.count / 1000).toFixed(1)}K Reviews
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
                {data.ratings.dudScores.map((d, i) => (
                  <span key={i} className="text-sm font-semibold text-slate-800">
                    {d.score} out of {d.outOf}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Key Specs */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">
              Key Specs
            </h3>
            {data.keySpecs.map((section) => (
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
        </section>

        {/* ── Detailed Summary ───────────────────────────────────── */}
        <section id="detailed" className="scroll-mt-28 mb-8">
          <h2 className="text-lg font-bold text-slate-900 mb-4">
            Detailed Summary
          </h2>
          {data.detailedSummary.map((section) => (
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

        {/* ── Quick TCO ─────────────────────────────────────────── */}
        <section id="tco" className="scroll-mt-28 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-slate-900">Quick TCO</h2>
            <span className="text-xs text-slate-400">⊙ 3 years</span>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
            <div
              className="grid gap-4 px-4 py-4"
              style={{ gridTemplateColumns: `160px repeat(${colCount}, 1fr)` }}
            >
              <div>
                <p className="text-sm text-slate-600">Estimated</p>
                <p className="text-xs text-slate-400">long-run cost</p>
                <p className="text-xs text-slate-400">(3 years)</p>
              </div>
              {data.tco.map((t, i) => (
                <div key={i}>
                  <p className="text-base font-bold text-slate-900">
                    {formatPrice(t.estimated3yr)}
                  </p>
                  <p className="text-xs text-slate-500">
                    +{formatPrice(t.monthlyCost)} / month
                  </p>
                </div>
              ))}
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
