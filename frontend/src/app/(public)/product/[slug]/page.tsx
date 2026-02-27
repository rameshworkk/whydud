import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { DudScoreGauge } from "@/components/product/dud-score-gauge";
import { CrossPlatformPricePanel } from "@/components/product/cross-platform-price-panel";
import { CategoryScoreBars } from "@/components/product/category-score-bars";
import { PriceChart } from "@/components/product/price-chart";
import { ReviewSidebar } from "@/components/reviews/review-sidebar";
import { ProductCard } from "@/components/product/product-card";
import { ShareButton } from "@/components/product/share-button";
import { RecentlyViewedTracker } from "@/components/product/recently-viewed-tracker";
import { productsApi } from "@/lib/api/products";
import { formatPrice } from "@/lib/utils";
import { config } from "@/config";
import {
  Cpu,
  HardDrive,
  Camera,
  Battery,
  Smartphone,
  Monitor,
  Wifi,
  Weight,
  MemoryStick,
  Info,
} from "lucide-react";
import type { ProductDetail, ProductSummary, PricePoint, Review, DudScoreLabel } from "@/types";
import type { LucideIcon } from "lucide-react";

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Map spec labels to Lucide icons for the Key Specs sidebar. */
const SPEC_ICON_MAP: Record<string, LucideIcon> = {
  model: Cpu,
  processor: Cpu,
  chipset: Cpu,
  soc: Cpu,
  ram: MemoryStick,
  memory: MemoryStick,
  storage: HardDrive,
  "internal storage": HardDrive,
  rom: HardDrive,
  camera: Camera,
  "rear camera": Camera,
  "front camera": Camera,
  battery: Battery,
  "battery capacity": Battery,
  os: Smartphone,
  "operating system": Smartphone,
  android: Smartphone,
  software: Smartphone,
  display: Monitor,
  screen: Monitor,
  "screen size": Monitor,
  resolution: Monitor,
  weight: Weight,
  connectivity: Wifi,
  network: Wifi,
  "5g": Wifi,
  sim: Smartphone,
  "sim type": Smartphone,
};

function getSpecIcon(label: string): LucideIcon {
  const key = label.toLowerCase().trim();
  if (SPEC_ICON_MAP[key]) return SPEC_ICON_MAP[key];
  for (const [mapKey, icon] of Object.entries(SPEC_ICON_MAP)) {
    if (key.includes(mapKey)) return icon;
  }
  return Info;
}

/** Derive a human-readable DudScore label from the numeric score. */
function getDudScoreLabel(score: number | null): DudScoreLabel {
  if (score == null) return "Not Rated";
  if (score >= 80) return "Excellent";
  if (score >= 65) return "Good";
  if (score >= 50) return "Average";
  if (score >= 35) return "Below Average";
  return "Dud";
}

/** Build placeholder DudScore component bars when the API doesn't return them. */
function makePlaceholderComponents(score: number | null) {
  const base = score ?? 50;
  return [
    { label: "Sentiment", value: Math.min(100, Math.round(base * 0.95)), color: "bg-teal" },
    { label: "Rating Quality", value: Math.min(100, Math.round(base * 1.05)), color: "bg-teal" },
    { label: "Price Value", value: Math.min(100, Math.round(base * 0.98)), color: "bg-teal" },
    { label: "Review Credibility", value: Math.min(100, Math.round(base * 1.08)), color: "bg-teal" },
    { label: "Price Stability", value: Math.min(100, Math.round(base * 0.92)), color: "bg-teal" },
    { label: "Return Signal", value: Math.min(100, Math.round(base)), color: "bg-teal" },
  ];
}

/** Convert specs Record to the {label, value}[] shape used by the template. */
function specsToList(specs: Record<string, string | number | boolean> | null): { label: string; value: string }[] {
  if (!specs) return [];
  return Object.entries(specs).map(([label, value]) => ({ label, value: String(value) }));
}

/** Build the marketplace color map for the price chart from listings. */
const MARKETPLACE_CHART_COLORS: Record<string, string> = {
  amazon_in: "#FF9900",
  flipkart: "#2874F0",
  croma: "#E31837",
  myntra: "#FF3F6C",
  meesho: "#9B2335",
  reliance_digital: "#3366CC",
};

/** Find the listing that has the best (lowest) price to get the MRP. */
function getBestListing(p: ProductDetail) {
  if (p.listings.length === 0) return null;
  const sorted = [...p.listings]
    .filter((l) => l.currentPrice !== null && l.inStock)
    .sort((a, b) => (a.currentPrice ?? Infinity) - (b.currentPrice ?? Infinity));
  return sorted[0] ?? p.listings[0] ?? null;
}

/** Convert API ratingDistribution (Record<string,number> with raw counts) to percentages keyed 1-5. */
function normalizeRatingDistribution(
  dist: Record<string, number>,
  totalReviews: number
): Record<1 | 2 | 3 | 4 | 5, number> {
  const result: Record<1 | 2 | 3 | 4 | 5, number> = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
  for (const [key, count] of Object.entries(dist)) {
    const star = Number(key) as 1 | 2 | 3 | 4 | 5;
    if (star >= 1 && star <= 5) {
      result[star] = totalReviews > 0 ? Math.round((count / totalReviews) * 100) : 0;
    }
  }
  return result;
}

// ── Data fetching ────────────────────────────────────────────────────────────

async function fetchProductData(slug: string) {
  const [detailRes, priceRes, reviewsRes, similarRes, alternativesRes] = await Promise.all([
    productsApi.getDetail(slug),
    productsApi.getPriceHistory(slug),
    productsApi.getReviews(slug),
    productsApi.getSimilar(slug),
    productsApi.getAlternatives(slug),
  ]);

  const product: ProductDetail | null = detailRes.success ? detailRes.data : null;
  const priceHistory: PricePoint[] = priceRes.success ? priceRes.data : [];
  const reviews: Review[] = reviewsRes.success ? reviewsRes.data : [];
  const similarProducts: ProductSummary[] = similarRes.success ? similarRes.data : [];
  const alternatives: ProductSummary[] = alternativesRes.success ? alternativesRes.data : [];

  return { product, priceHistory, reviews, similarProducts, alternatives };
}

// ── Metadata ─────────────────────────────────────────────────────────────────

interface ProductPageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: ProductPageProps): Promise<Metadata> {
  const { slug } = await params;
  const [detailRes, shareRes] = await Promise.all([
    productsApi.getDetail(slug),
    productsApi.getShareData(slug),
  ]);

  if (!detailRes.success) {
    return { title: "Product Not Found — Whydud" };
  }

  const p = detailRes.data;
  const share = shareRes.success ? shareRes.data : null;
  const fallbackDesc = `DudScore ${p.dudScore ?? "N/A"} · Best price ${formatPrice(p.currentBestPrice)} on ${p.currentBestMarketplace}`;
  const ogTitle = share?.ogTitle ?? p.title;
  const ogDescription = share?.ogDescription ?? fallbackDesc;
  const ogImage = share?.ogImage ?? p.images?.[0];
  const productUrl = share?.url ?? `${config.siteUrl}/product/${slug}`;

  return {
    title: `${p.title} — Whydud`,
    description: fallbackDesc,
    openGraph: {
      title: ogTitle,
      description: ogDescription,
      url: productUrl,
      siteName: "Whydud",
      type: "website",
      ...(ogImage && { images: [{ url: ogImage, alt: p.title }] }),
    },
    twitter: {
      card: ogImage ? "summary_large_image" : "summary",
      title: ogTitle,
      description: ogDescription,
      ...(ogImage && { images: [ogImage] }),
    },
  };
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default async function ProductPage({ params }: ProductPageProps) {
  const { slug } = await params;
  const { product: p, priceHistory, reviews, similarProducts, alternatives } = await fetchProductData(slug);

  if (!p) {
    notFound();
  }

  const bestListing = getBestListing(p);
  const mrp = bestListing?.mrp ?? null;
  const discountPct =
    mrp && p.currentBestPrice
      ? Math.round(((mrp - p.currentBestPrice) / mrp) * 100)
      : 0;

  const specs = specsToList(p.specs);
  const breadcrumb = ["Home", p.category.name, p.brand.name, p.title];
  const mainImage = p.images?.[0] ?? "https://placehold.co/400x500/e8f4fd/1e40af?text=No+Image";
  const dudScoreLabel = getDudScoreLabel(p.dudScore);
  const dudScoreComponents = makePlaceholderComponents(p.dudScore);

  const ratingDistribution = normalizeRatingDistribution(
    p.reviewSummary.ratingDistribution,
    p.reviewSummary.totalReviews
  );

  // Build marketplace map for the price chart from the listings
  const marketplaceChartMap: Record<number, { name: string; color: string }> = {};
  for (const listing of p.listings) {
    if (!marketplaceChartMap[listing.marketplace.id]) {
      marketplaceChartMap[listing.marketplace.id] = {
        name: listing.marketplace.name,
        color: MARKETPLACE_CHART_COLORS[listing.marketplace.slug] ?? "#6B7280",
      };
    }
  }

  return (
    <>
      <Header />
      <RecentlyViewedTracker slug={slug} />

      {/* Three-column dashboard — each column scrolls independently */}
      <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-[#F8FAFC]">

        {/* -- Left Sidebar: Product image + Key Specs -- */}
        <aside className="w-[260px] shrink-0 overflow-y-auto no-scrollbar border-r border-slate-200 bg-white flex flex-col">
          {/* Product image */}
          <div className="p-4 border-b border-slate-100">
            <div className="relative aspect-square w-full rounded-xl overflow-hidden bg-slate-50 border border-slate-100 flex items-center justify-center">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={mainImage}
                alt={p.title}
                className="object-contain p-4 w-full h-full"
              />
            </div>
            {/* Thumbnail strip */}
            {p.images && p.images.length > 1 && (
              <div className="flex gap-2 mt-3">
                {p.images.slice(0, 4).map((img, i) => (
                  <div
                    key={i}
                    className={`w-14 h-14 rounded-lg border-2 overflow-hidden cursor-pointer ${
                      i === 0 ? "border-[#F97316]" : "border-slate-200"
                    }`}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={img}
                      alt={`View ${i + 1}`}
                      className="object-contain p-1 w-full h-full"
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Key Specs */}
          <div className="p-4 flex flex-col gap-0.5 flex-1">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">
              Key Specs
            </h3>
            {specs.length > 0 ? (
              specs.map((spec) => {
                const IconComp = getSpecIcon(spec.label);
                return (
                  <div
                    key={spec.label}
                    className="flex items-center gap-2.5 py-2 border-b border-slate-50 last:border-b-0"
                  >
                    <IconComp className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="text-xs text-slate-500 shrink-0 w-[80px]">{spec.label}</span>
                    <span className="text-xs font-medium text-slate-800 text-right leading-snug flex-1">
                      {spec.value}
                    </span>
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-slate-400">No specifications available.</p>
            )}
            {specs.length > 0 && (
              <button className="mt-3 text-xs font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
                View all specifications →
              </button>
            )}
          </div>
        </aside>

        {/* -- Center: Title, price, DudScore, marketplace prices, chart -- */}
        <main className="flex-1 overflow-y-auto no-scrollbar px-6 py-5">
          {/* Breadcrumb */}
          <nav className="flex items-center gap-1.5 text-xs text-slate-400 mb-4 flex-wrap">
            {breadcrumb.map((crumb, i) => (
              <span key={`${crumb}-${i}`} className="flex items-center gap-1.5">
                {i > 0 && <span>›</span>}
                {i < breadcrumb.length - 1 ? (
                  <Link href="/" className="hover:text-[#F97316] transition-colors">
                    {crumb}
                  </Link>
                ) : (
                  <span className="text-slate-600 font-medium">{crumb}</span>
                )}
              </span>
            ))}
          </nav>

          {/* Brand + category + share */}
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              {p.brand.name} · {p.category.name}
            </p>
            <ShareButton
              url={`${config.siteUrl}/product/${p.slug}`}
              title={p.title}
              description={`DudScore ${p.dudScore ?? "N/A"} · Best price ${formatPrice(p.currentBestPrice)} on ${p.currentBestMarketplace}`}
            />
          </div>

          {/* Title */}
          <h1 className="text-xl font-bold text-slate-900 leading-snug mb-2">{p.title}</h1>

          {/* Rating summary */}
          <div className="flex items-center gap-2 mb-4">
            <div className="flex gap-0.5">
              {Array.from({ length: 5 }, (_, i) => (
                <span
                  key={i}
                  className={`text-base ${
                    i < Math.round(p.avgRating ?? 0) ? "text-yellow-400" : "text-slate-200"
                  }`}
                >
                  ★
                </span>
              ))}
            </div>
            <span className="text-sm font-semibold text-slate-700">
              {(p.avgRating ?? 0).toFixed(1)}
            </span>
            <span className="text-xs text-slate-400">
              ({p.totalReviews.toLocaleString("en-IN")} reviews)
            </span>
          </div>

          {/* Price block */}
          <div className="flex items-baseline gap-3 mb-1">
            <span className="text-2xl font-black text-slate-900">
              {formatPrice(p.currentBestPrice)}
            </span>
            {mrp && mrp !== p.currentBestPrice && (
              <span className="text-sm text-slate-400 line-through">
                {formatPrice(mrp)}
              </span>
            )}
            {discountPct > 0 && (
              <span className="bg-green-100 text-green-700 text-xs font-bold px-2 py-0.5 rounded-full">
                {discountPct}% off
              </span>
            )}
          </div>

          {/* Best price source + lowest ever */}
          <p className="text-xs text-slate-500 mb-4">
            Best price on{" "}
            <span className="font-semibold text-slate-700">{p.currentBestMarketplace}</span>
            {p.lowestPriceEver != null && (
              <>
                {" · "}
                <span className="text-green-600 font-medium">
                  Lowest ever: {formatPrice(p.lowestPriceEver)}
                </span>
              </>
            )}
          </p>

          {/* -- DudScore section -- */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 mb-4">
            <div className="flex items-start gap-3">
              {/* Gauge */}
              <div className="w-[140px] shrink-0">
                <DudScoreGauge score={p.dudScore} label={dudScoreLabel} />
              </div>

              {/* Score breakdown */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <h2 className="text-xs font-semibold text-slate-700">DudScore Breakdown</h2>
                  {p.dudScoreConfidence && (
                    <span className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded-full capitalize">
                      {p.dudScoreConfidence}
                    </span>
                  )}
                </div>
                <CategoryScoreBars components={dudScoreComponents} />
                <button className="mt-2 text-xs font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
                  View all reviews →
                </button>
              </div>
            </div>
          </div>

          {/* -- Compare all available options -- */}
          {p.listings.length > 0 && (
            <div className="mb-5">
              <div className="flex items-center gap-2 mb-3">
                <h2 className="text-sm font-semibold text-slate-700">
                  Compare all available options
                </h2>
                {p.lowestPriceEver != null && p.currentBestPrice != null && p.currentBestPrice <= p.lowestPriceEver && (
                  <span className="text-[10px] font-bold text-[#F97316] bg-[#FFF7ED] px-2 py-0.5 rounded-full">
                    Price drop
                  </span>
                )}
              </div>
              <CrossPlatformPricePanel
                listings={p.listings}
                lowestPriceEver={p.lowestPriceEver}
              />
            </div>
          )}

          {/* -- Price History -- */}
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <h2 className="text-sm font-semibold text-slate-700 mb-1">Price History</h2>
            <PriceChart data={priceHistory} marketplaces={marketplaceChartMap} />
          </div>

          {/* -- Similar Products -- */}
          {similarProducts.length > 0 && (
            <div className="mt-5">
              <h2 className="text-sm font-semibold text-slate-700 mb-3">Similar Products</h2>
              <div className="flex gap-3 overflow-x-auto pb-1 snap-x snap-mandatory no-scrollbar">
                {similarProducts.map((product) => (
                  <div key={product.id} className="snap-start shrink-0 w-[180px] md:w-[200px]">
                    <ProductCard product={product} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* -- Alternatives -- */}
          {alternatives.length > 0 && (
            <div className="mt-5">
              <h2 className="text-sm font-semibold text-slate-700 mb-3">Alternatives</h2>
              <div className="flex gap-3 overflow-x-auto pb-1 snap-x snap-mandatory no-scrollbar">
                {alternatives.map((product) => (
                  <div key={product.id} className="snap-start shrink-0 w-[180px] md:w-[200px]">
                    <ProductCard product={product} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </main>

        {/* -- Right Sidebar: Reviews -- */}
        <ReviewSidebar
          slug={slug}
          totalReviews={p.totalReviews}
          avgRating={p.avgRating ?? 0}
          ratingDistribution={ratingDistribution}
          initialReviews={reviews}
        />
      </div>
    </>
  );
}
