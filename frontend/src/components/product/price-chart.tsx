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
import type { MockPricePoint } from "@/lib/mock-product-detail";

interface PriceChartProps {
  data: MockPricePoint[];
}

type Range = "1M" | "3M" | "Max";

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

export function PriceChart({ data }: PriceChartProps) {
  const [range, setRange] = useState<Range>("3M");

  const filtered = useMemo(() => {
    if (range === "Max") return data;
    const days = range === "1M" ? 30 : 90;
    return data.slice(-days);
  }, [data, range]);

  // Downsample to ~20 points for readability
  const chartData = useMemo(() => {
    const step = Math.max(1, Math.floor(filtered.length / 20));
    return filtered
      .filter((_, i) => i % step === 0 || i === filtered.length - 1)
      .map((p) => ({
        ...p,
        dateLabel: formatAxisDate(p.date),
      }));
  }, [filtered]);

  const ranges: Range[] = ["1M", "3M", "Max"];

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
          <Line
            type="monotone"
            dataKey="amazon"
            name="amazon"
            stroke="#FF9900"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="flipkart"
            name="flipkart"
            stroke="#2874F0"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="croma"
            name="croma"
            stroke="#E31837"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
