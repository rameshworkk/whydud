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

export interface Seller {
  id: string;
  name: string;
  avgRating: number | null;
  positivePct: number | null;
  isVerified: boolean;
}

export interface SellerDetail {
  id: string;
  slug: string;
  name: string;
  isVerified: boolean;
  avatarUrl: string;
  avgRating: number | null;
  productCount: number;
  sellerSince: string;
  trustScore: number | null;
  description: string;
  categories: string[];
  photoCount: number;
  socials: Array<{ label: string; url: string }>;
  contact: {
    address: string[];
  };
  performance: {
    positiveReviewPct: number;
    reviewPeriod: string;
    avgResolutionTime: string;
    turnaroundTime: string;
    responseRate: string;
  };
}

export interface ProductListing {
  id: string;
  marketplace: Marketplace;
  seller: Seller | null;
  externalUrl: string;
  buyUrl: string;
  currentPrice: number | null;
  mrp: number | null;
  discountPct: number | null;
  inStock: boolean;
  rating: number | null;
  reviewCount: number;
  lastScrapedAt: string | null;
}

/** Flat product card shape from ProductListSerializer (list/search pages). */
export interface ProductSummary {
  id: string;
  slug: string;
  title: string;
  brandName: string | null;
  brandSlug: string | null;
  categoryName: string | null;
  categorySlug: string | null;
  dudScore: number | null;
  dudScoreConfidence: DudScoreConfidence | null;
  avgRating: number | null;
  totalReviews: number;
  currentBestPrice: number | null;
  currentBestMarketplace: string;
  lowestPriceEver: number | null;
  images: string[] | null;
  isRefurbished: boolean;
  status: string;
}

export interface ReviewSummary {
  totalReviews: number;
  avgRating: number | null;
  ratingDistribution: Record<string, number>;
  verifiedPurchasePct: number | null;
  avgCredibilityScore: number | null;
  fraudFlaggedCount: number;
}

/** Full product detail from ProductDetailSerializer (product page). */
export interface ProductDetail {
  id: string;
  slug: string;
  title: string;
  brand: Brand;
  category: Category;
  description: string;
  specs: Record<string, string | number | boolean> | null;
  images: string[] | null;
  dudScore: number | null;
  dudScoreConfidence: DudScoreConfidence | null;
  dudScoreUpdatedAt: string | null;
  avgRating: number | null;
  totalReviews: number;
  currentBestPrice: number | null;
  currentBestMarketplace: string;
  lowestPriceEver: number | null;
  lowestPriceDate: string | null;
  status: string;
  isRefurbished: boolean;
  listings: ProductListing[];
  reviewSummary: ReviewSummary;
  firstSeenAt: string | null;
  lastScrapedAt: string | null;
}

export interface PricePoint {
  time: string;
  price: number;
  marketplaceId: number;
}

export interface Review {
  id: string;
  reviewerName: string;
  externalReviewerName?: string;
  rating: 1 | 2 | 3 | 4 | 5;
  title: string;
  body: string;
  isVerifiedPurchase: boolean;
  reviewDate: string | null;
  helpfulVoteCount: number;
  marketplaceName?: string | null;
  marketplaceSlug?: string | null;
  variantInfo?: string;
  externalReviewUrl?: string;
  isScraped: boolean;
  media: string[];
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
  discountType: "flat" | "percent" | "cashback" | "noCostEmi";
  discountValue: number;
  maxDiscount: number | null;
  minPurchase: number | null;
  emiTenures: number[];
  validUntil: string | null;
  couponCode: string;
  lastVerifiedAt: string | null;
}

/** Deal from DealSerializer — product is nested as ProductSummary. */
export interface Deal {
  id: string;
  product: ProductSummary;
  marketplaceName: string;
  marketplaceSlug: string;
  dealType: "error_price" | "lowest_ever" | "genuine_discount" | "flash_sale";
  currentPrice: number;
  referencePrice: number | null;
  discountPct: number | null;
  discountPctDisplay: string | null;
  confidence: "high" | "medium" | "low";
  isActive: boolean;
  detectedAt: string;
  expiresAt: string | null;
  views: number;
  clicks: number;
}

/** Search response from Meilisearch proxy — offset-based, NOT cursor. */
export interface SearchResponse {
  results: ProductSummary[];
  total: number;
  offset: number;
  limit: number;
  query: string;
  source: string;
}

export interface DiscussionThread {
  id: string;
  product: string;
  user: { id: string; name: string; avatarUrl: string };
  threadType: "question" | "discussion" | "tip";
  title: string;
  body: string;
  upvotes: number;
  replyCount: number;
  isPinned: boolean;
  isResolved: boolean;
  createdAt: string;
}

export interface DiscussionReply {
  id: string;
  thread: string;
  user: { id: string; name: string; avatarUrl: string };
  body: string;
  upvotes: number;
  isAccepted: boolean;
  parentReply: string | null;
  createdAt: string;
}

export interface BankCard {
  id: string;
  bankSlug: string;
  bankName: string;
  cardVariant: string;
  cardType: string;
  cardNetwork: string;
  isCoBranded: boolean;
  defaultCashbackPct: number | null;
  logoUrl: string;
}

export interface City {
  id: number;
  name: string;
  state: string;
  tier: number;
  avgElectricityCost: number;
}

export interface TCOModel {
  id: string;
  category: Category;
  modelName: string;
  version: number;
  costFactors: Record<string, unknown>;
  isActive: boolean;
}

export interface UserTCOProfile {
  id: string;
  city: City;
  electricityCostPerUnit: number;
  hoursPerDay: Record<string, number>;
}

export interface DudScoreConfig {
  id: string;
  version: number;
  weights: Record<string, number>;
  isActive: boolean;
}

export interface PriceAlert {
  id: string;
  product: string;
  targetPrice: number;
  currentPrice?: number;
  marketplace?: string;
  isActive: boolean;
  isTriggered: boolean;
  triggeredAt?: string | null;
  lastAlertedAt: string | null;
  createdAt: string;
}

export interface ShareData {
  url: string;
  ogTitle: string;
  ogDescription: string;
  ogImage: string;
}
