/** Mock data for homepage development before live API is connected. */

export interface MockProduct {
  id: string;
  slug: string;
  title: string;
  brand: string;
  category: string;
  /** Current best price in paisa. */
  price: number;
  /** Maximum retail price in paisa. */
  mrp: number;
  discount_pct: number;
  rating: number;
  review_count: number;
  dud_score: number | null;
  /** Marketplace slug (matches MARKETPLACES registry). */
  marketplace: string;
  image: string;
  is_recommended: boolean;
}

export interface MockDeal {
  id: string;
  product: MockProduct;
  deal_type: "error_price" | "lowest_ever" | "massive_discount";
  /** Current deal price in paisa. */
  current_price: number;
  /** Reference/normal price in paisa. */
  reference_price: number;
  discount_pct: number;
  detected_at: string;
}

export const MOCK_PRODUCTS: MockProduct[] = [
  {
    id: "prod-001",
    slug: "samsung-galaxy-s24-fe-5g-256gb-graphite",
    title: "Samsung Galaxy S24 FE 5G (256GB, 8GB RAM, Exynos 2500) — Graphite",
    brand: "Samsung",
    category: "Smartphones",
    price: 4299900,
    mrp: 4999900,
    discount_pct: 14,
    rating: 4.3,
    review_count: 2841,
    dud_score: 82,
    marketplace: "amazon_in",
    image: "https://placehold.co/300x300/e2f0fb/1e40af?text=Galaxy+S24+FE",
    is_recommended: true,
  },
  {
    id: "prod-002",
    slug: "boat-airdopes-141-bluetooth-earbuds",
    title: "boAt Airdopes 141 Bluetooth TWS Earbuds with 42H Playtime, ENx Tech",
    brand: "boAt",
    category: "Earphones & Headphones",
    price: 59900,
    mrp: 199900,
    discount_pct: 70,
    rating: 4.1,
    review_count: 89432,
    dud_score: 71,
    marketplace: "flipkart",
    image: "https://placehold.co/300x300/fef3c7/92400e?text=boAt+Airdopes",
    is_recommended: false,
  },
  {
    id: "prod-003",
    slug: "noise-colorfit-ultra-2-smartwatch",
    title: "Noise ColorFit Ultra 2 1.75\" AMOLED Smartwatch with BT Calling, 100+ Sports Modes",
    brand: "Noise",
    category: "Smartwatches",
    price: 129900,
    mrp: 499900,
    discount_pct: 74,
    rating: 4.2,
    review_count: 34571,
    dud_score: 68,
    marketplace: "amazon_in",
    image: "https://placehold.co/300x300/f0fdf4/166534?text=Noise+Ultra+2",
    is_recommended: true,
  },
  {
    id: "prod-004",
    slug: "prestige-iris-750w-mixer-grinder-3jar",
    title: "Prestige Iris 750W Mixer Grinder with 3 Stainless Steel Jars",
    brand: "Prestige",
    category: "Kitchen Appliances",
    price: 179500,
    mrp: 259500,
    discount_pct: 31,
    rating: 4.4,
    review_count: 18230,
    dud_score: 88,
    marketplace: "flipkart",
    image: "https://placehold.co/300x300/fdf2f8/831843?text=Prestige+Mixer",
    is_recommended: true,
  },
  {
    id: "prod-005",
    slug: "mamaearth-onion-shampoo-250ml",
    title: "Mamaearth Onion Shampoo for Hair Fall Control with Onion & Plant Keratin, 250ml",
    brand: "Mamaearth",
    category: "Hair Care",
    price: 29900,
    mrp: 39900,
    discount_pct: 25,
    rating: 4.0,
    review_count: 52341,
    dud_score: 59,
    marketplace: "nykaa",
    image: "https://placehold.co/300x300/fef9c3/713f12?text=Mamaearth+Onion",
    is_recommended: false,
  },
  {
    id: "prod-006",
    slug: "peter-england-slim-fit-formal-shirt-blue",
    title: "Peter England Men's Slim Fit Solid Formal Shirt (Blue, Size 42)",
    brand: "Peter England",
    category: "Men's Clothing",
    price: 69900,
    mrp: 139900,
    discount_pct: 50,
    rating: 4.2,
    review_count: 7821,
    dud_score: null,
    marketplace: "myntra",
    image: "https://placehold.co/300x300/eff6ff/1e3a8a?text=Peter+England",
    is_recommended: false,
  },
  {
    id: "prod-007",
    slug: "bajaj-rex-plus-500w-mixer-grinder",
    title: "Bajaj REX Plus 500W Mixer Grinder with 3 Stainless Steel Jars & 1 Multipurpose Jar",
    brand: "Bajaj",
    category: "Kitchen Appliances",
    price: 109900,
    mrp: 199900,
    discount_pct: 45,
    rating: 4.3,
    review_count: 24109,
    dud_score: 77,
    marketplace: "amazon_in",
    image: "https://placehold.co/300x300/fff7ed/9a3412?text=Bajaj+Rex+Plus",
    is_recommended: true,
  },
  {
    id: "prod-008",
    slug: "lavie-womens-large-tote-handbag-tan",
    title: "Lavie Sport Women's Large Tote Handbag with Adjustable Strap — Tan",
    brand: "Lavie",
    category: "Women's Bags",
    price: 149900,
    mrp: 349900,
    discount_pct: 57,
    rating: 3.9,
    review_count: 4210,
    dud_score: 54,
    marketplace: "flipkart",
    image: "https://placehold.co/300x300/fdf4ff/6b21a8?text=Lavie+Handbag",
    is_recommended: false,
  },
];

export const MOCK_DEALS: MockDeal[] = [
  {
    id: "deal-001",
    product: MOCK_PRODUCTS[1], // boAt Airdopes 141
    deal_type: "error_price",
    current_price: 29900,
    reference_price: 199900,
    discount_pct: 85,
    detected_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: "deal-002",
    product: MOCK_PRODUCTS[0], // Samsung Galaxy S24 FE
    deal_type: "lowest_ever",
    current_price: 3799900,
    reference_price: 4999900,
    discount_pct: 24,
    detected_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: "deal-003",
    product: MOCK_PRODUCTS[2], // Noise ColorFit Ultra 2
    deal_type: "massive_discount",
    current_price: 79900,
    reference_price: 499900,
    discount_pct: 84,
    detected_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: "deal-004",
    product: MOCK_PRODUCTS[6], // Bajaj Rex Plus
    deal_type: "lowest_ever",
    current_price: 74900,
    reference_price: 199900,
    discount_pct: 63,
    detected_at: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
  },
];
