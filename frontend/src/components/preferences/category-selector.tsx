"use client";

import {
  Wind,
  Snowflake,
  Droplets,
  Refrigerator,
  WashingMachine,
  Car,
  Laptop,
  Box,
  Check,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils/index";
import type { PreferenceSchema, PurchasePreference } from "@/lib/api/types";

// ── Category icon mapping ────────────────────────────────────────────────────

const CATEGORY_ICONS: Record<string, LucideIcon> = {
  "air-purifiers": Wind,
  "air-conditioners": Snowflake,
  "water-purifiers": Droplets,
  "refrigerators": Refrigerator,
  "washing-machines": WashingMachine,
  "vehicles": Car,
  "laptops": Laptop,
};

function getCategoryIcon(slug: string): LucideIcon {
  return CATEGORY_ICONS[slug] ?? Box;
}

// ── Props ────────────────────────────────────────────────────────────────────

interface CategorySelectorProps {
  schemas: PreferenceSchema[];
  savedPreferences: PurchasePreference[];
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
}

// ── Component ────────────────────────────────────────────────────────────────

export function CategorySelector({
  schemas,
  savedPreferences,
  selectedSlug,
  onSelect,
}: CategorySelectorProps) {
  const savedSlugs = new Set(savedPreferences.map((p) => p.categorySlug));

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {schemas.map((schema) => {
        const Icon = getCategoryIcon(schema.categorySlug);
        const isSaved = savedSlugs.has(schema.categorySlug);
        const isSelected = selectedSlug === schema.categorySlug;

        return (
          <button
            key={schema.categorySlug}
            type="button"
            onClick={() => onSelect(schema.categorySlug)}
            className={cn(
              "relative flex flex-col items-center gap-2 rounded-lg border p-4 text-center transition-shadow",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2",
              isSelected
                ? "border-[#F97316] bg-[#FFF7ED] shadow-md"
                : "border-[#E2E8F0] bg-white hover:border-[#CBD5E1] hover:shadow-sm"
            )}
          >
            {/* Saved badge */}
            {isSaved && (
              <span className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-[#16A34A]">
                <Check className="h-3 w-3 text-white" />
              </span>
            )}

            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-lg",
                isSelected ? "bg-[#F97316]/10" : "bg-[#F8FAFC]"
              )}
            >
              <Icon
                className={cn(
                  "h-5 w-5",
                  isSelected ? "text-[#F97316]" : "text-[#64748B]"
                )}
              />
            </div>

            <span
              className={cn(
                "text-sm font-medium leading-tight",
                isSelected ? "text-[#1E293B]" : "text-[#64748B]"
              )}
            >
              {schema.categoryName}
            </span>

            {isSaved && (
              <span className="text-xs text-[#16A34A] font-medium">
                Saved
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
