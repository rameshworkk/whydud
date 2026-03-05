"use client";

import { useState, useEffect } from "react";
import { purchasesApi } from "@/lib/api/inbox";
import { formatPrice } from "@/lib/utils/format";
import { DashboardContent } from "@/components/dashboard/DashboardCharts";
import type { PurchaseDashboard } from "@/types";

const STAT_ICONS: Record<string, string> = {
  spend: "\uD83D\uDCB0",
  orders: "\uD83D\uDCE6",
  average: "\uD83D\uDCCA",
  platform: "\uD83C\uDFEA",
};

function StatSkeleton() {
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 animate-pulse">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-6 h-6 rounded bg-slate-200" />
        <div className="w-20 h-3 rounded bg-slate-200" />
      </div>
      <div className="w-24 h-6 rounded bg-slate-200" />
    </div>
  );
}

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<PurchaseDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchDashboard() {
      try {
        const res = await purchasesApi.getDashboard();
        if (res.success && "data" in res) {
          // Provide safe defaults for fields the backend may not return
          const d = res.data;
          setDashboard({
            totalSpent: d.totalSpent ?? 0,
            totalOrders: d.totalOrders ?? 0,
            averageOrderValue: d.averageOrderValue ?? 0,
            topMarketplace: d.topMarketplace ?? null,
            monthlySpending: d.monthlySpending ?? [],
            categoryBreakdown: d.categoryBreakdown ?? [],
            activeRefunds: d.activeRefunds ?? 0,
            expiringReturns: d.expiringReturns ?? 0,
            activeSubscriptions: d.activeSubscriptions ?? 0,
          });
        } else if (!res.success && "error" in res) {
          setError(res.error.message);
        }
      } catch {
        setError("Failed to load dashboard data.");
      } finally {
        setLoading(false);
      }
    }
    fetchDashboard();
  }, []);

  const stats = dashboard
    ? [
        { label: "Total spend", value: formatPrice(dashboard.totalSpent), icon: "spend" },
        { label: "Orders", value: String(dashboard.totalOrders), icon: "orders" },
        { label: "Average order", value: formatPrice(dashboard.averageOrderValue), icon: "average" },
        { label: "Top platform", value: dashboard.topMarketplace ?? "N/A", icon: "platform" },
      ]
    : [];

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Expense Tracker</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Analyse your spending across platforms and categories.
        </p>
      </div>

      {/* Error / auth state */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm font-medium text-slate-700 mb-1">
            Something went wrong
          </p>
          <p className="text-xs text-slate-500">{error}</p>
        </div>
      )}

      {/* 4 stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => <StatSkeleton key={i} />)
          : stats.map((stat) => (
              <div
                key={stat.label}
                className="rounded-xl border border-[#E2E8F0] bg-white p-4"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-base">{STAT_ICONS[stat.icon]}</span>
                  <span className="text-xs text-slate-500 font-medium">
                    {stat.label}
                  </span>
                </div>
                <p className="text-xl font-bold text-slate-900">{stat.value}</p>
              </div>
            ))}
      </div>

      {/* Client-side charts + tabs */}
      {loading ? (
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-6 animate-pulse">
          <div className="h-[300px] flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-slate-300 border-t-[#F97316] rounded-full animate-spin" />
          </div>
        </div>
      ) : dashboard ? (
        <DashboardContent dashboard={dashboard} />
      ) : !error ? (
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-12 text-center">
          <p className="text-2xl mb-2">{"\uD83D\uDCE6"}</p>
          <p className="text-sm font-semibold text-slate-700">No spending data yet</p>
          <p className="text-xs text-slate-500 mt-1">
            Connect your shopping email or make purchases to see your expense tracker.
          </p>
        </div>
      ) : null}
    </div>
  );
}
