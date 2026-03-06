import type { Metadata } from "next";
import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { ProductCard } from "@/components/product/ProductCard";
import { categoriesApi } from "@/lib/api/products";
import { searchApi } from "@/lib/api/search";
import type { Category } from "@/types";

interface CategoryPageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({
  params,
}: CategoryPageProps): Promise<Metadata> {
  const { slug } = await params;
  const res = await categoriesApi.getDetail(slug).catch(() => null);
  const cat = res && "data" in res ? (res.data as Category) : null;
  const name = cat?.name ?? slug.replace(/-/g, " ");
  return {
    title: `${name} — Whydud`,
    description: cat?.description || `Browse ${name} products on Whydud`,
  };
}

export default async function CategoryPage({ params }: CategoryPageProps) {
  const { slug } = await params;

  // Fetch category detail and products in parallel
  const [catRes, searchRes] = await Promise.all([
    categoriesApi.getDetail(slug).catch(() => null),
    searchApi.search("", { category: slug }).catch(() => null),
  ]);

  const category =
    catRes && "data" in catRes ? (catRes.data as Category) : null;
  const searchData = searchRes?.success ? searchRes.data : null;
  const products =
    searchData && "results" in searchData ? searchData.results : [];

  // If it's a department or mid-level category, fetch its children
  const childrenRes =
    category && category.level < 2
      ? await categoriesApi.list({ parent: slug }).catch(() => null)
      : null;
  const children =
    childrenRes && "data" in childrenRes
      ? (childrenRes.data as Category[])
      : [];

  const breadcrumb = category?.breadcrumb ?? [
    { slug, name: slug.replace(/-/g, " ") },
  ];

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8">
        {/* Breadcrumb navigation */}
        <nav className="flex items-center gap-1.5 text-sm text-slate-500 mb-6">
          <Link href="/" className="hover:text-orange-600 transition-colors">
            Home
          </Link>
          <span>/</span>
          <Link
            href="/categories"
            className="hover:text-orange-600 transition-colors"
          >
            Categories
          </Link>
          {breadcrumb.map((item, i) => (
            <span key={item.slug} className="flex items-center gap-1.5">
              <span>/</span>
              {i === breadcrumb.length - 1 ? (
                <span className="text-slate-900 font-medium">{item.name}</span>
              ) : (
                <Link
                  href={`/categories/${item.slug}`}
                  className="hover:text-orange-600 transition-colors"
                >
                  {item.name}
                </Link>
              )}
            </span>
          ))}
        </nav>

        <div className="flex items-center gap-3 mb-6">
          <h1 className="text-2xl font-bold text-slate-900">
            {category?.name ?? slug.replace(/-/g, " ")}
          </h1>
          {category && category.productCount > 0 && (
            <span className="text-sm text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-full">
              {category.productCount.toLocaleString("en-IN")} products
            </span>
          )}
        </div>

        {category?.description && (
          <p className="text-slate-600 mb-6 max-w-2xl">
            {category.description}
          </p>
        )}

        {/* If visiting a department or category, show children as cards */}
        {children.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 mb-10">
            {children.map((child) => (
              <Link
                key={child.slug}
                href={`/categories/${child.slug}`}
                className="bg-white rounded-lg border border-slate-200 shadow-sm p-4 hover:shadow-md transition-shadow"
              >
                <h3 className="font-medium text-slate-900 text-sm">
                  {child.name}
                </h3>
                {child.productCount > 0 && (
                  <p className="text-xs text-slate-500 mt-1">
                    {child.productCount.toLocaleString("en-IN")} products
                  </p>
                )}
              </Link>
            ))}
          </div>
        )}

        {/* Product grid */}
        {products.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {products.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        )}

        {products.length === 0 && children.length === 0 && (
          <p className="text-slate-500 text-center py-12">
            No products found in this category.
          </p>
        )}
      </main>
      <Footer />
    </>
  );
}
