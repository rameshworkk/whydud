"use client";

import { useState, useEffect } from "react";
import { purchasesApi } from "@/lib/api/inbox";
import { formatPrice, formatDate } from "@/lib/utils";
import type { DetectedSubscription } from "@/types";

function SubSkeleton() {
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-4 animate-pulse">
      <div className="flex-1">
        <div className="w-32 h-3.5 rounded bg-slate-200 mb-2" />
        <div className="w-48 h-2.5 rounded bg-slate-200" />
      </div>
      <div className="text-right">
        <div className="w-20 h-4 rounded bg-slate-200 mb-1" />
        <div className="w-16 h-2.5 rounded bg-slate-200" />
      </div>
    </div>
  );
}

export default function SubscriptionsPage() {
  const [subs, setSubs] = useState<DetectedSubscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchSubs() {
      try {
        const res = await purchasesApi.getSubscriptions();
        if (res.success && Array.isArray(res.data)) {
          setSubs(res.data);
        } else if (!res.success && "error" in res) {
          setError(res.error.message);
        }
      } catch {
        setError("Failed to load subscriptions.");
      } finally {
        setLoading(false);
      }
    }
    fetchSubs();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-slate-900">Subscriptions</h1>

      {error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center">
          <p className="text-sm font-medium text-slate-700 mb-2">
            Please log in to view your subscriptions.
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
          {Array.from({ length: 3 }).map((_, i) => (
            <SubSkeleton key={i} />
          ))}
        </div>
      ) : !error && subs.length === 0 ? (
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-12 text-center">
          <p className="text-2xl mb-2">{"\uD83D\uDD01"}</p>
          <p className="text-sm font-semibold text-slate-700">No subscriptions detected</p>
          <p className="text-xs text-slate-500 mt-1">
            Auto-renew subscriptions are detected from your inbox emails.
          </p>
        </div>
      ) : !error ? (
        <div className="flex flex-col gap-3">
          {subs.map((sub) => (
            <div
              key={sub.id}
              className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-4"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-slate-800">
                    {sub.serviceName}
                  </p>
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                      sub.isActive
                        ? "text-green-600 bg-green-50"
                        : "text-slate-500 bg-slate-100"
                    }`}
                  >
                    {sub.isActive ? "Active" : "Inactive"}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  {sub.marketplace} · {sub.frequency}
                </p>
                {sub.nextChargeDate && (
                  <p className="text-xs text-slate-400 mt-0.5">
                    Next charge: {formatDate(sub.nextChargeDate)}
                  </p>
                )}
              </div>
              <div className="text-right shrink-0">
                <p className="text-sm font-bold text-slate-900">
                  {formatPrice(sub.amount)}
                </p>
                <p className="text-xs text-slate-400 capitalize">/{sub.frequency}</p>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
