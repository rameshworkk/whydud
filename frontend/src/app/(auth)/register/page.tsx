"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { authApi } from "@/lib/api/auth";
import { useAuth } from "@/hooks/useAuth";

const STEPS = ["Create Account", "Choose Email", "Get Started"];

const MARKETPLACES = [
  { name: "Amazon.in", logo: "\uD83D\uDED2", instructions: "Go to Account \u2192 Manage email addresses \u2192 Add your @whyd.xyz email" },
  { name: "Flipkart", logo: "\uD83D\uDECD\uFE0F", instructions: "Go to My Account \u2192 Edit Profile \u2192 Add email address" },
  { name: "Myntra", logo: "\uD83D\uDC57", instructions: "Go to Profile \u2192 Edit \u2192 Update email to your @whyd.xyz" },
  { name: "Ajio", logo: "\uD83E\uDDE5", instructions: "Go to My Account \u2192 Personal Information \u2192 Update email" },
  { name: "Nykaa", logo: "\uD83D\uDC84", instructions: "Go to My Profile \u2192 Edit \u2192 Add your @whyd.xyz email" },
  { name: "Croma", logo: "\uD83D\uDCF1", instructions: "Go to My Account \u2192 Profile \u2192 Update email address" },
  { name: "Tata CLiQ", logo: "\uD83C\uDFEC", instructions: "Go to My Account \u2192 Profile Settings \u2192 Update email" },
  { name: "Meesho", logo: "\uD83D\uDED2", instructions: "Go to My Account \u2192 Settings \u2192 Update email" },
];

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center justify-center gap-0 mb-8">
      {STEPS.map((label, i) => (
        <div key={label} className="flex items-center">
          {i > 0 && (
            <div
              className={`w-10 h-0.5 ${
                i <= current ? "bg-[#F97316]" : "bg-slate-200"
              }`}
            />
          )}
          <div className="flex flex-col items-center">
            <div
              className={`w-3 h-3 rounded-full border-2 transition-colors ${
                i < current
                  ? "bg-[#F97316] border-[#F97316]"
                  : i === current
                  ? "bg-white border-[#F97316]"
                  : "bg-white border-slate-300"
              }`}
            />
            <span
              className={`text-[10px] mt-1.5 font-medium ${
                i <= current ? "text-[#F97316]" : "text-slate-400"
              }`}
            >
              {label}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

function Step1CreateAccount({
  onNext,
}: {
  onNext: (data: { name: string; email: string; token: string }) => void;
}) {
  const { login } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Simple password strength (0-4)
  const strength = [
    password.length >= 8,
    /[A-Z]/.test(password),
    /[0-9]/.test(password),
    /[^a-zA-Z0-9]/.test(password),
  ].filter(Boolean).length;
  const strengthColors = ["bg-red-400", "bg-orange-400", "bg-yellow-400", "bg-green-400"];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    const res = await authApi.register({ email, password, name });

    if (res.success) {
      const { token, user } = res.data;
      login(token, user);
      onNext({ name, email, token });
    } else {
      setError(res.error.message);
      setIsLoading(false);
    }
  }

  return (
    <>
      <div className="mb-6 text-center">
        <h1 className="text-2xl font-semibold text-slate-900">
          Create your account
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Get your free @whyd.xyz shopping email and start tracking.
        </p>
      </div>

      <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Full name */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="name" className="text-sm font-medium text-slate-700">
            Full name
          </label>
          <input
            id="name"
            type="text"
            autoComplete="name"
            required
            placeholder="Enter your full name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
          />
        </div>

        {/* Email */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="email" className="text-sm font-medium text-slate-700">
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

        {/* Password */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="password"
            className="text-sm font-medium text-slate-700"
          >
            Password
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              required
              minLength={8}
              placeholder="Minimum 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-[#E2E8F0] bg-white px-3 py-2.5 pr-10 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:ring-2 focus:ring-[#F97316] focus:border-[#F97316] transition-shadow"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                  <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              )}
            </button>
          </div>
          {/* Password strength bar */}
          <div className="flex gap-1 mt-1">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className={`h-1 flex-1 rounded-full transition-colors ${
                  password.length > 0 && i < strength
                    ? strengthColors[strength - 1]
                    : "bg-slate-200"
                }`}
              />
            ))}
          </div>
          <p className="text-xs text-slate-400">Minimum 8 characters</p>
        </div>

        {/* Terms */}
        <label className="flex items-start gap-2 cursor-pointer">
          <input
            type="checkbox"
            required
            className="rounded border-slate-300 text-[#F97316] focus:ring-[#F97316] w-4 h-4 mt-0.5"
          />
          <span className="text-xs text-slate-500 leading-relaxed">
            I agree to the{" "}
            <Link href="/terms" className="text-[#F97316] hover:underline">
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link href="/privacy" className="text-[#F97316] hover:underline">
              Privacy Policy
            </Link>
          </span>
        </label>

        {/* Create account button */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full rounded-lg bg-[#F97316] py-2.5 text-sm font-semibold text-white hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isLoading ? "Creating account\u2026" : "Create account"}
        </button>
      </form>

      {/* Divider */}
      <div className="my-5 flex items-center gap-3">
        <hr className="flex-1 border-[#E2E8F0]" />
        <span className="text-xs text-slate-400 font-medium">or</span>
        <hr className="flex-1 border-[#E2E8F0]" />
      </div>

      {/* Google OAuth */}
      <a
        href="/accounts/google/login/?process=login"
        className="w-full flex items-center justify-center gap-2.5 rounded-lg border border-[#E2E8F0] bg-white py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 active:bg-slate-100 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2"
      >
        <svg width="18" height="18" viewBox="0 0 24 24">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A11.96 11.96 0 0 0 1 12c0 1.94.46 3.77 1.18 5.07l3.66-2.98z" fill="#FBBC05" />
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
        </svg>
        Continue with Google
      </a>

      {/* Sign in link */}
      <p className="mt-6 text-center text-sm text-slate-500">
        Already have an account?{" "}
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

function Step2ChooseEmail({ onNext, onSkip }: { onNext: (username: string) => void; onSkip: () => void }) {
  const [username, setUsername] = useState("");
  const [checking, setChecking] = useState(false);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function checkAvailability(value: string) {
    if (value.length < 3) {
      setAvailable(null);
      return;
    }
    setChecking(true);
    const { whydudEmailApi } = await import("@/lib/api/auth");
    const res = await whydudEmailApi.checkAvailability(value);
    if (res.success) {
      setAvailable(res.data.available);
    }
    setChecking(false);
  }

  async function handleCreate() {
    if (!username || username.length < 3) return;
    setError("");
    setIsLoading(true);
    const { whydudEmailApi } = await import("@/lib/api/auth");
    const res = await whydudEmailApi.create(username);
    if (res.success) {
      onNext(username);
    } else {
      setError(res.error.message);
      setIsLoading(false);
    }
  }

  return (
    <>
      <div className="mb-6 text-center">
        <span className="text-3xl mb-3 block">{"\uD83D\uDCE7"}</span>
        <h1 className="text-2xl font-semibold text-slate-900">
          Get your free @whyd.xyz email
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Use this on shopping sites for automatic purchase tracking
        </p>
      </div>

      <div className="flex flex-col gap-4">
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Username input */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="username"
            className="text-sm font-medium text-slate-700"
          >
            Choose your username
          </label>
          <div className="flex rounded-lg border border-[#E2E8F0] overflow-hidden focus-within:ring-2 focus-within:ring-[#F97316] focus-within:border-[#F97316] transition-shadow">
            <input
              id="username"
              type="text"
              placeholder="ramesh"
              value={username}
              onChange={(e) => {
                const v = e.target.value.toLowerCase().replace(/[^a-z0-9._-]/g, "");
                setUsername(v);
                setAvailable(null);
                checkAvailability(v);
              }}
              className="flex-1 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none placeholder:text-slate-400"
            />
            <span className="flex items-center px-3 text-sm text-slate-500 bg-slate-50 border-l border-[#E2E8F0] font-medium">
              @whyd.xyz
            </span>
          </div>
          {username.length > 0 && (
            <p
              className={`text-xs font-medium ${
                checking
                  ? "text-slate-400"
                  : available === true
                  ? "text-green-600"
                  : available === false
                  ? "text-red-500"
                  : username.length < 3
                  ? "text-red-500"
                  : "text-slate-400"
              }`}
            >
              {checking
                ? "Checking\u2026"
                : available === true
                ? "\u2705 Available!"
                : available === false
                ? "Username is taken or reserved"
                : username.length < 3
                ? "Username must be at least 3 characters"
                : ""}
            </p>
          )}
        </div>

        {/* Create email button */}
        <button
          onClick={handleCreate}
          disabled={!available || isLoading}
          className="w-full rounded-lg bg-[#F97316] py-2.5 text-sm font-semibold text-white hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? "Creating email\u2026" : "Create email"}
        </button>

        {/* Skip */}
        <button
          onClick={onSkip}
          className="text-sm text-slate-500 hover:text-slate-700 font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
        >
          Skip for now \u2192
        </button>
      </div>
    </>
  );
}

function Step3Onboarding() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [checked, setChecked] = useState<Set<string>>(new Set());

  const toggle = (name: string) => {
    setExpanded(expanded === name ? null : name);
  };

  const toggleCheck = (name: string) => {
    const next = new Set(checked);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setChecked(next);
  };

  return (
    <>
      <div className="mb-6 text-center">
        <h1 className="text-2xl font-semibold text-slate-900">
          Register on shopping sites
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Add your @whyd.xyz email to these marketplaces for automatic tracking
        </p>
      </div>

      {/* Progress */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-medium text-slate-600">
            {checked.size} of {MARKETPLACES.length} sites set up
          </span>
          <span className="text-xs text-slate-400">
            {Math.round((checked.size / MARKETPLACES.length) * 100)}%
          </span>
        </div>
        <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
          <div
            className="h-full rounded-full bg-[#F97316] transition-all"
            style={{
              width: `${(checked.size / MARKETPLACES.length) * 100}%`,
            }}
          />
        </div>
      </div>

      {/* Marketplace list */}
      <div className="flex flex-col gap-2 max-h-[340px] overflow-y-auto no-scrollbar">
        {MARKETPLACES.map((mp) => (
          <div
            key={mp.name}
            className="rounded-lg border border-[#E2E8F0] bg-white overflow-hidden"
          >
            <button
              onClick={() => toggle(mp.name)}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
            >
              <span className="text-lg shrink-0">{mp.logo}</span>
              <span className="flex-1 text-sm font-medium text-slate-700">
                {mp.name}
              </span>
              {checked.has(mp.name) && (
                <span className="text-xs font-semibold text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
                  Done
                </span>
              )}
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className={`text-slate-400 transition-transform ${
                  expanded === mp.name ? "rotate-180" : ""
                }`}
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>
            {expanded === mp.name && (
              <div className="px-4 pb-3 border-t border-[#E2E8F0]">
                <p className="text-xs text-slate-500 leading-relaxed mt-2 mb-3">
                  {mp.instructions}
                </p>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checked.has(mp.name)}
                    onChange={() => toggleCheck(mp.name)}
                    className="rounded border-slate-300 text-[#F97316] focus:ring-[#F97316] w-4 h-4"
                  />
                  <span className="text-xs font-medium text-slate-600">
                    I&apos;ve added it
                  </span>
                </label>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* CTA */}
      <div className="mt-5 flex flex-col gap-2">
        <Link
          href="/dashboard"
          className="w-full rounded-lg bg-[#F97316] py-2.5 text-sm font-semibold text-white text-center hover:bg-[#EA580C] active:bg-[#C2410C] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2"
        >
          Go to Dashboard
        </Link>
        <Link
          href="/dashboard"
          className="text-sm text-slate-500 hover:text-slate-700 font-medium text-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded"
        >
          I&apos;ll do this later
        </Link>
      </div>
    </>
  );
}

export default function RegisterPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);

  function handleAccountCreated() {
    setStep(1);
  }

  function handleEmailCreated() {
    setStep(2);
  }

  function handleSkipEmail() {
    // User skipped email — go directly to dashboard
    router.push("/dashboard");
  }

  return (
    <>
      {/* Logo */}
      <div className="text-center mb-2">
        <Link
          href="/"
          className="text-2xl font-black text-[#F97316] tracking-tight"
        >
          Whydud
        </Link>
      </div>

      {/* Step indicator */}
      <StepIndicator current={step} />

      {/* Step content */}
      {step === 0 && <Step1CreateAccount onNext={handleAccountCreated} />}
      {step === 1 && (
        <Step2ChooseEmail onNext={handleEmailCreated} onSkip={handleSkipEmail} />
      )}
      {step === 2 && <Step3Onboarding />}
    </>
  );
}
