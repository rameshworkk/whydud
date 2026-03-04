"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { VoteButtons } from "./VoteButtons";
import { ReplyForm } from "./ReplyForm";
import { discussionsApi } from "@/lib/api/discussions";
import { useAuth } from "@/hooks/useAuth";
import { formatRelative, cn } from "@/lib/utils";
import type { DiscussionThread, DiscussionReply, DiscussionThreadType } from "@/types";

// ── Config ──────────────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<DiscussionThreadType, { label: string; bg: string; text: string }> = {
  question: { label: "Question", bg: "bg-blue-50", text: "text-blue-700" },
  experience: { label: "Experience", bg: "bg-purple-50", text: "text-purple-700" },
  comparison: { label: "Comparison", bg: "bg-amber-50", text: "text-amber-700" },
  tip: { label: "Tip", bg: "bg-green-50", text: "text-green-700" },
  alert: { label: "Alert", bg: "bg-red-50", text: "text-red-700" },
};

/** Deterministic avatar color from name string. */
function avatarColor(name: string): string {
  const colors: string[] = [
    "bg-[#F97316]", "bg-[#4DB6AC]", "bg-blue-500",
    "bg-purple-500", "bg-pink-500", "bg-amber-500",
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const idx = Math.abs(hash) % colors.length;
  return colors[idx] as string;
}

// ── Reply Card ──────────────────────────────────────────────────────────────

interface ReplyCardProps {
  reply: DiscussionReply;
  isThreadAuthor: boolean;
  currentUserId: string | null;
  threadType: DiscussionThreadType;
  threadId: string;
  onRefresh: () => void;
}

function ReplyCard({ reply, isThreadAuthor, currentUserId, threadType, threadId, onRefresh }: ReplyCardProps) {
  const [showReplyForm, setShowReplyForm] = useState(false);

  const handleVote = useCallback(
    async (vote: 1 | -1) => {
      const res = await discussionsApi.voteReply(reply.id, vote);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    [reply.id],
  );

  const handleAccept = useCallback(async () => {
    const res = await discussionsApi.acceptReply(reply.id);
    if (res.success) onRefresh();
  }, [reply.id, onRefresh]);

  const isOwner = currentUserId === reply.author.id;

  return (
    <div
      className={cn(
        "rounded-lg border p-4",
        reply.isAccepted
          ? "border-[#16A34A] bg-green-50/50"
          : "border-slate-200 bg-white",
      )}
    >
      {/* Accepted answer badge */}
      {reply.isAccepted && (
        <div className="flex items-center gap-1.5 mb-2">
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-green-100 text-[#16A34A]">
            Accepted Answer
          </span>
        </div>
      )}

      {/* Author + time */}
      <div className="flex items-center gap-2 mb-2">
        <div className={cn("w-6 h-6 rounded-full flex items-center justify-center text-white text-[10px] font-bold shrink-0", avatarColor(reply.author.name))}>
          {reply.author.name.charAt(0).toUpperCase()}
        </div>
        <span className="text-xs font-semibold text-slate-700">{reply.author.name}</span>
        <span className="text-xs text-slate-400">{formatRelative(reply.createdAt)}</span>
      </div>

      {/* Body */}
      <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap mb-3">
        {reply.body}
      </p>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <VoteButtons
          upvotes={reply.upvotes}
          downvotes={reply.downvotes}
          userVote={reply.userVote}
          onVote={handleVote}
        />

        <button
          onClick={() => setShowReplyForm((v) => !v)}
          className="text-xs font-semibold text-slate-500 hover:text-[#F97316] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
        >
          Reply
        </button>

        {/* Mark as accepted — only for thread author, only for question threads */}
        {threadType === "question" && isThreadAuthor && !isOwner && !reply.isAccepted && (
          <button
            onClick={handleAccept}
            className="text-xs font-semibold text-[#16A34A] hover:text-green-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
          >
            Mark as accepted
          </button>
        )}
      </div>

      {/* Nested reply form */}
      {showReplyForm && (
        <ReplyForm
          threadId={threadId}
          parentReplyId={reply.id}
          compact
          onCancel={() => setShowReplyForm(false)}
          onReplied={() => {
            setShowReplyForm(false);
            onRefresh();
          }}
        />
      )}
    </div>
  );
}

// ── Thread Detail ───────────────────────────────────────────────────────────

interface ThreadDetailProps {
  thread: DiscussionThread;
  replies: DiscussionReply[];
}

/** Full discussion thread view with all replies. */
export function ThreadDetail({ thread, replies: initialReplies }: ThreadDetailProps) {
  const router = useRouter();
  const { user } = useAuth();
  const currentUserId = user?.id ?? null;
  const [replies, setReplies] = useState<DiscussionReply[]>(initialReplies);
  const typeConf = TYPE_CONFIG[thread.threadType] ?? TYPE_CONFIG.question;
  const isThreadAuthor = currentUserId === thread.author.id;

  const handleThreadVote = useCallback(
    async (vote: 1 | -1) => {
      const res = await discussionsApi.voteThread(thread.id, vote);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    [thread.id],
  );

  const refreshReplies = useCallback(async () => {
    const res = await discussionsApi.get(thread.id);
    if (res.success) {
      setReplies(res.data.replies);
    }
  }, [thread.id]);

  // Separate accepted replies (show first) from others
  const acceptedReplies = replies.filter((r) => r.isAccepted);
  const otherReplies = replies.filter((r) => !r.isAccepted);
  const sortedReplies = [...acceptedReplies, ...otherReplies];

  return (
    <div className="max-w-3xl mx-auto">
      {/* Back nav */}
      <button
        onClick={() => router.back()}
        className="text-xs font-semibold text-slate-500 hover:text-[#F97316] transition-colors mb-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
      >
        &larr; Back
      </button>

      {/* Thread card */}
      <div className="rounded-lg border border-slate-200 bg-white p-5 mb-4">
        {/* Type badge + meta */}
        <div className="flex items-center gap-2 mb-3">
          <span className={cn("text-[11px] font-semibold px-2 py-0.5 rounded-full", typeConf.bg, typeConf.text)}>
            {typeConf.label}
          </span>
          {thread.isPinned && (
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-[#FFF7ED] text-[#F97316]">
              Pinned
            </span>
          )}
          {thread.isLocked && (
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
              Locked
            </span>
          )}
        </div>

        {/* Title */}
        <h1 className="text-lg font-bold text-slate-900 leading-snug mb-2">{thread.title}</h1>

        {/* Author + time */}
        <div className="flex items-center gap-2 mb-4">
          <div className={cn("w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0", avatarColor(thread.author.name))}>
            {thread.author.name.charAt(0).toUpperCase()}
          </div>
          <span className="text-sm font-medium text-slate-700">{thread.author.name}</span>
          <span className="text-xs text-slate-400">{formatRelative(thread.createdAt)}</span>
          <span className="text-xs text-slate-400 ml-auto">{thread.viewCount} views</span>
        </div>

        {/* Body */}
        <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap mb-4">
          {thread.body}
        </p>

        {/* Vote */}
        <VoteButtons
          upvotes={thread.upvotes}
          downvotes={thread.downvotes}
          userVote={thread.userVote}
          onVote={handleThreadVote}
        />
      </div>

      {/* Replies header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-700">
          {replies.length} {replies.length === 1 ? "Reply" : "Replies"}
        </h2>
      </div>

      {/* Replies */}
      {sortedReplies.length > 0 ? (
        <div className="flex flex-col gap-3 mb-4">
          {sortedReplies.map((reply) => (
            <ReplyCard
              key={reply.id}
              reply={reply}
              isThreadAuthor={isThreadAuthor}
              currentUserId={currentUserId}
              threadType={thread.threadType}
              threadId={thread.id}
              onRefresh={refreshReplies}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white p-6 text-center mb-4">
          <p className="text-sm text-slate-400">No replies yet. Be the first to respond!</p>
        </div>
      )}

      {/* Reply form at bottom */}
      {!thread.isLocked ? (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-2">Write a reply</h3>
          <ReplyForm
            threadId={thread.id}
            onReplied={refreshReplies}
          />
        </div>
      ) : (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-center">
          <p className="text-sm text-slate-400">This thread is locked and no longer accepts replies.</p>
        </div>
      )}
    </div>
  );
}
