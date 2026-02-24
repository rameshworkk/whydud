"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense } from "react";
import { authApi } from "@/lib/api/auth";
import { useAuth } from "@/hooks/useAuth";

function OAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [error, setError] = useState("");

  useEffect(() => {
    const code = searchParams.get("code");
    const urlError = searchParams.get("error");

    if (urlError) {
      setError(urlError === "oauth_failed" ? "Google sign-in failed. Please try again." : urlError);
      return;
    }

    if (!code) {
      setError("No authorization code received.");
      return;
    }

    async function exchangeCode(oauthCode: string) {
      const res = await authApi.exchangeOAuthCode(oauthCode);

      if (res.success && "data" in res) {
        login(res.data.token, res.data.user);
        router.push("/dashboard");
      } else if (!res.success && "error" in res) {
        setError(res.error.message);
      }
    }

    exchangeCode(code);
  }, [searchParams, login, router]);

  if (error) {
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
            Sign-in failed
          </h1>
        </div>

        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-5 mb-4 text-center">
          <p className="text-sm font-medium text-red-800">
            Unable to complete sign-in
          </p>
          <p className="mt-1 text-xs text-red-600">{error}</p>
        </div>

        <Link
          href="/login"
          className="block text-center text-sm font-medium text-[#F97316] hover:text-[#EA580C] transition-colors"
        >
          Try signing in again
        </Link>
      </>
    );
  }

  return (
    <>
      <div className="mb-8 text-center">
        <Link
          href="/"
          className="text-2xl font-black text-[#F97316] tracking-tight"
        >
          Whydud
        </Link>
      </div>

      <div className="text-center py-4">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-[#F97316] border-r-transparent mb-3" />
        <p className="text-sm text-slate-500">Completing sign-in...</p>
      </div>
    </>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="text-center py-4">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-[#F97316] border-r-transparent mb-3" />
          <p className="text-sm text-slate-500">Loading...</p>
        </div>
      }
    >
      <OAuthCallbackContent />
    </Suspense>
  );
}
