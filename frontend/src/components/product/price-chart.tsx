"use client";

import { useState, useMemo } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { PricePoint } from "@/types";

interface PriceChartProps {
  data: PricePoint[];
  /** Map of marketplaceId → { name, color } for rendering lines */
  marketplaces?: Record<number, { name: string; color: string }>;
}

type Range = "1M" | "3M" | "6M" | "1Y" | "Max";

const DEFAULT_COLORS = ["#FF9900", "#2874F0", "#E31837", "#FF3F6C", "#9B2335", "#3366CC"];

const RANGE_DAYS: Record<Range, number> = {
  "1M": 30,
  "3M": 90,
  "6M": 180,
  "1Y": 365,
  "Max": 0,
};

function formatRupees(paisa: number): string {
  const rupees = paisa / 100;
  if (rupees >= 100000) return `₹${(rupees / 100000).toFixed(1)}L`;
  if (rupees >= 1000) return `₹${(rupees / 1000).toFixed(1)}K`;
  return `₹${rupees.toFixed(0)}`;
}

function formatFullRupees(paisa: number): string {
  const rupees = Math.round(paisa / 100);
  return `₹${rupees.toLocaleString("en-IN")}`;
}

/** Format axis date with year when range spans multiple years */
function formatAxisDate(dateStr: string, showYear: boolean): string {
  const d = new Date(dateStr);
  if (showYear) {
    const month = d.toLocaleDateString("en-IN", { month: "short" });
    const year = d.getFullYear().toString().slice(2); // '24
    return `${month} '${year}`;
  }
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

/** Format tooltip date always with full year */
function formatTooltipDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

/**
 * Pivot PricePoint[] into chart-friendly rows.
 * { time, [marketplaceName]: price, ... }
 */
function pivotData(
  points: PricePoint[],
  marketplaceMap: Record<number, { name: string; color: string }>,
  showYear: boolean,
): Record<string, string | number>[] {
  const grouped = new Map<string, Record<string, string | number>>();

  for (const pt of points) {
    const key = pt.time.split("T")[0] ?? pt.time;
    if (!grouped.has(key)) {
      grouped.set(key, {
        time: key,
        dateLabel: formatAxisDate(key, showYear),
      });
    }
    const row = grouped.get(key)!;
    const mpName = marketplaceMap[pt.marketplaceId]?.name ?? `mp_${pt.marketplaceId}`;
    row[mpName] = pt.price;
  }

  return Array.from(grouped.values()).sort((a, b) =>
    (a.time as string).localeCompare(b.time as string)
  );
}

/** Compute price stats from filtered data */
function computeStats(points: PricePoint[]) {
  if (points.length === 0) return null;

  const prices = points.map((p) => p.price);
  const current = prices[prices.length - 1]!;
  const lowest = Math.min(...prices);
  const highest = Math.max(...prices);
  const average = Math.round(prices.reduce((a, b) => a + b, 0) / prices.length);

  return { current, lowest, highest, average };
}

export function PriceChart({ data, marketplaces }: PriceChartProps) {
  const [range, setRange] = useState<Range>("Max");

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
    const days = RANGE_DAYS[range];
    if (days === 0) return data;

    // Minimum points per range so every tab shows a real chart
    const MIN_POINTS: Record<Range, number> = {
      "1M": 14,
      "3M": 20,
      "6M": 24,
      "1Y": 36,
      "Max": 0,
    };

    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString();
    const inRange = data.filter((p) => p.time >= cutoffStr);

    const needed = MIN_POINTS[range];
    if (inRange.length < needed && data.length > inRange.length) {
      return data.slice(-Math.min(needed, data.length));
    }
    return inRange;
  }, [data, range]);

  // Check if data spans multiple years to decide axis format
  const showYear = useMemo(() => {
    if (filtered.length < 2) return false;
    const first = new Date(filtered[0]!.time).getFullYear();
    const last = new Date(filtered[filtered.length - 1]!.time).getFullYear();
    return first !== last;
  }, [filtered]);

  const pivoted = useMemo(() => pivotData(filtered, marketplaceMap, showYear), [filtered, marketplaceMap, showYear]);

  // Downsample to ~30 points for readability
  const chartData = useMemo(() => {
    if (pivoted.length <= 35) return pivoted;
    const step = Math.max(1, Math.floor(pivoted.length / 30));
    return pivoted.filter((_, i) => i % step === 0 || i === pivoted.length - 1);
  }, [pivoted]);

  const lineKeys = useMemo(() => {
    return Object.values(marketplaceMap).map((mp) => ({
      name: mp.name,
      color: mp.color,
    }));
  }, [marketplaceMap]);

  const stats = useMemo(() => computeStats(filtered), [filtered]);

  const ranges: Range[] = ["1M", "3M", "6M", "1Y", "Max"];

  if (data.length === 0) {
    return (
      <div className="w-full py-8 text-center text-sm text-slate-400">
        No price history data available yet.
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Price stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-3 mb-4">
          <div className="text-center">
            <p className="text-[10px] uppercase tracking-wide text-slate-400 mb-0.5">Current</p>
            <p className="text-sm font-semibold text-slate-800">{formatFullRupees(stats.current)}</p>
          </div>
          <div className="text-center">
            <p className="text-[10px] uppercase tracking-wide text-slate-400 mb-0.5">Lowest</p>
            <p className="text-sm font-semibold text-green-600">{formatFullRupees(stats.lowest)}</p>
          </div>
          <div className="text-center">
            <p className="text-[10px] uppercase tracking-wide text-slate-400 mb-0.5">Highest</p>
            <p className="text-sm font-semibold text-red-500">{formatFullRupees(stats.highest)}</p>
          </div>
          <div className="text-center">
            <p className="text-[10px] uppercase tracking-wide text-slate-400 mb-0.5">Average</p>
            <p className="text-sm font-semibold text-slate-600">{formatFullRupees(stats.average)}</p>
          </div>
        </div>
      )}

      {/* Range selector */}
      <div className="flex items-center gap-1 mb-3">
        <span className="text-xs text-slate-500 mr-1">All Platforms</span>
        <span className="text-slate-300 mr-1">|</span>
        {ranges.map((r) => (
          <button
            key={r}
            onClick={() => setRange(r)}
            className={`px-2.5 py-0.5 text-xs font-semibold rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] ${
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
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart
          data={chartData}
          margin={{ top: 4, right: 4, left: 0, bottom: 4 }}
        >
          <defs>
            {lineKeys.map((lk) => (
              <linearGradient key={lk.name} id={`grad-${lk.name}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={lk.color} stopOpacity={0.15} />
                <stop offset="95%" stopColor={lk.color} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
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
            labelFormatter={(label, payload) => {
              const time = payload?.[0]?.payload?.time;
              return time ? formatTooltipDate(time) : label;
            }}
            formatter={(value: number, name: string) => [
              formatFullRupees(value),
              name,
            ]}
            labelStyle={{ fontSize: 11, fontWeight: 600, color: "#1E293B" }}
            contentStyle={{
              border: "1px solid #E2E8F0",
              borderRadius: "8px",
              fontSize: 12,
              boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
            }}
          />
          {lineKeys.map((lk) => (
            <Area
              key={lk.name}
              type="monotone"
              dataKey={lk.name}
              name={lk.name}
              stroke={lk.color}
              strokeWidth={2}
              fill={`url(#grad-${lk.name})`}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, fill: "#fff" }}
              connectNulls
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-2">
        {lineKeys.map((lk) => (
          <div key={lk.name} className="flex items-center gap-1.5">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: lk.color }}
            />
            <span className="text-xs text-slate-500">{lk.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
