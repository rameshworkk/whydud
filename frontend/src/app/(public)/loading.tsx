import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export default function PublicLoading() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-[1280px] px-4 py-8">
        <div className="animate-pulse space-y-6">
          {/* Title skeleton */}
          <div className="h-8 w-64 rounded bg-slate-200" />
          <div className="h-4 w-96 rounded bg-slate-100" />

          {/* Grid skeleton */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 mt-8">
            {Array.from({ length: 8 }, (_, i) => (
              <div key={i} className="rounded-lg border border-slate-200 bg-white p-3">
                <div className="aspect-square rounded-lg bg-slate-100 mb-3" />
                <div className="h-3 w-16 rounded bg-slate-100" />
                <div className="h-4 w-full rounded bg-slate-100 mt-1" />
                <div className="h-4 w-3/4 rounded bg-slate-100 mt-1" />
                <div className="h-5 w-20 rounded bg-slate-100 mt-3" />
              </div>
            ))}
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
