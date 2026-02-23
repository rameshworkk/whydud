import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export default function DealsLoading() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-[1280px] px-4 py-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-40 rounded bg-slate-200" />
          <div className="h-4 w-72 rounded bg-slate-100" />

          <div className="flex gap-2">
            {Array.from({ length: 4 }, (_, i) => (
              <div key={i} className="h-9 w-24 rounded-full bg-slate-200" />
            ))}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i} className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-16 h-16 rounded-lg bg-slate-100" />
                  <div className="flex-1">
                    <div className="h-3.5 w-3/4 rounded bg-slate-100 mb-2" />
                    <div className="h-3 w-1/2 rounded bg-slate-100" />
                  </div>
                </div>
                <div className="h-5 w-24 rounded bg-slate-100 mb-2" />
                <div className="h-8 w-full rounded-lg bg-slate-100" />
              </div>
            ))}
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
