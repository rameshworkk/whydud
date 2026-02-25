"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { ProductSummary } from "@/types/product";

const MAX_COMPARE = 4;

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

export function CompareProvider({ children }: { children: ReactNode }) {
  const [products, setProducts] = useState<ProductSummary[]>([]);

  const addToCompare = useCallback((product: ProductSummary) => {
    setProducts((prev) => {
      if (prev.length >= MAX_COMPARE) return prev;
      if (prev.some((p) => p.slug === product.slug)) return prev;
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
