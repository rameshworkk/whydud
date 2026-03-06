"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";
import { toast } from "sonner";
import type { ProductSummary } from "@/types/product";

const MAX_COMPARE = 4;
const STORAGE_KEY = "whydud_compare";

/** Minimal shape we persist to localStorage (avoids bloat). */
interface CompareItem {
  slug: string;
  title: string;
  image: string | null;
  price: number | null;
  categorySlug: string | null;
  categoryName: string | null;
}

function toCompareItem(p: ProductSummary): CompareItem {
  return {
    slug: p.slug,
    title: p.title,
    image: p.images?.[0] ?? null,
    price: p.currentBestPrice,
    categorySlug: p.categorySlug,
    categoryName: p.categoryName,
  };
}

interface CompareContextValue {
  products: ProductSummary[];
  /** Add a product to the compare tray (max 4, no duplicates). */
  addToCompare: (product: ProductSummary) => void;
  /** Remove a product from the compare tray by slug. */
  removeFromCompare: (slug: string) => void;
  /** Clear all products from the compare tray. */
  clearCompare: () => void;
  /** Check whether a product is already in the compare tray. */
  isInCompare: (slug: string) => boolean;
  /** Whether the tray is at max capacity (4 products). */
  isFull: boolean;
}

const CompareContext = createContext<CompareContextValue | null>(null);

/** Read persisted items from localStorage on mount. */
function loadPersistedItems(): ProductSummary[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const items: CompareItem[] = JSON.parse(raw);
    if (!Array.isArray(items)) return [];
    // Reconstruct minimal ProductSummary from persisted items
    return items.slice(0, MAX_COMPARE).map((item) => ({
      id: "",
      slug: item.slug,
      title: item.title,
      brandName: null,
      brandSlug: null,
      categoryName: item.categoryName ?? null,
      categorySlug: item.categorySlug ?? null,
      dudScore: null,
      dudScoreConfidence: null,
      avgRating: null,
      totalReviews: 0,
      currentBestPrice: item.price,
      currentBestMarketplace: "",
      lowestPriceEver: null,
      images: item.image ? [item.image] : null,
      isRefurbished: false,
      status: "active",
    }));
  } catch {
    return [];
  }
}

function persistItems(products: ProductSummary[]) {
  if (typeof window === "undefined") return;
  try {
    const items: CompareItem[] = products.map(toCompareItem);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    // localStorage full or unavailable — silently ignore
  }
}

export function CompareProvider({ children }: { children: ReactNode }) {
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [hydrated, setHydrated] = useState(false);

  // Restore from localStorage on mount (client only)
  useEffect(() => {
    setProducts(loadPersistedItems());
    setHydrated(true);
  }, []);

  // Persist whenever products change (after hydration)
  useEffect(() => {
    if (hydrated) {
      persistItems(products);
    }
  }, [products, hydrated]);

  const addToCompare = useCallback((product: ProductSummary) => {
    setProducts((prev) => {
      if (prev.some((p) => p.slug === product.slug)) return prev;
      if (prev.length >= MAX_COMPARE) {
        toast.warning("Max 4 products. Remove one first.");
        return prev;
      }
      // Only allow same-category products in the compare tray
      const first = prev[0];
      if (first && first.categorySlug && product.categorySlug) {
        if (first.categorySlug !== product.categorySlug) {
          toast.warning(
            `You can only compare products in the same category. Current: ${first.categoryName ?? first.categorySlug}`
          );
          return prev;
        }
      }
      return [...prev, product];
    });
  }, []);

  const removeFromCompare = useCallback((slug: string) => {
    setProducts((prev) => prev.filter((p) => p.slug !== slug));
  }, []);

  const clearCompare = useCallback(() => {
    setProducts([]);
  }, []);

  const isInCompare = useCallback(
    (slug: string) => products.some((p) => p.slug === slug),
    [products]
  );

  return (
    <CompareContext.Provider
      value={{
        products,
        addToCompare,
        removeFromCompare,
        clearCompare,
        isInCompare,
        isFull: products.length >= MAX_COMPARE,
      }}
    >
      {children}
    </CompareContext.Provider>
  );
}

export function useCompare(): CompareContextValue {
  const ctx = useContext(CompareContext);
  if (!ctx) {
    throw new Error("useCompare must be used within <CompareProvider>");
  }
  return ctx;
}
