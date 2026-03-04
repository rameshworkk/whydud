"use client";

import { useState, useEffect, useCallback } from "react";
import { ThreadCard } from "./ThreadCard";
import { CreateThreadForm } from "./CreateThreadForm";
import { productsApi } from "@/lib/api/products";
import type { DiscussionThread } from "@/types";

interface DiscussionSectionProps {
  productSlug: string;
}

/** Discussion threads section embedded on the product page — shows top 3. */
export function DiscussionSection({ productSlug }: DiscussionSectionProps) {
  const [threads, setThreads] = useState<DiscussionThread[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const fetchThreads = useCallback(async () => {
    setLoading(true);
    try {
      const res = await productsApi.getDiscussions(productSlug);
      if (res.success) {
        setThreads(res.data.slice(0, 3));
      }
    } finally {
      setLoading(false);
    }
  }, [productSlug]);

  useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  return (
    <section id="discussions" className="mt-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-700">Community Discussions</h2>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="text-xs font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
        >
          {showForm ? "Cancel" : "Start a Discussion"}
        </button>
      </div>

      {/* Create thread form */}
      {showForm && (
        <div className="mb-4">
          <CreateThreadForm
            productSlug={productSlug}
            onCancel={() => setShowForm(false)}
            onCreated={() => {
              setShowForm(false);
              fetchThreads();
            }}
          />
        </div>
      )}

      {/* Thread list */}
      {loading ? (
        <div className="py-6 flex justify-center">
          <span className="w-5 h-5 border-2 border-slate-200 border-t-[#F97316] rounded-full animate-spin" />
        </div>
      ) : threads.length > 0 ? (
        <div className="flex flex-col gap-3">
          {threads.map((thread) => (
            <ThreadCard key={thread.id} thread={thread} />
          ))}
          {threads.length >= 3 && (
            <a
              href={`/product/${productSlug}#discussions`}
              className="text-xs font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors text-center py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
            >
              View all discussions
            </a>
          )}
        </div>
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white p-6 text-center">
          <p className="text-sm text-slate-400 mb-2">No discussions yet.</p>
          {!showForm && (
            <button
              onClick={() => setShowForm(true)}
              className="text-xs font-semibold text-[#F97316] hover:text-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
            >
              Be the first to start a discussion
            </button>
          )}
        </div>
      )}
    </section>
  );
}
