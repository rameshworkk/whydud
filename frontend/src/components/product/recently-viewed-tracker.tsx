"use client";

import { useLogProductView } from "@/hooks/use-recently-viewed";

/**
 * Invisible client component that logs a product view on mount.
 * Drop into the server-rendered product page — renders nothing.
 */
export function RecentlyViewedTracker({ slug }: { slug: string }) {
  useLogProductView(slug);
  return null;
}
