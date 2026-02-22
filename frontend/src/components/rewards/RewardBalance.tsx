import type { RewardBalance as RewardBalanceType } from "@/types";

interface RewardBalanceProps {
  balance: RewardBalanceType | null;
  isLoading?: boolean;
}

/** Rewards points balance card. */
export function RewardBalance({ balance, isLoading }: RewardBalanceProps) {
  if (isLoading) {
    return <div className="h-28 animate-pulse rounded-xl bg-muted" />;
  }

  return (
    <div className="rounded-xl border bg-card p-6">
      <p className="text-sm text-muted-foreground">Available Points</p>
      <p className="mt-1 text-4xl font-black">
        {balance?.currentBalance.toLocaleString("en-IN") ?? "—"}
      </p>
      <div className="mt-4 flex gap-4 text-xs text-muted-foreground">
        <span>Earned {balance?.totalEarned.toLocaleString("en-IN") ?? 0}</span>
        <span>Spent {balance?.totalSpent.toLocaleString("en-IN") ?? 0}</span>
      </div>
    </div>
  );
}
