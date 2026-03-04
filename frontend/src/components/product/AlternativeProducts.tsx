import { productsApi } from "@/lib/api/products";
import { ProductCard } from "@/components/product/product-card";

interface AlternativeProductsProps {
  slug: string;
}

/** Horizontal scroll section of alternative products (different brand, same category + ±20% price). */
export async function AlternativeProducts({ slug }: AlternativeProductsProps) {
  const res = await productsApi.getAlternatives(slug);
  const products = res.success ? res.data : [];

  if (products.length === 0) return null;

  return (
    <section className="mt-5">
      <h2 className="text-sm font-semibold text-slate-700 mb-3">People Also Considered</h2>
      <div className="flex gap-3 overflow-x-auto pb-1 snap-x snap-mandatory no-scrollbar">
        {products.map((product) => (
          <div key={product.id} className="snap-start shrink-0 w-[180px] md:w-[200px]">
            <ProductCard product={product} />
          </div>
        ))}
      </div>
    </section>
  );
}
