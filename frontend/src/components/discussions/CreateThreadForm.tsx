"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { discussionsApi } from "@/lib/api/discussions";
import { cn } from "@/lib/utils";
import type { DiscussionThreadType } from "@/types";

interface CreateThreadFormProps {
  productSlug: string;
  onCancel: () => void;
  onCreated?: () => void;
}

const THREAD_TYPES: { value: DiscussionThreadType; label: string; description: string }[] = [
  { value: "question", label: "Question", description: "Ask the community something" },
  { value: "experience", label: "Experience", description: "Share your usage experience" },
  { value: "comparison", label: "Comparison", description: "Compare with another product" },
  { value: "tip", label: "Tip", description: "Share a useful tip" },
  { value: "alert", label: "Alert", description: "Warn about an issue" },
];

/** Form for creating a new discussion thread on a product. */
export function CreateThreadForm({ productSlug, onCancel, onCreated }: CreateThreadFormProps) {
  const router = useRouter();
  const [threadType, setThreadType] = useState<DiscussionThreadType>("question");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!title.trim() || !body.trim()) return;

      setLoading(true);
      setError(null);

      try {
        const res = await discussionsApi.create(productSlug, {
          threadType,
          title: title.trim(),
          body: body.trim(),
        });

        if (res.success) {
          onCreated?.();
          router.push(`/discussions/${res.data.id}`);
        } else {
          setError(res.error.message);
        }
      } catch {
        setError("Failed to create discussion. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    [productSlug, threadType, title, body, router, onCreated],
  );

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-900 mb-3">Start a Discussion</h3>

      {/* Thread type selector */}
      <div className="mb-3">
        <label className="text-xs font-medium text-slate-600 mb-1.5 block">Type</label>
        <div className="flex flex-wrap gap-2">
          {THREAD_TYPES.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => setThreadType(t.value)}
              title={t.description}
              className={cn(
                "px-3 py-1.5 rounded-full text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
                threadType === t.value
                  ? "bg-[#F97316] text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Title */}
      <div className="mb-3">
        <label htmlFor="thread-title" className="text-xs font-medium text-slate-600 mb-1.5 block">
          Title
        </label>
        <input
          id="thread-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="What do you want to discuss?"
          maxLength={300}
          required
          className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-slate-50 text-slate-900 placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:border-[#F97316] transition-colors"
        />
        <span className="text-[11px] text-slate-400 mt-1 block text-right">{title.length}/300</span>
      </div>

      {/* Body */}
      <div className="mb-4">
        <label htmlFor="thread-body" className="text-xs font-medium text-slate-600 mb-1.5 block">
          Details
        </label>
        <textarea
          id="thread-body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Provide more context..."
          required
          rows={4}
          className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-slate-50 text-slate-900 placeholder:text-slate-400 resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:border-[#F97316] transition-colors"
        />
      </div>

      {/* Error */}
      {error && (
        <p className="text-xs text-[#DC2626] mb-3">{error}</p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 justify-end">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-xs font-semibold text-slate-600 rounded-lg hover:bg-slate-100 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={loading || !title.trim() || !body.trim()}
          className={cn(
            "px-4 py-2 text-xs font-semibold rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
            loading || !title.trim() || !body.trim()
              ? "bg-slate-200 text-slate-400 cursor-not-allowed"
              : "bg-[#F97316] text-white hover:bg-[#EA580C]",
          )}
        >
          {loading ? "Posting..." : "Post"}
        </button>
      </div>
    </form>
  );
}
