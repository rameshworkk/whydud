"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Switch } from "@/components/ui/switch";
import { notificationsApi } from "@/lib/api/notifications";
import type { NotificationPreferences, NotificationChannel } from "@/lib/api/types";

/** Row config: key must match NotificationPreferences field names. */
const NOTIFICATION_ROWS: {
  key: keyof NotificationPreferences;
  label: string;
  description: string;
}[] = [
  { key: "priceDrops", label: "Price Drops", description: "When a tracked product's price decreases" },
  { key: "returnWindows", label: "Return Windows", description: "Reminders before return windows close" },
  { key: "refundDelays", label: "Refund Delays", description: "Alerts when refunds are taking too long" },
  { key: "backInStock", label: "Back in Stock", description: "When an out-of-stock product returns" },
  { key: "reviewUpvotes", label: "Review Upvotes", description: "When someone upvotes your review" },
  { key: "priceAlerts", label: "Price Alerts", description: "When a product hits your target price" },
  { key: "discussionReplies", label: "Discussion Replies", description: "Replies to your discussion threads" },
  { key: "levelUp", label: "Level Up", description: "When you reach a new reviewer level" },
  { key: "pointsEarned", label: "Points Earned", description: "When you earn reward points" },
];

const DEBOUNCE_MS = 800;

export function NotificationPreferencesTab() {
  const [prefs, setPrefs] = useState<NotificationPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingRef = useRef<Partial<NotificationPreferences>>({});

  useEffect(() => {
    async function load() {
      const res = await notificationsApi.getPreferences();
      if (res.success && "data" in res) {
        setPrefs(res.data);
      }
      setLoading(false);
    }
    load();
  }, []);

  const flush = useCallback(async () => {
    const patch = { ...pendingRef.current };
    pendingRef.current = {};
    if (Object.keys(patch).length === 0) return;

    setSaving(true);
    setMessage(null);
    const res = await notificationsApi.updatePreferences(patch);
    if (res.success && "data" in res) {
      setPrefs(res.data);
      setMessage({ type: "success", text: "Preferences saved." });
    } else if (!res.success && "error" in res) {
      setMessage({ type: "error", text: res.error.message });
    }
    setSaving(false);
  }, []);

  function toggle(key: keyof NotificationPreferences, channel: keyof NotificationChannel) {
    if (!prefs) return;

    const current = prefs[key];
    const updated: NotificationChannel = { ...current, [channel]: !current[channel] };

    // Optimistic update
    setPrefs({ ...prefs, [key]: updated });

    // Accumulate pending changes
    pendingRef.current[key] = updated;

    // Debounce the API call
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(flush, DEBOUNCE_MS);
  }

  // Flush on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        flush();
      }
    };
  }, [flush]);

  if (loading) {
    return (
      <div className="max-w-2xl flex flex-col gap-5 animate-pulse">
        <div className="w-48 h-4 rounded bg-slate-200" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="w-full h-12 rounded-lg bg-slate-200" />
        ))}
      </div>
    );
  }

  if (!prefs) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm font-medium text-slate-700">Failed to load notification preferences.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5 max-w-2xl">
      <div>
        <h3 className="text-sm font-semibold text-slate-800 mb-1">
          Notification Preferences
        </h3>
        <p className="text-xs text-slate-500">
          Choose how you want to be notified for each event type.
        </p>
      </div>

      {message && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm transition-opacity ${
            message.type === "success"
              ? "border-green-200 bg-green-50 text-green-700"
              : "border-red-200 bg-red-50 text-red-700"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Table */}
      <div className="rounded-lg border border-[#E2E8F0] overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-[1fr_80px_80px] bg-[#F8FAFC] px-4 py-3 border-b border-[#E2E8F0]">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Notification Type
          </span>
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider text-center">
            In-App
          </span>
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider text-center">
            Email
          </span>
        </div>

        {/* Rows */}
        {NOTIFICATION_ROWS.map((row, i) => {
          const channel = prefs[row.key];
          const isLast = i === NOTIFICATION_ROWS.length - 1;

          return (
            <div
              key={row.key}
              className={`grid grid-cols-[1fr_80px_80px] items-center px-4 py-3 bg-white hover:bg-[#F8FAFC] transition-colors ${
                !isLast ? "border-b border-[#E2E8F0]" : ""
              }`}
            >
              <div>
                <p className="text-sm font-medium text-slate-800">{row.label}</p>
                <p className="text-xs text-slate-400">{row.description}</p>
              </div>
              <div className="flex justify-center">
                <Switch
                  checked={channel.inApp}
                  onCheckedChange={() => toggle(row.key, "inApp")}
                  aria-label={`${row.label} in-app notifications`}
                  className="data-[state=checked]:bg-[#F97316]"
                />
              </div>
              <div className="flex justify-center">
                <Switch
                  checked={channel.email}
                  onCheckedChange={() => toggle(row.key, "email")}
                  aria-label={`${row.label} email notifications`}
                  className="data-[state=checked]:bg-[#F97316]"
                />
              </div>
            </div>
          );
        })}
      </div>

      {saving && (
        <p className="text-xs text-slate-400">Saving...</p>
      )}
    </div>
  );
}
