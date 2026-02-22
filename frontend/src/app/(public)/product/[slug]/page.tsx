import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { DudScoreDisplay } from "@/components/product/DudScoreDisplay";
import { PriceHistory } from "@/components/product/PriceHistory";
import { ReviewCard, ReviewCardSkeleton } from "@/components/product/ReviewCard";
import { TCOCalculator } from "@/components/tco/TCOCalculator";
import { productsApi } from "@/lib/api/products";
import { formatPrice } from "@/lib/utils";

interface ProductPageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: ProductPageProps): Promise<Metadata> {
  const { slug } = await params;
  const res = await productsApi.getDetail(slug);
  if (!res.success) return { title: "Product Not Found" };
  return {
    title: res.data.title,
    description: `DudScore ${res.data.dudScore ?? "—"} · ${res.data.brand.name} · from ${formatPrice(res.data.currentBestPrice)}`,
    openGraph: {
      images: res.data.images?.[0] ? [res.data.images[0]] : [],
    },
  };
}

export default async function ProductPage({ params }: ProductPageProps) {
  const { slug } = await params;

  // TODO Sprint 1 Week 3: implement productsApi.getDetail
  const productRes = await productsApi.getDetail(slug).catch(() => null);
  if (!productRes?.success) notFound();

  const product = productRes.data;

  // Fetch price history and reviews in parallel
  const [priceHistoryRes, reviewsRes] = await Promise.allSettled([
    productsApi.getPriceHistory(slug),
    productsApi.getReviews(slug),
  ]);

  const priceHistory =
    priceHistoryRes.status === "fulfilled" && priceHistoryRes.value.success
      ? priceHistoryRes.value.data
      : [];

  const reviews =
    reviewsRes.status === "fulfilled" && reviewsRes.value.success
      ? reviewsRes.value.data
      : [];

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-6">
        {/* Hero: image + title + DudScore + top prices */}
        <div className="grid lg:grid-cols-[1fr_380px] gap-8 mb-12">
          {/* Left: image + info */}
          <div className="flex flex-col gap-6">
            {/* TODO Sprint 1 Week 3: ProductHero with image gallery */}
            <div className="aspect-square max-h-96 w-full rounded-2xl bg-muted flex items-center justify-center text-muted-foreground">
              Product image gallery
            </div>

            <div>
              <p className="text-sm text-muted-foreground">{product.brand.name}</p>
              <h1 className="mt-1 text-2xl font-bold leading-snug">{product.title}</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                {product.category.name}
              </p>
            </div>
          </div>

          {/* Right: pricing panel */}
          <div className="flex flex-col gap-4">
            {/* DudScore */}
            <div className="rounded-2xl border bg-card p-6 flex items-center gap-6">
              <DudScoreDisplay
                score={product.dudScore}
                confidence={product.dudScoreConfidence}
                size="lg"
              />
              <div className="text-sm text-muted-foreground">
                <p>Based on {product.totalReviews.toLocaleString("en-IN")} reviews</p>
                <p className="mt-0.5">Avg rating ★ {product.avgRating?.toFixed(1) ?? "—"}</p>
              </div>
            </div>

            {/* Best price */}
            <div className="rounded-2xl border bg-card p-6">
              <p className="text-sm text-muted-foreground">Best price</p>
              <p className="mt-1 text-3xl font-black">{formatPrice(product.currentBestPrice)}</p>
              <p className="text-sm text-muted-foreground">on {product.currentBestMarketplace}</p>

              {product.lowestPriceEver != null && (
                <p className="mt-2 text-xs text-muted-foreground">
                  Lowest ever: {formatPrice(product.lowestPriceEver)}
                </p>
              )}

              {/* TODO Sprint 3: PersonalizedDealCard, EMI options */}
              <button className="mt-4 w-full rounded-xl bg-primary py-2.5 font-semibold text-primary-foreground">
                View on {product.currentBestMarketplace}
              </button>
            </div>

            {/* Marketplace prices */}
            <div className="rounded-2xl border bg-card p-4">
              <p className="text-sm font-semibold mb-3">All Prices</p>
              <div className="flex flex-col gap-2">
                {product.listings.map((listing) => (
                  <div key={listing.id} className="flex items-center justify-between text-sm">
                    <span>{listing.marketplace.name}</span>
                    <div className="flex items-center gap-2">
                      {!listing.inStock && (
                        <span className="text-xs text-muted-foreground">Out of stock</span>
                      )}
                      <span className="font-semibold">{formatPrice(listing.currentPrice)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Price History */}
        <section className="mb-10">
          <h2 className="text-xl font-bold mb-4">Price History</h2>
          <PriceHistory data={priceHistory} />
        </section>

        {/* Specs */}
        {product.specs && (
          <section className="mb-10">
            <h2 className="text-xl font-bold mb-4">Specifications</h2>
            <div className="rounded-xl border overflow-hidden">
              <table className="w-full text-sm">
                <tbody>
                  {Object.entries(product.specs).map(([key, val], i) => (
                    <tr key={key} className={i % 2 === 0 ? "bg-muted/50" : ""}>
                      <td className="px-4 py-2 font-medium text-muted-foreground w-1/3">{key}</td>
                      <td className="px-4 py-2">{String(val)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* TCO (if category supports it) */}
        {product.category.hasTcoModel && (
          <section className="mb-10">
            <TCOCalculator productSlug={slug} categorySlug={product.category.slug} />
          </section>
        )}

        {/* Reviews */}
        <section className="mb-10">
          <h2 className="text-xl font-bold mb-4">
            Reviews ({product.totalReviews.toLocaleString("en-IN")})
          </h2>
          <div className="flex flex-col gap-4">
            {reviews.length > 0
              ? reviews.map((r) => <ReviewCard key={r.id} review={r} />)
              : Array.from({ length: 3 }).map((_, i) => <ReviewCardSkeleton key={i} />)}
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
