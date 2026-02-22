import type { Metadata } from "next";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export const metadata: Metadata = { title: "Compare Products" };

interface ComparePageProps {
  searchParams: Promise<{ slugs?: string }>;
}

export default async function ComparePage({ searchParams }: ComparePageProps) {
  const { slugs } = await searchParams;
  const slugList = slugs?.split(",").filter(Boolean) ?? [];

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8">
        <h1 className="text-2xl font-bold mb-2">Compare Products</h1>
        <p className="text-sm text-muted-foreground mb-6">Compare up to 4 products side-by-side.</p>

        {slugList.length === 0 ? (
          <div className="rounded-2xl border border-dashed p-16 text-center text-muted-foreground">
            <p>Search for products and click &quot;Add to Compare&quot; to get started.</p>
          </div>
        ) : (
          // TODO Sprint 4 Week 10: Full comparison table
          <p className="text-muted-foreground">Comparison for: {slugList.join(", ")}</p>
        )}
      </main>
      <Footer />
    </>
  );
}
