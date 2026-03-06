import type { Metadata } from "next";
import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { categoriesApi } from "@/lib/api/products";
import type { Department } from "@/types";

export const metadata: Metadata = {
  title: "Browse Categories — Whydud",
  description: "Browse products by category across all Indian marketplaces",
};

export default async function CategoriesPage() {
  const res = await categoriesApi.getTree().catch(() => null);
  const departments: Department[] =
    res && "data" in res ? (res.data as Department[]) : [];

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-8">
          Browse Categories
        </h1>

        <div className="space-y-10">
          {departments.map((dept) => (
            <section key={dept.slug}>
              <div className="flex items-center gap-2 mb-4">
                <h2 className="text-lg font-semibold text-slate-800">
                  {dept.name}
                </h2>
                {dept.productCount > 0 && (
                  <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                    {dept.productCount.toLocaleString("en-IN")} products
                  </span>
                )}
              </div>

              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {dept.categories.map((cat) => (
                  <div
                    key={cat.slug}
                    className="bg-white rounded-lg border border-slate-200 shadow-sm p-4"
                  >
                    <h3 className="font-medium text-slate-900 mb-3">
                      {cat.name}
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {cat.subcategories.map((sub) => (
                        <Link
                          key={sub.slug}
                          href={`/categories/${sub.slug}`}
                          className="text-sm text-slate-600 hover:text-orange-600 hover:bg-orange-50 px-2 py-1 rounded transition-colors"
                        >
                          {sub.name}
                          {sub.productCount > 0 && (
                            <span className="ml-1 text-xs text-slate-400">
                              ({sub.productCount})
                            </span>
                          )}
                        </Link>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>

        {departments.length === 0 && (
          <p className="text-slate-500 text-center py-12">
            No categories available yet.
          </p>
        )}
      </main>
      <Footer />
    </>
  );
}
