/** Re-export all API types from the canonical types directory. */
export type { ApiSuccess, ApiError, ApiResponse, PaginatedResponse } from "@/types/api";
export type { ProductSummary, ProductDetail, ProductListing, Brand, Category } from "@/types/product";
export type { User, WhydudEmail, PaymentMethod, MarketplacePreference, MarketplaceInfo } from "@/types/user";

// ---------------------------------------------------------------------------
// Reviews
// ---------------------------------------------------------------------------

export interface WriteReviewPayload {
  rating: number;
  title?: string;
  bodyPositive?: string;
  bodyNegative?: string;
  npsScore?: number;
  featureRatings?: Record<string, number>;
  purchasePlatform?: string;
  purchaseSeller?: string;
  purchaseDeliveryDate?: string;
  purchasePricePaid?: number;
  sellerDeliveryRating?: number;
  sellerPackagingRating?: number;
  sellerAccuracyRating?: number;
  sellerCommunicationRating?: number;
}

export interface ReviewFeature {
  key: string;
  label: string;
  icon?: string;
}

export interface ReviewerProfile {
  userName: string;
  totalReviews: number;
  totalUpvotesReceived: number;
  totalHelpfulVotes: number;
  reviewQualityAvg: number | null;
  reviewerLevel: string;
  badges: string[];
  leaderboardRank?: number;
  isTopReviewer: boolean;
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export interface NotificationChannel {
  inApp: boolean;
  email: boolean;
}

export interface Notification {
  id: number;
  type: string;
  title: string;
  body?: string;
  actionUrl?: string;
  actionLabel?: string;
  isRead: boolean;
  createdAt: string;
  metadata?: Record<string, unknown>;
}

export interface NotificationPreferences {
  priceDrops: NotificationChannel;
  returnWindows: NotificationChannel;
  refundDelays: NotificationChannel;
  backInStock: NotificationChannel;
  reviewUpvotes: NotificationChannel;
  priceAlerts: NotificationChannel;
  discussionReplies: NotificationChannel;
  levelUp: NotificationChannel;
}

// ---------------------------------------------------------------------------
// Purchase Preferences
// ---------------------------------------------------------------------------

export interface PurchasePreference {
  categorySlug: string;
  preferences: Record<string, unknown>;
  updatedAt: string;
}

export interface PreferenceField {
  key: string;
  type: string;
  label: string;
  unit?: string;
  options?: string[];
  min?: number;
  max?: number;
  defaultValue?: unknown;
  quickSelect?: Array<{ label: string; value: unknown }>;
}

export interface PreferenceSection {
  key: string;
  title: string;
  icon: string;
  fields: PreferenceField[];
}

export interface PreferenceSchema {
  categorySlug: string;
  schema: { sections: PreferenceSection[] };
  version: number;
}

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

export interface StockAlert {
  id: string;
  product: string;
  listing: string;
  isActive: boolean;
  createdAt: string;
}

// ---------------------------------------------------------------------------
// TCO (calculation schema — distinct from TCOModel in @/types/product)
// ---------------------------------------------------------------------------

export interface TCOInput {
  key: string;
  label: string;
  type: string;
  unit?: string;
  min?: number;
  max?: number;
  defaultValue?: unknown;
  defaultFrom?: string;
}

export interface TCOModelSchema {
  id: string;
  categorySlug: string;
  name: string;
  version: number;
  inputSchema: {
    inputs: TCOInput[];
    ownershipYears: { min: number; max: number; default: number };
    presets: Record<string, Record<string, unknown>>;
  };
  costComponents: Record<string, unknown>;
}

export interface TCOBreakdownGroup {
  label: string;
  total: number;
  components: Array<{ name: string; label: string; value: number }>;
}

export interface TCOResult {
  total: number;
  perYear: number;
  perMonth: number;
  ownershipYears: number;
  breakdown: {
    purchase: TCOBreakdownGroup;
    ongoingAnnual: TCOBreakdownGroup;
    oneTimeRisk: TCOBreakdownGroup;
    resale: TCOBreakdownGroup;
  };
  product?: { slug: string; title: string; brand: string | null };
  tcoModel?: { name: string; version: number; categorySlug: string };
}
