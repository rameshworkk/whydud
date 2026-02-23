"use client";

import {
  MOCK_BALANCE,
  MOCK_EARN_CARDS,
  MOCK_GIFT_CARDS,
  MOCK_POINTS_HISTORY,
} from "@/lib/mock-rewards-data";
import { formatPrice } from "@/lib/utils/format";

export default function RewardsPage() {
  const b = MOCK_BALANCE;
  const progressPct = (b.currentBalance / b.nextMilestone) * 100;
  const remaining = b.nextMilestone - b.currentBalance;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-slate-900">Rewards</h1>

      {/* Balance card */}
      <div className="rounded-xl border border-[#E2E8F0] bg-white p-6">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-sm text-slate-500">Your Balance</p>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-3xl font-bold text-slate-900">
                {b.currentBalance.toLocaleString("en-IN")} points
              </span>
              <span className="text-sm text-slate-400">
                ≈ ₹{b.valueInRupees} value
              </span>
            </div>
          </div>
          <div className="text-right text-xs text-slate-400">
            <p>Earned: {b.totalEarned.toLocaleString("en-IN")}</p>
            <p>Spent: {b.totalSpent.toLocaleString("en-IN")}</p>
          </div>
        </div>
        <div className="h-3 rounded-full bg-slate-100 overflow-hidden">
          <div
            className="h-full rounded-full bg-[#F97316] transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <p className="text-xs text-slate-500 mt-2">
          {remaining.toLocaleString("en-IN")} more points for{" "}
          {b.nextMilestoneReward}
        </p>
      </div>

      {/* How to Earn */}
      <div>
        <h2 className="text-base font-bold text-slate-900 mb-3">
          How to Earn
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {MOCK_EARN_CARDS.map((card) => (
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
          {MOCK_GIFT_CARDS.map((gc) => (
            <div
              key={gc.id}
              className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex flex-col items-center text-center"
            >
              <span className="text-3xl mb-2">{gc.logo}</span>
              <p className="text-sm font-semibold text-slate-800">
                {gc.brand}
              </p>
              <p className="text-base font-bold text-slate-900 mt-1">
                {formatPrice(gc.denomination)}
              </p>
              <p className="text-xs text-slate-400 mt-0.5">
                {gc.pointsCost.toLocaleString("en-IN")} pts
              </p>
              <button
                disabled={b.currentBalance < gc.pointsCost}
                className="mt-3 w-full rounded-lg bg-[#F97316] py-2 text-xs font-semibold text-white hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Redeem
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Points History */}
      <div>
        <h2 className="text-base font-bold text-slate-900 mb-3">
          Points History
        </h2>
        <div className="rounded-xl border border-[#E2E8F0] bg-white overflow-hidden">
          {MOCK_POINTS_HISTORY.map((entry, i) => (
            <div
              key={entry.id}
              className={`flex items-center justify-between px-5 py-3 ${
                i < MOCK_POINTS_HISTORY.length - 1
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
                {new Date(entry.date).toLocaleDateString("en-IN", {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                })}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
