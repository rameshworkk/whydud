import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Create your Whydud account" };

export default function RegisterPage() {
  // TODO Sprint 1 Week 2: multi-step registration
  // Step 1: email + password
  // Step 2: @whyd.xyz username
  // Step 3: onboarding (city, card vault, marketplace setup guide)
  return (
    <>
      <div className="mb-8 text-center">
        <Link href="/" className="text-2xl font-black">Whydud</Link>
        <h1 className="mt-2 text-xl font-semibold">Create your account</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Get your free @whyd.xyz shopping email and start tracking.
        </p>
      </div>

      <form className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="name" className="text-sm font-medium">Full name</label>
          <input
            id="name"
            type="text"
            autoComplete="name"
            className="rounded-lg border bg-muted px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="email" className="text-sm font-medium">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            className="rounded-lg border bg-muted px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="password" className="text-sm font-medium">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            className="rounded-lg border bg-muted px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
          />
          <p className="text-xs text-muted-foreground">Minimum 8 characters</p>
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="username" className="text-sm font-medium">
            @whyd.xyz username <span className="text-muted-foreground font-normal">(optional)</span>
          </label>
          <div className="flex rounded-lg border bg-muted overflow-hidden focus-within:ring-2 focus-within:ring-primary">
            <input
              id="username"
              type="text"
              placeholder="ramesh"
              className="flex-1 bg-transparent px-3 py-2 text-sm outline-none"
            />
            <span className="flex items-center px-3 text-sm text-muted-foreground bg-muted border-l">
              @whyd.xyz
            </span>
          </div>
        </div>

        <button
          type="submit"
          className="rounded-lg bg-primary py-2.5 font-semibold text-primary-foreground"
        >
          Create account
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="text-primary font-medium">
          Sign in
        </Link>
      </p>
    </>
  );
}
