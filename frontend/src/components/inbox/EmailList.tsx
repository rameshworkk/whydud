"use client";

import type { InboxEmail } from "@/types";
import { formatRelative } from "@/lib/utils";

interface EmailListProps {
  emails: InboxEmail[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  isLoading?: boolean;
}

const CATEGORY_BADGES: Record<string, string> = {
  order: "bg-blue-100 text-blue-700",
  shipping: "bg-purple-100 text-purple-700",
  refund: "bg-green-100 text-green-700",
  return: "bg-orange-100 text-orange-700",
  subscription: "bg-pink-100 text-pink-700",
  promo: "bg-gray-100 text-gray-700",
};

/** Email list panel in the inbox two-panel layout. */
export function EmailList({ emails, selectedId, onSelect, isLoading }: EmailListProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-1 p-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />
        ))}
      </div>
    );
  }

  if (emails.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        No emails
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-0.5">
      {emails.map((email) => (
        <button
          key={email.id}
          onClick={() => onSelect(email.id)}
          className={`flex flex-col gap-1 rounded-lg px-3 py-2 text-left transition-colors ${
            selectedId === email.id ? "bg-primary/10" : "hover:bg-muted"
          } ${!email.isRead ? "font-semibold" : ""}`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm truncate">{email.senderName || email.senderAddress}</span>
            <span className="shrink-0 text-xs text-muted-foreground">{formatRelative(email.receivedAt)}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground truncate flex-1">{email.subject}</span>
            {email.category && email.category !== "other" && (
              <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-xs ${CATEGORY_BADGES[email.category] ?? ""}`}>
                {email.category}
              </span>
            )}
          </div>
        </button>
      ))}
    </div>
  );
}
