"use client";

import { useState, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { PricePoint } from "@/types";

interface PriceChartProps {
  data: PricePoint[];
  /** Map of marketplaceId → { name, color } for rendering lines */
  marketplaces?: Record<number, { name: string; color: string }>;
}

type Range = "1M" | "3M" | "Max";

const DEFAULT_COLORS = ["#FF9900", "#2874F0", "#E31837", "#FF3F6C", "#9B2335", "#3366CC"];

function formatRupees(paisa: number): string {
  const rupees = paisa / 100;
  if (rupees >= 100000) return `₹${(rupees / 100000).toFixed(1)}L`;
  if (rupees >= 1000) return `₹${(rupees / 1000).toFixed(1)}K`;
  return `₹${rupees.toFixed(0)}`;
}

function formatAxisDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

/**
 * Pivot PricePoint[] (one row per marketplace per time) into
 * chart-friendly rows: { time, dateLabel, [marketplaceKey]: price, ... }
 */
function pivotData(
  points: PricePoint[],
  marketplaceMap: Record<number, { name: string; color: string }>
): Record<string, string | number>[] {
  const grouped = new Map<string, Record<string, string | number>>();

  for (const pt of points) {
    const key = pt.time.split("T")[0] ?? pt.time;
    if (!grouped.has(key)) {
      grouped.set(key, { time: key, dateLabel: formatAxisDate(key) });
    }
    const row = grouped.get(key)!;
    const mpName = marketplaceMap[pt.marketplaceId]?.name ?? `mp_${pt.marketplaceId}`;
    row[mpName] = pt.price;
  }

  return Array.from(grouped.values()).sort((a, b) =>
    (a.time as string).localeCompare(b.time as string)
  );
}

export function PriceChart({ data, marketplaces }: PriceChartProps) {
  const [range, setRange] = useState<Range>("3M");

  // Discover marketplace IDs from data if not explicitly provided
  const marketplaceMap = useMemo(() => {
    if (marketplaces) return marketplaces;
    const ids = [...new Set(data.map((p) => p.marketplaceId))];
    const map: Record<number, { name: string; color: string }> = {};
    ids.forEach((id, idx) => {
      map[id] = { name: `Marketplace ${id}`, color: DEFAULT_COLORS[idx % DEFAULT_COLORS.length]! };
    });
    return map;
  }, [data, marketplaces]);

  const filtered = useMemo(() => {
    if (range === "Max") return data;
    const days = range === "1M" ? 30 : 90;
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString();
    return data.filter((p) => p.time >= cutoffStr);
  }, [data, range]);

  const pivoted = useMemo(() => pivotData(filtered, marketplaceMap), [filtered, marketplaceMap]);

  // Downsample to ~20 points for readability
  const chartData = useMemo(() => {
    const step = Math.max(1, Math.floor(pivoted.length / 20));
    return pivoted.filter((_, i) => i % step === 0 || i === pivoted.length - 1);
  }, [pivoted]);

  const lineKeys = useMemo(() => {
    return Object.values(marketplaceMap).map((mp) => ({
      name: mp.name,
      color: mp.color,
    }));
  }, [marketplaceMap]);

  const ranges: Range[] = ["1M", "3M", "Max"];

  if (data.length === 0) {
    return (
      <div className="w-full py-8 text-center text-sm text-slate-400">
        No price history data available yet.
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Range selector */}
      <div className="flex items-center gap-1 mb-4">
        <span className="text-xs text-slate-500 mr-2">All Platforms</span>
        {ranges.map((r) => (
          <button
            key={r}
            onClick={() => setRange(r)}
            className={`px-3 py-1 text-xs font-semibold rounded-full transition-colors ${
              range === r
                ? "bg-[#F97316] text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {r}
          </button>
        ))}
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={200}>
        <LineChart
          data={chartData}
          margin={{ top: 4, right: 4, left: 0, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
          <XAxis
            dataKey="dateLabel"
            tick={{ fontSize: 10, fill: "#94A3B8" }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={formatRupees}
            tick={{ fontSize: 10, fill: "#94A3B8" }}
            tickLine={false}
            axisLine={false}
            width={52}
            domain={["auto", "auto"]}
          />
          <Tooltip
            formatter={(value: number, name: string) => [
              formatRupees(value),
              name.charAt(0).toUpperCase() + name.slice(1),
            ]}
            labelStyle={{ fontSize: 11, color: "#1E293B" }}
            contentStyle={{
              border: "1px solid #E2E8F0",
              borderRadius: "8px",
              fontSize: 11,
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
            formatter={(v) => v.charAt(0).toUpperCase() + v.slice(1)}
          />
          {lineKeys.map((lk) => (
            <Line
              key={lk.name}
              type="monotone"
              dataKey={lk.name}
              name={lk.name}
              stroke={lk.color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
