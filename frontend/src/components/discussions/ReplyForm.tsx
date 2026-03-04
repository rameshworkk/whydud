"use client";

import { useState, useCallback } from "react";
import { discussionsApi } from "@/lib/api/discussions";
import { cn } from "@/lib/utils";

interface ReplyFormProps {
  threadId: string;
  parentReplyId?: string;
  onReplied?: () => void;
  onCancel?: () => void;
  compact?: boolean;
}

/** Form for posting a reply to a discussion thread. */
export function ReplyForm({ threadId, parentReplyId, onReplied, onCancel, compact }: ReplyFormProps) {
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!body.trim()) return;

      setLoading(true);
      setError(null);

      try {
        const res = await discussionsApi.reply(threadId, body.trim(), parentReplyId);
        if (res.success) {
          setBody("");
          onReplied?.();
        } else {
          setError(res.error.message);
        }
      } catch {
        setError("Failed to post reply. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    [threadId, parentReplyId, body, onReplied],
  );

  return (
    <form onSubmit={handleSubmit} className={cn("flex flex-col gap-2", compact ? "mt-2" : "mt-4")}>
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={compact ? "Write a reply..." : "Share your thoughts..."}
        required
        rows={compact ? 2 : 3}
        className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-slate-50 text-slate-900 placeholder:text-slate-400 resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:border-[#F97316] transition-colors"
      />

      {error && <p className="text-xs text-[#DC2626]">{error}</p>}

      <div className="flex items-center gap-2 justify-end">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1.5 text-xs font-semibold text-slate-600 rounded-lg hover:bg-slate-100 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={loading || !body.trim()}
          className={cn(
            "px-4 py-1.5 text-xs font-semibold rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
            loading || !body.trim()
              ? "bg-slate-200 text-slate-400 cursor-not-allowed"
              : "bg-[#F97316] text-white hover:bg-[#EA580C]",
          )}
        >
          {loading ? "Posting..." : "Post Reply"}
        </button>
      </div>
    </form>
  );
}
