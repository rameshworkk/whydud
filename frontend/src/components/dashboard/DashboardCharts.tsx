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
import { useState } from "react";
import { formatPrice } from "@/lib/utils/format";
import type { PurchaseDashboard } from "@/types";

const DASHBOARD_TABS = [
  "Overview",
  "Platforms",
  "Categories",
  "Timeline",
  "Insights",
] as const;

const PLATFORM_COLORS = [
  "#4F46E5", "#7C3AED", "#D97706", "#059669", "#DC2626",
  "#0891B2", "#DB2777", "#D1D5DB",
];

const CATEGORY_COLORS = [
  "#4F46E5", "#7C3AED", "#A78BFA", "#C4B5FD", "#D97706",
  "#059669", "#DC2626", "#0891B2",
];

interface DashboardContentProps {
  dashboard: PurchaseDashboard;
}

/** Monthly Spend line chart */
function MonthlySpendChart({ data, totalSpent }: { data: PurchaseDashboard["monthlySpending"]; totalSpent: number }) {
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-6">
      <div className="mb-1">
        <h3 className="text-sm font-semibold text-slate-700">Monthly Spend</h3>
        <p className="text-xs text-slate-400">Your spending across recent months</p>
      </div>
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-3xl font-bold text-slate-900">{formatPrice(totalSpent)}</span>
      </div>
      {data.length > 0 ? (
        <div className="h-[180px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 12, fill: "#94A3B8" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis hide />
              <Tooltip
                formatter={(value: number) => formatPrice(value)}
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
      ) : (
        <div className="h-[180px] flex items-center justify-center text-sm text-slate-400">
          No monthly data available yet
        </div>
      )}
    </div>
  );
}

/** Spend by Platform donut chart — derived from categoryBreakdown by marketplace */
function PlatformDonut({ categories }: { categories: PurchaseDashboard["categoryBreakdown"] }) {
  const totalAmount = categories.reduce((s, p) => s + p.amount, 0);
  const chartData = categories.map((c, i) => ({
    name: c.category,
    amount: c.amount,
    color: PLATFORM_COLORS[i % PLATFORM_COLORS.length],
  }));

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
      {chartData.length > 0 ? (
        <>
          <div className="flex items-center justify-center">
            <div className="relative w-[200px] h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={85}
                    dataKey="amount"
                    paddingAngle={2}
                    strokeWidth={0}
                  >
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-lg font-bold text-slate-900">
                  {formatPrice(totalAmount)}
                </span>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap justify-center gap-4 mt-3">
            {chartData.map((p) => (
              <div key={p.name} className="flex items-center gap-1.5">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: p.color }}
                />
                <span className="text-xs text-slate-500">{p.name}</span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="h-[200px] flex items-center justify-center text-sm text-slate-400">
          No category data available yet
        </div>
      )}
    </div>
  );
}

/** Spend by Category horizontal bars */
function CategoryBars({ categories, totalSpent }: { categories: PurchaseDashboard["categoryBreakdown"]; totalSpent: number }) {
  const totalAmount = categories.reduce((s, c) => s + c.amount, 0);
  const barsData = categories.map((cat, i) => ({
    name: cat.category,
    amount: cat.amount,
    count: cat.count,
    percentage: totalAmount > 0 ? Math.round((cat.amount / totalAmount) * 100) : 0,
    color: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
  }));

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
        <span className="text-3xl font-bold text-slate-900">{formatPrice(totalSpent)}</span>
      </div>
      {barsData.length > 0 ? (
        <div className="flex flex-col gap-3.5">
          {barsData.map((cat) => (
            <div key={cat.name}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-slate-600">
                  {cat.name} ({cat.count} orders)
                </span>
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
      ) : (
        <div className="py-8 text-center text-sm text-slate-400">
          No category data available yet
        </div>
      )}
    </div>
  );
}

/** Insight cards row — generated from dashboard data */
function InsightCards({ dashboard }: { dashboard: PurchaseDashboard }) {
  const insights: Array<{ title: string; description: string; icon: string }> = [];

  if (dashboard.topMarketplace) {
    insights.push({
      title: `Your top platform is ${dashboard.topMarketplace}`,
      description: `You've made most of your purchases on ${dashboard.topMarketplace}.`,
      icon: "\uD83D\uDCC8",
    });
  }

  if (dashboard.categoryBreakdown.length > 0) {
    const topCat = dashboard.categoryBreakdown[0]!;
    insights.push({
      title: `${topCat.category} is your top category`,
      description: `You've spent ${formatPrice(topCat.amount)} across ${topCat.count} orders in this category.`,
      icon: "\uD83C\uDFF7\uFE0F",
    });
  }

  if (dashboard.activeRefunds > 0) {
    insights.push({
      title: `${dashboard.activeRefunds} active refund${dashboard.activeRefunds > 1 ? "s" : ""}`,
      description: "You have refunds being processed. Keep an eye on them.",
      icon: "\uD83D\uDCB0",
    });
  }

  if (dashboard.expiringReturns > 0) {
    insights.push({
      title: `${dashboard.expiringReturns} return${dashboard.expiringReturns > 1 ? "s" : ""} expiring soon`,
      description: "Some return windows are closing soon. Act fast if needed.",
      icon: "\uD83D\uDD04",
    });
  }

  if (dashboard.activeSubscriptions > 0) {
    insights.push({
      title: `${dashboard.activeSubscriptions} active subscription${dashboard.activeSubscriptions > 1 ? "s" : ""}`,
      description: "You have active subscriptions being tracked.",
      icon: "\uD83D\uDD01",
    });
  }

  if (insights.length === 0) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {insights.slice(0, 3).map((insight) => (
        <div
          key={insight.title}
          className="rounded-xl border border-[#E2E8F0] bg-white p-5"
        >
          <div className="flex items-start gap-3">
            <span className="text-xl shrink-0 mt-0.5">{insight.icon}</span>
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
export function DashboardContent({ dashboard }: DashboardContentProps) {
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
          <MonthlySpendChart data={dashboard.monthlySpending} totalSpent={dashboard.totalSpent} />
        </div>
        <div className="lg:col-span-2">
          <PlatformDonut categories={dashboard.categoryBreakdown} />
        </div>
      </div>

      {/* Category bars */}
      <CategoryBars categories={dashboard.categoryBreakdown} totalSpent={dashboard.totalSpent} />

      {/* Insight cards */}
      <InsightCards dashboard={dashboard} />
    </div>
  );
}
