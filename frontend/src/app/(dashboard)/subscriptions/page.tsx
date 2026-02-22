import type { Metadata } from "next";

export const metadata: Metadata = { title: "Subscription Tracker" };

export default async function SubscriptionsPage() {
  // TODO Sprint 4 Week 11
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Subscriptions</h1>
      <div className="rounded-2xl border border-dashed p-12 text-center text-muted-foreground">
        <p>Subscription detection launches in Sprint 4 (Week 11).</p>
        <p className="mt-1 text-sm">Auto-renew subscriptions are detected from your inbox emails.</p>
      </div>
    </div>
  );
}
