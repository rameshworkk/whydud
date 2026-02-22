import type { Metadata } from "next";

export const metadata: Metadata = { title: "Refund Tracker" };

export default async function RefundsPage() {
  // TODO Sprint 4 Week 11
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Refund Tracker</h1>
      <div className="rounded-2xl border border-dashed p-12 text-center text-muted-foreground">
        <p>Refund tracking launches in Sprint 4 (Week 11).</p>
        <p className="mt-1 text-sm">Refund delays will be auto-detected from your inbox.</p>
      </div>
    </div>
  );
}
