"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { recentlyViewedApi } from "@/lib/api/products";
import { getToken } from "@/lib/api/client";
import type { ProductSummary } from "@/types";

/**
 * Log a product view on mount (fire-and-forget, auth required).
 * Call this from the product detail page.
 */
export function useLogProductView(productSlug: string) {
  const logged = useRef(false);

  useEffect(() => {
    if (logged.current) return;
    if (!getToken()) return;

    logged.current = true;
    recentlyViewedApi.log(productSlug).catch(() => {
      // Silently fail — logging a view is non-critical
    });
  }, [productSlug]);
}

/**
 * Fetch the user's recently viewed products.
 * Returns empty array for logged-out users.
 */
export function useRecentlyViewed(limit = 8) {
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setProducts([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const res = await recentlyViewedApi.list(limit);
      if (res.success) {
        setProducts(Array.isArray(res.data) ? res.data : []);
      }
    } catch {
      // Silently fail
    }
    setIsLoading(false);
  }, [limit]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { products, isLoading, refresh };
}
