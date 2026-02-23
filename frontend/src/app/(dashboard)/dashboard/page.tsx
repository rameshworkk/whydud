import type { Metadata } from "next";
import { MOCK_DASHBOARD_STATS } from "@/lib/mock-dashboard-data";
import { DashboardContent } from "@/components/dashboard/DashboardCharts";

export const metadata: Metadata = { title: "Expense Tracker — Whydud" };

const STAT_ICONS: Record<string, string> = {
  spend: "💰",
  orders: "📦",
  average: "📊",
  platform: "🏪",
};

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Expense Tracker</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Analyse your spending across platforms and categories.
        </p>
      </div>

      {/* 4 stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {MOCK_DASHBOARD_STATS.map((stat) => (
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
      <DashboardContent />
    </div>
  );
}
