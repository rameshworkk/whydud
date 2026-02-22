import type { Metadata } from "next";

export const metadata: Metadata = { title: "Settings" };

export default function SettingsPage() {
  // TODO Sprint 1 Week 2 onwards: Profile, @whyd.xyz, Card Vault, TCO, Subscription tabs
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      <div className="flex gap-2 border-b pb-2">
        {["Profile", "@whyd.xyz", "Card Vault", "TCO Preferences", "Subscription"].map((tab) => (
          <button
            key={tab}
            className="px-3 py-1.5 text-sm rounded-t-lg first:bg-primary first:text-primary-foreground hover:bg-muted"
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Profile section placeholder */}
      <div className="flex flex-col gap-4 max-w-md">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">Full name</label>
          <input className="rounded-lg border bg-muted px-3 py-2 text-sm" placeholder="Your name" />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">Email</label>
          <input className="rounded-lg border bg-muted px-3 py-2 text-sm" disabled />
        </div>
        <button className="self-start rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
          Save changes
        </button>
      </div>
    </div>
  );
}
