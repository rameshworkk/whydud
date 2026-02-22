import Link from "next/link";
import { formatRelative } from "@/lib/utils";

interface Thread {
  id: string;
  threadType: string;
  title: string;
  replyCount: number;
  upvotes: number;
  viewCount: number;
  lastReplyAt: string | null;
  createdAt: string;
}

interface ThreadCardProps {
  thread: Thread;
}

const TYPE_LABELS: Record<string, string> = {
  question: "❓ Question",
  experience: "💬 Experience",
  comparison: "⚖️ Comparison",
  tip: "💡 Tip",
  alert: "⚠️ Alert",
};

/** Discussion thread preview card. */
export function ThreadCard({ thread }: ThreadCardProps) {
  return (
    <Link
      href={`/discussions/${thread.id}`}
      className="flex flex-col gap-2 rounded-xl border bg-card p-4 hover:shadow-sm transition-shadow"
    >
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">
          {TYPE_LABELS[thread.threadType] ?? thread.threadType}
        </span>
      </div>
      <h3 className="font-semibold leading-snug">{thread.title}</h3>
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span>▲ {thread.upvotes}</span>
        <span>💬 {thread.replyCount} replies</span>
        <span>👁 {thread.viewCount}</span>
        <span className="ml-auto">
          {thread.lastReplyAt ? formatRelative(thread.lastReplyAt) : formatRelative(thread.createdAt)}
        </span>
      </div>
    </Link>
  );
}
