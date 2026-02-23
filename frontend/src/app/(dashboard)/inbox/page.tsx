"use client";

import { useState } from "react";
import {
  MOCK_EMAILS,
  INBOX_FOLDER_COUNTS,
  MARKETPLACE_FILTERS,
  type MockEmail,
} from "@/lib/mock-inbox-data";
import { formatPrice } from "@/lib/utils/format";

const FOLDERS = [
  { id: "all", label: "All Mail", icon: "📥" },
  { id: "order", label: "Orders", icon: "📦" },
  { id: "shipping", label: "Shipping", icon: "🚚" },
  { id: "refund", label: "Refunds", icon: "💰" },
  { id: "return", label: "Returns", icon: "🔄" },
  { id: "subscription", label: "Subscriptions", icon: "🔁" },
  { id: "promo", label: "Promotions", icon: "📢" },
  { id: "starred", label: "Starred", icon: "⭐" },
];

const CATEGORY_COLORS: Record<string, string> = {
  order: "bg-blue-100 text-blue-700",
  shipping: "bg-purple-100 text-purple-700",
  refund: "bg-green-100 text-green-700",
  return: "bg-orange-100 text-orange-700",
  subscription: "bg-pink-100 text-pink-700",
  promo: "bg-slate-100 text-slate-600",
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

export default function InboxPage() {
  const [activeFolder, setActiveFolder] = useState("all");
  const [selectedEmail, setSelectedEmail] = useState<MockEmail | null>(
    MOCK_EMAILS[0] ?? null
  );
  const [searchQuery, setSearchQuery] = useState("");

  const filteredEmails = MOCK_EMAILS.filter((e) => {
    if (activeFolder === "starred") return e.isStarred;
    if (activeFolder !== "all") return e.category === activeFolder;
    return true;
  }).filter(
    (e) =>
      !searchQuery ||
      e.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.senderName.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-bold text-slate-900">Inbox</h1>

      <div className="flex rounded-xl border border-[#E2E8F0] overflow-hidden bg-white min-h-[620px]">
        {/* ── Folder sidebar ──────────────────────────────────── */}
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
                {(INBOX_FOLDER_COUNTS[f.id] ?? 0) > 0 && (
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                      activeFolder === f.id
                        ? "bg-white/20 text-white"
                        : "bg-slate-200 text-slate-500"
                    }`}
                  >
                    {INBOX_FOLDER_COUNTS[f.id]}
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
              {MARKETPLACE_FILTERS.map((mp) => (
                <div
                  key={mp.name}
                  className="flex items-center justify-between text-xs text-slate-500"
                >
                  <span>{mp.name}</span>
                  <span className="text-slate-400">{mp.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Email list ──────────────────────────────────────── */}
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
            {filteredEmails.map((email) => (
              <button
                key={email.id}
                onClick={() => setSelectedEmail(email)}
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
                    {email.snippet.slice(0, 50)}...
                  </span>
                  <span
                    className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0 ${
                      CATEGORY_COLORS[email.category]
                    }`}
                  >
                    {email.category}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* ── Email reader ────────────────────────────────────── */}
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
              </div>

              {/* Parsed data card */}
              {selectedEmail.parsedData && (
                <div className="rounded-lg border-2 border-green-200 bg-green-50 p-4 mb-5">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-base">
                      {selectedEmail.parsedData.type === "order"
                        ? "📦"
                        : selectedEmail.parsedData.type === "refund"
                        ? "💰"
                        : "🚚"}
                    </span>
                    <span className="text-sm font-bold text-green-800">
                      {selectedEmail.parsedData.type === "order"
                        ? "Order Detected"
                        : selectedEmail.parsedData.type === "refund"
                        ? "Refund Detected"
                        : "Shipping Update"}
                    </span>
                  </div>
                  <p className="text-sm font-semibold text-slate-800">
                    {selectedEmail.parsedData.productName}
                  </p>
                  <p className="text-sm text-slate-600 mt-0.5">
                    {formatPrice(selectedEmail.parsedData.amount)} on{" "}
                    {selectedEmail.parsedData.marketplace}
                  </p>
                  {selectedEmail.parsedData.dudScore && (
                    <p className="text-sm text-slate-600 mt-0.5">
                      DudScore:{" "}
                      <span className="font-semibold">
                        {selectedEmail.parsedData.dudScore}
                      </span>{" "}
                      <span
                        className={
                          selectedEmail.parsedData.dudScore >= 80
                            ? "text-green-600"
                            : selectedEmail.parsedData.dudScore >= 60
                            ? "text-yellow-600"
                            : "text-red-600"
                        }
                      >
                        {selectedEmail.parsedData.dudScoreLabel}
                      </span>
                    </p>
                  )}
                  <button className="mt-3 text-xs font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded">
                    View in Dashboard →
                  </button>
                </div>
              )}

              {/* Email body */}
              <div className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">
                {selectedEmail.body}
              </div>
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
