"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#F8FAFC] font-sans antialiased">
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center">
          <h2 className="text-2xl font-bold text-[#1E293B]">Something went wrong</h2>
          <p className="max-w-md text-sm text-[#64748B]">
            {error.message ?? "An unexpected error occurred. Please try again."}
          </p>
          <button
            onClick={reset}
            className="rounded-md bg-[#F97316] px-4 py-2 text-sm font-medium text-white hover:bg-[#EA580C] transition-colors"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
