"use client";

import { useState, useEffect } from "react";
import { purchasesApi } from "@/lib/api/inbox";
import { formatPrice, formatDate } from "@/lib/utils";
import type { ParsedOrder } from "@/types";

function OrderSkeleton() {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-[#E2E8F0] bg-white p-4 animate-pulse">
      <div className="flex-1">
        <div className="w-48 h-3.5 rounded bg-slate-200 mb-2" />
        <div className="w-32 h-2.5 rounded bg-slate-200" />
      </div>
      <div className="text-right">
        <div className="w-20 h-4 rounded bg-slate-200 mb-1" />
        <div className="w-16 h-2.5 rounded bg-slate-200" />
      </div>
    </div>
  );
}

export default function PurchasesPage() {
  const [orders, setOrders] = useState<ParsedOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchOrders() {
      try {
        const res = await purchasesApi.list();
        if (res.success && Array.isArray(res.data)) {
          setOrders(res.data);
        } else if (!res.success && "error" in res) {
          setError(res.error.message);
        }
      } catch {
        setError("Failed to load purchases.");
      } finally {
        setLoading(false);
      }
    }
    fetchOrders();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-slate-900">Purchase History</h1>

      {error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center">
          <p className="text-sm font-medium text-slate-700 mb-2">
            Please log in to view your purchase history.
          </p>
          <a
            href="/login"
            className="inline-block rounded-lg bg-[#F97316] px-5 py-2 text-sm font-semibold text-white hover:bg-[#EA580C] transition-colors"
          >
            Log In
          </a>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <OrderSkeleton key={i} />
          ))}
        </div>
      ) : !error && orders.length === 0 ? (
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-12 text-center">
          <p className="text-2xl mb-2">{"\uD83D\uDED2"}</p>
          <p className="text-sm font-semibold text-slate-700">No purchases detected yet</p>
          <p className="text-xs text-slate-500 mt-1">
            Connect your @whyd.xyz email to auto-track orders.
          </p>
        </div>
      ) : !error ? (
        <div className="flex flex-col gap-3">
          {orders.map((order) => (
            <div
              key={order.id}
              className="flex items-center gap-4 rounded-xl border border-[#E2E8F0] bg-white p-4"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-800 line-clamp-1">
                  {order.productName}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {order.marketplace} · {formatDate(order.orderDate)}
                </p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-sm font-bold text-slate-900">
                  {formatPrice(order.totalAmount)}
                </p>
                <p className="text-xs text-slate-400 capitalize">
                  {order.source?.replace("_", " ") ?? "email"}
                </p>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
