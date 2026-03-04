import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { ThreadDetail } from "@/components/discussions/ThreadDetail";
import { discussionsApi } from "@/lib/api/discussions";

// ── Data fetching ────────────────────────────────────────────────────────────

async function fetchThread(id: string) {
  const res = await discussionsApi.get(id);
  if (!res.success) return null;
  return { thread: res.data.thread, replies: res.data.replies ?? [] };
}

// ── Metadata ─────────────────────────────────────────────────────────────────

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const data = await fetchThread(id);

  if (!data) {
    return { title: "Discussion Not Found — Whydud" };
  }

  return {
    title: `${data.thread.title} — Discussion | Whydud`,
    description: data.thread.body.slice(0, 160),
  };
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default async function DiscussionPage({ params }: PageProps) {
  const { id } = await params;
  const data = await fetchThread(id);

  if (!data) {
    notFound();
  }

  return (
    <>
      <Header />
      <main className="min-h-[calc(100vh-64px)] bg-[#F8FAFC] py-6 px-4 md:px-8">
        <ThreadDetail
          thread={data.thread}
          replies={data.replies}
        />
      </main>
    </>
  );
}
