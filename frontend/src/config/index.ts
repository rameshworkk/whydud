/** App-wide configuration constants. */

export const config = {
  siteName: "Whydud",
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL ?? "https://whydud.com",
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",

  limits: {
    free: { wishlists: 20, priceAlerts: 5, comparisons: 2 },
    registered: { wishlists: 20, priceAlerts: 5, comparisons: 4 },
    connected: { wishlists: 50, priceAlerts: 20, comparisons: 4 },
    premium: { wishlists: Infinity, priceAlerts: Infinity, comparisons: 4 },
  },

  dudScore: {
    excellent: { min: 90, label: "Excellent", color: "#16a34a" },
    good: { min: 70, label: "Good", color: "#65a30d" },
    average: { min: 50, label: "Average", color: "#ca8a04" },
    below: { min: 30, label: "Below Average", color: "#ea580c" },
    dud: { min: 0, label: "Dud", color: "#dc2626" },
  },

  rewards: {
    pointsPerReview: 20,
    pointsPerEmailConnect: 50,
    pointsPerReferral: 30,
  },
} as const;
