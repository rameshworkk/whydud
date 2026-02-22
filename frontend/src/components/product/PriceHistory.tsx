"use client";

// TODO Sprint 2 Week 5: implement with Recharts + TimescaleDB data
import type { PricePoint } from "@/types";

interface PriceHistoryProps {
  data: PricePoint[];
  isLoading?: boolean;
}

/** Price history chart using Recharts. Lazy-loaded. */
export function PriceHistory({ data, isLoading }: PriceHistoryProps) {
  if (isLoading) {
    return <div className="h-48 w-full animate-pulse rounded-lg bg-muted" />;
  }

  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center rounded-lg border text-sm text-muted-foreground">
        No price history available
      </div>
    );
  }

  // TODO Sprint 2: Replace placeholder with actual Recharts LineChart
  return (
    <div className="h-48 w-full rounded-lg border flex items-center justify-center text-sm text-muted-foreground">
      Price history chart — {data.length} data points
    </div>
  );
}
