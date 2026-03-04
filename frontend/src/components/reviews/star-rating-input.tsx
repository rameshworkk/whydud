"use client";

import { useState } from "react";
import { Star } from "lucide-react";
import { cn } from "@/lib/utils/index";

const SIZE_MAP = {
  sm: { icon: "h-4 w-4", gap: "gap-0.5" },
  md: { icon: "h-5 w-5", gap: "gap-1" },
  lg: { icon: "h-7 w-7", gap: "gap-1" },
} as const;

const STAR_LABELS = ["Poor", "Fair", "Good", "Very Good", "Excellent"] as const;

interface StarRatingInputProps {
  value: number;
  onChange?: (rating: number) => void;
  size?: "sm" | "md" | "lg";
  readonly?: boolean;
  /** Show hover label text (e.g. "Good", "Excellent") next to stars */
  showLabel?: boolean;
}

export function StarRatingInput({
  value,
  onChange,
  size = "md",
  readonly = false,
  showLabel = false,
}: StarRatingInputProps) {
  const [hovered, setHovered] = useState(0);
  const { icon, gap } = SIZE_MAP[size];

  const displayed = !readonly && hovered > 0 ? hovered : value;
  const activeLabel = displayed > 0 ? STAR_LABELS[displayed - 1] : null;

  return (
    <div className="inline-flex items-center gap-2">
      <div
        className={cn("inline-flex items-center", gap)}
        role={readonly ? "img" : "radiogroup"}
        aria-label={`Rating: ${value} out of 5 stars`}
        onMouseLeave={() => {
          if (!readonly) setHovered(0);
        }}
      >
        {Array.from({ length: 5 }, (_, i) => {
          const starValue = i + 1;
          const filled = starValue <= displayed;

          if (readonly) {
            return (
              <Star
                key={i}
                className={cn(
                  icon,
                  filled
                    ? "text-[#FBBF24] fill-[#FBBF24]"
                    : "text-[#E2E8F0] fill-[#E2E8F0]"
                )}
                aria-hidden="true"
              />
            );
          }

          return (
            <button
              key={i}
              type="button"
              role="radio"
              aria-checked={value === starValue}
              aria-label={`${starValue} star${starValue > 1 ? "s" : ""} — ${STAR_LABELS[i]}`}
              onClick={() => onChange?.(starValue)}
              onMouseEnter={() => setHovered(starValue)}
              className={cn(
                "rounded-sm transition-transform duration-150",
                "hover:scale-110 active:scale-95",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1"
              )}
            >
              <Star
                className={cn(
                  icon,
                  "transition-colors duration-150",
                  filled
                    ? "text-[#FBBF24] fill-[#FBBF24]"
                    : "text-[#E2E8F0] fill-[#E2E8F0] hover:text-[#FBBF24]/50 hover:fill-[#FBBF24]/50"
                )}
                aria-hidden="true"
              />
            </button>
          );
        })}
      </div>

      {/* Hover / selected label */}
      {showLabel && !readonly && activeLabel && (
        <span className="text-sm font-medium text-[#64748B] min-w-[5rem]">
          {activeLabel}
        </span>
      )}
    </div>
  );
}
