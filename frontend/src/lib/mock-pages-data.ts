/**
 * Mock data for Search, Compare, and Seller pages.
 * All prices in paisa.
 */

// ─── Search page: seller sidebar ──────────────────────────────────────────────

export interface MockSellerSidebar {
  name: string;
  slug: string;
  verified: boolean;
  avatar: string;
  description: string;
  rating: number;
  reviewCount: number;
  productCount: number;
  reviews: { reviewer: string; avatarColor: string; text: string; rating: number }[];
  relatedProducts: { title: string; slug: string; image: string; price: number }[];
}

export const MOCK_SELLER_SIDEBAR: MockSellerSidebar = {
  name: "ACEFOUR ACCESSORIES PRIVATE LIMITED",
  slug: "acefour-accessories",
  verified: true,
  avatar: "https://placehold.co/48x48/F97316/fff?text=A",
  description:
    "ACEFOUR ACCESSORIES PRIVATE LIMITED is a prominent ecommerce seller in India. Over the past 2 years they have fulfilled orders across 120+ categories with 4.2 average rating.",
  rating: 4.2,
  reviewCount: 1842,
  productCount: 345,
  reviews: [
    {
      reviewer: "Pragati goel",
      avatarColor: "#4DB6AC",
      text: "Top Notch Quality. Great product quality at affordable price.",
      rating: 5,
    },
    {
      reviewer: "Arnab Sen",
      avatarColor: "#F97316",
      text: "Fast delivery and genuinely good quality bags.",
      rating: 4,
    },
  ],
  relatedProducts: [
    {
      title: "Safari Polyester Cabin Size Spinner Suitcase 8 Wheel...",
      slug: "safari-spinner-suitcase",
      image: "https://placehold.co/80x80/e8f4fd/1e40af?text=Suitcase",
      price: 179900,
    },
    {
      title: "Prestige Procleanico Cabin Size 4 Wheel Premium...",
      slug: "prestige-cabin-bag",
      image: "https://placehold.co/80x80/fef3c7/92400e?text=Cabin",
      price: 259900,
    },
  ],
};

// ─── Compare page ─────────────────────────────────────────────────────────────

export interface CompareProduct {
  slug: string;
  title: string;
  brand: string;
  image: string;
  price: number;
  bestBuy: boolean;
}

export interface CompareHighlight {
  badge: string;
  badgeColor: string;
  productTitle: string;
  description: string;
}

export interface CompareScoreRow {
  label: string;
  scores: number[]; // 0–5 per product
}

export interface CompareSpecRow {
  label: string;
  values: { text: string; detail?: string; isBest?: boolean }[];
}

export interface CompareDetailRow {
  label: string;
  values: string[];
}

export interface CompareData {
  products: CompareProduct[];
  highlights: CompareHighlight[];
  categoryScores: CompareScoreRow[];
  ratings: {
    customerRatings: { stars: number; count: number }[];
    dudScores: { score: number; outOf: number }[];
  };
  keySpecs: { section: string; rows: CompareSpecRow[] }[];
  detailedSummary: { section: string; rows: CompareDetailRow[] }[];
  tco: { estimated3yr: number; monthlyCost: number }[];
}

export const MOCK_COMPARE: CompareData = {
  products: [
    {
      slug: "oneplus-13r",
      title: "OnePlus 13R",
      brand: "OnePlus",
      image: "https://placehold.co/160x200/f0f0f0/1a1a1a?text=OnePlus+13R",
      price: 3600000,
      bestBuy: true,
    },
    {
      slug: "redmi-13-5g",
      title: "Redmi 13 5G",
      brand: "Xiaomi",
      image: "https://placehold.co/160x200/f0f0f0/1a1a1a?text=Redmi+13+5G",
      price: 3600000,
      bestBuy: true,
    },
    {
      slug: "motorola-edge-50",
      title: "Motorola Edge 50",
      brand: "Motorola",
      image: "https://placehold.co/160x200/f0f0f0/1a1a1a?text=Moto+Edge+50",
      price: 3600000,
      bestBuy: true,
    },
  ],

  highlights: [
    {
      badge: "Best Overall",
      badgeColor: "bg-[#F97316] text-white",
      productTitle: "OnePlus 13R",
      description:
        "Strong performance, best results, minor size trade-off.",
    },
    {
      badge: "Best Value for money",
      badgeColor: "bg-[#F97316] text-white",
      productTitle: "Redmi 13 5G",
      description:
        "Similar display, 3 cameras for significantly lower price.",
    },
    {
      badge: "Best Display",
      badgeColor: "bg-[#F97316] text-white",
      productTitle: "Motorola Edge 50",
      description:
        "Curved OLED with superior peak brightness.",
    },
  ],

  categoryScores: [
    { label: "Style & Design", scores: [4, 3, 5] },
    { label: "User Friendly", scores: [4, 4, 4] },
    { label: "Look & Feel", scores: [5, 3, 4] },
    { label: "Value for money", scores: [3, 5, 3] },
  ],

  ratings: {
    customerRatings: [
      { stars: 4.5, count: 1200 },
      { stars: 4.2, count: 1300 },
      { stars: 4.3, count: 1200 },
    ],
    dudScores: [
      { score: 9.0, outOf: 10 },
      { score: 9.2, outOf: 10 },
      { score: 9.2, outOf: 10 },
    ],
  },

  keySpecs: [
    {
      section: "Performance",
      rows: [
        {
          label: "Processor",
          values: [
            { text: "MediaTek Dimensity 8350 Apex", isBest: true },
            { text: "MediaTek Dimensity 8350 Apex", isBest: false },
            { text: "MediaTek Dimensity 8350 Apex", isBest: false },
          ],
        },
      ],
    },
    {
      section: "Display",
      rows: [
        {
          label: "Screen Size",
          values: [
            { text: "6.77\" AMOLED", detail: "Primary Camera", isBest: true },
            { text: "6.77\" AMOLED", detail: "Primary Camera" },
            { text: "6.77\" AMOLED", detail: "Primary Camera" },
          ],
        },
      ],
    },
    {
      section: "Rear Camera",
      rows: [
        {
          label: "Main",
          values: [
            { text: "43 HP", detail: "Primary Camera" },
            { text: "48 HP", detail: "Primary Camera", isBest: true },
            { text: "48 HP", detail: "Primary Camera" },
          ],
        },
        {
          label: "Ultra Wide",
          values: [
            { text: "8 HP", detail: "Ultra Wide Angle Camera" },
            { text: "2 HP", detail: "Ultra Wide Angle Camera" },
            { text: "8 HP", detail: "Ultra Wide Angle Camera", isBest: true },
          ],
        },
      ],
    },
    {
      section: "Front Camera",
      rows: [
        {
          label: "Main",
          values: [
            { text: "42 HP", detail: "Primary Camera" },
            { text: "48 HP", detail: "Primary Camera", isBest: true },
            { text: "48 HP", detail: "Primary Camera" },
          ],
        },
        {
          label: "Ultra Wide",
          values: [
            { text: "3 HP", detail: "Ultra Wide Angle Camera" },
            { text: "8 HP", detail: "Ultra Wide Angle Camera", isBest: true },
            { text: "8 HP", detail: "Ultra Wide Angle Camera" },
          ],
        },
      ],
    },
    {
      section: "Battery",
      rows: [
        {
          label: "Capacity",
          values: [
            { text: "7700 mAh", isBest: true },
            { text: "7700 mAh" },
            { text: "7700 mAh" },
          ],
        },
      ],
    },
    {
      section: "Storage",
      rows: [
        {
          label: "Internal",
          values: [
            { text: "128 GB", isBest: true },
            { text: "128 GB" },
            { text: "128 GB" },
          ],
        },
      ],
    },
  ],

  detailedSummary: [
    {
      section: "General",
      rows: [
        { label: "Country of origin", values: ["No", "No", "No"] },
        { label: "Model", values: ["No", "No", "No"] },
        { label: "SIM Type", values: ["No", "No", "No"] },
        { label: "Dual Sim", values: ["Yes", "Yes", "Yes"] },
        { label: "SIM size", values: ["No", "No", "No"] },
        { label: "SAR", values: ["No", "No", "No"] },
        {
          label: "Reverse Charging",
          values: [
            "Yes",
            "Yes",
            "Yes",
          ],
        },
        { label: "IR Blaster", values: ["Yes", "Yes", "Yes"] },
      ],
    },
    {
      section: "Unique Features",
      rows: [
        { label: "3.5mm Audio Jack", values: ["No", "No", "No"] },
        { label: "FM Radio", values: ["No", "No", "No"] },
        { label: "Water Resistant", values: ["No", "No", "No"] },
        { label: "NFC (Near Field Communication)", values: ["Yes", "Yes", "Yes"] },
        { label: "Memory Card Support", values: ["No", "No", "No"] },
        { label: "Wireless Charging", values: ["No", "No", "No"] },
        { label: "Reverse Charging", values: ["No", "No", "Yes"] },
      ],
    },
    {
      section: "Performance",
      rows: [
        { label: "AnTuTu score", values: ["", "", ""] },
        { label: "Geekbench score", values: ["", "", ""] },
        { label: "3DMark Score", values: ["", "", ""] },
        { label: "Speaker Score", values: ["", "", ""] },
        { label: "Battery Test Result", values: ["", "", ""] },
      ],
    },
  ],

  tco: [
    { estimated3yr: 8396000, monthlyCost: 139900 },
    { estimated3yr: 8396000, monthlyCost: 139900 },
    { estimated3yr: 8396000, monthlyCost: 139900 },
  ],
};

// ─── Seller detail page ───────────────────────────────────────────────────────

export interface MockSellerDetail {
  slug: string;
  name: string;
  verified: boolean;
  avatar: string;
  rating: number;
  productCount: number;
  sellerSince: string;
  trustScore: number;
  description: string;
  categories: string[];
  photoCount: number;
  socials: { label: string; url: string }[];
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

export const MOCK_SELLER_DETAIL: MockSellerDetail = {
  slug: "kintsugi-aura-ceramics",
  name: "KingsugiAura Ceramics",
  verified: true,
  avatar: "https://placehold.co/80x80/e8f4fd/1e40af?text=KA",
  rating: 4.8,
  productCount: 212,
  sellerSince: "5 years",
  trustScore: 48,
  description:
    "KintsugiAura Ceramics is devoted to crafting authentic, handcrafted Japanese ceramics that blend tradition with timeless artistry. Each piece reflects the beauty of imperfection, bringing the warmth and elegance of Japanese culture into your home. We take pride in maintaining the highest standards of quality and customer service.",
  categories: [
    "Tea Sets",
    "Bowls",
    "Plates",
    "Sake Sets",
    "Vases",
    "Decorative items",
  ],
  photoCount: 8,
  socials: [
    { label: "Instagram", url: "#" },
    { label: "Whatsapp", url: "#" },
  ],
  contact: {
    address: [
      "Billing address",
      "514 Chai Chee Lane",
      "Singapore",
      "Singapore - 469029",
    ],
  },
  performance: {
    positiveReviewPct: 95,
    reviewPeriod: "the past 9 months",
    avgResolutionTime: "1–2 Days",
    turnaroundTime: "24 Hours",
    responseRate: "95%",
  },
};
