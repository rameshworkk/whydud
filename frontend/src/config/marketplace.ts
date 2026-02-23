/** Indian marketplace registry — matches backend Marketplace model slugs. */

export interface Marketplace {
  slug: string;
  name: string;
  shortName: string;
  baseUrl: string;
  /** Single-letter or 2-char display label used in price comparison badges. */
  badgeLabel: string;
  /** Tailwind bg color class for the marketplace badge. */
  badgeColor: string;
}

export const MARKETPLACES: Marketplace[] = [
  {
    slug: "amazon_in",
    name: "Amazon.in",
    shortName: "Amazon",
    baseUrl: "https://www.amazon.in",
    badgeLabel: "A",
    badgeColor: "bg-[#FF9900]",
  },
  {
    slug: "flipkart",
    name: "Flipkart",
    shortName: "Flipkart",
    baseUrl: "https://www.flipkart.com",
    badgeLabel: "F",
    badgeColor: "bg-[#2874F0]",
  },
  {
    slug: "myntra",
    name: "Myntra",
    shortName: "Myntra",
    baseUrl: "https://www.myntra.com",
    badgeLabel: "M",
    badgeColor: "bg-[#FF3F6C]",
  },
  {
    slug: "snapdeal",
    name: "Snapdeal",
    shortName: "Snapdeal",
    baseUrl: "https://www.snapdeal.com",
    badgeLabel: "S",
    badgeColor: "bg-[#E40046]",
  },
  {
    slug: "croma",
    name: "Croma",
    shortName: "Croma",
    baseUrl: "https://www.croma.com",
    badgeLabel: "C",
    badgeColor: "bg-[#67B346]",
  },
  {
    slug: "tatacliq",
    name: "TataCLiQ",
    shortName: "TataCLiQ",
    baseUrl: "https://www.tatacliq.com",
    badgeLabel: "T",
    badgeColor: "bg-[#A51C30]",
  },
  {
    slug: "reliance_digital",
    name: "Reliance Digital",
    shortName: "Reliance",
    baseUrl: "https://www.reliancedigital.in",
    badgeLabel: "R",
    badgeColor: "bg-[#0058A9]",
  },
  {
    slug: "nykaa",
    name: "Nykaa",
    shortName: "Nykaa",
    baseUrl: "https://www.nykaa.com",
    badgeLabel: "N",
    badgeColor: "bg-[#FC2779]",
  },
  {
    slug: "ajio",
    name: "AJIO",
    shortName: "AJIO",
    baseUrl: "https://www.ajio.com",
    badgeLabel: "AJ",
    badgeColor: "bg-[#1B1B1B]",
  },
  {
    slug: "meesho",
    name: "Meesho",
    shortName: "Meesho",
    baseUrl: "https://www.meesho.com",
    badgeLabel: "Me",
    badgeColor: "bg-[#F43397]",
  },
  {
    slug: "jiomart",
    name: "JioMart",
    shortName: "JioMart",
    baseUrl: "https://www.jiomart.com",
    badgeLabel: "J",
    badgeColor: "bg-[#0070C0]",
  },
];

/** Look up a marketplace by slug. Returns undefined if not found. */
export function getMarketplace(slug: string): Marketplace | undefined {
  return MARKETPLACES.find((m) => m.slug === slug);
}
