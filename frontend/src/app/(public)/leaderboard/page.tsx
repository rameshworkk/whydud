"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import {
  Trophy,
  ThumbsUp,
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  Star,
} from "lucide-react";
import { reviewsApi } from "@/lib/api/reviews";
import { cn } from "@/lib/utils/index";
import type { ReviewerProfile } from "@/lib/api/types";
import type { PaginatedApiResponse } from "@/types/api";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CATEGORIES = [
  { slug: "", label: "All Categories" },
  { slug: "smartphones", label: "Smartphones" },
  { slug: "laptops", label: "Laptops" },
  { slug: "headphones", label: "Headphones" },
  { slug: "televisions", label: "Televisions" },
  { slug: "cameras", label: "Cameras" },
  { slug: "tablets", label: "Tablets" },
  { slug: "smartwatches", label: "Smartwatches" },
  { slug: "washing-machines", label: "Washing Machines" },
  { slug: "refrigerators", label: "Refrigerators" },
  { slug: "air-conditioners", label: "Air Conditioners" },
] as const;

const LEVEL_CONFIG: Record<
  string,
  { bg: string; text: string; border: string; label: string }
> = {
  bronze: {
    bg: "bg-amber-800/10",
    text: "text-amber-800",
    border: "border-amber-300",
    label: "Bronze",
  },
  silver: {
    bg: "bg-slate-400/10",
    text: "text-slate-600",
    border: "border-slate-300",
    label: "Silver",
  },
  gold: {
    bg: "bg-yellow-500/10",
    text: "text-yellow-700",
    border: "border-yellow-400",
    label: "Gold",
  },
  platinum: {
    bg: "bg-violet-500/10",
    text: "text-violet-700",
    border: "border-violet-300",
    label: "Platinum",
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getLevelConfig(level: string) {
  const key = level.toLowerCase();
  return (
    LEVEL_CONFIG[key] ?? {
      bg: "bg-slate-100",
      text: "text-[#64748B]",
      border: "border-[#E2E8F0]",
      label: level || "Newcomer",
    }
  );
}

function extractCursor(url: string | null): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    return u.searchParams.get("cursor");
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function RankMedal({ rank }: { rank: number }) {
  if (rank === 1) {
    return (
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-yellow-300 to-yellow-500 text-sm font-bold text-yellow-900 shadow-sm">
        1
      </div>
    );
  }
  if (rank === 2) {
    return (
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-slate-200 to-slate-400 text-sm font-bold text-slate-700 shadow-sm">
        2
      </div>
    );
  }
  if (rank === 3) {
    return (
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-amber-600 text-sm font-bold text-amber-900 shadow-sm">
        3
      </div>
    );
  }
  return null;
}

function LevelBadge({ level }: { level: string }) {
  const config = getLevelConfig(level);
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold",
        config.bg,
        config.text,
        config.border
      )}
    >
      {config.label}
    </span>
  );
}

function AvatarCircle({
  name,
  size = "md",
}: {
  name: string;
  size?: "sm" | "md" | "lg";
}) {
  const sizeClass =
    size === "lg"
      ? "h-16 w-16 text-xl"
      : size === "md"
        ? "h-12 w-12 text-base"
        : "h-8 w-8 text-xs";
  return (
    <div
      className={cn(
        "shrink-0 rounded-full bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center",
        sizeClass
      )}
    >
      <span className="font-bold text-[#64748B]">
        {name?.charAt(0)?.toUpperCase() ?? "?"}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeletons
// ---------------------------------------------------------------------------

function PodiumSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "rounded-xl border border-[#E2E8F0] bg-white animate-pulse",
            i === 0 ? "p-8" : "p-6"
          )}
        >
          <div className="flex flex-col items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-slate-200" />
            <div className="h-12 w-12 rounded-full bg-slate-200" />
            <div className="h-4 w-28 rounded bg-slate-200" />
            <div className="h-4 w-16 rounded-full bg-slate-200" />
            <div className="flex gap-6 mt-1">
              <div className="h-3 w-16 rounded bg-slate-200" />
              <div className="h-3 w-16 rounded bg-slate-200" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function RowSkeleton() {
  return (
    <div className="flex items-center gap-4 rounded-lg border border-[#E2E8F0] bg-white px-4 py-3.5 animate-pulse">
      <div className="h-8 w-8 rounded-full bg-slate-200 shrink-0" />
      <div className="h-8 w-8 rounded-full bg-slate-200 shrink-0" />
      <div className="flex-1">
        <div className="h-3.5 w-32 rounded bg-slate-200" />
      </div>
      <div className="h-4 w-14 rounded-full bg-slate-200" />
      <div className="h-3 w-12 rounded bg-slate-200" />
      <div className="h-3 w-12 rounded bg-slate-200" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Top-3 Podium Card
// ---------------------------------------------------------------------------

function PodiumCard({
  reviewer,
  rank,
}: {
  reviewer: ReviewerProfile;
  rank: number;
}) {
  const isFirst = rank === 1;

  return (
    <div
      className={cn(
        "rounded-xl border bg-white text-center transition-shadow",
        isFirst
          ? "border-[#F97316]/30 shadow-md sm:scale-105 sm:-translate-y-2"
          : "border-[#E2E8F0] shadow-sm hover:shadow-md",
        isFirst ? "p-8" : "p-6",
        // Desktop podium order: 2nd | 1st | 3rd
        rank === 1 && "order-first sm:order-2",
        rank === 2 && "order-2 sm:order-1",
        rank === 3 && "order-3 sm:order-3"
      )}
    >
      {/* Medal */}
      <div className="flex justify-center mb-3">
        <RankMedal rank={rank} />
      </div>

      {/* Avatar */}
      <div className="flex justify-center mb-3">
        <AvatarCircle name={reviewer.userName} size={isFirst ? "lg" : "md"} />
      </div>

      {/* Name */}
      <h3
        className={cn(
          "font-semibold text-[#1E293B] mb-2",
          isFirst ? "text-lg" : "text-sm"
        )}
      >
        {reviewer.userName}
      </h3>

      {/* Level badge */}
      <div className="mb-3">
        <LevelBadge level={reviewer.reviewerLevel} />
      </div>

      {/* Stats */}
      <div className="flex items-center justify-center gap-5 text-xs text-[#64748B]">
        <span className="flex items-center gap-1">
          <MessageSquare className="h-3.5 w-3.5" />
          {reviewer.totalReviews} reviews
        </span>
        <span className="flex items-center gap-1">
          <ThumbsUp className="h-3.5 w-3.5" />
          {reviewer.totalUpvotesReceived} upvotes
        </span>
      </div>

      {/* Quality score for rank 1 */}
      {isFirst && reviewer.reviewQualityAvg != null && (
        <div className="mt-3 flex items-center justify-center gap-1 text-xs">
          <Star className="h-3.5 w-3.5 text-[#FBBF24]" />
          <span className="font-medium text-[#1E293B]">
            {reviewer.reviewQualityAvg.toFixed(1)} avg quality
          </span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Reviewer Row (rank 4+)
// ---------------------------------------------------------------------------

function ReviewerRow({
  reviewer,
  rank,
}: {
  reviewer: ReviewerProfile;
  rank: number;
}) {
  return (
    <div className="rounded-lg border border-[#E2E8F0] bg-white px-4 py-3.5 grid grid-cols-[2.5rem_2rem_1fr_auto] sm:grid-cols-[2.5rem_2rem_1fr_7rem_6rem_6rem] items-center gap-3">
      {/* Rank */}
      <span className="text-sm font-semibold text-[#64748B]">#{rank}</span>

      {/* Avatar */}
      <AvatarCircle name={reviewer.userName} size="sm" />

      {/* Name */}
      <span className="text-sm font-medium text-[#1E293B] truncate">
        {reviewer.userName}
      </span>

      {/* Level badge — hidden on mobile, shown on desktop */}
      <div className="hidden sm:block">
        <LevelBadge level={reviewer.reviewerLevel} />
      </div>

      {/* Reviews */}
      <div className="hidden sm:flex items-center justify-end gap-1">
        <span className="text-sm font-medium text-[#1E293B]">
          {reviewer.totalReviews}
        </span>
        <MessageSquare className="h-3.5 w-3.5 text-[#64748B]" />
      </div>

      {/* Upvotes */}
      <div className="flex items-center justify-end gap-1">
        <span className="text-sm font-medium text-[#1E293B]">
          {reviewer.totalUpvotesReceived}
        </span>
        <ThumbsUp className="h-3.5 w-3.5 text-[#64748B]" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function LeaderboardPage() {
  const [reviewers, setReviewers] = useState<ReviewerProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [prevCursor, setPrevCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchLeaderboard = useCallback(
    async (cursor?: string) => {
      setLoading(true);
      setError(null);
      try {
        const res = category
          ? await reviewsApi.getCategoryLeaderboard(category, cursor)
          : await reviewsApi.getLeaderboard(cursor);

        // Response may be PaginatedApiResponse (with pagination) or plain ApiResponse
        const raw = res as unknown as PaginatedApiResponse<ReviewerProfile>;

        if (raw.success && Array.isArray(raw.data)) {
          setReviewers(raw.data);
          const pagination = (
            raw as unknown as Record<string, unknown>
          ).pagination as
            | { next: string | null; previous: string | null }
            | undefined;
          setNextCursor(extractCursor(pagination?.next ?? null));
          setPrevCursor(extractCursor(pagination?.previous ?? null));
        } else if (!res.success && "error" in res) {
          setError(res.error.message);
        }
      } catch {
        setError("Failed to load leaderboard.");
      } finally {
        setLoading(false);
      }
    },
    [category]
  );

  // Re-fetch when category changes
  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard]);

  const top3 = reviewers.slice(0, 3);
  const rest = reviewers.slice(3);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-[1280px] px-4 py-8">
        {/* ── Header ── */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Trophy className="h-6 w-6 text-[#F97316]" />
              <h1 className="text-2xl font-bold text-[#1E293B]">
                Top Reviewers This Week
              </h1>
            </div>
            <p className="text-sm text-[#64748B]">
              Recognizing our most helpful and trusted community reviewers
            </p>
          </div>

          {/* Category filter */}
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className={cn(
              "h-10 rounded-lg border border-[#E2E8F0] bg-white px-3 pr-8 text-sm text-[#1E293B]",
              "focus:outline-none focus:ring-2 focus:ring-[#F97316] focus:border-transparent",
              "hover:border-slate-300 transition-colors cursor-pointer"
            )}
          >
            {CATEGORIES.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        {/* ── Error ── */}
        {error && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center mb-8">
            <p className="text-sm text-slate-700">{error}</p>
          </div>
        )}

        {/* ── Top 3 Podium ── */}
        {loading ? (
          <PodiumSkeleton />
        ) : top3.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8 sm:items-end">
            {top3.map((reviewer, i) => {
              const rank = reviewer.leaderboardRank ?? i + 1;
              return (
                <PodiumCard
                  key={`${reviewer.userName}-${rank}`}
                  reviewer={reviewer}
                  rank={rank}
                />
              );
            })}
          </div>
        ) : !error ? (
          <div className="rounded-xl border border-dashed border-[#E2E8F0] bg-white p-16 text-center mb-8">
            <Trophy className="h-10 w-10 text-[#E2E8F0] mx-auto mb-3" />
            <p className="text-sm font-semibold text-[#1E293B]">
              No reviewers yet
            </p>
            <p className="text-xs text-[#64748B] mt-1">
              Be the first to review products and climb the leaderboard!
            </p>
          </div>
        ) : null}

        {/* ── Remaining Reviewers ── */}
        {loading ? (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <RowSkeleton key={i} />
            ))}
          </div>
        ) : rest.length > 0 ? (
          <>
            {/* Column header — desktop only */}
            <div className="hidden sm:grid sm:grid-cols-[2.5rem_2rem_1fr_7rem_6rem_6rem] gap-3 px-4 pb-2 text-[10px] font-semibold text-[#64748B] uppercase tracking-wider">
              <span>Rank</span>
              <span />
              <span>Reviewer</span>
              <span>Level</span>
              <span className="text-right">Reviews</span>
              <span className="text-right">Upvotes</span>
            </div>

            <div className="flex flex-col gap-2">
              {rest.map((reviewer, i) => {
                const rank = reviewer.leaderboardRank ?? i + 4;
                return (
                  <ReviewerRow
                    key={`${reviewer.userName}-${rank}`}
                    reviewer={reviewer}
                    rank={rank}
                  />
                );
              })}
            </div>
          </>
        ) : null}

        {/* ── Pagination ── */}
        {!loading && (prevCursor || nextCursor) && (
          <div className="flex items-center justify-center gap-3 mt-8">
            <button
              type="button"
              disabled={!prevCursor}
              onClick={() => prevCursor && fetchLeaderboard(prevCursor)}
              className={cn(
                "flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm font-medium transition-colors",
                prevCursor
                  ? "border-[#E2E8F0] text-[#1E293B] hover:border-[#F97316] hover:text-[#F97316] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
                  : "border-slate-100 text-slate-300 cursor-not-allowed"
              )}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>
            <button
              type="button"
              disabled={!nextCursor}
              onClick={() => nextCursor && fetchLeaderboard(nextCursor)}
              className={cn(
                "flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm font-medium transition-colors",
                nextCursor
                  ? "border-[#E2E8F0] text-[#1E293B] hover:border-[#F97316] hover:text-[#F97316] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
                  : "border-slate-100 text-slate-300 cursor-not-allowed"
              )}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </main>
      <Footer />
    </>
  );
}
