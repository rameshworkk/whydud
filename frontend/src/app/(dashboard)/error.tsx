"use client";

import { useEffect } from "react";
import Link from "next/link";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function DashboardError({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-8 text-center">
      <h2 className="text-xl font-bold text-slate-900">Something went wrong</h2>
      <p className="text-slate-500 max-w-md text-sm">
        {error.message ?? "An unexpected error occurred loading your dashboard."}
      </p>
      <div className="flex items-center gap-3">
        <button
          onClick={reset}
          className="rounded-full bg-[#F97316] px-5 py-2 text-sm font-semibold text-white hover:bg-[#EA580C] transition-colors"
        >
          Try again
        </button>
        <Link
          href="/dashboard"
          className="rounded-full border border-slate-200 px-5 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
        >
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
