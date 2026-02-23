"use client";

import { useState, useEffect } from "react";
import { authApi, whydudEmailApi, cardVaultApi } from "@/lib/api/auth";
import type { User, WhydudEmail, PaymentMethod } from "@/types";

const TABS = [
  "Profile",
  "@whyd.xyz",
  "Card Vault",
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

      <div>
        <h3 className="text-sm font-semibold text-slate-800 mb-2">
          Change password
        </h3>
        <div className="flex flex-col gap-3">
          <input
            type="password"
            placeholder="Current password"
            className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm outline-none placeholder:text-slate-400 focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
          />
          <input
            type="password"
            placeholder="New password"
            className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm outline-none placeholder:text-slate-400 focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
          />
          <button className="self-start rounded-lg border border-[#E2E8F0] px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]">
            Update password
          </button>
        </div>
      </div>
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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchSettings() {
      try {
        const [userRes, emailRes, cardsRes] = await Promise.all([
          authApi.me(),
          whydudEmailApi.getStatus(),
          cardVaultApi.list(),
        ]);

        if (userRes.success && "data" in userRes) setUser(userRes.data);
        if (emailRes.success && "data" in emailRes) setWhydEmail(emailRes.data);
        if (cardsRes.success && "data" in cardsRes) setCards(cardsRes.data);
      } catch {
        // Tabs show empty/default state on failure
      } finally {
        setLoading(false);
      }
    }
    fetchSettings();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-slate-900">Settings</h1>

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
      {activeTab === "Card Vault" && <CardVaultTab cards={cards} loading={loading} />}
      {activeTab === "TCO Preferences" && <TCOPreferencesTab />}
      {activeTab === "Subscription" && <SubscriptionTab user={user} />}
      {activeTab === "Data & Privacy" && <DataPrivacyTab />}
    </div>
  );
}
