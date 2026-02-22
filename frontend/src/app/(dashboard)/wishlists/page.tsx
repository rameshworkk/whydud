import type { Metadata } from "next";
import { wishlistsApi } from "@/lib/api/wishlists";

export const metadata: Metadata = { title: "My Wishlists" };

export default async function WishlistsPage() {
  // TODO Sprint 3 Week 9
  const res = await wishlistsApi.list().catch(() => null);
  const wishlists = res?.success ? res.data : [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">My Wishlists</h1>
        <button className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
          + New wishlist
        </button>
      </div>

      {wishlists.length === 0 ? (
        <div className="rounded-2xl border border-dashed p-12 text-center text-muted-foreground">
          <p>No wishlists yet.</p>
          <p className="mt-1 text-sm">Browse products and add items to track prices.</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {wishlists.map((wl) => (
            <div key={wl.id} className="rounded-xl border bg-card p-4">
              <p className="font-semibold">{wl.name}</p>
              <p className="text-sm text-muted-foreground">{wl.items.length} items</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
