import Link from "next/link";
import { formatRelative, truncate } from "@/lib/utils";
import type { DiscussionThread, DiscussionThreadType } from "@/types";

interface ThreadCardProps {
  thread: DiscussionThread;
}

const TYPE_CONFIG: Record<DiscussionThreadType, { label: string; bg: string; text: string }> = {
  question: { label: "Question", bg: "bg-blue-50", text: "text-blue-700" },
  experience: { label: "Experience", bg: "bg-purple-50", text: "text-purple-700" },
  comparison: { label: "Comparison", bg: "bg-amber-50", text: "text-amber-700" },
  tip: { label: "Tip", bg: "bg-green-50", text: "text-green-700" },
  alert: { label: "Alert", bg: "bg-red-50", text: "text-red-700" },
};

/** Discussion thread preview card for the product page section. */
export function ThreadCard({ thread }: ThreadCardProps) {
  const typeConf = TYPE_CONFIG[thread.threadType] ?? TYPE_CONFIG.question;

  return (
    <Link
      href={`/discussions/${thread.id}`}
      className="block rounded-lg border border-slate-200 bg-white p-4 hover:shadow-md transition-shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
    >
      {/* Badge + meta row */}
      <div className="flex items-center gap-2 mb-2">
        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${typeConf.bg} ${typeConf.text}`}>
          {typeConf.label}
        </span>
        {thread.isPinned && (
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-[#FFF7ED] text-[#F97316]">
            Pinned
          </span>
        )}
        <span className="ml-auto text-xs text-slate-400">
          {thread.lastReplyAt ? formatRelative(thread.lastReplyAt) : formatRelative(thread.createdAt)}
        </span>
      </div>

      {/* Title */}
      <h3 className="text-sm font-semibold text-slate-900 leading-snug mb-1">
        {thread.title}
      </h3>

      {/* Body preview */}
      {thread.body && (
        <p className="text-xs text-slate-500 leading-relaxed mb-3 line-clamp-2">
          {truncate(thread.body, 120)}
        </p>
      )}

      {/* Footer: author + stats */}
      <div className="flex items-center gap-3 text-xs text-slate-400">
        <span className="font-medium text-slate-600">{thread.author.name}</span>
        <span className="flex items-center gap-1">
          <span className="text-slate-500">&#9650;</span> {thread.upvotes}
        </span>
        <span>{thread.replyCount} {thread.replyCount === 1 ? "reply" : "replies"}</span>
        <span>{thread.viewCount} views</span>
      </div>
    </Link>
  );
}
