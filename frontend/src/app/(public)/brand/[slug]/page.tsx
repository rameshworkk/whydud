import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { BrandTrustGauge } from "@/components/product/brand-trust-gauge";
import { brandsApi } from "@/lib/api/brands";
import { formatPrice } from "@/lib/utils";
import { config } from "@/config";
import { ShieldCheck, Package, ArrowRight, Star } from "lucide-react";
import type { BrandTrustScore, ProductSummary } from "@/types";

// ── Helpers ──────────────────────────────────────────────────────────────────

function getDudScoreColor(score: number | null): string {
  if (score == null) return "#6B7280";
  if (score >= 80) return "#16A34A";
  if (score >= 65) return "#65A30D";
  if (score >= 50) return "#CA8A04";
  if (score >= 35) return "#EA580C";
  return "#DC2626";
}

// ── Data fetching ────────────────────────────────────────────────────────────

async function fetchBrandData(slug: string) {
  const [trustRes, productsRes] = await Promise.all([
    brandsApi.getTrustScore(slug),
    brandsApi.getProducts(slug),
  ]);

  const trustScore: BrandTrustScore | null = trustRes.success ? trustRes.data : null;
  const products: ProductSummary[] = productsRes.success ? productsRes.data : [];

  return { trustScore, products };
}

// ── Metadata ─────────────────────────────────────────────────────────────────

interface BrandPageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: BrandPageProps): Promise<Metadata> {
  const { slug } = await params;
  const { trustScore } = await fetchBrandData(slug);

  if (!trustScore) {
    return { title: "Brand Not Found — Whydud" };
  }

  const title = `${trustScore.brandName} Brand Trust Score — ${Math.round(trustScore.avgDudScore)}/100 | Whydud`;
  const description = `${trustScore.brandName} has a brand trust score of ${Math.round(trustScore.avgDudScore)}/100 (${trustScore.trustTier}) based on ${trustScore.productCount} products analyzed on Whydud.`;

  return {
    title,
    description,
    alternates: { canonical: `${config.siteUrl}/brand/${slug}` },
    openGraph: {
      title,
      description,
      type: "website",
      url: `${config.siteUrl}/brand/${slug}`,
      siteName: config.siteName,
    },
  };
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default async function BrandPage({ params }: BrandPageProps) {
  const { slug } = await params;
  const { trustScore, products } = await fetchBrandData(slug);

  if (!trustScore) {
    notFound();
  }

  return (
    <>
      <Header />
      <main className="min-h-[calc(100vh-64px)] bg-[#F8FAFC]">
        <div className="max-w-site mx-auto px-4 md:px-6 lg:px-12 py-8">
          {/* Breadcrumb */}
          <nav className="flex items-center gap-1.5 text-xs text-[#64748B] mb-6">
            <Link href="/" className="hover:text-[#F97316] transition-colors">
              Home
            </Link>
            <span>/</span>
            <Link href="/leaderboard" className="hover:text-[#F97316] transition-colors">
              Brands
            </Link>
            <span>/</span>
            <span className="text-[#1E293B] font-medium">{trustScore.brandName}</span>
          </nav>

          {/* Brand Header */}
          <div className="flex items-center gap-4 mb-8">
            {trustScore.brandLogoUrl ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={trustScore.brandLogoUrl}
                alt={trustScore.brandName}
                className="w-16 h-16 rounded-xl object-contain bg-white border border-slate-200 p-2"
              />
            ) : (
              <div className="w-16 h-16 rounded-xl bg-[#4DB6AC]/10 border border-[#4DB6AC]/20 flex items-center justify-center">
                <Package className="w-8 h-8 text-[#4DB6AC]" />
              </div>
            )}
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-[#1E293B]">{trustScore.brandName}</h1>
                {trustScore.brandVerified && (
                  <ShieldCheck className="w-5 h-5 text-[#4DB6AC]" />
                )}
              </div>
              <p className="text-sm text-[#64748B]">
                {trustScore.productCount} products analyzed
              </p>
            </div>
          </div>

          {/* Two-column layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Trust Score Gauge */}
            <div className="lg:col-span-1">
              <BrandTrustGauge score={trustScore} />
            </div>

            {/* Right: Product Grid */}
            <div className="lg:col-span-2">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-[#1E293B]">
                  Products by {trustScore.brandName}
                </h2>
              </div>

              {products.length === 0 ? (
                <div className="bg-white rounded-lg border border-slate-200 p-8 text-center text-[#64748B]">
                  No products found for this brand yet.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                  {products.map((product) => (
                    <Link
                      key={product.id}
                      href={`/product/${product.slug}`}
                      className="bg-white rounded-lg border border-slate-200 shadow-sm hover:shadow-md transition-shadow p-4 flex flex-col"
                    >
                      {/* Product image */}
                      <div className="relative aspect-square w-full rounded-lg overflow-hidden bg-slate-50 mb-3">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={product.images?.[0] ?? "https://placehold.co/200x200/e8f4fd/1e40af?text=No+Image"}
                          alt={product.title}
                          className="object-contain p-2 w-full h-full"
                        />
                      </div>

                      {/* Title */}
                      <h3 className="text-sm font-medium text-[#1E293B] line-clamp-2 mb-2">
                        {product.title}
                      </h3>

                      {/* Rating */}
                      {product.avgRating != null && (
                        <div className="flex items-center gap-1 mb-2">
                          <Star className="w-3.5 h-3.5 fill-[#FBBF24] text-[#FBBF24]" />
                          <span className="text-xs font-medium text-[#1E293B]">
                            {product.avgRating.toFixed(1)}
                          </span>
                          <span className="text-xs text-[#64748B]">
                            ({product.totalReviews})
                          </span>
                        </div>
                      )}

                      {/* Price + DudScore */}
                      <div className="mt-auto flex items-center justify-between">
                        <span className="text-sm font-bold text-[#1E293B]">
                          {formatPrice(product.currentBestPrice)}
                        </span>
                        {product.dudScore != null && (
                          <span
                            className="text-xs font-semibold px-1.5 py-0.5 rounded"
                            style={{
                              color: getDudScoreColor(product.dudScore),
                              backgroundColor: `${getDudScoreColor(product.dudScore)}15`,
                            }}
                          >
                            {Math.round(product.dudScore)}
                          </span>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              )}

              {products.length > 0 && (
                <div className="mt-4 text-center">
                  <Link
                    href={`/search?brand=${slug}`}
                    className="inline-flex items-center gap-1 text-sm text-[#F97316] hover:text-[#EA580C] font-medium transition-colors"
                  >
                    View all {trustScore.brandName} products
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
