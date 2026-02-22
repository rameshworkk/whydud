import Link from "next/link";

/** Site footer — server component. */
export function Footer() {
  return (
    <footer className="border-t bg-muted/40 py-8 text-sm text-muted-foreground">
      <div className="mx-auto max-w-7xl px-4">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          <div>
            <p className="font-semibold text-foreground mb-2">Whydud</p>
            <p className="text-xs">India&apos;s Product Intelligence Platform</p>
          </div>
          <div>
            <p className="font-semibold text-foreground mb-2">Discover</p>
            <ul className="space-y-1">
              <li><Link href="/search" className="hover:text-foreground">Search</Link></li>
              <li><Link href="/deals" className="hover:text-foreground">Deals</Link></li>
              <li><Link href="/compare" className="hover:text-foreground">Compare</Link></li>
            </ul>
          </div>
          <div>
            <p className="font-semibold text-foreground mb-2">Account</p>
            <ul className="space-y-1">
              <li><Link href="/dashboard" className="hover:text-foreground">Dashboard</Link></li>
              <li><Link href="/inbox" className="hover:text-foreground">Inbox</Link></li>
              <li><Link href="/wishlists" className="hover:text-foreground">Wishlists</Link></li>
            </ul>
          </div>
          <div>
            <p className="font-semibold text-foreground mb-2">Legal</p>
            <ul className="space-y-1">
              <li><Link href="/privacy" className="hover:text-foreground">Privacy Policy</Link></li>
              <li><Link href="/terms" className="hover:text-foreground">Terms of Service</Link></li>
            </ul>
          </div>
        </div>
        <p className="mt-8 text-xs text-center">
          © {new Date().getFullYear()} Whydud. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
