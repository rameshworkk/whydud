import type { Metadata } from "next";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { ProductCard } from "@/components/product/ProductCard";
import { searchApi } from "@/lib/api/search";

interface CategoryPageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: CategoryPageProps): Promise<Metadata> {
  const { slug } = await params;
  return { title: `${slug} — Products` };
}

export default async function CategoryPage({ params }: CategoryPageProps) {
  const { slug } = await params;
  const res = await searchApi.search("", { category: slug }).catch(() => null);
  const products = res?.success ? res.data.data : [];

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8">
        <h1 className="text-2xl font-bold capitalize mb-6">{slug.replace(/-/g, " ")}</h1>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
