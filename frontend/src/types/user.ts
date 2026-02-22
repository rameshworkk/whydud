/** User and account-related TypeScript types. */

export type UserRole =
  | "registered"
  | "connected"
  | "premium"
  | "moderator"
  | "senior_moderator"
  | "admin"
  | "super_admin";

export type SubscriptionTier = "free" | "premium";

export interface User {
  id: string;
  email: string;
  name: string;
  avatarUrl: string;
  role: UserRole;
  subscriptionTier: SubscriptionTier;
  hasWhydudEmail: boolean;
  createdAt: string;
}

export interface WhydudEmail {
  id: string;
  username: string;
  emailAddress: string;
  isActive: boolean;
  totalEmailsReceived: number;
  totalOrdersDetected: number;
  onboardingComplete: boolean;
  marketplacesRegistered: string[];
  createdAt: string;
}

export type PaymentMethodType = "credit_card" | "debit_card" | "upi" | "wallet" | "membership";

export interface PaymentMethod {
  id: string;
  methodType: PaymentMethodType;
  bankName: string;
  cardVariant: string;
  cardNetwork: string;
  walletProvider: string;
  upiApp: string;
  upiBank: string;
  membershipType: string;
  emiEligible: boolean;
  nickname: string;
  isPreferred: boolean;
  createdAt: string;
}

export interface Wishlist {
  id: string;
  name: string;
  isDefault: boolean;
  isPublic: boolean;
  shareSlug: string | null;
  items: WishlistItem[];
  createdAt: string;
}

export interface WishlistItem {
  id: string;
  product: string; // product UUID
  priceWhenAdded: number | null;
  targetPrice: number | null;
  alertEnabled: boolean;
  currentPrice: number | null;
  priceChangePct: number | null;
  notes: string;
  priority: number;
  addedAt: string;
}

export interface RewardBalance {
  totalEarned: number;
  totalSpent: number;
  totalExpired: number;
  currentBalance: number;
  updatedAt: string;
}

export interface InboxEmail {
  id: string;
  senderAddress: string;
  senderName: string;
  subject: string;
  receivedAt: string;
  category: "order" | "shipping" | "refund" | "return" | "subscription" | "promo" | "other";
  marketplace: string;
  parseStatus: "pending" | "parsed" | "failed" | "skipped";
  isRead: boolean;
  isStarred: boolean;
  createdAt: string;
}

export interface ParsedOrder {
  id: string;
  source: "whydud_email" | "gmail";
  orderId: string;
  marketplace: string;
  productName: string;
  quantity: number;
  pricePaid: number | null;
  totalAmount: number | null;
  currency: string;
  orderDate: string | null;
  deliveryDate: string | null;
  sellerName: string;
  paymentMethod: string;
  matchStatus: "pending" | "matched" | "unmatched";
  createdAt: string;
}
