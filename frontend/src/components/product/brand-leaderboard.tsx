"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Package,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { brandsApi } from "@/lib/api/brands";
import type { BrandTrustScore, BrandTrustTier } from "@/types";

// ---------------------------------------------------------------------------
// Tier config
// ---------------------------------------------------------------------------

const TIER_CONFIG: Record<
  BrandTrustTier,
  { bg: string; text: string; border: string; label: string; Icon: typeof Shield }
> = {
  excellent: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200", label: "Excellent", Icon: ShieldCheck },
  good: { bg: "bg-lime-50", text: "text-lime-700", border: "border-lime-200", label: "Good", Icon: ShieldCheck },
  average: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200", label: "Average", Icon: Shield },
  poor: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200", label: "Poor", Icon: ShieldAlert },
  avoid: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200", label: "Avoid", Icon: ShieldX },
};

const SCORE_COLORS: Record<string, string> = {
  excellent: "#16A34A",
  good: "#65A30D",
  average: "#CA8A04",
  poor: "#EA580C",
  avoid: "#DC2626",
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function BrandRow({ brand, rank }: { brand: BrandTrustScore; rank: number }) {
  const tier = TIER_CONFIG[brand.trustTier];
  const TierIcon = tier.Icon;
  const color = SCORE_COLORS[brand.trustTier] ?? "#6B7280";

  return (
    <Link
      href={`/brand/${brand.brandSlug}`}
      className="rounded-lg border border-[#E2E8F0] bg-white px-4 py-3.5 grid grid-cols-[2rem_2.5rem_1fr_5rem_4rem] sm:grid-cols-[2rem_2.5rem_1fr_6rem_5rem_5rem] items-center gap-3 hover:shadow-md transition-shadow"
    >
      {/* Rank */}
      <span className="text-sm font-semibold text-[#64748B]">#{rank}</span>

      {/* Logo/icon */}
      {brand.brandLogoUrl ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={brand.brandLogoUrl}
          alt={brand.brandName}
          className="w-8 h-8 rounded-lg object-contain bg-white border border-slate-100 p-0.5"
        />
      ) : (
        <div className="w-8 h-8 rounded-lg bg-[#4DB6AC]/10 flex items-center justify-center">
          <Package className="w-4 h-4 text-[#4DB6AC]" />
        </div>
      )}

      {/* Name + products */}
      <div className="min-w-0">
        <span className="text-sm font-medium text-[#1E293B] truncate block">
          {brand.brandName}
          {brand.brandVerified && (
            <ShieldCheck className="w-3.5 h-3.5 text-[#4DB6AC] inline ml-1" />
          )}
        </span>
        <span className="text-xs text-[#64748B]">{brand.productCount} products</span>
      </div>

      {/* Tier badge */}
      <span
        className={`hidden sm:inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${tier.bg} ${tier.text} ${tier.border}`}
      >
        <TierIcon className="w-3 h-3" />
        {tier.label}
      </span>

      {/* Score */}
      <span
        className="text-sm font-bold text-right"
        style={{ color }}
      >
        {Math.round(brand.avgDudScore)}
      </span>

      {/* Consistency */}
      <span className="hidden sm:block text-xs text-[#64748B] text-right">
        {brand.qualityConsistency != null ? `σ ${brand.qualityConsistency.toFixed(1)}` : "—"}
      </span>
    </Link>
  );
}

function RowSkeleton() {
  return (
    <div className="flex items-center gap-4 rounded-lg border border-[#E2E8F0] bg-white px-4 py-3.5 animate-pulse">
      <div className="h-5 w-5 rounded bg-slate-200" />
      <div className="h-8 w-8 rounded-lg bg-slate-200" />
      <div className="flex-1">
        <div className="h-3.5 w-32 rounded bg-slate-200" />
      </div>
      <div className="h-4 w-14 rounded-full bg-slate-200" />
      <div className="h-4 w-10 rounded bg-slate-200" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function BrandLeaderboard() {
  const [top, setTop] = useState<BrandTrustScore[]>([]);
  const [bottom, setBottom] = useState<BrandTrustScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"top" | "bottom">("top");

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await brandsApi.getLeaderboard();
        if (res.success) {
          setTop(res.data.top);
          setBottom(res.data.bottom);
        } else {
          setError(res.error.message);
        }
      } catch {
        setError("Failed to load brand leaderboard.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const brands = view === "top" ? top : bottom;

  return (
    <div>
      {/* Section header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            {view === "top" ? (
              <TrendingUp className="h-5 w-5 text-[#16A34A]" />
            ) : (
              <TrendingDown className="h-5 w-5 text-[#DC2626]" />
            )}
            <h2 className="text-xl font-bold text-[#1E293B]">
              {view === "top" ? "Most Trusted Brands" : "Least Trusted Brands"}
            </h2>
          </div>
          <p className="text-sm text-[#64748B]">
            Based on average DudScore across all scored products
          </p>
        </div>

        {/* Toggle */}
        <div className="flex rounded-lg border border-[#E2E8F0] bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setView("top")}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              view === "top"
                ? "bg-[#16A34A] text-white"
                : "text-[#64748B] hover:text-[#1E293B]"
            }`}
          >
            Top Brands
          </button>
          <button
            type="button"
            onClick={() => setView("bottom")}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              view === "bottom"
                ? "bg-[#DC2626] text-white"
                : "text-[#64748B] hover:text-[#1E293B]"
            }`}
          >
            Bottom Brands
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center mb-4">
          <p className="text-sm text-slate-700">{error}</p>
        </div>
      )}

      {/* Column headers — desktop */}
      {!loading && brands.length > 0 && (
        <div className="hidden sm:grid sm:grid-cols-[2rem_2.5rem_1fr_6rem_5rem_5rem] gap-3 px-4 pb-2 text-[10px] font-semibold text-[#64748B] uppercase tracking-wider">
          <span>Rank</span>
          <span />
          <span>Brand</span>
          <span>Tier</span>
          <span className="text-right">Score</span>
          <span className="text-right">Consistency</span>
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <RowSkeleton key={i} />
          ))}
        </div>
      ) : brands.length > 0 ? (
        <div className="flex flex-col gap-2">
          {brands.map((brand, i) => (
            <BrandRow key={brand.brandSlug} brand={brand} rank={i + 1} />
          ))}
        </div>
      ) : !error ? (
        <div className="rounded-xl border border-dashed border-[#E2E8F0] bg-white p-16 text-center">
          <Shield className="h-10 w-10 text-[#E2E8F0] mx-auto mb-3" />
          <p className="text-sm font-semibold text-[#1E293B]">No brand scores yet</p>
          <p className="text-xs text-[#64748B] mt-1">
            Brand trust scores are computed weekly once enough products have DudScores.
          </p>
        </div>
      ) : null}
    </div>
  );
}
