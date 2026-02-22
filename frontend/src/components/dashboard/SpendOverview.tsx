"use client";

import { formatPrice } from "@/lib/utils";

interface SpendOverviewProps {
  lifetimeTotal: number | null;
  isLoading?: boolean;
}

/** Purchase dashboard spend summary card. */
export function SpendOverview({ lifetimeTotal, isLoading }: SpendOverviewProps) {
  if (isLoading) {
    return <div className="h-32 animate-pulse rounded-xl bg-muted" />;
  }

  return (
    <div className="rounded-xl border bg-card p-6">
      <p className="text-sm text-muted-foreground">Lifetime spend tracked</p>
      <p className="mt-1 text-4xl font-black">{formatPrice(lifetimeTotal)}</p>
      {/* TODO Sprint 3 Week 8: Monthly trend chart (Recharts AreaChart) */}
      <div className="mt-4 h-16 rounded-lg bg-muted flex items-center justify-center text-xs text-muted-foreground">
        Monthly trend chart — coming Sprint 3
      </div>
    </div>
  );
}
