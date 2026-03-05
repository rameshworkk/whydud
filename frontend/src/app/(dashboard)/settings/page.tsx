"use client";

import { useState, useEffect } from "react";
import { authApi, whydudEmailApi, cardVaultApi, marketplacePreferencesApi } from "@/lib/api/auth";
import type { User, WhydudEmail, PaymentMethod, MarketplacePreference, MarketplaceInfo } from "@/types";
import { NotificationPreferencesTab } from "@/components/settings/NotificationPreferences";

const TABS = [
  "Profile",
  "@whyd.xyz",
  "Marketplaces",
  "Card Vault",
  "Notifications",
  "TCO Preferences",
  "Subscription",
  "Data & Privacy",
] as const;

type Tab = (typeof TABS)[number];

const MARKETPLACES = [
  "Amazon.in",
  "Flipkart",
  "Myntra",
  "Ajio",
  "Nykaa",
  "Croma",
];

function TabSkeleton() {
  return (
    <div className="max-w-lg flex flex-col gap-5 animate-pulse">
      <div className="w-48 h-4 rounded bg-slate-200" />
      <div className="w-full h-10 rounded-lg bg-slate-200" />
      <div className="w-full h-10 rounded-lg bg-slate-200" />
      <div className="w-full h-10 rounded-lg bg-slate-200" />
      <div className="w-24 h-10 rounded-lg bg-slate-200" />
    </div>
  );
}

function ProfileTab({ user, loading }: { user: User | null; loading: boolean }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [pwLoading, setPwLoading] = useState(false);
  const [pwMessage, setPwMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    setPwMessage(null);
    setPwLoading(true);

    const res = await authApi.changePassword({ currentPassword, newPassword });

    if (res.success && "data" in res) {
      // Update stored token since backend re-creates it
      const { setToken } = await import("@/lib/api/client");
      setToken(res.data.token);
      setPwMessage({ type: "success", text: "Password updated successfully." });
      setCurrentPassword("");
      setNewPassword("");
    } else if (!res.success && "error" in res) {
      setPwMessage({ type: "error", text: res.error.message });
    }

    setPwLoading(false);
  }

  if (loading) return <TabSkeleton />;

  return (
    <div className="max-w-lg flex flex-col gap-5">
      <div className="flex items-center gap-4">
        <div className="w-16 h-16 rounded-full bg-[#F97316] flex items-center justify-center text-white text-xl font-bold">
          {user?.name?.charAt(0)?.toUpperCase() ?? "U"}
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-800">{user?.name ?? "—"}</p>
          <button className="text-xs text-[#F97316] hover:text-[#EA580C] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
            Change photo
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-slate-700">Full name</label>
        <input
          defaultValue={user?.name ?? ""}
          className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-slate-700">Email</label>
        <input
          defaultValue={user?.email ?? ""}
          disabled
          className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-2.5 text-sm text-slate-500"
        />
        <p className="text-xs text-slate-400">
          Email cannot be changed. Contact support if needed.
        </p>
      </div>

      <button className="self-start rounded-lg bg-[#F97316] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2">
        Save changes
      </button>

      <hr className="border-[#E2E8F0]" />

      <form onSubmit={handleChangePassword}>
        <h3 className="text-sm font-semibold text-slate-800 mb-2">
          Change password
        </h3>

        {pwMessage && (
          <div className={`rounded-lg border px-4 py-3 text-sm mb-3 ${
            pwMessage.type === "success"
              ? "border-green-200 bg-green-50 text-green-700"
              : "border-red-200 bg-red-50 text-red-700"
          }`}>
            {pwMessage.text}
          </div>
        )}

        <div className="flex flex-col gap-3">
          <input
            type="password"
            placeholder="Current password"
            required
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm outline-none placeholder:text-slate-400 focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
          />
          <input
            type="password"
            placeholder="New password (min 8 characters)"
            required
            minLength={8}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm outline-none placeholder:text-slate-400 focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
          />
          <button
            type="submit"
            disabled={pwLoading}
            className="self-start rounded-lg border border-[#E2E8F0] px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {pwLoading ? "Updating…" : "Update password"}
          </button>
        </div>
      </form>
    </div>
  );
}

function WhydEmailTab({ whydEmail, loading }: { whydEmail: WhydudEmail | null; loading: boolean }) {
  if (loading) return <TabSkeleton />;

  return (
    <div className="max-w-lg flex flex-col gap-5">
      {whydEmail ? (
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-slate-800">
              {whydEmail.emailAddress}
            </span>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
              whydEmail.isActive
                ? "text-green-600 bg-green-50"
                : "text-slate-500 bg-slate-100"
            }`}>
              {whydEmail.isActive ? "Active" : "Inactive"}
            </span>
          </div>
          <div className="flex gap-4 text-xs text-slate-500 mt-1">
            <span>{whydEmail.totalEmailsReceived} emails received</span>
            <span>{whydEmail.totalOrdersDetected} orders tracked</span>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-[#E2E8F0] bg-white p-8 text-center">
          <p className="text-sm text-slate-500">No @whyd.xyz email set up yet.</p>
          <button className="mt-3 rounded-lg bg-[#F97316] px-4 py-2 text-sm font-semibold text-white hover:bg-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2">
            Create @whyd.xyz email
          </button>
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold text-slate-800 mb-3">
          Marketplace setup
        </h3>
        <div className="flex flex-col gap-2">
          {MARKETPLACES.map((mp) => {
            const connected = whydEmail?.marketplacesRegistered?.includes(mp) ?? false;
            return (
              <div
                key={mp}
                className="flex items-center justify-between rounded-lg border border-[#E2E8F0] bg-white px-4 py-3"
              >
                <span className="text-sm text-slate-700">{mp}</span>
                {connected ? (
                  <span className="text-xs font-medium text-green-600">
                    Connected
                  </span>
                ) : (
                  <button className="text-xs font-medium text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
                    Set up
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {whydEmail && (
        <>
          <hr className="border-[#E2E8F0]" />
          <div>
            <h3 className="text-sm font-semibold text-red-600 mb-2">
              Danger zone
            </h3>
            <button className="rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500">
              Deactivate @whyd.xyz email
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function CardVaultTab({ cards, loading }: { cards: PaymentMethod[]; loading: boolean }) {
  if (loading) return <TabSkeleton />;

  return (
    <div className="flex flex-col gap-5">
      <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 flex items-center gap-3">
        <span className="text-lg">🔒</span>
        <div>
          <p className="text-sm font-semibold text-green-800">
            We never store card numbers
          </p>
          <p className="text-xs text-green-600">
            Only bank name and card variant are saved for offer matching.
          </p>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-800">
            Your Cards ({cards.length})
          </h3>
          <button className="text-xs font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
            + Add card
          </button>
        </div>
        {cards.length === 0 ? (
          <div className="rounded-xl border border-dashed border-[#E2E8F0] bg-white p-8 text-center">
            <p className="text-sm text-slate-400">No cards saved yet. Add a card to get personalized bank offer matching.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {cards.map((card) => (
              <div
                key={card.id}
                className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center text-sm font-bold text-slate-600">
                    {card.bankName
                      .split(" ")
                      .map((w) => w[0])
                      .join("")}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-800">
                      {card.bankName} — {card.cardVariant}
                    </p>
                    <p className="text-xs text-slate-500">
                      {card.cardNetwork}{card.nickname ? ` · ${card.nickname}` : ""}
                    </p>
                  </div>
                </div>
                <button className="text-xs text-slate-400 hover:text-red-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <h3 className="text-sm font-semibold text-slate-800 mb-3">
          Wallets & Memberships
        </h3>
        <div className="grid grid-cols-2 gap-3">
          {["Amazon Pay", "Paytm", "Prime", "Flipkart Plus"].map((w) => (
            <div
              key={w}
              className="rounded-lg border border-[#E2E8F0] bg-white p-3 flex items-center justify-between"
            >
              <span className="text-sm text-slate-700">{w}</span>
              <span className="text-xs text-slate-400">Not linked</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function TCOPreferencesTab() {
  return (
    <div className="max-w-lg flex flex-col gap-5">
      <p className="text-sm text-slate-500">
        These preferences are used for Total Cost of Ownership calculations.
      </p>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-slate-700">City</label>
        <input
          defaultValue=""
          placeholder="Enter your city"
          className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
        />
        <p className="text-xs text-slate-400">
          Auto-fills electricity tariff and cooling days
        </p>
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-slate-700">
          Electricity tariff (₹/kWh)
        </label>
        <input
          defaultValue="8.50"
          type="number"
          step="0.10"
          className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-slate-700">
          Default ownership period (years)
        </label>
        <input
          defaultValue="5"
          type="number"
          min="1"
          max="15"
          className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-slate-700">
          AC hours per day
        </label>
        <input
          defaultValue="8"
          type="number"
          min="0"
          max="24"
          className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-slate-700">
          Washer loads per week
        </label>
        <input
          defaultValue="4"
          type="number"
          min="0"
          max="21"
          className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
        />
      </div>

      <button className="self-start rounded-lg bg-[#F97316] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2">
        Save preferences
      </button>
    </div>
  );
}

function SubscriptionTab({ user }: { user: User | null }) {
  const isPremium = user?.subscriptionTier === "premium";

  return (
    <div className="max-w-lg flex flex-col gap-5">
      <div className="rounded-xl border border-[#E2E8F0] bg-white p-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-slate-800">
            Current Plan
          </span>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
            isPremium ? "text-[#F97316] bg-orange-50" : "text-slate-500 bg-slate-100"
          }`}>
            {isPremium ? "Premium" : "Free"}
          </span>
        </div>
        <p className="text-xs text-slate-500">
          {isPremium
            ? "You're on the Premium plan. Enjoy all features."
            : "You're on the free plan. Upgrade to Premium for advanced features."}
        </p>
      </div>

      {!isPremium && (
        <div className="rounded-xl border-2 border-[#F97316] bg-[#FFF7ED] p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">⭐</span>
            <h3 className="text-base font-bold text-slate-900">
              Whydud Premium
            </h3>
          </div>
          <ul className="text-sm text-slate-600 space-y-2 mb-4">
            <li className="flex items-center gap-2">
              <span className="text-green-500">✓</span> Unlimited price alerts
            </li>
            <li className="flex items-center gap-2">
              <span className="text-green-500">✓</span> Advanced TCO calculator
            </li>
            <li className="flex items-center gap-2">
              <span className="text-green-500">✓</span> Priority deal notifications
            </li>
            <li className="flex items-center gap-2">
              <span className="text-green-500">✓</span> Export purchase data
            </li>
            <li className="flex items-center gap-2">
              <span className="text-green-500">✓</span> Ad-free experience
            </li>
          </ul>
          <div className="flex items-baseline gap-1 mb-3">
            <span className="text-2xl font-bold text-slate-900">₹199</span>
            <span className="text-sm text-slate-500">/ month</span>
          </div>
          <button className="w-full rounded-lg bg-[#F97316] py-2.5 text-sm font-semibold text-white hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2">
            Upgrade to Premium
          </button>
        </div>
      )}
    </div>
  );
}

const MARKETPLACE_BADGE_COLORS: Record<string, string> = {
  amazon_in: "bg-[#FF9900]",
  flipkart: "bg-[#2874F0]",
  myntra: "bg-[#FF3F6C]",
  snapdeal: "bg-[#E40046]",
  croma: "bg-[#67B346]",
  tatacliq: "bg-[#A51C30]",
  reliance_digital: "bg-[#0058A9]",
  nykaa: "bg-[#FC2779]",
  ajio: "bg-[#1B1B1B]",
  meesho: "bg-[#F43397]",
  jiomart: "bg-[#0070C0]",
};

const MARKETPLACE_BADGE_LABELS: Record<string, string> = {
  amazon_in: "A",
  flipkart: "F",
  myntra: "M",
  snapdeal: "S",
  croma: "C",
  tatacliq: "T",
  reliance_digital: "R",
  nykaa: "N",
  ajio: "AJ",
  meesho: "Me",
  jiomart: "J",
};

function MarketplacesTab({
  marketplacePref,
  loading,
}: {
  marketplacePref: MarketplacePreference | null;
  loading: boolean;
}) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (marketplacePref && !initialized) {
      setSelected(new Set(marketplacePref.preferredMarketplaces));
      setInitialized(true);
    }
  }, [marketplacePref, initialized]);

  if (loading) return <TabSkeleton />;

  const allMarketplaces = marketplacePref?.allMarketplaces ?? [];
  const noneSelected = selected.size === 0;

  function toggleMarketplace(id: number) {
    setMessage(null);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function selectAll() {
    setMessage(null);
    setSelected(new Set());
  }

  async function handleSave() {
    setSaving(true);
    setMessage(null);
    const res = await marketplacePreferencesApi.update(Array.from(selected));
    if (res.success) {
      setMessage({ type: "success", text: "Marketplace preferences saved." });
    } else if (!res.success && "error" in res) {
      setMessage({ type: "error", text: res.error.message });
    }
    setSaving(false);
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h3 className="text-sm font-semibold text-slate-800 mb-1">
          Marketplace Preferences
        </h3>
        <p className="text-xs text-slate-500">
          {noneSelected
            ? "You're seeing prices from all marketplaces. Select specific ones to filter."
            : `You'll only see prices and deals from ${selected.size} selected marketplace${selected.size === 1 ? "" : "s"}.`}
        </p>
      </div>

      {message && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm ${
            message.type === "success"
              ? "border-green-200 bg-green-50 text-green-700"
              : "border-red-200 bg-red-50 text-red-700"
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500">
          {noneSelected
            ? "All marketplaces shown (default)"
            : `${selected.size} of ${allMarketplaces.length} selected`}
        </span>
        {!noneSelected && (
          <button
            type="button"
            onClick={selectAll}
            className="text-xs font-medium text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
          >
            Show all
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {allMarketplaces.map((mp: MarketplaceInfo) => {
          const isChecked = noneSelected || selected.has(mp.id);
          const isExplicitlySelected = selected.has(mp.id);
          const badgeColor = MARKETPLACE_BADGE_COLORS[mp.slug] ?? "bg-slate-500";
          const badgeLabel = MARKETPLACE_BADGE_LABELS[mp.slug] ?? mp.name[0];

          return (
            <button
              key={mp.id}
              type="button"
              onClick={() => toggleMarketplace(mp.id)}
              className={`flex items-center gap-3 rounded-lg border px-4 py-3 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] ${
                isExplicitlySelected
                  ? "border-[#F97316] bg-[#FFF7ED]"
                  : noneSelected
                    ? "border-[#E2E8F0] bg-white hover:border-slate-300"
                    : "border-[#E2E8F0] bg-white opacity-50 hover:opacity-75"
              }`}
            >
              <span
                className={`inline-flex items-center justify-center w-8 h-8 rounded-md text-xs font-bold text-white shrink-0 ${badgeColor}`}
              >
                {badgeLabel}
              </span>
              <span className="text-sm font-medium text-slate-800 flex-1">
                {mp.name}
              </span>
              <div
                className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                  isExplicitlySelected
                    ? "border-[#F97316] bg-[#F97316]"
                    : "border-slate-300 bg-white"
                }`}
              >
                {isExplicitlySelected && (
                  <svg
                    className="w-3 h-3 text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={3}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
            </button>
          );
        })}
      </div>

      <button
        type="button"
        onClick={handleSave}
        disabled={saving}
        className="self-start rounded-lg bg-[#F97316] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {saving ? "Saving..." : "Save Preferences"}
      </button>
    </div>
  );
}

function DataPrivacyTab() {
  return (
    <div className="max-w-lg flex flex-col gap-5">
      <div>
        <h3 className="text-sm font-semibold text-slate-800 mb-3">
          Connected Services
        </h3>
        <div className="flex flex-col gap-2">
          {[
            { name: "Gmail (Google OAuth)", status: "Connected" },
            { name: "@whyd.xyz Email", status: "Active" },
          ].map((svc) => (
            <div
              key={svc.name}
              className="flex items-center justify-between rounded-lg border border-[#E2E8F0] bg-white px-4 py-3"
            >
              <span className="text-sm text-slate-700">{svc.name}</span>
              <div className="flex items-center gap-3">
                <span className="text-xs font-medium text-green-600">
                  {svc.status}
                </span>
                <button className="text-xs text-slate-400 hover:text-red-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
                  Disconnect
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <hr className="border-[#E2E8F0]" />

      <div>
        <h3 className="text-sm font-semibold text-slate-800 mb-2">
          Export my data
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          Download all your data as a JSON file.
        </p>
        <button className="rounded-lg border border-[#E2E8F0] px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]">
          Request data export
        </button>
      </div>

      <hr className="border-[#E2E8F0]" />

      <div>
        <h3 className="text-sm font-semibold text-red-600 mb-2">
          Delete account
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          Permanently delete your account and all associated data. This action
          cannot be undone.
        </p>
        <button className="rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500">
          Delete my account
        </button>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("Profile");
  const [user, setUser] = useState<User | null>(null);
  const [whydEmail, setWhydEmail] = useState<WhydudEmail | null>(null);
  const [cards, setCards] = useState<PaymentMethod[]>([]);
  const [marketplacePref, setMarketplacePref] = useState<MarketplacePreference | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchSettings() {
      try {
        const [userRes, emailRes, cardsRes, mpRes] = await Promise.all([
          authApi.me(),
          whydudEmailApi.getStatus(),
          cardVaultApi.list(),
          marketplacePreferencesApi.get(),
        ]);

        if (userRes.success && "data" in userRes) setUser(userRes.data);
        if (emailRes.success && "data" in emailRes) setWhydEmail(emailRes.data);
        if (cardsRes.success && "data" in cardsRes) setCards(cardsRes.data);
        if (mpRes.success && "data" in mpRes) setMarketplacePref(mpRes.data);

        // If all requests failed, show error
        if (!userRes.success && !emailRes.success && !cardsRes.success) {
          setError("Failed to load settings.");
        }
      } catch {
        setError("Failed to load settings.");
      } finally {
        setLoading(false);
      }
    }
    fetchSettings();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-slate-900">Settings</h1>

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm font-medium text-slate-700 mb-1">
            Something went wrong
          </p>
          <p className="text-xs text-slate-500">{error}</p>
        </div>
      )}

      {/* Tab navigation */}
      <div className="flex gap-1 border-b border-[#E2E8F0] overflow-x-auto no-scrollbar">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`shrink-0 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded-t ${
              tab === activeTab
                ? "border-[#F97316] text-[#F97316]"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "Profile" && <ProfileTab user={user} loading={loading} />}
      {activeTab === "@whyd.xyz" && <WhydEmailTab whydEmail={whydEmail} loading={loading} />}
      {activeTab === "Marketplaces" && <MarketplacesTab marketplacePref={marketplacePref} loading={loading} />}
      {activeTab === "Card Vault" && <CardVaultTab cards={cards} loading={loading} />}
      {activeTab === "Notifications" && <NotificationPreferencesTab />}
      {activeTab === "TCO Preferences" && <TCOPreferencesTab />}
      {activeTab === "Subscription" && <SubscriptionTab user={user} />}
      {activeTab === "Data & Privacy" && <DataPrivacyTab />}
    </div>
  );
}
