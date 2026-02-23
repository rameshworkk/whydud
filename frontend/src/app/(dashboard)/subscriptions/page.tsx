import type { Metadata } from "next";
import { purchasesApi } from "@/lib/api/inbox";
import { formatPrice, formatDate } from "@/lib/utils";

export const metadata: Metadata = { title: "Subscription Tracker" };

export default async function SubscriptionsPage() {
  const res = await purchasesApi.getSubscriptions().catch(() => null);
  const subs = res?.success && Array.isArray(res.data) ? res.data : [];

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-slate-900">Subscriptions</h1>

      {subs.length === 0 ? (
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-12 text-center">
          <p className="text-2xl mb-2">🔁</p>
          <p className="text-sm font-semibold text-slate-700">No subscriptions detected</p>
          <p className="text-xs text-slate-500 mt-1">
            Auto-renew subscriptions are detected from your inbox emails.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {subs.map((sub) => (
            <div key={sub.id} className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-slate-800">
                    {sub.serviceName}
                  </p>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                    sub.isActive ? "text-green-600 bg-green-50" : "text-slate-500 bg-slate-100"
                  }`}>
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
                <p className="text-xs text-slate-400 capitalize">
                  /{sub.frequency}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
