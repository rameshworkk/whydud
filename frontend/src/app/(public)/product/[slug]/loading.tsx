import { Header } from "@/components/layout/Header";

export default function ProductLoading() {
  return (
    <>
      <Header />
      <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-[#F8FAFC] animate-pulse">
        {/* Left sidebar skeleton */}
        <aside className="w-[260px] shrink-0 border-r border-slate-200 bg-white p-4">
          <div className="aspect-square rounded-xl bg-slate-100" />
          <div className="flex gap-2 mt-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="w-14 h-14 rounded-lg bg-slate-100" />
            ))}
          </div>
          <div className="mt-6 space-y-3">
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i} className="flex justify-between">
                <div className="h-3 w-20 rounded bg-slate-100" />
                <div className="h-3 w-24 rounded bg-slate-100" />
              </div>
            ))}
          </div>
        </aside>

        {/* Center skeleton */}
        <main className="flex-1 px-6 py-5 space-y-4">
          <div className="h-3 w-48 rounded bg-slate-100" />
          <div className="h-3 w-32 rounded bg-slate-100" />
          <div className="h-6 w-3/4 rounded bg-slate-200" />
          <div className="h-4 w-48 rounded bg-slate-100" />
          <div className="h-10 w-40 rounded bg-slate-200 mt-2" />
          <div className="h-48 rounded-xl bg-slate-100 mt-4" />
          <div className="h-64 rounded-xl bg-slate-100 mt-4" />
        </main>

        {/* Right sidebar skeleton */}
        <aside className="w-[340px] shrink-0 border-l border-slate-200 bg-white p-4 space-y-4">
          <div className="h-6 w-32 rounded bg-slate-200" />
          <div className="h-24 rounded-lg bg-slate-100" />
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="h-32 rounded-lg bg-slate-100" />
          ))}
        </aside>
      </div>
    </>
  );
}
