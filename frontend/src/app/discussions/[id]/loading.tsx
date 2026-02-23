import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export default function DiscussionLoading() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-4 py-8 animate-pulse">
        <div className="h-7 w-3/4 rounded bg-slate-200 mb-3" />
        <div className="flex gap-4 mb-6">
          <div className="h-4 w-16 rounded bg-slate-100" />
          <div className="h-4 w-16 rounded bg-slate-100" />
          <div className="h-4 w-20 rounded bg-slate-100" />
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-6 mb-6">
          <div className="h-4 w-full rounded bg-slate-100 mb-2" />
          <div className="h-4 w-5/6 rounded bg-slate-100 mb-2" />
          <div className="h-4 w-3/4 rounded bg-slate-100" />
        </div>
        <div className="h-5 w-24 rounded bg-slate-200 mb-4" />
        <div className="space-y-4">
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="rounded-xl border border-slate-200 bg-white p-4 h-24" />
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
