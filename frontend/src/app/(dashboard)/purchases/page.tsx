import type { Metadata } from "next";
import { purchasesApi } from "@/lib/api/inbox";
import { formatPrice, formatDate } from "@/lib/utils";

export const metadata: Metadata = { title: "Purchase History" };

export default async function PurchasesPage() {
  const res = await purchasesApi.list().catch(() => null);
  const orders = res?.success ? res.data.data : [];

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Purchase History</h1>

      {orders.length === 0 ? (
        <div className="rounded-2xl border border-dashed p-12 text-center text-muted-foreground">
          <p>No purchases detected yet.</p>
          <p className="mt-1 text-sm">Connect your @whyd.xyz email to auto-track orders.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {orders.map((order) => (
            <div key={order.id} className="flex items-center gap-4 rounded-xl border bg-card p-4">
              <div className="flex-1">
                <p className="font-medium text-sm">{order.productName}</p>
                <p className="text-xs text-muted-foreground">
                  {order.marketplace} · {formatDate(order.orderDate)}
                </p>
              </div>
              <div className="text-right">
                <p className="font-semibold">{formatPrice(order.totalAmount)}</p>
                <p className="text-xs capitalize text-muted-foreground">{order.source.replace("_", " ")}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
