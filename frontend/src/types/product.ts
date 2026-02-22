/** Product-related TypeScript types matching Django serializers. */

export type DudScoreLabel =
  | "Excellent"
  | "Good"
  | "Average"
  | "Below Average"
  | "Dud"
  | "Not Rated";

export type DudScoreConfidence =
  | "preliminary"
  | "low"
  | "medium"
  | "high"
  | "very_high";

export interface DudScore {
  score: number | null;
  label: DudScoreLabel;
  confidence: DudScoreConfidence | null;
  updatedAt: string | null;
  components: {
    sentiment: number;
    ratingQuality: number;
    priceValue: number;
    reviewCredibility: number;
    priceStability: number;
    returnSignal: number;
  } | null;
}

export interface Marketplace {
  id: number;
  slug: string;
  name: string;
  baseUrl: string;
}

export interface Category {
  id: number;
  slug: string;
  name: string;
  level: number;
  hasTcoModel: boolean;
  productCount: number;
}

export interface Brand {
  id: number;
  slug: string;
  name: string;
  logoUrl: string;
  verified: boolean;
}

export interface ProductListing {
  id: string;
  marketplace: Marketplace;
  externalUrl: string;
  affiliateUrl: string;
  currentPrice: number | null; // paisa
  mrp: number | null;
  discountPct: number | null;
  inStock: boolean;
  rating: number | null;
  reviewCount: number;
  lastScrapedAt: string | null;
}

export interface ProductSummary {
  id: string;
  slug: string;
  title: string;
  brand: Brand;
  category: Category;
  dudScore: number | null;
  dudScoreConfidence: DudScoreConfidence | null;
  avgRating: number | null;
  totalReviews: number;
  currentBestPrice: number | null;
  currentBestMarketplace: string;
  lowestPriceEver: number | null;
  images: string[] | null;
}

export interface ProductDetail extends ProductSummary {
  description: string;
  specs: Record<string, string | number | boolean> | null;
  listings: ProductListing[];
  dudScoreUpdatedAt: string | null;
  lastScrapedAt: string | null;
}

export interface PricePoint {
  time: string;
  price: number; // paisa
  marketplaceId: number;
}

export interface Review {
  id: string;
  reviewerName: string;
  rating: 1 | 2 | 3 | 4 | 5;
  title: string;
  body: string;
  isVerifiedPurchase: boolean;
  reviewDate: string | null;
  sentimentScore: number | null;
  sentimentLabel: "positive" | "negative" | "neutral" | null;
  extractedPros: string[];
  extractedCons: string[];
  credibilityScore: number | null;
  isFlagged: boolean;
  upvotes: number;
  downvotes: number;
  voteScore: number;
}

export interface MarketplaceOffer {
  id: string;
  offerType: string;
  title: string;
  bankSlug: string;
  cardType: string;
  cardVariants: string[];
  discountType: "flat" | "percent" | "cashback" | "no_cost_emi";
  discountValue: number;
  maxDiscount: number | null;
  minPurchase: number | null;
  emiTenures: number[];
  validUntil: string | null;
  couponCode: string;
  lastVerifiedAt: string | null;
}

export interface Deal {
  id: string;
  productTitle: string;
  productSlug: string;
  marketplaceName: string;
  dealType: "error_price" | "lowest_ever" | "genuine_discount" | "flash_sale";
  currentPrice: number;
  referencePrice: number | null;
  discountPct: number | null;
  confidence: "high" | "medium" | "low";
  detectedAt: string;
  expiresAt: string | null;
  views: number;
  clicks: number;
}
