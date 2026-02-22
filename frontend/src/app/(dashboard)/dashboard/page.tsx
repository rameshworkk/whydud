import type { Metadata } from "next";
import { SpendOverview } from "@/components/dashboard/SpendOverview";
import { purchasesApi } from "@/lib/api/inbox";

export const metadata: Metadata = { title: "Purchase Dashboard" };

export default async function DashboardPage() {
  // TODO Sprint 3 Week 8: implement purchasesApi.getDashboard
  const dashRes = await purchasesApi.getDashboard().catch(() => null);
  const dashboard = dashRes?.success ? dashRes.data : null;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Purchase Dashboard</h1>

      <SpendOverview lifetimeTotal={null} isLoading={!dashboard} />

      {/* TODO Sprint 3 Week 8: CategoryBreakdown, MarketplaceBreakdown, AlertsPanel, RecentOrders */}
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="h-48 rounded-xl bg-muted animate-pulse" />
        <div className="h-48 rounded-xl bg-muted animate-pulse" />
      </div>

      <div className="rounded-xl border bg-card p-6 text-sm text-muted-foreground">
        Connect your @whyd.xyz email to start tracking purchases automatically.
      </div>
    </div>
  );
}
