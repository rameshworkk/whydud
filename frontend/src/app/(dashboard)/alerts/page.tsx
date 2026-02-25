"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { Trash2, Pencil, Check, X } from "lucide-react";
import { alertsApi } from "@/lib/api/alerts";
import { formatPrice, formatDate } from "@/lib/utils/format";
import { cn } from "@/lib/utils/index";
import type { PriceAlert } from "@/types";
import type { StockAlert } from "@/lib/api/types";

// Extended types with product context from backend
interface MyPriceAlert extends PriceAlert {
  productTitle: string;
  productSlug: string;
}

interface MyStockAlert extends StockAlert {
  productTitle: string;
  productSlug: string;
  marketplaceName: string;
}

function AlertRowSkeleton() {
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-4 animate-pulse">
      <div className="flex-1">
        <div className="w-40 h-3.5 rounded bg-slate-200 mb-2" />
        <div className="w-56 h-2.5 rounded bg-slate-200" />
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <div className="w-16 h-5 rounded-full bg-slate-200" />
        <div className="w-7 h-7 rounded bg-slate-200" />
        <div className="w-7 h-7 rounded bg-slate-200" />
      </div>
    </div>
  );
}

function priceAlertStatus(alert: MyPriceAlert): { text: string; color: string } {
  if (alert.isTriggered) {
    return { text: "Triggered", color: "bg-[#FFF7ED] text-[#F97316]" };
  }
  if (alert.isActive) {
    return { text: "Active", color: "bg-green-50 text-[#16A34A]" };
  }
  return { text: "Inactive", color: "bg-slate-100 text-[#64748B]" };
}

function stockAlertStatus(alert: MyStockAlert): { text: string; color: string } {
  if (alert.isActive) {
    return { text: "Watching", color: "bg-green-50 text-[#16A34A]" };
  }
  return { text: "Inactive", color: "bg-slate-100 text-[#64748B]" };
}

// ── Inline Price Edit ────────────────────────────────────────────────────────

function InlinePriceEdit({
  currentValue,
  onSave,
  onCancel,
}: {
  currentValue: number;
  onSave: (newPrice: number) => void;
  onCancel: () => void;
}) {
  const [value, setValue] = useState(String(currentValue / 100));
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const paisa = Math.round(Number(value) * 100);
    if (!isNaN(paisa) && paisa > 0) {
      onSave(paisa);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-1">
      <span className="text-xs text-[#64748B]">₹</span>
      <input
        ref={inputRef}
        type="number"
        min={1}
        step={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="w-20 rounded border border-[#E2E8F0] px-1.5 py-0.5 text-xs text-[#1E293B] focus:border-[#F97316] focus:outline-none focus:ring-1 focus:ring-[#F97316]/20"
      />
      <button
        type="submit"
        className="flex h-5 w-5 items-center justify-center rounded text-[#16A34A] hover:bg-green-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
        title="Save"
      >
        <Check className="h-3 w-3" />
      </button>
      <button
        type="button"
        onClick={onCancel}
        className="flex h-5 w-5 items-center justify-center rounded text-[#64748B] hover:bg-slate-100 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
        title="Cancel"
      >
        <X className="h-3 w-3" />
      </button>
    </form>
  );
}

// ── Page Component ───────────────────────────────────────────────────────────

export default function AlertsPage() {
  const [priceAlerts, setPriceAlerts] = useState<MyPriceAlert[]>([]);
  const [stockAlerts, setStockAlerts] = useState<MyStockAlert[]>([]);
  const [loadingPrice, setLoadingPrice] = useState(true);
  const [loadingStock, setLoadingStock] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);

  useEffect(() => {
    async function fetchAlerts() {
      try {
        const [priceRes, stockRes] = await Promise.all([
          alertsApi.getAlerts(),
          alertsApi.getStockAlerts(),
        ]);

        if (priceRes.success && "data" in priceRes) {
          setPriceAlerts(priceRes.data as MyPriceAlert[]);
        } else if (!priceRes.success && "error" in priceRes) {
          setError(priceRes.error.message);
        }

        if (stockRes.success && "data" in stockRes) {
          setStockAlerts(stockRes.data as MyStockAlert[]);
        }
      } catch {
        setError("Failed to load alerts.");
      } finally {
        setLoadingPrice(false);
        setLoadingStock(false);
      }
    }
    fetchAlerts();
  }, []);

  async function handleDeletePrice(id: string) {
    try {
      const res = await alertsApi.deleteAlert(id);
      if (res.success) {
        setPriceAlerts((prev) => prev.filter((a) => a.id !== id));
      }
    } catch {
      // Silently fail
    }
  }

  async function handleUpdatePrice(id: string, newPrice: number) {
    try {
      const res = await alertsApi.updateAlert(id, newPrice);
      if (res.success && "data" in res) {
        setPriceAlerts((prev) =>
          prev.map((a) => (a.id === id ? { ...a, ...res.data } : a))
        );
      }
    } catch {
      // Silently fail
    }
    setEditingId(null);
  }

  async function handleDeleteStock(id: string) {
    try {
      const res = await alertsApi.deleteStockAlert(id);
      if (res.success) {
        setStockAlerts((prev) => prev.filter((a) => a.id !== id));
      }
    } catch {
      // Silently fail
    }
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Alerts</h1>
        <p className="text-sm text-[#64748B] mt-0.5">
          Manage your price drop and stock availability alerts
        </p>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center">
          <p className="text-sm font-medium text-slate-700 mb-2">
            Please log in to view your alerts.
          </p>
          <a
            href="/login"
            className="inline-block rounded-lg bg-[#F97316] px-5 py-2 text-sm font-semibold text-white hover:bg-[#EA580C] transition-colors"
          >
            Log In
          </a>
        </div>
      )}

      {/* ── Price Alerts ──────────────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <h2 className="text-base font-bold text-slate-900">Price Alerts</h2>
          {!loadingPrice && priceAlerts.length > 0 && (
            <span className="text-xs font-semibold text-[#64748B] bg-slate-100 px-2 py-0.5 rounded-full">
              {priceAlerts.length}
            </span>
          )}
        </div>

        <div className="flex flex-col gap-3">
          {loadingPrice ? (
            Array.from({ length: 3 }).map((_, i) => <AlertRowSkeleton key={i} />)
          ) : priceAlerts.length === 0 && !error ? (
            <div className="rounded-xl border border-[#E2E8F0] bg-white p-10 text-center">
              <p className="text-2xl mb-2">{"\uD83D\uDD14"}</p>
              <p className="text-sm font-semibold text-slate-700">
                No price alerts yet
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Set alerts on product pages to get notified when prices drop!
              </p>
              <Link
                href="/search"
                className="inline-block mt-4 text-sm font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
              >
                Browse Products →
              </Link>
            </div>
          ) : (
            priceAlerts.map((alert) => {
              const status = priceAlertStatus(alert);
              const isEditing = editingId === alert.id;

              return (
                <div
                  key={alert.id}
                  className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-4"
                >
                  {/* Alert info */}
                  <div className="flex-1 min-w-0">
                    <Link
                      href={`/product/${alert.productSlug}`}
                      className="text-sm font-semibold text-slate-800 hover:text-[#F97316] transition-colors line-clamp-1"
                    >
                      {alert.productTitle}
                    </Link>

                    <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                      {/* Target price */}
                      <div className="flex items-center gap-1">
                        <span className="text-[10px] text-[#94A3B8] uppercase tracking-wide">
                          Target
                        </span>
                        {isEditing ? (
                          <InlinePriceEdit
                            currentValue={alert.targetPrice}
                            onSave={(p) => handleUpdatePrice(alert.id, p)}
                            onCancel={() => setEditingId(null)}
                          />
                        ) : (
                          <span className="text-xs font-bold text-[#F97316]">
                            {formatPrice(alert.targetPrice)}
                          </span>
                        )}
                      </div>

                      <span className="text-xs text-slate-300">|</span>

                      {/* Current price */}
                      <div className="flex items-center gap-1">
                        <span className="text-[10px] text-[#94A3B8] uppercase tracking-wide">
                          Current
                        </span>
                        <span className="text-xs font-semibold text-slate-700">
                          {formatPrice(alert.currentPrice)}
                        </span>
                      </div>

                      {alert.marketplace && (
                        <>
                          <span className="text-xs text-slate-300">|</span>
                          <span className="text-[10px] text-[#94A3B8]">
                            {alert.marketplace}
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Status + actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={cn(
                        "text-[10px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap",
                        status.color
                      )}
                    >
                      {status.text}
                    </span>

                    {!isEditing && (
                      <button
                        type="button"
                        onClick={() => setEditingId(alert.id)}
                        className={cn(
                          "flex h-7 w-7 items-center justify-center rounded-lg border border-[#E2E8F0]",
                          "text-[#64748B] hover:text-[#F97316] hover:border-[#F97316]",
                          "transition-colors",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
                        )}
                        title="Edit target price"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => handleDeletePrice(alert.id)}
                      className={cn(
                        "flex h-7 w-7 items-center justify-center rounded-lg border border-[#E2E8F0]",
                        "text-[#64748B] hover:text-[#DC2626] hover:border-red-300",
                        "transition-colors",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
                      )}
                      title="Delete alert"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </section>

      {/* ── Stock Alerts ──────────────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <h2 className="text-base font-bold text-slate-900">Stock Alerts</h2>
          {!loadingStock && stockAlerts.length > 0 && (
            <span className="text-xs font-semibold text-[#64748B] bg-slate-100 px-2 py-0.5 rounded-full">
              {stockAlerts.length}
            </span>
          )}
        </div>

        <div className="flex flex-col gap-3">
          {loadingStock ? (
            Array.from({ length: 2 }).map((_, i) => <AlertRowSkeleton key={i} />)
          ) : stockAlerts.length === 0 && !error ? (
            <div className="rounded-xl border border-[#E2E8F0] bg-white p-10 text-center">
              <p className="text-2xl mb-2">{"\uD83D\uDCE6"}</p>
              <p className="text-sm font-semibold text-slate-700">
                No stock alerts
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Browse out-of-stock products to set availability alerts.
              </p>
            </div>
          ) : (
            stockAlerts.map((alert) => {
              const status = stockAlertStatus(alert);

              return (
                <div
                  key={alert.id}
                  className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-4"
                >
                  {/* Alert info */}
                  <div className="flex-1 min-w-0">
                    <Link
                      href={`/product/${alert.productSlug}`}
                      className="text-sm font-semibold text-slate-800 hover:text-[#F97316] transition-colors line-clamp-1"
                    >
                      {alert.productTitle}
                    </Link>

                    <div className="flex items-center gap-3 mt-1.5">
                      <span className="text-xs text-[#64748B]">
                        {alert.marketplaceName}
                      </span>
                      <span className="text-xs text-slate-300">|</span>
                      <span className="text-[10px] text-[#94A3B8]">
                        Added {formatDate(alert.createdAt)}
                      </span>
                    </div>
                  </div>

                  {/* Status + delete */}
                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={cn(
                        "text-[10px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap",
                        status.color
                      )}
                    >
                      {status.text}
                    </span>

                    <button
                      type="button"
                      onClick={() => handleDeleteStock(alert.id)}
                      className={cn(
                        "flex h-7 w-7 items-center justify-center rounded-lg border border-[#E2E8F0]",
                        "text-[#64748B] hover:text-[#DC2626] hover:border-red-300",
                        "transition-colors",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
                      )}
                      title="Delete stock alert"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </section>
    </div>
  );
}
