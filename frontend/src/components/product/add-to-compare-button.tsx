"use client";

import { Scale, Check } from "lucide-react";
import { useCompare } from "@/contexts/compare-context";
import { cn } from "@/lib/utils/index";
import type { ProductSummary } from "@/types/product";

interface AddToCompareButtonProps {
  product: ProductSummary;
  /** Optional extra classes on the outer button. */
  className?: string;
}

export function AddToCompareButton({
  product,
  className,
}: AddToCompareButtonProps) {
  const { addToCompare, removeFromCompare, isInCompare, isFull } =
    useCompare();

  const active = isInCompare(product.slug);
  const disabled = !active && isFull;

  function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (active) {
      removeFromCompare(product.slug);
    } else if (!isFull) {
      addToCompare(product);
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled}
      title={
        disabled
          ? "Compare tray is full (max 4 products)"
          : active
          ? "Remove from compare"
          : "Add to compare"
      }
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium",
        "transition-colors duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1",
        active
          ? "border-[#16A34A]/30 bg-[#F0FDF4] text-[#16A34A] hover:bg-[#DCFCE7] focus-visible:ring-[#16A34A]"
          : "border-[#E2E8F0] bg-white text-[#1E293B] hover:border-[#F97316] hover:text-[#F97316] focus-visible:ring-[#F97316]",
        disabled && "cursor-not-allowed opacity-50",
        className
      )}
    >
      {active ? (
        <>
          <Check className="h-3.5 w-3.5" />
          In Compare
        </>
      ) : (
        <>
          <Scale className="h-3.5 w-3.5" />
          Compare
        </>
      )}
    </button>
  );
}
