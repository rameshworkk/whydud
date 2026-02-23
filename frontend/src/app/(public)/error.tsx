"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function PublicError({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <>
      <Header />
      <main className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-8 text-center">
        <h2 className="text-2xl font-bold text-slate-900">Something went wrong</h2>
        <p className="text-slate-500 max-w-md text-sm">
          {error.message ?? "An unexpected error occurred. Please try again."}
        </p>
        <div className="flex items-center gap-3">
          <button
            onClick={reset}
            className="rounded-full bg-[#F97316] px-5 py-2 text-sm font-semibold text-white hover:bg-[#EA580C] transition-colors"
          >
            Try again
          </button>
          <Link
            href="/"
            className="rounded-full border border-slate-200 px-5 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
          >
            Go home
          </Link>
        </div>
      </main>
      <Footer />
    </>
  );
}
