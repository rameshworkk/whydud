"use client";

import { useState, useCallback } from "react";
import { cn } from "@/lib/utils";

interface VoteButtonsProps {
  upvotes: number;
  downvotes: number;
  userVote: 1 | -1 | null;
  onVote: (vote: 1 | -1) => Promise<{ action: string; vote: 1 | -1 | null }>;
}

/** Reddit-style up/down vote buttons with toggle state. */
export function VoteButtons({ upvotes, downvotes, userVote, onVote }: VoteButtonsProps) {
  const [currentVote, setCurrentVote] = useState<1 | -1 | null>(userVote);
  const [score, setScore] = useState(upvotes - downvotes);
  const [loading, setLoading] = useState(false);

  const handleVote = useCallback(
    async (vote: 1 | -1) => {
      if (loading) return;
      setLoading(true);
      try {
        const res = await onVote(vote);
        if (res.action === "removed") {
          // Vote was toggled off
          setScore((prev) => prev - vote);
          setCurrentVote(null);
        } else if (res.action === "changed") {
          // Vote was flipped (e.g. -1 → 1 = delta of 2)
          setScore((prev) => prev + vote * 2);
          setCurrentVote(vote);
        } else {
          // New vote cast
          setScore((prev) => prev + vote);
          setCurrentVote(vote);
        }
      } catch {
        // Silently fail — user may not be authenticated
      } finally {
        setLoading(false);
      }
    },
    [loading, onVote],
  );

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => handleVote(1)}
        disabled={loading}
        aria-label="Upvote"
        className={cn(
          "w-7 h-7 flex items-center justify-center rounded transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
          currentVote === 1
            ? "text-[#F97316] bg-[#FFF7ED]"
            : "text-slate-400 hover:text-[#F97316] hover:bg-slate-50",
          loading && "opacity-50 cursor-not-allowed",
        )}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 19V5M5 12l7-7 7 7" />
        </svg>
      </button>

      <span className={cn(
        "text-xs font-semibold min-w-[20px] text-center tabular-nums",
        currentVote === 1 && "text-[#F97316]",
        currentVote === -1 && "text-[#DC2626]",
        currentVote === null && "text-slate-600",
      )}>
        {score}
      </span>

      <button
        onClick={() => handleVote(-1)}
        disabled={loading}
        aria-label="Downvote"
        className={cn(
          "w-7 h-7 flex items-center justify-center rounded transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
          currentVote === -1
            ? "text-[#DC2626] bg-red-50"
            : "text-slate-400 hover:text-[#DC2626] hover:bg-slate-50",
          loading && "opacity-50 cursor-not-allowed",
        )}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 5v14M19 12l-7 7-7-7" />
        </svg>
      </button>
    </div>
  );
}
