"use client";

import Link from "next/link";
import { Shield, ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";
import type { BrandTrustTier } from "@/types";

interface BrandTrustBadgeProps {
  brandSlug: string;
  brandName: string;
  avgDudScore: number;
  trustTier: BrandTrustTier;
  /** Compact mode for inline display next to brand name. */
  compact?: boolean;
}

const TIER_CONFIG: Record<
  BrandTrustTier,
  { label: string; bg: string; text: string; border: string; Icon: typeof Shield }
> = {
  excellent: {
    label: "Excellent",
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
    Icon: ShieldCheck,
  },
  good: {
    label: "Good",
    bg: "bg-lime-50",
    text: "text-lime-700",
    border: "border-lime-200",
    Icon: ShieldCheck,
  },
  average: {
    label: "Average",
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
    Icon: Shield,
  },
  poor: {
    label: "Poor",
    bg: "bg-orange-50",
    text: "text-orange-700",
    border: "border-orange-200",
    Icon: ShieldAlert,
  },
  avoid: {
    label: "Avoid",
    bg: "bg-red-50",
    text: "text-red-700",
    border: "border-red-200",
    Icon: ShieldX,
  },
};

export function BrandTrustBadge({
  brandSlug,
  brandName,
  avgDudScore,
  trustTier,
  compact = false,
}: BrandTrustBadgeProps) {
  const tier = TIER_CONFIG[trustTier];
  const { Icon } = tier;

  if (compact) {
    return (
      <Link
        href={`/brand/${brandSlug}`}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${tier.bg} ${tier.text} ${tier.border} hover:opacity-80 transition-opacity`}
        title={`${brandName} Brand Trust: ${Math.round(avgDudScore)}/100 (${tier.label})`}
      >
        <Icon className="w-3 h-3" />
        <span>{Math.round(avgDudScore)}</span>
      </Link>
    );
  }

  return (
    <Link
      href={`/brand/${brandSlug}`}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${tier.bg} ${tier.text} ${tier.border} hover:opacity-80 transition-opacity`}
    >
      <Icon className="w-4 h-4" />
      <div className="flex flex-col">
        <span className="text-xs font-semibold leading-tight">
          Brand Trust: {Math.round(avgDudScore)}/100
        </span>
        <span className="text-[10px] opacity-75 leading-tight">{tier.label}</span>
      </div>
    </Link>
  );
}
