"use client";

import { useState } from "react";
import Link from "next/link";
import {
  MOCK_WISHLISTS,
  MOCK_WISHLIST_ITEMS,
  type MockWishlist,
} from "@/lib/mock-wishlists-data";
import { formatPrice } from "@/lib/utils/format";

export default function WishlistsPage() {
  const [selectedWishlist, setSelectedWishlist] = useState<MockWishlist>(
    MOCK_WISHLISTS[0]!
  );

  const priceChange = (added: number, current: number) => {
    const pct = ((current - added) / added) * 100;
    if (pct === 0) return null;
    return {
      pct: Math.abs(pct).toFixed(0),
      isDown: pct < 0,
    };
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

      {/* Wishlist cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {MOCK_WISHLISTS.map((wl) => (
          <button
            key={wl.id}
            onClick={() => setSelectedWishlist(wl)}
            className={`rounded-xl border bg-white p-5 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] ${
              selectedWishlist.id === wl.id
                ? "border-[#F97316] shadow-md"
                : "border-[#E2E8F0] hover:shadow-sm"
            }`}
          >
            <div className="flex items-center gap-3 mb-3">
              <span className="text-2xl">{wl.icon}</span>
              <div>
                <p className="text-sm font-semibold text-slate-800">
                  {wl.name}
                </p>
                <p className="text-xs text-slate-500">
                  {wl.itemCount} items
                </p>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-slate-900">
                {formatPrice(wl.totalPrice)}
              </span>
              {wl.priceDrops > 0 && (
                <span className="text-xs font-semibold text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
                  {wl.priceDrops} price drop{wl.priceDrops > 1 ? "s" : ""}
                </span>
              )}
            </div>
          </button>
        ))}
      </div>

      {/* Divider */}
      <hr className="border-[#E2E8F0]" />

      {/* Selected wishlist items */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              {selectedWishlist.icon} {selectedWishlist.name}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {selectedWishlist.itemCount} items
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-slate-700">
              Total: {formatPrice(selectedWishlist.totalPrice)}
            </span>
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
          </div>
        </div>

        <div className="flex flex-col gap-3">
          {MOCK_WISHLIST_ITEMS.map((item) => {
            const change = priceChange(item.addedPrice, item.currentPrice);
            return (
              <div
                key={item.id}
                className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-4"
              >
                {/* Product image */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={item.image}
                  alt={item.title}
                  className="w-16 h-16 rounded-lg border border-slate-100 object-contain shrink-0"
                />

                {/* Product info */}
                <div className="flex-1 min-w-0">
                  <Link
                    href={`/product/${item.slug}`}
                    className="text-sm font-semibold text-slate-800 hover:text-[#F97316] transition-colors line-clamp-1"
                  >
                    {item.title}
                  </Link>
                  <p className="text-xs text-slate-500 mt-0.5">{item.brand}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                        item.dudScore >= 80
                          ? "bg-green-50 text-green-700"
                          : item.dudScore >= 60
                          ? "bg-yellow-50 text-yellow-700"
                          : "bg-red-50 text-red-700"
                      }`}
                    >
                      {item.dudScore} {item.dudScoreLabel}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-1.5">
                    <span className="text-xs text-slate-400">
                      Target: {formatPrice(item.targetPrice)}
                    </span>
                    <span className="text-xs text-slate-300">|</span>
                    <label className="flex items-center gap-1.5 cursor-pointer">
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
                      <span className="text-[10px] text-slate-500">Alert</span>
                    </label>
                  </div>
                </div>

                {/* Price column */}
                <div className="text-right shrink-0">
                  <p className="text-xs text-slate-400">
                    Added: {formatPrice(item.addedPrice)}
                  </p>
                  <p className="text-sm font-bold text-slate-900 mt-0.5">
                    {formatPrice(item.currentPrice)}
                  </p>
                  {change && (
                    <p
                      className={`text-xs font-semibold mt-0.5 ${
                        change.isDown ? "text-green-600" : "text-red-500"
                      }`}
                    >
                      {change.isDown ? "↓" : "↑"} {change.pct}%
                    </p>
                  )}
                  <button className="mt-2 text-[10px] text-slate-400 hover:text-red-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
                    Remove
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
