import type { Metadata } from "next";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { SearchFilters } from "@/components/search/SearchFilters";
import { ProductCard, ProductCardSkeleton } from "@/components/product/ProductCard";
import { searchApi } from "@/lib/api/search";

interface SearchPageProps {
  searchParams: Promise<{ q?: string; cursor?: string; sortBy?: string }>;
}

export function generateMetadata({ searchParams }: SearchPageProps): Metadata {
  return { title: "Search Results" };
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;
  const query = params.q ?? "";

  // TODO Sprint 1 Week 3: replace with live search call
  const results = query
    ? await searchApi.search(query, { sortBy: (params.sortBy as never) ?? "relevance" })
    : null;

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-6">
        <h1 className="text-xl font-bold mb-1">
          {query ? `Results for "${query}"` : "Search products"}
        </h1>

        {results?.success && (
          <p className="text-sm text-muted-foreground mb-6">
            {results.data.data.length} products found
          </p>
        )}

        <div className="flex gap-8">
          {/* Filters sidebar */}
          <div className="hidden md:block w-56 shrink-0">
            <SearchFilters onFilterChange={() => {}} />
          </div>

          {/* Results grid */}
          <div className="flex-1 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {results?.success
              ? results.data.data.map((p) => <ProductCard key={p.id} product={p} />)
              : Array.from({ length: 8 }).map((_, i) => <ProductCardSkeleton key={i} />)}
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
