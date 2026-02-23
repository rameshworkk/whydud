"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  MOCK_MONTHLY_SPEND,
  MOCK_PLATFORM_SPEND,
  MOCK_CATEGORY_SPEND,
  MOCK_INSIGHTS,
  DASHBOARD_TABS,
} from "@/lib/mock-dashboard-data";
import { useState } from "react";

/** Monthly Spend line chart */
function MonthlySpendChart() {
  const { data, total, change, changePositive, subtitle } = MOCK_MONTHLY_SPEND;

  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-6">
      <div className="mb-1">
        <h3 className="text-sm font-semibold text-slate-700">Monthly Spend</h3>
        <p className="text-xs text-slate-400">{subtitle}</p>
      </div>
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-3xl font-bold text-slate-900">{total}</span>
        <span
          className={`text-sm font-semibold ${
            changePositive ? "text-green-600" : "text-red-600"
          }`}
        >
          {change}
        </span>
      </div>
      <div className="h-[180px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
            <XAxis
              dataKey="week"
              tick={{ fontSize: 12, fill: "#94A3B8" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis hide />
            <Tooltip
              formatter={(value: number) =>
                `₹${(value / 100).toLocaleString("en-IN")}`
              }
              contentStyle={{
                borderRadius: 8,
                border: "1px solid #E2E8F0",
                fontSize: 12,
              }}
            />
            <Line
              type="monotone"
              dataKey="amount"
              stroke="#4F46E5"
              strokeWidth={2.5}
              dot={{ r: 4, fill: "#4F46E5", strokeWidth: 2, stroke: "#fff" }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/** Spend by Platform donut chart */
function PlatformDonut() {
  const totalAmount = MOCK_PLATFORM_SPEND.reduce((s, p) => s + p.amount, 0);

  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-6">
      <div className="mb-1">
        <h3 className="text-sm font-semibold text-slate-700">
          Spend by Platform
        </h3>
        <p className="text-xs text-slate-400">
          Breakdown of your spending across different platforms.
        </p>
      </div>
      <div className="flex items-center justify-center">
        <div className="relative w-[200px] h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={MOCK_PLATFORM_SPEND}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={85}
                dataKey="amount"
                paddingAngle={2}
                strokeWidth={0}
              >
                {MOCK_PLATFORM_SPEND.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-lg font-bold text-slate-900">
              ₹{Math.round(totalAmount / 100).toLocaleString("en-IN")}
            </span>
          </div>
        </div>
      </div>
      <div className="flex justify-center gap-4 mt-3">
        {MOCK_PLATFORM_SPEND.map((p) => (
          <div key={p.name} className="flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: p.color }}
            />
            <span className="text-xs text-slate-500">{p.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Spend by Category horizontal bars */
function CategoryBars() {
  const { total, change, changePositive, categories } = MOCK_CATEGORY_SPEND;

  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-6">
      <div className="mb-1">
        <h3 className="text-sm font-semibold text-slate-700">
          Spend by Category
        </h3>
        <p className="text-xs text-slate-400">
          Breakdown of your spending across shopping categories.
        </p>
      </div>
      <div className="flex items-baseline gap-2 mb-5">
        <span className="text-3xl font-bold text-slate-900">{total}</span>
        <span
          className={`text-sm font-semibold ${
            changePositive ? "text-green-600" : "text-red-600"
          }`}
        >
          {change}
        </span>
      </div>
      <div className="flex flex-col gap-3.5">
        {categories.map((cat) => (
          <div key={cat.name}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-slate-600">{cat.name}</span>
              <span className="text-xs text-slate-400">{cat.percentage}%</span>
            </div>
            <div className="h-2.5 rounded-full bg-slate-100 overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${cat.percentage}%`,
                  backgroundColor: cat.color,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Insight cards row */
function InsightCards() {
  const iconMap: Record<string, string> = {
    trending: "📈",
    category: "🏷️",
    calendar: "📅",
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {MOCK_INSIGHTS.map((insight) => (
        <div
          key={insight.title}
          className="rounded-xl border border-[#E2E8F0] bg-white p-5"
        >
          <div className="flex items-start gap-3">
            <span className="text-xl shrink-0 mt-0.5">
              {iconMap[insight.icon] ?? "💡"}
            </span>
            <div>
              <h4 className="text-sm font-semibold text-slate-800 leading-snug">
                {insight.title}
              </h4>
              <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                {insight.description}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/** Full dashboard client component with tabs and charts */
export function DashboardContent() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <div className="flex flex-col gap-6">
      {/* Tab navigation */}
      <div className="flex gap-1 border-b border-[#E2E8F0]">
        {DASHBOARD_TABS.map((tab, i) => (
          <button
            key={tab}
            onClick={() => setActiveTab(i)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded-t ${
              i === activeTab
                ? "border-[#4F46E5] text-[#4F46E5]"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3">
          <MonthlySpendChart />
        </div>
        <div className="lg:col-span-2">
          <PlatformDonut />
        </div>
      </div>

      {/* Category bars */}
      <CategoryBars />

      {/* Insight cards */}
      <InsightCards />
    </div>
  );
}
