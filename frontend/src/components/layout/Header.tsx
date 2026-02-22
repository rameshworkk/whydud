import Link from "next/link";

/** Top navigation bar — server component. */
export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4">
        <Link href="/" className="font-bold text-xl tracking-tight">
          Whydud
        </Link>

        {/* TODO Sprint 1 Week 3: SearchBar component */}
        <div className="flex-1" />

        <nav className="flex items-center gap-4 text-sm">
          <Link href="/deals" className="text-muted-foreground hover:text-foreground">
            Deals
          </Link>
          {/* TODO Sprint 1 Week 2: Auth-aware nav (wishlist, inbox, avatar) */}
          <Link
            href="/login"
            className="rounded-md bg-primary px-3 py-1.5 text-primary-foreground text-sm font-medium"
          >
            Sign in
          </Link>
        </nav>
      </div>
    </header>
  );
}
