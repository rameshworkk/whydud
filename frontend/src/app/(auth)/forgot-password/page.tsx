"use client";

import Link from "next/link";
import { useState } from "react";
import { authApi } from "@/lib/api/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    const res = await authApi.forgotPassword({ email });

    if (res.success) {
      setSent(true);
    } else if (!res.success && "error" in res) {
      setError(res.error.message);
    }

    setIsLoading(false);
  }

  return (
    <>
      {/* Logo + heading */}
      <div className="mb-8 text-center">
        <Link
          href="/"
          className="text-2xl font-black text-[#F97316] tracking-tight"
        >
          Whydud
        </Link>
        <h1 className="mt-3 text-2xl font-semibold text-slate-900">
          Forgot password
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Enter your email and we&apos;ll send you a reset link.
        </p>
      </div>

      {sent ? (
        <div className="text-center">
          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-5 mb-4">
            <p className="text-sm font-medium text-green-800">
              Check your email
            </p>
            <p className="mt-1 text-xs text-green-600">
              If an account with that email exists, we&apos;ve sent a password
              reset link. Check your inbox (and spam folder).
            </p>
          </div>
          <Link
            href="/login"
            className="text-sm font-medium text-[#F97316] hover:text-[#EA580C] transition-colors"
          >
            Back to sign in
          </Link>
        </div>
      ) : (
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="email"
              className="text-sm font-medium text-slate-700"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-lg bg-[#F97316] py-2.5 text-sm font-semibold text-white hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isLoading ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}

      <p className="mt-6 text-center text-sm text-slate-500">
        Remember your password?{" "}
        <Link
          href="/login"
          className="font-medium text-[#F97316] hover:text-[#EA580C] transition-colors"
        >
          Sign in
        </Link>
      </p>
    </>
  );
}
