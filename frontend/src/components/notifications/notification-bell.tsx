"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Bell,
  TrendingDown,
  RotateCcw,
  PackageCheck,
  Star,
  MessageSquare,
  Trophy,
  AlertTriangle,
  ShieldCheck,
  Info,
  Coins,
  CreditCard,
  ShoppingBag,
} from "lucide-react";
import { cn } from "@/lib/utils/index";
import { notificationsApi } from "@/lib/api/notifications";
import { formatRelative } from "@/lib/utils/format";
import type { Notification } from "@/lib/api/types";

const POLL_INTERVAL = 30_000;

/** Map notification type → icon + colour */
function notificationIcon(type: string) {
  switch (type) {
    case "price_drop":
    case "price_alert":
      return { Icon: TrendingDown, color: "text-emerald-500 bg-emerald-50" };
    case "return_window":
      return { Icon: RotateCcw, color: "text-amber-500 bg-amber-50" };
    case "refund_delay":
      return { Icon: AlertTriangle, color: "text-red-500 bg-red-50" };
    case "back_in_stock":
      return { Icon: PackageCheck, color: "text-[#4DB6AC] bg-teal-50" };
    case "review_upvote":
      return { Icon: Star, color: "text-[#FBBF24] bg-yellow-50" };
    case "discussion_reply":
      return { Icon: MessageSquare, color: "text-blue-500 bg-blue-50" };
    case "level_up":
      return { Icon: Trophy, color: "text-[#F97316] bg-orange-50" };
    case "dudscore_change":
      return { Icon: ShieldCheck, color: "text-[#4DB6AC] bg-teal-50" };
    case "points_earned":
      return { Icon: Coins, color: "text-[#FBBF24] bg-yellow-50" };
    case "subscription_renewal":
      return { Icon: CreditCard, color: "text-purple-500 bg-purple-50" };
    case "order_detected":
      return { Icon: ShoppingBag, color: "text-[#4DB6AC] bg-teal-50" };
    default:
      return { Icon: Info, color: "text-[#64748B] bg-slate-50" };
  }
}

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // ── Fetch unread count ────────────────────────────────────────
  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await notificationsApi.getUnreadCount();
      if (res.success && res.data) {
        setUnreadCount(res.data.count);
      }
    } catch {
      // Silently fail — non-critical
    }
  }, []);

  // ── Poll unread count every 30s ───────────────────────────────
  useEffect(() => {
    fetchUnreadCount();
    const id = setInterval(fetchUnreadCount, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [fetchUnreadCount]);

  // ── Fetch recent notifications when dropdown opens ────────────
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const res = await notificationsApi.list();
        if (!cancelled && res.success && res.data) {
          setNotifications(res.data.slice(0, 5));
        }
      } catch {
        // Silently fail
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [open]);

  // ── Click outside to close ────────────────────────────────────
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // ── Mark single notification as read ──────────────────────────
  async function handleMarkRead(id: number) {
    try {
      await notificationsApi.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, isRead: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // Silently fail
    }
  }

  // ── Mark all as read ──────────────────────────────────────────
  async function handleMarkAllRead() {
    try {
      await notificationsApi.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
      setUnreadCount(0);
    } catch {
      // Silently fail
    }
  }

  return (
    <div ref={ref} className="relative">
      {/* ── Bell button ─────────────────────────────────────────── */}
      <button
        aria-label={
          unreadCount > 0
            ? `Notifications — ${unreadCount} unread`
            : "Notifications"
        }
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "relative flex h-9 w-9 items-center justify-center rounded-md",
          "text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#1E293B]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
          "transition-colors",
          open && "bg-[#F1F5F9] text-[#1E293B]"
        )}
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span
            className={cn(
              "absolute flex items-center justify-center rounded-full bg-[#F97316] text-white font-semibold",
              "border-2 border-white",
              unreadCount > 9
                ? "top-0 -right-1 h-[18px] min-w-[18px] px-1 text-[10px]"
                : "top-0.5 right-0.5 h-4 w-4 text-[10px]"
            )}
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* ── Dropdown panel ──────────────────────────────────────── */}
      {open && (
        <div
          className={cn(
            "absolute right-0 top-full mt-2 w-80 sm:w-96",
            "rounded-lg border border-[#E2E8F0] bg-white shadow-lg z-50",
            "overflow-hidden"
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-[#E2E8F0] px-4 py-3">
            <h3 className="text-sm font-semibold text-[#1E293B]">
              Notifications
            </h3>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs font-medium text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:underline"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* Notification list */}
          <div className="max-h-[360px] overflow-y-auto">
            {loading ? (
              <div className="space-y-1 p-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 rounded-md p-3"
                  >
                    <div className="h-8 w-8 rounded-full bg-[#F1F5F9] animate-pulse shrink-0" />
                    <div className="flex-1 space-y-2">
                      <div className="h-3.5 w-3/4 rounded bg-[#F1F5F9] animate-pulse" />
                      <div className="h-3 w-1/3 rounded bg-[#F1F5F9] animate-pulse" />
                    </div>
                  </div>
                ))}
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
                <Bell className="h-8 w-8 text-[#CBD5E1] mb-2" />
                <p className="text-sm text-[#64748B]">No notifications yet</p>
                <p className="text-xs text-[#94A3B8] mt-1">
                  We&apos;ll notify you about price drops, reviews, and more.
                </p>
              </div>
            ) : (
              <div className="p-1">
                {notifications.map((n) => {
                  const { Icon, color } = notificationIcon(n.type);
                  return (
                    <button
                      key={n.id}
                      onClick={() => {
                        if (!n.isRead) handleMarkRead(n.id);
                        if (n.actionUrl) {
                          setOpen(false);
                          window.location.href = n.actionUrl;
                        }
                      }}
                      className={cn(
                        "w-full flex items-start gap-3 rounded-md p-3 text-left transition-colors",
                        "hover:bg-[#F8FAFC]",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#F97316]",
                        !n.isRead && "bg-[#FFF7ED]/60"
                      )}
                    >
                      {/* Icon */}
                      <span
                        className={cn(
                          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                          color
                        )}
                      >
                        <Icon className="h-4 w-4" />
                      </span>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <p
                          className={cn(
                            "text-sm leading-snug",
                            n.isRead
                              ? "text-[#64748B]"
                              : "text-[#1E293B] font-medium"
                          )}
                        >
                          {n.title}
                        </p>
                        <p className="text-xs text-[#94A3B8] mt-0.5">
                          {formatRelative(n.createdAt)}
                        </p>
                      </div>

                      {/* Unread dot */}
                      {!n.isRead && (
                        <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[#F97316]" />
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-[#E2E8F0]">
            <Link
              href="/notifications"
              onClick={() => setOpen(false)}
              className={cn(
                "block w-full py-3 text-center text-sm font-medium",
                "text-[#F97316] hover:bg-[#FFF7ED] transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#F97316]"
              )}
            >
              View all notifications
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
