"use client";

import { useState, useEffect } from "react";
import { rewardsApi } from "@/lib/api/rewards";
import { formatPrice } from "@/lib/utils/format";
import type { RewardBalance, GiftCard, RewardPointsLedger } from "@/types";

/** Static earn cards — these describe how to earn points, not fetched from API */
const EARN_CARDS = [
  { icon: "\u270D\uFE0F", title: "Write a Review", points: 20, description: "Write a review for a product you've purchased" },
  { icon: "\uD83D\uDCE7", title: "Connect Email", points: 50, description: "Connect your shopping email to start tracking" },
  { icon: "\uD83D\uDC65", title: "Refer a Friend", points: 30, description: "Invite a friend to join Whydud" },
  { icon: "\uD83D\uDD25", title: "Login Streak", points: 10, description: "Log in for 7 consecutive days" },
];

function BalanceSkeleton() {
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-6 animate-pulse">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="w-20 h-3 rounded bg-slate-200 mb-2" />
          <div className="w-40 h-7 rounded bg-slate-200" />
        </div>
        <div className="text-right">
          <div className="w-24 h-2.5 rounded bg-slate-200 mb-1" />
          <div className="w-24 h-2.5 rounded bg-slate-200" />
        </div>
      </div>
      <div className="h-3 rounded-full bg-slate-200" />
    </div>
  );
}

function GiftCardSkeleton() {
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex flex-col items-center animate-pulse">
      <div className="w-12 h-12 rounded-lg bg-slate-200 mb-2" />
      <div className="w-16 h-3.5 rounded bg-slate-200 mb-1" />
      <div className="w-20 h-4 rounded bg-slate-200 mb-1" />
      <div className="w-14 h-2.5 rounded bg-slate-200 mb-3" />
      <div className="w-full h-8 rounded-lg bg-slate-200" />
    </div>
  );
}

export default function RewardsPage() {
  const [balance, setBalance] = useState<RewardBalance | null>(null);
  const [giftCards, setGiftCards] = useState<GiftCard[]>([]);
  const [history, setHistory] = useState<RewardPointsLedger[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchAll() {
      try {
        const [balanceRes, giftCardsRes, historyRes] = await Promise.all([
          rewardsApi.getBalance(),
          rewardsApi.getGiftCards(),
          rewardsApi.getHistory(),
        ]);

        if (balanceRes.success && "data" in balanceRes) {
          setBalance(balanceRes.data);
        }
        if (giftCardsRes.success && "data" in giftCardsRes) {
          setGiftCards(giftCardsRes.data);
        }
        if (historyRes.success && "data" in historyRes) {
          setHistory(historyRes.data);
        }

        // Check if all failed
        if (
          (!balanceRes.success) &&
          (!giftCardsRes.success) &&
          (!historyRes.success)
        ) {
          const err = !balanceRes.success && "error" in balanceRes ? balanceRes.error.message : "Failed to load rewards data.";
          setError(err);
        }
      } catch {
        setError("Failed to load rewards data.");
      } finally {
        setLoading(false);
      }
    }
    fetchAll();
  }, []);

  const currentBalance = balance?.currentBalance ?? 0;
  // Estimate value: 1 point = ~0.1 rupee (10 paisa)
  const valueInRupees = Math.round(currentBalance * 0.1);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-slate-900">Rewards</h1>

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm font-medium text-slate-700 mb-1">
            Something went wrong
          </p>
          <p className="text-xs text-slate-500">{error}</p>
        </div>
      )}

      {/* Balance card */}
      {loading ? (
        <BalanceSkeleton />
      ) : balance ? (
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-6">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm text-slate-500">Your Balance</p>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-3xl font-bold text-slate-900">
                  {balance.currentBalance.toLocaleString("en-IN")} points
                </span>
                <span className="text-sm text-slate-400">
                  {"\u2248"} {"\u20B9"}{valueInRupees} value
                </span>
              </div>
            </div>
            <div className="text-right text-xs text-slate-400">
              <p>Earned: {balance.totalEarned.toLocaleString("en-IN")}</p>
              <p>Spent: {balance.totalSpent.toLocaleString("en-IN")}</p>
              {balance.totalExpired > 0 && (
                <p>Expired: {balance.totalExpired.toLocaleString("en-IN")}</p>
              )}
            </div>
          </div>
          {/* Progress bar — show progress toward a milestone (e.g., 1000 points) */}
          {(() => {
            const nextMilestone = 1000;
            const progressPct = Math.min((balance.currentBalance / nextMilestone) * 100, 100);
            const remaining = Math.max(nextMilestone - balance.currentBalance, 0);
            return (
              <>
                <div className="h-3 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-[#F97316] transition-all"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
                {remaining > 0 && (
                  <p className="text-xs text-slate-500 mt-2">
                    {remaining.toLocaleString("en-IN")} more points to reach {nextMilestone.toLocaleString("en-IN")} points
                  </p>
                )}
              </>
            );
          })()}
        </div>
      ) : !error ? (
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-12 text-center">
          <p className="text-2xl mb-2">{"\uD83C\uDFC6"}</p>
          <p className="text-sm font-semibold text-slate-700">No rewards data available</p>
          <p className="text-xs text-slate-500 mt-1">
            Start using Whydud to earn reward points.
          </p>
        </div>
      ) : null}

      {/* How to Earn */}
      <div>
        <h2 className="text-base font-bold text-slate-900 mb-3">
          How to Earn
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {EARN_CARDS.map((card) => (
            <div
              key={card.title}
              className="rounded-xl border border-[#E2E8F0] bg-white p-4 hover:shadow-sm transition-shadow"
            >
              <span className="text-2xl block mb-2">{card.icon}</span>
              <p className="text-sm font-semibold text-slate-800">
                {card.title}
              </p>
              <p className="text-xs font-bold text-[#F97316] mt-1">
                +{card.points} pts
              </p>
              <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                {card.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Redeem Gift Cards */}
      <div>
        <h2 className="text-base font-bold text-slate-900 mb-3">
          Redeem Gift Cards
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {loading
            ? Array.from({ length: 4 }).map((_, i) => <GiftCardSkeleton key={i} />)
            : giftCards.length === 0
            ? (
              <div className="col-span-full rounded-xl border border-[#E2E8F0] bg-white p-8 text-center">
                <p className="text-sm text-slate-400">
                  No gift cards available at the moment. Check back later.
                </p>
              </div>
            )
            : giftCards.map((gc) => {
              // Use the first denomination as default display
              const denomination = gc.denominations.length > 0 ? gc.denominations[0]! : 0;
              // Rough estimate: 100 paisa per point for redemption
              const pointsCost = Math.round(denomination / 10);

              return (
                <div
                  key={gc.id}
                  className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex flex-col items-center text-center"
                >
                  {gc.brandLogoUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={gc.brandLogoUrl}
                      alt={gc.brandName}
                      className="w-10 h-10 rounded-lg object-contain mb-2"
                    />
                  ) : (
                    <span className="text-3xl mb-2">{"\uD83C\uDF81"}</span>
                  )}
                  <p className="text-sm font-semibold text-slate-800">
                    {gc.brandName}
                  </p>
                  {gc.denominations.length > 0 && (
                    <p className="text-base font-bold text-slate-900 mt-1">
                      {formatPrice(denomination)}
                    </p>
                  )}
                  {gc.denominations.length > 1 && (
                    <p className="text-[10px] text-slate-400">
                      +{gc.denominations.length - 1} more options
                    </p>
                  )}
                  <p className="text-xs text-slate-400 mt-0.5">
                    {pointsCost.toLocaleString("en-IN")} pts
                  </p>
                  <button
                    disabled={currentBalance < pointsCost}
                    className="mt-3 w-full rounded-lg bg-[#F97316] py-2 text-xs font-semibold text-white hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Redeem
                  </button>
                </div>
              );
            })}
        </div>
      </div>

      {/* Points History */}
      <div>
        <h2 className="text-base font-bold text-slate-900 mb-3">
          Points History
        </h2>
        {loading ? (
          <div className="rounded-xl border border-[#E2E8F0] bg-white overflow-hidden animate-pulse">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className={`flex items-center justify-between px-5 py-3 ${
                  i < 4 ? "border-b border-[#F1F5F9]" : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-3.5 rounded bg-slate-200" />
                  <div className="w-40 h-3 rounded bg-slate-200" />
                </div>
                <div className="w-16 h-2.5 rounded bg-slate-200" />
              </div>
            ))}
          </div>
        ) : history.length === 0 ? (
          <div className="rounded-xl border border-[#E2E8F0] bg-white p-8 text-center">
            <p className="text-sm text-slate-400">
              No points history yet. Start earning points to see your activity here.
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-[#E2E8F0] bg-white overflow-hidden">
            {history.map((entry, i) => (
              <div
                key={entry.id}
                className={`flex items-center justify-between px-5 py-3 ${
                  i < history.length - 1
                    ? "border-b border-[#F1F5F9]"
                    : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`text-sm font-bold w-14 ${
                      entry.points >= 0 ? "text-green-600" : "text-red-500"
                    }`}
                  >
                    {entry.points >= 0 ? "+" : ""}
                    {entry.points}
                  </span>
                  <span className="text-sm text-slate-700">
                    {entry.description}
                  </span>
                </div>
                <span className="text-xs text-slate-400 shrink-0">
                  {new Date(entry.createdAt).toLocaleDateString("en-IN", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                  })}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
