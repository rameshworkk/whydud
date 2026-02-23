/** Mock data for product detail page development before live API is connected. */

export interface MockPricePoint {
  date: string;
  amazon: number; // paisa
  flipkart: number; // paisa
  croma: number; // paisa
}

export interface MockMarketplaceListing {
  marketplace: string;
  marketplaceSlug: string;
  price: number; // paisa
  inStock: boolean;
  affiliateUrl: string;
  /** % more expensive than the best price (null = best price) */
  diffPct: number | null;
}

export interface MockReviewDetail {
  id: string;
  reviewerName: string;
  avatarColor: string; // hex bg color for avatar circle
  rating: 1 | 2 | 3 | 4 | 5;
  title: string;
  body: string;
  dateLabel: string; // e.g. "7 days ago"
  isVerifiedPurchase: boolean;
  upvotes: number;
  downvotes: number;
}

export interface MockProductDetailData {
  slug: string;
  title: string;
  brand: string;
  category: string;
  breadcrumb: string[];
  image: string;

  // Pricing
  bestPrice: number; // paisa
  mrp: number; // paisa
  discountPct: number;
  bestMarketplace: string;
  lowestEver: number; // paisa

  // DudScore
  dudScore: number;
  dudScoreLabel: "Excellent" | "Good" | "Average" | "Below Average" | "Dud";
  dudScoreConfidence: string;
  dudScoreComponents: {
    label: string;
    value: number; // 0-100
    color: string; // tailwind bg color class
  }[];

  // Ratings
  avgRating: number;
  totalReviews: number;
  ratingDistribution: Record<1 | 2 | 3 | 4 | 5, number>; // star → count percentage (0-100)

  // Marketplace listings (sorted best first)
  listings: MockMarketplaceListing[];

  // Key specs
  specs: { label: string; value: string }[];

  // Price history
  priceHistory: MockPricePoint[];

  // Reviews
  reviews: MockReviewDetail[];
}

// ─── Generate deterministic price history ────────────────────────────────────

function makePriceHistory(): MockPricePoint[] {
  const points: MockPricePoint[] = [];
  const baseDate = new Date("2025-11-01");

  for (let i = 0; i < 90; i++) {
    const d = new Date(baseDate);
    d.setDate(d.getDate() + i);
    const wave = Math.sin(i * 0.12) * 150000;
    const wave2 = Math.cos(i * 0.07) * 80000;
    const trend = -i * 300;

    points.push({
      date: d.toISOString().split("T")[0]!,
      amazon: Math.round((4599900 + wave + trend) / 100) * 100,
      flipkart: Math.round((4499900 + wave * 0.9 + wave2 + trend) / 100) * 100,
      croma: Math.round((4699900 + wave2 + trend * 0.5) / 100) * 100,
    });
  }

  return points;
}

// ─── Product detail mock data ─────────────────────────────────────────────────

export const MOCK_PRODUCT_DETAIL: MockProductDetailData = {
  slug: "samsung-galaxy-s24-fe-5g-256gb-graphite",
  title: "Samsung Galaxy S24 FE 5G (256GB, 8GB RAM, Exynos 2500)",
  brand: "Samsung",
  category: "Smartphones",
  breadcrumb: ["Home", "Smartphones", "Samsung", "Galaxy S24 FE"],
  image: "https://placehold.co/400x500/e8f4fd/1e40af?text=Galaxy+S24+FE",

  bestPrice: 4299900,
  mrp: 4999900,
  discountPct: 14,
  bestMarketplace: "Amazon",
  lowestEver: 3999900,

  dudScore: 82,
  dudScoreLabel: "Good",
  dudScoreConfidence: "high",
  dudScoreComponents: [
    { label: "Sentiment", value: 78, color: "bg-teal" },
    { label: "Rating Quality", value: 85, color: "bg-teal" },
    { label: "Price Value", value: 81, color: "bg-teal" },
    { label: "Review Credibility", value: 88, color: "bg-teal" },
    { label: "Price Stability", value: 76, color: "bg-teal" },
    { label: "Return Signal", value: 82, color: "bg-teal" },
  ],

  avgRating: 4.3,
  totalReviews: 2841,
  ratingDistribution: {
    5: 52,
    4: 28,
    3: 12,
    2: 5,
    1: 3,
  },

  listings: [
    {
      marketplace: "Amazon",
      marketplaceSlug: "amazon_in",
      price: 4299900,
      inStock: true,
      affiliateUrl: "#",
      diffPct: null,
    },
    {
      marketplace: "Flipkart",
      marketplaceSlug: "flipkart",
      price: 4349900,
      inStock: true,
      affiliateUrl: "#",
      diffPct: 1.2,
    },
    {
      marketplace: "Croma",
      marketplaceSlug: "croma",
      price: 4499900,
      inStock: true,
      affiliateUrl: "#",
      diffPct: 4.7,
    },
  ],

  specs: [
    { label: "Display", value: "6.7 inch FHD+ Dynamic AMOLED" },
    { label: "Processor", value: "Exynos 2500 Octa-core" },
    { label: "RAM", value: "8 GB LPDDR5" },
    { label: "Storage", value: "256 GB UFS 3.1" },
    { label: "Battery", value: "4,700 mAh" },
    { label: "Rear Camera", value: "50MP + 10MP + 12MP" },
    { label: "Front Camera", value: "10 MP" },
    { label: "OS", value: "Android 14 / One UI 6.1" },
    { label: "5G", value: "Yes" },
    { label: "Weight", value: "213 g" },
  ],

  priceHistory: makePriceHistory(),

  reviews: [
    {
      id: "r-001",
      reviewerName: "Arnab Kumar",
      avatarColor: "#4DB6AC",
      rating: 5,
      title: "Superb camera & battery life!",
      body: "Been using this for 3 months now. The 50MP camera produces stunning shots even in low light. Battery easily lasts a full day with heavy usage. Exynos 2500 handles everything smoothly — no stutters in BGMI or YouTube. Build quality feels premium for the price.",
      dateLabel: "7 days ago",
      isVerifiedPurchase: true,
      upvotes: 42,
      downvotes: 3,
    },
    {
      id: "r-002",
      reviewerName: "Aditi Gautam",
      avatarColor: "#F97316",
      rating: 4,
      title: "Great phone but gets warm under load",
      body: "Overall really happy with this purchase. Performance is top-notch and the screen is gorgeous. Only issue is it heats up during long gaming sessions. Amazon delivery was super fast. Would recommend for the price point.",
      dateLabel: "12 days ago",
      isVerifiedPurchase: true,
      upvotes: 28,
      downvotes: 2,
    },
    {
      id: "r-003",
      reviewerName: "Rahul Sharma",
      avatarColor: "#1E293B",
      rating: 5,
      title: "Best mid-range flagship in 2025",
      body: "Moved from iPhone 13 to this and honestly no regrets. One UI 6.1 is buttery smooth. The satellite connectivity feature is a great bonus for travellers. Screen brightness is excellent even in direct sunlight.",
      dateLabel: "3 weeks ago",
      isVerifiedPurchase: true,
      upvotes: 61,
      downvotes: 5,
    },
    {
      id: "r-004",
      reviewerName: "Priya Menon",
      avatarColor: "#DC2626",
      rating: 3,
      title: "Average camera, overhyped",
      body: "Camera is decent but nothing extraordinary. Flipkart was offering it for less last Diwali. Battery life is as advertised. Fast charging is a bit slow compared to OnePlus. Still an okay buy for Samsung fans.",
      dateLabel: "1 month ago",
      isVerifiedPurchase: false,
      upvotes: 14,
      downvotes: 9,
    },
    {
      id: "r-005",
      reviewerName: "Karthik Nair",
      avatarColor: "#16A34A",
      rating: 5,
      title: "Perfect Samsung experience",
      body: "Samsung has really nailed it with the S24 FE. Galaxy AI features like Circle to Search are legitimately useful. Updates are prompt, and the 7-year OS update promise is great for long-term use.",
      dateLabel: "5 weeks ago",
      isVerifiedPurchase: true,
      upvotes: 35,
      downvotes: 1,
    },
  ],
};
