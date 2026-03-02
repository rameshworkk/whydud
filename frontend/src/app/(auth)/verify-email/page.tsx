"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense } from "react";
import { authApi } from "@/lib/api/auth";

type Status = "verifying" | "success" | "error" | "missing";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const uid = searchParams.get("uid") ?? "";
  const token = searchParams.get("token") ?? "";

  const [status, setStatus] = useState<Status>(!uid || !token ? "missing" : "verifying");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!uid || !token) return;

    async function verify() {
      const res = await authApi.verifyEmail({ uid, token });

      if (res.success) {
        setStatus("success");
      } else if (!res.success && "error" in res) {
        setMessage(res.error.message);
        setStatus("error");
      }
    }

    verify();
  }, [uid, token]);

  return (
    <>
      <div className="mb-8 text-center">
        <Link
          href="/"
          className="text-2xl font-black text-[#F97316] tracking-tight"
        >
          Whydud
        </Link>
        <h1 className="mt-3 text-2xl font-semibold text-slate-900">
          Email verification
        </h1>
      </div>

      {status === "verifying" && (
        <div className="text-center py-4">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-[#F97316] border-r-transparent mb-3" />
          <p className="text-sm text-slate-500">Verifying your email...</p>
        </div>
      )}

      {status === "success" && (
        <div className="text-center">
          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-5 mb-4">
            <p className="text-sm font-medium text-green-800">
              Email verified!
            </p>
            <p className="mt-1 text-xs text-green-600">
              Your email has been verified successfully.
            </p>
          </div>
          <Link
            href="/dashboard"
            className="inline-block rounded-lg bg-[#F97316] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2"
          >
            Go to Dashboard
          </Link>
        </div>
      )}

      {status === "error" && (
        <div className="text-center">
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-5 mb-4">
            <p className="text-sm font-medium text-red-800">
              Verification failed
            </p>
            <p className="mt-1 text-xs text-red-600">
              {message || "This verification link is invalid or has expired."}
            </p>
          </div>
          <Link
            href="/login"
            className="text-sm font-medium text-[#F97316] hover:text-[#EA580C] transition-colors"
          >
            Sign in to request a new link
          </Link>
        </div>
      )}

      {status === "missing" && (
        <div className="text-center">
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-5 mb-4">
            <p className="text-sm font-medium text-red-800">Invalid link</p>
            <p className="mt-1 text-xs text-red-600">
              This verification link is missing required parameters.
            </p>
          </div>
          <Link
            href="/login"
            className="text-sm font-medium text-[#F97316] hover:text-[#EA580C] transition-colors"
          >
            Sign in
          </Link>
        </div>
      )}
    </>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="text-center py-4">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-[#F97316] border-r-transparent mb-3" />
          <p className="text-sm text-slate-500">Loading...</p>
        </div>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
