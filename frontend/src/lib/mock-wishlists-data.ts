/**
 * Mock data for the Wishlists page.
 * All prices in paisa.
 */

export interface MockWishlist {
  id: string;
  name: string;
  icon: string;
  itemCount: number;
  totalPrice: number; // paisa
  priceDrops: number;
}

export interface MockWishlistItem {
  id: string;
  title: string;
  brand: string;
  image: string;
  slug: string;
  dudScore: number;
  dudScoreLabel: string;
  addedPrice: number; // paisa
  currentPrice: number; // paisa
  targetPrice: number; // paisa
  alertEnabled: boolean;
}

export const MOCK_WISHLISTS: MockWishlist[] = [
  { id: "wl1", name: "Birthday Gifts", icon: "🎂", itemCount: 8, totalPrice: 2450000, priceDrops: 3 },
  { id: "wl2", name: "Home Setup", icon: "🏠", itemCount: 12, totalPrice: 11200000, priceDrops: 1 },
  { id: "wl3", name: "Tech Wishlist", icon: "💻", itemCount: 5, totalPrice: 8900000, priceDrops: 0 },
];

export const MOCK_WISHLIST_ITEMS: MockWishlistItem[] = [
  {
    id: "wi1",
    title: "Sony WH-1000XM5 Wireless Headphones",
    brand: "Sony",
    image: "https://placehold.co/80x80/f0f0f0/1a1a1a?text=XM5",
    slug: "sony-wh1000xm5",
    dudScore: 88,
    dudScoreLabel: "Excellent",
    addedPrice: 2999000,
    currentPrice: 2499000,
    targetPrice: 2200000,
    alertEnabled: true,
  },
  {
    id: "wi2",
    title: "Apple AirPods Pro 2nd Gen (USB-C)",
    brand: "Apple",
    image: "https://placehold.co/80x80/f0f0f0/1a1a1a?text=APP",
    slug: "apple-airpods-pro-2",
    dudScore: 92,
    dudScoreLabel: "Excellent",
    addedPrice: 2490000,
    currentPrice: 2490000,
    targetPrice: 2000000,
    alertEnabled: true,
  },
  {
    id: "wi3",
    title: "Kindle Paperwhite (16 GB) 11th Gen",
    brand: "Amazon",
    image: "https://placehold.co/80x80/f0f0f0/1a1a1a?text=KPW",
    slug: "kindle-paperwhite-11",
    dudScore: 85,
    dudScoreLabel: "Good",
    addedPrice: 1499900,
    currentPrice: 1299900,
    targetPrice: 1100000,
    alertEnabled: false,
  },
  {
    id: "wi4",
    title: "Dyson V12 Detect Slim Cordless Vacuum",
    brand: "Dyson",
    image: "https://placehold.co/80x80/f0f0f0/1a1a1a?text=V12",
    slug: "dyson-v12-detect-slim",
    dudScore: 76,
    dudScoreLabel: "Good",
    addedPrice: 5499000,
    currentPrice: 5499000,
    targetPrice: 4500000,
    alertEnabled: true,
  },
  {
    id: "wi5",
    title: "Samsung Galaxy Watch6 Classic 47mm",
    brand: "Samsung",
    image: "https://placehold.co/80x80/f0f0f0/1a1a1a?text=GW6",
    slug: "samsung-galaxy-watch6-classic",
    dudScore: 81,
    dudScoreLabel: "Good",
    addedPrice: 3699900,
    currentPrice: 3199900,
    targetPrice: 2800000,
    alertEnabled: true,
  },
];
