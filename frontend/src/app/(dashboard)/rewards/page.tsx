import type { Metadata } from "next";
import { RewardBalance } from "@/components/rewards/RewardBalance";
import { rewardsApi } from "@/lib/api/rewards";

export const metadata: Metadata = { title: "Rewards & Gift Cards" };

export default async function RewardsPage() {
  const [balanceRes, catalogRes] = await Promise.allSettled([
    rewardsApi.getBalance(),
    rewardsApi.getGiftCards(),
  ]);

  const balance = balanceRes.status === "fulfilled" && balanceRes.value.success
    ? balanceRes.value.data
    : null;

  const giftCards = catalogRes.status === "fulfilled" && catalogRes.value.success
    ? catalogRes.value.data
    : [];

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Rewards & Gift Cards</h1>

      <RewardBalance balance={balance} />

      <div>
        <h2 className="text-lg font-semibold mb-3">Redeem Points</h2>
        {giftCards.length > 0 ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {giftCards.map((card) => (
              <div key={card.id} className="rounded-xl border bg-card p-4">
                <p className="font-semibold">{card.brandName}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  ₹{card.denominations.join(" / ₹")}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed p-10 text-center text-muted-foreground text-sm">
            Gift card catalog launching in Sprint 4 (Week 11).
          </div>
        )}
      </div>
    </div>
  );
}
