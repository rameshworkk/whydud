import type { DudScoreConfidence } from "@/types";
import { dudScoreColour, formatDudScore } from "@/lib/utils";
import { config } from "@/config";

interface DudScoreDisplayProps {
  score: number | null;
  confidence: DudScoreConfidence | null;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

/** DudScore badge — large version for product hero. */
export function DudScoreDisplay({
  score,
  confidence,
  size = "md",
  showLabel = true,
}: DudScoreDisplayProps) {
  const scoreClass = dudScoreColour(score);

  const label =
    score == null
      ? "Not Rated"
      : score >= 90
      ? "Excellent"
      : score >= 70
      ? "Good"
      : score >= 50
      ? "Average"
      : score >= 30
      ? "Below Average"
      : "Dud";

  const sizeClasses = {
    sm: "text-2xl",
    md: "text-4xl",
    lg: "text-6xl",
  };

  return (
    <div className="flex flex-col items-center gap-1">
      <span className={`font-black leading-none ${sizeClasses[size]} ${scoreClass}`}>
        {score != null ? formatDudScore(score) : "—"}
      </span>
      {showLabel && (
        <span className={`text-xs font-semibold uppercase tracking-widest ${scoreClass}`}>
          {label}
        </span>
      )}
      {confidence === "preliminary" && (
        <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
          Preliminary
        </span>
      )}
    </div>
  );
}
