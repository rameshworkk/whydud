import type { Metadata } from "next";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { ProductCard } from "@/components/product/product-card";
import { searchApi } from "@/lib/api/search";
import { productsApi } from "@/lib/api/products";
import type { ProductSummary } from "@/types";

interface SearchPageProps {
  searchParams: Promise<{ q?: string; category?: string; sortBy?: string; offset?: string }>;
}

export function generateMetadata(): Metadata {
  return { title: "Search Results — Whydud" };
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;
  const query = params.q ?? "";
  const category = params.category;
  const sortBy = params.sortBy as
    | "relevance"
    | "dudscore"
    | "price_asc"
    | "price_desc"
    | "newest"
    | undefined;
  const offset = params.offset ? parseInt(params.offset, 10) : undefined;

  let products: ProductSummary[] = [];

  // Try Meilisearch-backed search first, fallback to products list
  if (query) {
    try {
      const searchRes = await searchApi.search(query, { category, sortBy, offset });
      if (searchRes.success && "data" in searchRes) {
        const data = searchRes.data;
        // SearchResponse has a .results array; plain array fallback
        if (data && typeof data === "object" && "results" in data && Array.isArray(data.results)) {
          products = data.results;
        } else if (Array.isArray(data)) {
          products = data as unknown as ProductSummary[];
        }
      }
    } catch {
      // Meilisearch may not be synced — fall through to fallback
    }
  }

  // Fallback: list products from Django API
  if (products.length === 0) {
    try {
      const listRes = await productsApi.list({ category });
      if (listRes.success && "data" in listRes) {
        const data = listRes.data;
        if (Array.isArray(data)) {
          products = data;
        }
      }
    } catch {
      // API unreachable — render empty state
    }
  }

  return (
    <>
      <Header />
      <main className="mx-auto max-w-[1280px] px-4 py-6">
        {/* Results header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-lg font-bold text-slate-900">
              {query ? (
                <>
                  Results for <span className="text-slate-700">{query}</span>
                </>
              ) : (
                "All Products"
              )}
            </h1>
            <p className="text-sm text-slate-500 mt-0.5">
              {products.length} {products.length === 1 ? "product" : "products"} found
            </p>
          </div>
          <div className="flex items-center gap-4">
            {/* Sort dropdown */}
            <div className="flex items-center gap-2 text-sm">
              <span className="text-slate-500">Sort by:</span>
              <select className="border border-slate-200 rounded-md px-2 py-1 text-sm text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-[#F97316]">
                <option>Relevance</option>
                <option>Price: Low to High</option>
                <option>Price: High to Low</option>
                <option>Rating</option>
                <option>DudScore</option>
              </select>
            </div>
            {/* Results only toggle */}
            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                className="rounded border-slate-300 text-[#F97316] focus:ring-[#F97316]"
              />
              Results only
            </label>
          </div>
        </div>

        {/* Product grid */}
        {products.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {products.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <p className="text-lg font-semibold text-slate-700">No products found</p>
            <p className="text-sm text-slate-500 mt-1">
              {query
                ? `We couldn't find any products matching "${query}". Try a different search term.`
                : "No products are available at the moment."}
            </p>
          </div>
        )}
      </main>
      <Footer />
    </>
  );
}
