import Link from "next/link";
import { Header } from "@/components/layout/Header";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/inbox", label: "Inbox", icon: "📬" },
  { href: "/wishlists", label: "Wishlists", icon: "❤️" },
  { href: "/purchases", label: "Purchases", icon: "🛍️" },
  { href: "/refunds", label: "Refunds", icon: "↩️" },
  { href: "/subscriptions", label: "Subscriptions", icon: "🔁" },
  { href: "/rewards", label: "Rewards", icon: "🎁" },
  { href: "/settings", label: "Settings", icon: "⚙️" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  // TODO Sprint 1 Week 2: redirect unauthenticated users to /login
  return (
    <>
      <Header />
      <div className="mx-auto max-w-7xl px-4 py-6 flex gap-6">
        {/* Sidebar */}
        <nav className="hidden md:flex flex-col gap-1 w-52 shrink-0">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        {/* Page content */}
        <div className="flex-1 min-w-0">{children}</div>
      </div>
    </>
  );
}
