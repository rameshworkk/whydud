/**
 * Mock data for the Inbox page.
 * Simulates shopping email inbox with categorized emails.
 */

export interface MockEmail {
  id: string;
  senderName: string;
  senderAddress: string;
  subject: string;
  snippet: string;
  receivedAt: string;
  isRead: boolean;
  isStarred: boolean;
  category: "order" | "shipping" | "refund" | "return" | "subscription" | "promo";
  marketplace: string;
  /** Parsed data if order/refund detected */
  parsedData?: {
    type: "order" | "refund" | "shipping";
    productName: string;
    amount: number; // paisa
    marketplace: string;
    dudScore?: number;
    dudScoreLabel?: string;
  };
  /** HTML-like body text (mock) */
  body: string;
}

export const MOCK_EMAILS: MockEmail[] = [
  {
    id: "e1",
    senderName: "Amazon.in",
    senderAddress: "auto-confirm@amazon.in",
    subject: "Your order of OnePlus Nord 5 has been placed",
    snippet: "Thank you for your order. Your estimated delivery date is...",
    receivedAt: "2026-02-24T10:30:00Z",
    isRead: false,
    isStarred: false,
    category: "order",
    marketplace: "Amazon",
    parsedData: {
      type: "order",
      productName: "OnePlus Nord 5",
      amount: 2700000,
      marketplace: "Amazon.in",
      dudScore: 82,
      dudScoreLabel: "Good",
    },
    body: "Dear Customer,\n\nThank you for your order! Your order #402-1234567-8901234 has been confirmed.\n\nOnePlus Nord 5 (8GB RAM, 256GB Storage) - Marble Black\nPrice: ₹27,000\n\nEstimated delivery: Feb 27–28, 2026\nShipping to: Bangalore, Karnataka\n\nTrack your order on Amazon.in",
  },
  {
    id: "e2",
    senderName: "Flipkart",
    senderAddress: "noreply@flipkart.com",
    subject: "Order confirmed #FLP-9876543210",
    snippet: "Your order for Samsung Galaxy Buds3 Pro has been confirmed...",
    receivedAt: "2026-02-23T14:15:00Z",
    isRead: false,
    isStarred: true,
    category: "order",
    marketplace: "Flipkart",
    parsedData: {
      type: "order",
      productName: "Samsung Galaxy Buds3 Pro",
      amount: 1499900,
      marketplace: "Flipkart",
      dudScore: 78,
      dudScoreLabel: "Good",
    },
    body: "Hi there,\n\nYour order has been confirmed!\n\nSamsung Galaxy Buds3 Pro - Silver\nOrder ID: FLP-9876543210\nPrice: ₹14,999\n\nExpected delivery: Feb 26, 2026\n\nTrack your order on Flipkart",
  },
  {
    id: "e3",
    senderName: "Myntra",
    senderAddress: "orders@myntra.com",
    subject: "Refund processed for order #MYN-456789",
    snippet: "Your refund of ₹2,499 has been initiated and will be credited...",
    receivedAt: "2026-02-21T09:00:00Z",
    isRead: true,
    isStarred: false,
    category: "refund",
    marketplace: "Myntra",
    parsedData: {
      type: "refund",
      productName: "Allen Solly Formal Shirt",
      amount: 249900,
      marketplace: "Myntra",
    },
    body: "Dear Customer,\n\nYour refund for order #MYN-456789 has been processed.\n\nAllen Solly Formal Shirt - Blue\nRefund amount: ₹2,499\nRefund to: HDFC Bank ending 4521\nExpected credit: 5-7 business days\n\nThank you for shopping with Myntra!",
  },
  {
    id: "e4",
    senderName: "Amazon.in",
    senderAddress: "ship-confirm@amazon.in",
    subject: "Your package is out for delivery",
    snippet: "Your order of Boat Airdopes 141 is out for delivery today...",
    receivedAt: "2026-02-22T06:30:00Z",
    isRead: true,
    isStarred: false,
    category: "shipping",
    marketplace: "Amazon",
    parsedData: {
      type: "shipping",
      productName: "Boat Airdopes 141",
      amount: 149900,
      marketplace: "Amazon.in",
    },
    body: "Great news!\n\nYour package is out for delivery today.\n\nBoat Airdopes 141 - Active Black\nOrder #402-7654321-0987654\n\nDelivery partner: Amazon Logistics\nExpected by: 8 PM today\n\nTrack your package on Amazon.in",
  },
  {
    id: "e5",
    senderName: "Swiggy",
    senderAddress: "noreply@swiggy.com",
    subject: "Your Swiggy One membership is renewing soon",
    snippet: "Your Swiggy One annual membership will auto-renew on Mar 1...",
    receivedAt: "2026-02-20T12:00:00Z",
    isRead: true,
    isStarred: false,
    category: "subscription",
    marketplace: "Swiggy",
    body: "Hi there,\n\nJust a friendly reminder that your Swiggy One membership will auto-renew on March 1, 2026.\n\nMembership: Swiggy One Annual\nRenewal amount: ₹1,499\nPayment method: ICICI Bank ending 3456\n\nTo manage your subscription, visit the Swiggy app.",
  },
  {
    id: "e6",
    senderName: "Flipkart",
    senderAddress: "promotions@flipkart.com",
    subject: "Big Saving Days Sale starts tomorrow! Up to 80% off",
    snippet: "Exclusive early access for Plus members. Smartphones from ₹6,999...",
    receivedAt: "2026-02-19T18:00:00Z",
    isRead: true,
    isStarred: false,
    category: "promo",
    marketplace: "Flipkart",
    body: "Flipkart Big Saving Days\nFeb 20-25, 2026\n\nExclusive early access for Plus members!\n\nSmartphones from ₹6,999\nLaptops from ₹24,999\nFashion: Min 50% Off\nElectronics: Up to 80% Off\n\nBank offer: Extra 10% off with HDFC Bank cards",
  },
  {
    id: "e7",
    senderName: "Croma",
    senderAddress: "orders@croma.com",
    subject: "Return pickup scheduled for Feb 25",
    snippet: "Your return for LG 1.5 Ton Split AC has been scheduled...",
    receivedAt: "2026-02-23T16:45:00Z",
    isRead: false,
    isStarred: false,
    category: "return",
    marketplace: "Croma",
    body: "Dear Customer,\n\nYour return request has been approved and pickup scheduled.\n\nLG 1.5 Ton 5-Star Inverter Split AC\nOrder #CRM-2026-78901\nPickup date: Feb 25, 2026\nPickup time: 10 AM - 2 PM\n\nPlease ensure the product is packed in original packaging.",
  },
];

export const INBOX_FOLDER_COUNTS: Record<string, number> = {
  all: 7,
  order: 2,
  shipping: 1,
  refund: 1,
  return: 1,
  subscription: 1,
  promo: 1,
  starred: 1,
};

export const MARKETPLACE_FILTERS = [
  { name: "Amazon", count: 3 },
  { name: "Flipkart", count: 2 },
  { name: "Myntra", count: 1 },
  { name: "Croma", count: 1 },
];
