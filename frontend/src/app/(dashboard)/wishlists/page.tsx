"use client";

import { useState, useEffect } from "react";
import { wishlistsApi } from "@/lib/api/wishlists";
import { formatPrice } from "@/lib/utils/format";
import type { Wishlist, WishlistItem } from "@/types";

function WishlistCardSkeleton() {
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 animate-pulse">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 rounded-lg bg-slate-200" />
        <div>
          <div className="w-24 h-3.5 rounded bg-slate-200 mb-1" />
          <div className="w-14 h-2.5 rounded bg-slate-200" />
        </div>
      </div>
      <div className="w-20 h-4 rounded bg-slate-200" />
    </div>
  );
}

function ItemRowSkeleton() {
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-4 animate-pulse">
      <div className="w-16 h-16 rounded-lg bg-slate-200 shrink-0" />
      <div className="flex-1">
        <div className="w-48 h-3.5 rounded bg-slate-200 mb-2" />
        <div className="w-32 h-2.5 rounded bg-slate-200 mb-2" />
        <div className="w-24 h-2.5 rounded bg-slate-200" />
      </div>
      <div className="text-right">
        <div className="w-16 h-3 rounded bg-slate-200 mb-1" />
        <div className="w-20 h-4 rounded bg-slate-200" />
      </div>
    </div>
  );
}

export default function WishlistsPage() {
  const [wishlists, setWishlists] = useState<Wishlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedWishlistId, setSelectedWishlistId] = useState<string | null>(null);

  useEffect(() => {
    async function fetchWishlists() {
      try {
        const res = await wishlistsApi.list();
        if (res.success && "data" in res) {
          setWishlists(res.data);
          if (res.data.length > 0) {
            setSelectedWishlistId(res.data[0]!.id);
          }
        } else if (!res.success && "error" in res) {
          setError(res.error.message);
        }
      } catch {
        setError("Failed to load wishlists.");
      } finally {
        setLoading(false);
      }
    }
    fetchWishlists();
  }, []);

  const selectedWishlist = wishlists.find((wl) => wl.id === selectedWishlistId) ?? null;

  const priceChange = (added: number | null, current: number | null) => {
    if (added == null || current == null || added === 0) return null;
    const pct = ((current - added) / added) * 100;
    if (Math.abs(pct) < 0.5) return null;
    return {
      pct: Math.abs(pct).toFixed(0),
      isDown: pct < 0,
    };
  };

  const totalPrice = (items: WishlistItem[]) =>
    items.reduce((sum, item) => sum + (item.currentPrice ?? item.priceWhenAdded ?? 0), 0);

  const priceDropCount = (items: WishlistItem[]) =>
    items.filter((item) => (item.priceChangePct ?? 0) < 0).length;

  const handleRemoveItem = async (wishlistId: string, productId: string) => {
    try {
      const res = await wishlistsApi.removeItem(wishlistId, productId);
      if (res.success) {
        setWishlists((prev) =>
          prev.map((wl) =>
            wl.id === wishlistId
              ? { ...wl, items: (wl.items ?? []).filter((item) => item.product !== productId) }
              : wl
          )
        );
      }
    } catch {
      // Silently fail
    }
  };

  const handleToggleAlert = async (wishlistId: string, item: WishlistItem) => {
    try {
      await wishlistsApi.updateItem(wishlistId, item.product, {
        alertEnabled: !item.alertEnabled,
      });
      setWishlists((prev) =>
        prev.map((wl) =>
          wl.id === wishlistId
            ? {
                ...wl,
                items: (wl.items ?? []).map((i) =>
                  i.id === item.id ? { ...i, alertEnabled: !i.alertEnabled } : i
                ),
              }
            : wl
        )
      );
    } catch {
      // Silently fail
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-900">My Wishlists</h1>
        <button className="rounded-lg bg-[#F97316] px-4 py-2 text-sm font-semibold text-white hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2">
          + Create Wishlist
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center">
          <p className="text-sm font-medium text-slate-700 mb-2">
            Please log in to view your wishlists.
          </p>
          <a
            href="/login"
            className="inline-block rounded-lg bg-[#F97316] px-5 py-2 text-sm font-semibold text-white hover:bg-[#EA580C] transition-colors"
          >
            Log In
          </a>
        </div>
      )}

      {/* Wishlist cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading
          ? Array.from({ length: 3 }).map((_, i) => <WishlistCardSkeleton key={i} />)
          : wishlists.length === 0
          ? (
            <div className="col-span-full rounded-xl border border-[#E2E8F0] bg-white p-12 text-center">
              <p className="text-2xl mb-2">{"\uD83D\uDCCB"}</p>
              <p className="text-sm font-semibold text-slate-700">No wishlists yet</p>
              <p className="text-xs text-slate-500 mt-1">
                Create your first wishlist to start tracking product prices.
              </p>
            </div>
          )
          : wishlists.map((wl) => {
            const items = wl.items ?? [];
            const drops = priceDropCount(items);
            return (
              <button
                key={wl.id}
                onClick={() => setSelectedWishlistId(wl.id)}
                className={`rounded-xl border bg-white p-5 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] ${
                  selectedWishlistId === wl.id
                    ? "border-[#F97316] shadow-md"
                    : "border-[#E2E8F0] hover:shadow-sm"
                }`}
              >
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-2xl">{wl.isDefault ? "\u2B50" : "\uD83D\uDCCB"}</span>
                  <div>
                    <p className="text-sm font-semibold text-slate-800">
                      {wl.name}
                    </p>
                    <p className="text-xs text-slate-500">
                      {items.length} item{items.length !== 1 ? "s" : ""}
                    </p>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-slate-900">
                    {formatPrice(totalPrice(items))}
                  </span>
                  <div className="flex items-center gap-2">
                    {drops > 0 && (
                      <span className="text-xs font-semibold text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
                        {drops} price drop{drops > 1 ? "s" : ""}
                      </span>
                    )}
                    {wl.isPublic && (
                      <span className="text-xs font-medium text-slate-400 bg-slate-50 px-2 py-0.5 rounded-full">
                        Public
                      </span>
                    )}
                  </div>
                </div>
              </button>
            );
          })}
      </div>

      {/* Divider */}
      {selectedWishlist && <hr className="border-[#E2E8F0]" />}

      {/* Selected wishlist items */}
      {loading ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <ItemRowSkeleton key={i} />
          ))}
        </div>
      ) : selectedWishlist ? (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                {selectedWishlist.name}
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                {(selectedWishlist.items ?? []).length} item{(selectedWishlist.items ?? []).length !== 1 ? "s" : ""}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-slate-700">
                Total: {formatPrice(totalPrice(selectedWishlist.items ?? []))}
              </span>
              {selectedWishlist.shareSlug && (
                <button className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-[#F97316] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                  </svg>
                  Share wishlist
                </button>
              )}
            </div>
          </div>

          {(selectedWishlist.items ?? []).length === 0 ? (
            <div className="rounded-xl border border-[#E2E8F0] bg-white p-12 text-center">
              <p className="text-sm text-slate-400">
                No items in this wishlist yet. Add products to start tracking prices.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {(selectedWishlist.items ?? []).map((item) => {
                const change = priceChange(item.priceWhenAdded, item.currentPrice);
                return (
                  <div
                    key={item.id}
                    className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-4"
                  >
                    {/* Product placeholder image */}
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src="https://placehold.co/80x80/f0f0f0/64748b?text=Product"
                      alt="Product"
                      className="w-16 h-16 rounded-lg border border-slate-100 object-contain shrink-0"
                    />

                    {/* Product info */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-slate-800 line-clamp-1">
                        Product {item.product.slice(0, 8)}...
                      </p>
                      <p className="text-[10px] text-slate-400 mt-0.5 font-mono">
                        ID: {item.product}
                      </p>
                      {item.notes && (
                        <p className="text-xs text-slate-500 mt-1 line-clamp-1">
                          {item.notes}
                        </p>
                      )}
                      <div className="flex items-center gap-3 mt-1.5">
                        {item.targetPrice != null && (
                          <span className="text-xs text-slate-400">
                            Target: {formatPrice(item.targetPrice)}
                          </span>
                        )}
                        {item.targetPrice != null && (
                          <span className="text-xs text-slate-300">|</span>
                        )}
                        <label className="flex items-center gap-1.5 cursor-pointer">
                          <button
                            onClick={() => handleToggleAlert(selectedWishlist.id, item)}
                            className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
                          >
                            <span
                              className={`relative inline-block w-7 h-4 rounded-full transition-colors ${
                                item.alertEnabled ? "bg-[#F97316]" : "bg-slate-300"
                              }`}
                            >
                              <span
                                className={`absolute top-0.5 w-3 h-3 rounded-full bg-white shadow-sm transition-transform ${
                                  item.alertEnabled
                                    ? "translate-x-3.5"
                                    : "translate-x-0.5"
                                }`}
                              />
                            </span>
                          </button>
                          <span className="text-[10px] text-slate-500">Alert</span>
                        </label>
                      </div>
                    </div>

                    {/* Price column */}
                    <div className="text-right shrink-0">
                      {item.priceWhenAdded != null && (
                        <p className="text-xs text-slate-400">
                          Added: {formatPrice(item.priceWhenAdded)}
                        </p>
                      )}
                      <p className="text-sm font-bold text-slate-900 mt-0.5">
                        {formatPrice(item.currentPrice ?? item.priceWhenAdded)}
                      </p>
                      {change && (
                        <p
                          className={`text-xs font-semibold mt-0.5 ${
                            change.isDown ? "text-green-600" : "text-red-500"
                          }`}
                        >
                          {change.isDown ? "\u2193" : "\u2191"} {change.pct}%
                        </p>
                      )}
                      <button
                        onClick={() => handleRemoveItem(selectedWishlist.id, item.product)}
                        className="mt-2 text-[10px] text-slate-400 hover:text-red-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
