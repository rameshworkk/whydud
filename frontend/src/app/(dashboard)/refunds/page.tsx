import type { Metadata } from "next";
import { purchasesApi } from "@/lib/api/inbox";
import { formatPrice, formatDate } from "@/lib/utils";

export const metadata: Metadata = { title: "Refund Tracker" };

const STATUS_STYLES: Record<string, string> = {
  initiated: "text-blue-600 bg-blue-50",
  processing: "text-yellow-600 bg-yellow-50",
  completed: "text-green-600 bg-green-50",
  failed: "text-red-600 bg-red-50",
};

export default async function RefundsPage() {
  const res = await purchasesApi.getRefunds().catch(() => null);
  const refunds = res?.success && Array.isArray(res.data) ? res.data : [];

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-slate-900">Refund Tracker</h1>

      {refunds.length === 0 ? (
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-12 text-center">
          <p className="text-2xl mb-2">💰</p>
          <p className="text-sm font-semibold text-slate-700">No refunds tracked</p>
          <p className="text-xs text-slate-500 mt-1">
            Refund delays will be auto-detected from your inbox.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {refunds.map((refund) => (
            <div key={refund.id} className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-800 line-clamp-1">
                  {refund.productName}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {refund.marketplace} · Order #{refund.order.slice(0, 8)}
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
                <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full mt-1 capitalize ${
                  STATUS_STYLES[refund.status] ?? "text-slate-500 bg-slate-100"
                }`}>
                  {refund.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
