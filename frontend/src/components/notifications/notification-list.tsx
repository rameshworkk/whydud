"use client";

import { useState, useEffect, useCallback } from "react";
import { Bell, CheckCheck, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils/index";
import { notificationsApi } from "@/lib/api/notifications";
import { NotificationCard } from "./notification-card";
import type { Notification } from "@/lib/api/types";
import type { PaginatedApiResponse } from "@/types/api";

// ── Filter tabs ───────────────────────────────────────────────────────────────

interface FilterTab {
  key: string;
  label: string;
  types: string[];
}

const FILTER_TABS: FilterTab[] = [
  { key: "all", label: "All", types: [] },
  { key: "price", label: "Price Drops", types: ["price_drop", "price_alert"] },
  { key: "orders", label: "Orders", types: ["return_window", "refund_delay", "back_in_stock"] },
  { key: "reviews", label: "Reviews", types: ["review_upvote", "dudscore_change"] },
  { key: "system", label: "System", types: ["level_up", "discussion_reply"] },
];

function matchesFilter(n: Notification, tab: FilterTab): boolean {
  if (tab.types.length === 0) return true;
  return tab.types.includes(n.type);
}

// ── Component ─────────────────────────────────────────────────────────────────

export function NotificationList() {
  const [activeTab, setActiveTab] = useState("all");
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [markingAll, setMarkingAll] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);

  // ── Fetch notifications (initial) ───────────────────────────────
  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const res = await notificationsApi.list();
      if (res.success && res.data) {
        setNotifications(res.data);
        // Extract pagination cursor from raw response
        const paginated = res as unknown as PaginatedApiResponse<Notification>;
        setNextCursor(paginated.pagination?.next ?? null);
      }
    } catch {
      // Silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  // ── Load more (pagination) ──────────────────────────────────────
  async function handleLoadMore() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const res = await notificationsApi.list(nextCursor);
      if (res.success && res.data) {
        setNotifications((prev) => [...prev, ...res.data]);
        const paginated = res as unknown as PaginatedApiResponse<Notification>;
        setNextCursor(paginated.pagination?.next ?? null);
      }
    } catch {
      // Silently fail
    } finally {
      setLoadingMore(false);
    }
  }

  // ── Mark single as read ─────────────────────────────────────────
  async function handleMarkRead(id: number) {
    try {
      await notificationsApi.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, isRead: true } : n))
      );
    } catch {
      // Silently fail
    }
  }

  // ── Mark all as read ────────────────────────────────────────────
  async function handleMarkAllRead() {
    setMarkingAll(true);
    try {
      await notificationsApi.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
    } catch {
      // Silently fail
    } finally {
      setMarkingAll(false);
    }
  }

  // ── Derived data ────────────────────────────────────────────────
  const currentTab = FILTER_TABS.find((t) => t.key === activeTab) ?? { key: "all", label: "All", types: [] as string[] };
  const filtered = notifications.filter((n) => matchesFilter(n, currentTab));
  const unreadCount = notifications.filter((n) => !n.isRead).length;

  return (
    <div>
      {/* ── Header row ─────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-xl font-semibold text-[#1E293B]">Notifications</h1>

        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            disabled={markingAll}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium",
              "text-[#F97316] hover:bg-[#FFF7ED]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
              "transition-colors disabled:opacity-50"
            )}
          >
            <CheckCheck className="h-4 w-4" />
            Mark all as read
          </button>
        )}
      </div>

      {/* ── Filter tabs ────────────────────────────────────────── */}
      <div className="mt-4 flex gap-1 overflow-x-auto border-b border-[#E2E8F0] pb-px">
        {FILTER_TABS.map((tab) => {
          const count = tab.types.length === 0
            ? notifications.length
            : notifications.filter((n) => matchesFilter(n, tab)).length;

          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                "relative shrink-0 px-4 py-2.5 text-sm font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#F97316]",
                "rounded-t-md",
                activeTab === tab.key
                  ? "text-[#F97316]"
                  : "text-[#64748B] hover:text-[#1E293B] hover:bg-[#F8FAFC]"
              )}
            >
              {tab.label}
              {count > 0 && (
                <span
                  className={cn(
                    "ml-1.5 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-xs font-semibold",
                    activeTab === tab.key
                      ? "bg-[#FFF7ED] text-[#F97316]"
                      : "bg-[#F1F5F9] text-[#64748B]"
                  )}
                >
                  {count}
                </span>
              )}

              {/* Active tab indicator */}
              {activeTab === tab.key && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#F97316] rounded-t" />
              )}
            </button>
          );
        })}
      </div>

      {/* ── Notification cards ─────────────────────────────────── */}
      <div className="mt-4">
        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-lg bg-white p-4"
              >
                <div className="h-9 w-9 rounded-full bg-[#F1F5F9] animate-pulse shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-2/3 rounded bg-[#F1F5F9] animate-pulse" />
                  <div className="h-3.5 w-full rounded bg-[#F1F5F9] animate-pulse" />
                  <div className="h-3 w-1/4 rounded bg-[#F1F5F9] animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-lg border border-[#E2E8F0] bg-white py-16 px-4 text-center">
            <Bell className="h-10 w-10 text-[#CBD5E1] mb-3" />
            <p className="text-base font-medium text-[#1E293B]">
              No notifications yet
            </p>
            <p className="mt-1 text-sm text-[#64748B] max-w-sm">
              {activeTab === "all"
                ? "When you get price drops, order updates, or review activity, they'll show up here."
                : `No ${currentTab.label.toLowerCase()} notifications to show.`}
            </p>
          </div>
        ) : (
          <div className="space-y-1 rounded-lg border border-[#E2E8F0] bg-white overflow-hidden divide-y divide-[#F1F5F9]">
            {filtered.map((n) => (
              <NotificationCard
                key={n.id}
                notification={n}
                onMarkRead={handleMarkRead}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── Pagination ─────────────────────────────────────────── */}
      {!loading && nextCursor && (
        <div className="mt-6 flex justify-center">
          <button
            onClick={handleLoadMore}
            disabled={loadingMore}
            className={cn(
              "inline-flex items-center gap-2 rounded-lg border border-[#E2E8F0] bg-white px-5 py-2.5 text-sm font-medium",
              "text-[#1E293B] hover:bg-[#F8FAFC]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
              "transition-colors disabled:opacity-50"
            )}
          >
            {loadingMore ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading…
              </>
            ) : (
              "Load more notifications"
            )}
          </button>
        </div>
      )}
    </div>
  );
}
