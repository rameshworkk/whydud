import type { Metadata } from "next";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { DealCard } from "@/components/deals/DealCard";
import { dealsApi } from "@/lib/api/products";

export const metadata: Metadata = { title: "Blockbuster Deals" };

export default async function DealsPage() {
  // TODO Sprint 4 Week 10: live deals
  const res = await dealsApi.list().catch(() => null);
  const deals = res?.success ? res.data : [];

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8">
        <h1 className="text-3xl font-black mb-1">Blockbuster Deals</h1>
        <p className="text-muted-foreground mb-6">
          Error pricing, lowest-ever prices, and verified genuine discounts.
        </p>

        {/* Filters — TODO Sprint 4 */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {["All", "Error Price", "Lowest Ever", "Genuine Discount"].map((f) => (
            <button
              key={f}
              className="rounded-full border px-4 py-1.5 text-sm hover:bg-muted first:bg-primary first:text-primary-foreground"
            >
              {f}
            </button>
          ))}
        </div>

        {deals.length > 0 ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {deals.map((deal) => (
              <DealCard key={deal.id} deal={deal} />
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed p-16 text-center text-muted-foreground">
            <p>Deal detection launching in Sprint 4 (Week 10).</p>
          </div>
        )}
      </main>
      <Footer />
    </>
  );
}
