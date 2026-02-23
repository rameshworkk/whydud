import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export default function CompareLoading() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-[1280px] px-4 py-6 animate-pulse">
        <div className="h-7 w-48 rounded bg-slate-200 mb-4" />
        <div className="bg-white rounded-xl border border-slate-200 p-6 mb-4">
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex flex-col items-center">
                <div className="w-28 h-36 rounded-lg bg-slate-100 mb-3" />
                <div className="h-4 w-32 rounded bg-slate-100" />
                <div className="h-5 w-20 rounded bg-slate-200 mt-2" />
              </div>
            ))}
          </div>
        </div>
        <div className="space-y-4">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="h-16 rounded-lg bg-slate-100" />
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
