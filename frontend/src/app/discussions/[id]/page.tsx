import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { discussionsApi } from "@/lib/api/discussions";

interface DiscussionPageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: DiscussionPageProps): Promise<Metadata> {
  const { id } = await params;
  const res = await discussionsApi.get(id).catch(() => null);
  const title = res?.success ? String((res.data as { title?: string }).title ?? "Discussion") : "Discussion";
  return { title };
}

export default async function DiscussionPage({ params }: DiscussionPageProps) {
  const { id } = await params;
  const res = await discussionsApi.get(id).catch(() => null);
  if (!res?.success) notFound();

  const thread = res.data as {
    id: string;
    title: string;
    body: string;
    threadType: string;
    upvotes: number;
    replyCount: number;
    replies?: Array<{ id: string; body: string; upvotes: number; isAccepted: boolean }>;
  };

  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="text-2xl font-bold mb-2">{thread.title}</h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground mb-6">
          <span className="capitalize">{thread.threadType}</span>
          <span>▲ {thread.upvotes}</span>
          <span>💬 {thread.replyCount} replies</span>
        </div>

        <div className="rounded-xl border bg-card p-6 mb-6">
          <p className="text-sm whitespace-pre-line">{thread.body}</p>
        </div>

        {/* Replies */}
        <h2 className="text-lg font-semibold mb-4">Replies</h2>
        <div className="flex flex-col gap-4">
          {(thread.replies ?? []).map((reply) => (
            <div
              key={reply.id}
              className={`rounded-xl border p-4 ${reply.isAccepted ? "border-green-500 bg-green-50" : "bg-card"}`}
            >
              {reply.isAccepted && (
                <span className="text-xs font-semibold text-green-700 mb-2 block">✓ Accepted Answer</span>
              )}
              <p className="text-sm">{reply.body}</p>
              <div className="mt-2 text-xs text-muted-foreground">▲ {reply.upvotes}</div>
            </div>
          ))}
        </div>

        {/* Reply form — TODO Sprint 4: auth gate */}
        <div className="mt-8">
          <h3 className="font-semibold mb-2">Add a reply</h3>
          <textarea
            className="w-full rounded-xl border bg-muted px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary"
            rows={4}
            placeholder="Share your experience or answer…"
          />
          <button className="mt-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
            Post reply
          </button>
        </div>
      </main>
      <Footer />
    </>
  );
}
