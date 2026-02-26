"use client";

import { useState, useEffect } from "react";
import { purchasesApi } from "@/lib/api/inbox";
import { formatPrice, formatDate } from "@/lib/utils";
import type { RefundTracking } from "@/types";

const STATUS_STYLES: Record<string, string> = {
  initiated: "text-blue-600 bg-blue-50",
  processing: "text-yellow-600 bg-yellow-50",
  completed: "text-green-600 bg-green-50",
  failed: "text-red-600 bg-red-50",
};

function RefundSkeleton() {
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-4 animate-pulse">
      <div className="flex-1">
        <div className="w-48 h-3.5 rounded bg-slate-200 mb-2" />
        <div className="w-32 h-2.5 rounded bg-slate-200" />
      </div>
      <div className="text-right">
        <div className="w-20 h-4 rounded bg-slate-200 mb-1" />
        <div className="w-16 h-3 rounded bg-slate-200" />
      </div>
    </div>
  );
}

export default function RefundsPage() {
  const [refunds, setRefunds] = useState<RefundTracking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchRefunds() {
      try {
        const res = await purchasesApi.getRefunds();
        if (res.success && Array.isArray(res.data)) {
          setRefunds(res.data);
        } else if (!res.success && "error" in res) {
          setError(res.error.message);
        }
      } catch {
        setError("Failed to load refunds.");
      } finally {
        setLoading(false);
      }
    }
    fetchRefunds();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-slate-900">Refund Tracker</h1>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm font-medium text-slate-700 mb-1">
            Something went wrong
          </p>
          <p className="text-xs text-slate-500">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <RefundSkeleton key={i} />
          ))}
        </div>
      ) : !error && refunds.length === 0 ? (
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-12 text-center">
          <p className="text-2xl mb-2">{"\uD83D\uDCB0"}</p>
          <p className="text-sm font-semibold text-slate-700">No refunds tracked</p>
          <p className="text-xs text-slate-500 mt-1">
            Refund delays will be auto-detected from your inbox.
          </p>
        </div>
      ) : !error ? (
        <div className="flex flex-col gap-3">
          {refunds.map((refund) => (
            <div
              key={refund.id}
              className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-4"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-800 line-clamp-1">
                  {refund.productName}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {refund.marketplace} · Order #{refund.order?.slice(0, 8)}
                </p>
                {refund.expectedByDate && (
                  <p className="text-xs text-slate-400 mt-0.5">
                    Expected by {formatDate(refund.expectedByDate)}
                  </p>
                )}
              </div>
              <div className="text-right shrink-0">
                <p className="text-sm font-bold text-slate-900">
                  {formatPrice(refund.refundAmount)}
                </p>
                <span
                  className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full mt-1 capitalize ${
                    STATUS_STYLES[refund.status] ?? "text-slate-500 bg-slate-100"
                  }`}
                >
                  {refund.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
