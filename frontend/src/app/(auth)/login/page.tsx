import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Sign in to Whydud" };

export default function LoginPage() {
  // TODO Sprint 1 Week 2: wire to authApi.login + Google OAuth
  return (
    <>
      <div className="mb-8 text-center">
        <Link href="/" className="text-2xl font-black">Whydud</Link>
        <h1 className="mt-2 text-xl font-semibold">Sign in</h1>
      </div>

      <form className="flex flex-col gap-4">
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
            autoComplete="current-password"
            required
            className="rounded-lg border bg-muted px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <button
          type="submit"
          className="rounded-lg bg-primary py-2.5 font-semibold text-primary-foreground"
        >
          Sign in
        </button>
      </form>

      <div className="my-4 flex items-center gap-3 text-xs text-muted-foreground">
        <hr className="flex-1" /> or <hr className="flex-1" />
      </div>

      <button className="w-full rounded-lg border py-2.5 text-sm font-medium hover:bg-muted">
        Continue with Google
      </button>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Don&apos;t have an account?{" "}
        <Link href="/register" className="text-primary font-medium">
          Sign up
        </Link>
      </p>
    </>
  );
}
