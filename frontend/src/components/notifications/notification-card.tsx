"use client";

import {
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
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils/index";
import { formatRelative } from "@/lib/utils/format";
import type { Notification } from "@/lib/api/types";

/** Icon + colour mapping by notification type. */
const ICON_MAP: Record<string, { Icon: LucideIcon; color: string }> = {
  price_drop: { Icon: TrendingDown, color: "text-emerald-500 bg-emerald-50" },
  price_alert: { Icon: TrendingDown, color: "text-emerald-500 bg-emerald-50" },
  return_window: { Icon: RotateCcw, color: "text-amber-500 bg-amber-50" },
  refund_delay: { Icon: AlertTriangle, color: "text-red-500 bg-red-50" },
  back_in_stock: { Icon: PackageCheck, color: "text-[#4DB6AC] bg-teal-50" },
  review_upvote: { Icon: Star, color: "text-[#FBBF24] bg-yellow-50" },
  discussion_reply: { Icon: MessageSquare, color: "text-blue-500 bg-blue-50" },
  level_up: { Icon: Trophy, color: "text-[#F97316] bg-orange-50" },
  dudscore_change: { Icon: ShieldCheck, color: "text-[#4DB6AC] bg-teal-50" },
  points_earned: { Icon: Coins, color: "text-[#FBBF24] bg-yellow-50" },
  subscription_renewal: { Icon: CreditCard, color: "text-purple-500 bg-purple-50" },
  order_detected: { Icon: ShoppingBag, color: "text-[#4DB6AC] bg-teal-50" },
};

const DEFAULT_ICON = { Icon: Info, color: "text-[#64748B] bg-slate-50" };

interface NotificationCardProps {
  notification: Notification;
  onMarkRead: (id: number) => void;
}

export function NotificationCard({ notification, onMarkRead }: NotificationCardProps) {
  const { Icon, color } = ICON_MAP[notification.type] ?? DEFAULT_ICON;

  function handleClick() {
    if (!notification.isRead) {
      onMarkRead(notification.id);
    }
    if (notification.actionUrl) {
      window.location.href = notification.actionUrl;
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}
      className={cn(
        "flex items-start gap-3 rounded-lg p-4 transition-colors cursor-pointer",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#F97316]",
        notification.isRead
          ? "bg-white hover:bg-[#F8FAFC]"
          : "bg-orange-50 border-l-[3px] border-l-[#F97316] hover:bg-orange-50/70"
      )}
    >
      {/* ── Type icon ──────────────────────────────────────────── */}
      <span
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-full",
          color
        )}
      >
        <Icon className="h-[18px] w-[18px]" />
      </span>

      {/* ── Content ────────────────────────────────────────────── */}
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-sm leading-snug",
            notification.isRead
              ? "text-[#1E293B] font-medium"
              : "text-[#1E293B] font-semibold"
          )}
        >
          {notification.title}
        </p>

        {notification.body && (
          <p className="mt-0.5 text-sm text-[#64748B] leading-relaxed line-clamp-2">
            {notification.body}
          </p>
        )}

        <div className="mt-2 flex items-center gap-3">
          <span className="text-xs text-[#94A3B8]">
            {formatRelative(notification.createdAt)}
          </span>

          {notification.actionUrl && notification.actionLabel && (
            <span
              className={cn(
                "inline-flex items-center rounded-md px-2.5 py-1 text-xs font-medium",
                "bg-[#F97316] text-white",
                "hover:bg-[#EA580C] active:bg-[#C2410C]",
                "transition-colors"
              )}
            >
              {notification.actionLabel}
            </span>
          )}
        </div>
      </div>

      {/* ── Unread indicator ───────────────────────────────────── */}
      {!notification.isRead && (
        <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-[#F97316]" />
      )}
    </div>
  );
}
