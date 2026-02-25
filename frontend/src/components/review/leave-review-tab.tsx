"use client";

import { useRef } from "react";
import { Camera, ChevronRight, X } from "lucide-react";
import { cn } from "@/lib/utils/index";
import { StarRatingInput } from "@/components/reviews/star-rating-input";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface LeaveReviewData {
  rating: number;
  title: string;
  bodyPositive: string;
  bodyNegative: string;
  npsScore: number | null;
  mediaFiles: File[];
}

interface LeaveReviewTabProps {
  data: LeaveReviewData;
  onChange: (update: Partial<LeaveReviewData>) => void;
  onNext: () => void;
  onRateFeatures?: () => void;
}

// ── NPS Scale ─────────────────────────────────────────────────────────────────

const NPS_VALUES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as const;

function npsColor(value: number, selected: number | null): string {
  if (selected !== value) return "border-[#E2E8F0] bg-white text-[#1E293B] hover:bg-[#F8FAFC]";
  if (value <= 6) return "border-red-300 bg-red-50 text-red-700";
  if (value <= 8) return "border-amber-300 bg-amber-50 text-amber-700";
  return "border-emerald-300 bg-emerald-50 text-emerald-700";
}

// ── Component ─────────────────────────────────────────────────────────────────

export function LeaveReviewTab({
  data,
  onChange,
  onNext,
  onRateFeatures,
}: LeaveReviewTabProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleMediaChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files?.length) return;
    onChange({ mediaFiles: [...data.mediaFiles, ...Array.from(files)] });
    e.target.value = "";
  }

  function removeMedia(index: number) {
    onChange({ mediaFiles: data.mediaFiles.filter((_, i) => i !== index) });
  }

  const canProceed = data.rating > 0;

  return (
    <div className="space-y-6">
      {/* ── Overall rating ─────────────────────────────────────── */}
      <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-base font-semibold text-[#1E293B]">
              Your rating{" "}
              <span className="text-xs font-normal text-[#94A3B8]">
                required
              </span>
            </p>
            <p className="mt-0.5 text-sm text-[#64748B]">
              How would you rate this product overall?
            </p>

            {/* Rate other features link */}
            {onRateFeatures && (
              <button
                type="button"
                onClick={onRateFeatures}
                className={cn(
                  "mt-2 inline-flex items-center gap-1 text-sm font-medium text-[#1E293B] underline underline-offset-2",
                  "hover:text-[#F97316]",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded",
                  "transition-colors"
                )}
              >
                Rate other features
                <ChevronRight className="h-4 w-4" />
              </button>
            )}
          </div>

          <StarRatingInput
            value={data.rating}
            onChange={(rating) => onChange({ rating })}
            size="lg"
          />
        </div>
      </div>

      {/* ── Review title ───────────────────────────────────────── */}
      <div className="space-y-1.5">
        <label
          htmlFor="lr-title"
          className="block text-sm font-semibold text-[#1E293B]"
        >
          Give your review a title{" "}
          <span className="text-xs font-normal text-[#94A3B8]">required</span>
        </label>
        <input
          id="lr-title"
          type="text"
          value={data.title}
          onChange={(e) => onChange({ title: e.target.value })}
          placeholder="What's important for people to know?"
          className={cn(
            "h-10 w-full rounded-lg border border-[#E2E8F0] bg-white px-3 text-sm",
            "text-[#1E293B] placeholder:text-[#94A3B8]",
            "focus:border-[#F97316] focus:outline-none focus:ring-2 focus:ring-[#F97316]/20",
            "transition-colors"
          )}
        />
      </div>

      {/* ── Share your experience ──────────────────────────────── */}
      <div className="space-y-3">
        <p className="text-sm font-semibold text-[#1E293B]">
          Share your experience
        </p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {/* What did you like? */}
          <div className="space-y-1.5">
            <label
              htmlFor="lr-positive"
              className="block text-sm text-[#1E293B]"
            >
              What did you like?
            </label>
            <textarea
              id="lr-positive"
              value={data.bodyPositive}
              onChange={(e) => onChange({ bodyPositive: e.target.value })}
              placeholder="Tell us what you enjoyed about this product..."
              rows={5}
              className={cn(
                "w-full resize-none rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm leading-relaxed",
                "text-[#1E293B] placeholder:text-[#94A3B8]",
                "focus:border-[#F97316] focus:outline-none focus:ring-2 focus:ring-[#F97316]/20",
                "transition-colors"
              )}
            />
          </div>

          {/* What you didn't like? */}
          <div className="space-y-1.5">
            <label
              htmlFor="lr-negative"
              className="block text-sm text-[#1E293B]"
            >
              What you didn&apos;t like?
            </label>
            <textarea
              id="lr-negative"
              value={data.bodyNegative}
              onChange={(e) => onChange({ bodyNegative: e.target.value })}
              placeholder="Share your concerns or issues you experienced..."
              rows={5}
              className={cn(
                "w-full resize-none rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm leading-relaxed",
                "text-[#1E293B] placeholder:text-[#94A3B8]",
                "focus:border-[#F97316] focus:outline-none focus:ring-2 focus:ring-[#F97316]/20",
                "transition-colors"
              )}
            />
          </div>
        </div>
      </div>

      {/* ── Media upload ───────────────────────────────────────── */}
      <div className="space-y-3">
        <p className="text-sm font-semibold text-[#1E293B]">
          Add photos or videos to your review
        </p>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,video/*"
          multiple
          onChange={handleMediaChange}
          className="hidden"
          aria-label="Upload photos or videos"
        />

        <div className="flex flex-wrap gap-2">
          {/* Existing file chips */}
          {data.mediaFiles.map((file, i) => (
            <div
              key={`${file.name}-${i}`}
              className="flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3 py-2 text-sm text-[#1E293B]"
            >
              <Camera className="h-3.5 w-3.5 text-[#64748B] shrink-0" />
              <span className="max-w-[120px] truncate">{file.name}</span>
              <button
                type="button"
                onClick={() => removeMedia(i)}
                className="shrink-0 rounded p-0.5 text-[#64748B] hover:text-red-500 hover:bg-red-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
                aria-label={`Remove ${file.name}`}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}

          {/* Upload button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className={cn(
              "flex items-center gap-2 rounded-lg border border-[#E2E8F0] bg-white px-4 py-2 text-sm font-medium",
              "text-[#1E293B] hover:bg-[#F8FAFC] active:bg-[#F1F5F9]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
              "transition-colors"
            )}
          >
            <Camera className="h-4 w-4 text-[#64748B]" />
            Upload
          </button>
        </div>
      </div>

      {/* ── NPS score ──────────────────────────────────────────── */}
      <div className="space-y-3">
        <p className="text-sm font-semibold text-[#1E293B]">
          On a scale of 0-10 how likely are you to recommend this to a friend?
        </p>

        <div>
          <div className="flex flex-wrap gap-1.5">
            {NPS_VALUES.map((v) => (
              <button
                key={v}
                type="button"
                onClick={() =>
                  onChange({ npsScore: data.npsScore === v ? null : v })
                }
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-lg border text-sm font-medium",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1",
                  "transition-colors",
                  npsColor(v, data.npsScore)
                )}
                aria-label={`${v} out of 10`}
                aria-pressed={data.npsScore === v}
              >
                {v}
              </button>
            ))}
          </div>
          <div className="mt-1.5 flex justify-between">
            <span className="text-xs text-[#94A3B8]">Not likely at all</span>
            <span className="text-xs text-[#94A3B8]">Extremely likely</span>
          </div>
        </div>
      </div>

      {/* ── Footer button ──────────────────────────────────────── */}
      <div className="flex items-center justify-end pt-2">
        <button
          type="button"
          onClick={onNext}
          disabled={!canProceed}
          className={cn(
            "rounded-lg px-8 py-2.5 text-sm font-medium",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1",
            "transition-colors",
            canProceed
              ? "bg-[#E2E8F0] text-[#1E293B] hover:bg-[#CBD5E1] active:bg-[#94A3B8]"
              : "bg-[#F1F5F9] text-[#94A3B8] cursor-not-allowed"
          )}
        >
          Next
        </button>
      </div>
    </div>
  );
}
