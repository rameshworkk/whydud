import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export default function SellerLoading() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-[1280px] px-4 py-6">
        <div className="flex gap-6 animate-pulse">
          <div className="flex-1 min-w-0">
            {/* Header card */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 mb-6">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-xl bg-slate-200" />
                <div className="flex-1">
                  <div className="h-5 w-48 rounded bg-slate-200 mb-2" />
                  <div className="h-3 w-64 rounded bg-slate-100" />
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 mb-6">
              {Array.from({ length: 4 }, (_, i) => (
                <div key={i} className="h-9 w-28 rounded-full bg-slate-200" />
              ))}
            </div>

            {/* Content */}
            <div className="space-y-4">
              <div className="h-4 w-full rounded bg-slate-100" />
              <div className="h-4 w-5/6 rounded bg-slate-100" />
              <div className="h-4 w-4/6 rounded bg-slate-100" />
            </div>
          </div>

          {/* Sidebar */}
          <div className="w-[320px] shrink-0 hidden lg:flex flex-col gap-4">
            <div className="rounded-xl border border-slate-200 bg-white p-5 h-48" />
            <div className="rounded-xl border border-slate-200 bg-white p-5 h-36" />
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
