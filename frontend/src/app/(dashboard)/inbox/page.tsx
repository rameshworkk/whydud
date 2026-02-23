"use client";

import { useState, useEffect, useCallback } from "react";
import { inboxApi } from "@/lib/api/inbox";
import type { InboxEmail } from "@/types";

const FOLDERS = [
  { id: "all", label: "All Mail", icon: "\uD83D\uDCE5" },
  { id: "order", label: "Orders", icon: "\uD83D\uDCE6" },
  { id: "shipping", label: "Shipping", icon: "\uD83D\uDE9A" },
  { id: "refund", label: "Refunds", icon: "\uD83D\uDCB0" },
  { id: "return", label: "Returns", icon: "\uD83D\uDD04" },
  { id: "subscription", label: "Subscriptions", icon: "\uD83D\uDD01" },
  { id: "promo", label: "Promotions", icon: "\uD83D\uDCE2" },
  { id: "starred", label: "Starred", icon: "\u2B50" },
];

const CATEGORY_COLORS: Record<string, string> = {
  order: "bg-blue-100 text-blue-700",
  shipping: "bg-purple-100 text-purple-700",
  refund: "bg-green-100 text-green-700",
  return: "bg-orange-100 text-orange-700",
  subscription: "bg-pink-100 text-pink-700",
  promo: "bg-slate-100 text-slate-600",
  other: "bg-slate-100 text-slate-600",
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  if (days === 1) return "Yesterday";
  return `${days}d ago`;
}

/** Extended email with optional body from detail endpoint */
interface EmailWithBody extends InboxEmail {
  bodyHtml?: string;
}

function EmailListSkeleton() {
  return (
    <div className="flex flex-col">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="px-4 py-3 border-b border-[#F1F5F9] animate-pulse">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-24 h-3 rounded bg-slate-200" />
            <div className="ml-auto w-10 h-2.5 rounded bg-slate-200" />
          </div>
          <div className="w-48 h-3 rounded bg-slate-200 mb-1.5" />
          <div className="w-32 h-2.5 rounded bg-slate-200" />
        </div>
      ))}
    </div>
  );
}

export default function InboxPage() {
  const [emails, setEmails] = useState<InboxEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFolder, setActiveFolder] = useState("all");
  const [selectedEmail, setSelectedEmail] = useState<EmailWithBody | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Fetch email list
  useEffect(() => {
    async function fetchEmails() {
      setLoading(true);
      setError(null);
      try {
        const filters: Record<string, string | boolean | undefined> = {};
        if (activeFolder === "starred") {
          filters.isStarred = true;
        } else if (activeFolder !== "all") {
          filters.category = activeFolder;
        }
        const res = await inboxApi.list(filters);
        if (res.success && "data" in res) {
          setEmails(res.data);
        } else if (!res.success && "error" in res) {
          setError(res.error.message);
        }
      } catch {
        setError("Failed to load emails.");
      } finally {
        setLoading(false);
      }
    }
    fetchEmails();
  }, [activeFolder]);

  // Fetch individual email detail
  const handleSelectEmail = useCallback(async (email: InboxEmail) => {
    setSelectedEmail({ ...email });
    setDetailLoading(true);
    try {
      const res = await inboxApi.get(email.id);
      if (res.success && "data" in res) {
        setSelectedEmail(res.data);
        // Mark as read if not already
        if (!email.isRead) {
          await inboxApi.markRead(email.id, true);
          setEmails((prev) =>
            prev.map((e) => (e.id === email.id ? { ...e, isRead: true } : e))
          );
        }
      }
    } catch {
      // Keep the basic email info even if detail fails
    } finally {
      setDetailLoading(false);
    }
  }, []);

  // Compute folder counts from current email list
  const folderCounts: Record<string, number> = {};
  emails.forEach((e) => {
    folderCounts["all"] = (folderCounts["all"] ?? 0) + 1;
    folderCounts[e.category] = (folderCounts[e.category] ?? 0) + 1;
    if (e.isStarred) folderCounts["starred"] = (folderCounts["starred"] ?? 0) + 1;
  });

  // Compute marketplace counts
  const marketplaceCounts: Record<string, number> = {};
  emails.forEach((e) => {
    if (e.marketplace) {
      marketplaceCounts[e.marketplace] = (marketplaceCounts[e.marketplace] ?? 0) + 1;
    }
  });
  const marketplaceFilters = Object.entries(marketplaceCounts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);

  // Client-side search filter
  const filteredEmails = emails.filter(
    (e) =>
      !searchQuery ||
      e.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.senderName.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-bold text-slate-900">Inbox</h1>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex rounded-xl border border-[#E2E8F0] overflow-hidden bg-white min-h-[620px]">
        {/* Folder sidebar */}
        <div className="w-[180px] shrink-0 border-r border-[#E2E8F0] bg-[#F8FAFC] flex flex-col">
          <nav className="flex flex-col gap-0.5 p-2">
            {FOLDERS.map((f) => (
              <button
                key={f.id}
                onClick={() => setActiveFolder(f.id)}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] ${
                  activeFolder === f.id
                    ? "bg-[#F97316] text-white"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                <span className="text-base">{f.icon}</span>
                <span className="flex-1">{f.label}</span>
                {(folderCounts[f.id] ?? 0) > 0 && (
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                      activeFolder === f.id
                        ? "bg-white/20 text-white"
                        : "bg-slate-200 text-slate-500"
                    }`}
                  >
                    {folderCounts[f.id]}
                  </span>
                )}
              </button>
            ))}
          </nav>

          {/* Marketplace filter */}
          <div className="border-t border-[#E2E8F0] p-3 mt-auto">
            <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Marketplaces
            </p>
            <div className="flex flex-col gap-1">
              {marketplaceFilters.length > 0 ? (
                marketplaceFilters.map((mp) => (
                  <div
                    key={mp.name}
                    className="flex items-center justify-between text-xs text-slate-500"
                  >
                    <span>{mp.name}</span>
                    <span className="text-slate-400">{mp.count}</span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-400">No marketplaces</p>
              )}
            </div>
          </div>
        </div>

        {/* Email list */}
        <div className="w-[300px] shrink-0 border-r border-[#E2E8F0] flex flex-col">
          {/* Search bar */}
          <div className="p-3 border-b border-[#E2E8F0]">
            <div className="flex items-center gap-2 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-2">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className="text-slate-400"
              >
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                placeholder="Search emails..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-transparent text-sm text-slate-700 placeholder:text-slate-400 outline-none flex-1"
              />
            </div>
          </div>

          {/* Email items */}
          <div className="flex-1 overflow-y-auto no-scrollbar">
            {loading ? (
              <EmailListSkeleton />
            ) : filteredEmails.length === 0 ? (
              <div className="flex-1 flex items-center justify-center p-6 text-sm text-slate-400 text-center">
                {searchQuery
                  ? "No emails match your search"
                  : "No emails in this folder"}
              </div>
            ) : (
              filteredEmails.map((email) => (
                <button
                  key={email.id}
                  onClick={() => handleSelectEmail(email)}
                  className={`w-full flex flex-col gap-1 px-4 py-3 text-left border-b border-[#F1F5F9] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#F97316] ${
                    selectedEmail?.id === email.id
                      ? "bg-[#FFF7ED]"
                      : "hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {!email.isRead && (
                      <span className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />
                    )}
                    <span
                      className={`text-sm truncate flex-1 ${
                        !email.isRead
                          ? "font-semibold text-slate-900"
                          : "text-slate-700"
                      }`}
                    >
                      {email.senderName}
                    </span>
                    <span className="text-[10px] text-slate-400 shrink-0">
                      {timeAgo(email.receivedAt)}
                    </span>
                  </div>
                  <p
                    className={`text-xs truncate ${
                      !email.isRead ? "text-slate-700" : "text-slate-500"
                    }`}
                  >
                    {email.subject}
                  </p>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-400 truncate flex-1">
                      {email.marketplace || email.senderAddress}
                    </span>
                    <span
                      className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0 ${
                        CATEGORY_COLORS[email.category] ?? "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {email.category}
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Email reader */}
        <div className="flex-1 flex flex-col overflow-y-auto">
          {selectedEmail ? (
            <div className="p-6">
              {/* Email header */}
              <h2 className="text-lg font-bold text-slate-900 mb-2">
                {selectedEmail.subject}
              </h2>
              <div className="flex items-center gap-3 text-sm text-slate-500 mb-4">
                <span>
                  From:{" "}
                  <span className="text-slate-700">
                    {selectedEmail.senderAddress}
                  </span>
                </span>
                <span className="text-slate-300">|</span>
                <span>
                  {new Date(selectedEmail.receivedAt).toLocaleDateString(
                    "en-IN",
                    {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    }
                  )}
                </span>
                <span className="text-slate-300">|</span>
                <span
                  className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                    CATEGORY_COLORS[selectedEmail.category] ?? "bg-slate-100 text-slate-600"
                  }`}
                >
                  {selectedEmail.category}
                </span>
                {selectedEmail.parseStatus && (
                  <>
                    <span className="text-slate-300">|</span>
                    <span
                      className={`text-xs font-medium ${
                        selectedEmail.parseStatus === "parsed"
                          ? "text-green-600"
                          : selectedEmail.parseStatus === "failed"
                          ? "text-red-500"
                          : "text-slate-400"
                      }`}
                    >
                      {selectedEmail.parseStatus === "parsed"
                        ? "Parsed"
                        : selectedEmail.parseStatus === "failed"
                        ? "Parse failed"
                        : selectedEmail.parseStatus === "pending"
                        ? "Parsing..."
                        : "Skipped"}
                    </span>
                  </>
                )}
              </div>

              {/* Email body */}
              {detailLoading ? (
                <div className="animate-pulse space-y-3">
                  <div className="h-3 w-full rounded bg-slate-200" />
                  <div className="h-3 w-5/6 rounded bg-slate-200" />
                  <div className="h-3 w-4/6 rounded bg-slate-200" />
                  <div className="h-3 w-full rounded bg-slate-200" />
                  <div className="h-3 w-3/4 rounded bg-slate-200" />
                </div>
              ) : selectedEmail.bodyHtml ? (
                <div
                  className="text-sm text-slate-600 leading-relaxed prose prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: selectedEmail.bodyHtml }}
                />
              ) : (
                <div className="text-sm text-slate-400 italic">
                  Email body not available. The email may still be processing.
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-sm text-slate-400">
              Select an email to read
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
