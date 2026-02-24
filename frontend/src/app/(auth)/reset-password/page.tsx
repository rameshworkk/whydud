"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { authApi } from "@/lib/api/auth";

export default function ResetPasswordPage() {
  const searchParams = useSearchParams();
  const uid = searchParams.get("uid") ?? "";
  const token = searchParams.get("token") ?? "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const missingParams = !uid || !token;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);

    const res = await authApi.resetPassword({ uid, token, newPassword });

    if (res.success) {
      setSuccess(true);
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
          Reset password
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Enter your new password below.
        </p>
      </div>

      {missingParams ? (
        <div className="text-center">
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-5 mb-4">
            <p className="text-sm font-medium text-red-800">Invalid link</p>
            <p className="mt-1 text-xs text-red-600">
              This reset link is invalid or has expired. Please request a new
              one.
            </p>
          </div>
          <Link
            href="/forgot-password"
            className="text-sm font-medium text-[#F97316] hover:text-[#EA580C] transition-colors"
          >
            Request new reset link
          </Link>
        </div>
      ) : success ? (
        <div className="text-center">
          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-5 mb-4">
            <p className="text-sm font-medium text-green-800">
              Password reset successfully
            </p>
            <p className="mt-1 text-xs text-green-600">
              You can now sign in with your new password.
            </p>
          </div>
          <Link
            href="/login"
            className="inline-block rounded-lg bg-[#F97316] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#EA580C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2"
          >
            Sign in
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
              htmlFor="newPassword"
              className="text-sm font-medium text-slate-700"
            >
              New password
            </label>
            <input
              id="newPassword"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              placeholder="Minimum 8 characters"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="confirmPassword"
              className="text-sm font-medium text-slate-700"
            >
              Confirm password
            </label>
            <input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              placeholder="Re-enter your new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-lg bg-[#F97316] py-2.5 text-sm font-semibold text-white hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isLoading ? "Resetting…" : "Reset password"}
          </button>
        </form>
      )}

      <p className="mt-6 text-center text-sm text-slate-500">
        <Link
          href="/login"
          className="font-medium text-[#F97316] hover:text-[#EA580C] transition-colors"
        >
          Back to sign in
        </Link>
      </p>
    </>
  );
}
