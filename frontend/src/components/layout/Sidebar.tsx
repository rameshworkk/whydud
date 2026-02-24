"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Mail,
  Heart,
  ShoppingBag,
  RotateCcw,
  RefreshCw,
  Gift,
  Settings,
  LogOut,
  LucideIcon,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils/index";

interface NavItem {
  href: string;
  label: string;
  Icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
  { href: "/inbox", label: "Inbox", Icon: Mail },
  { href: "/wishlists", label: "Wishlists", Icon: Heart },
  { href: "/purchases", label: "Purchases", Icon: ShoppingBag },
  { href: "/refunds", label: "Refunds", Icon: RotateCcw },
  { href: "/subscriptions", label: "Subscriptions", Icon: RefreshCw },
  { href: "/rewards", label: "Rewards", Icon: Gift },
  { href: "/settings", label: "Settings", Icon: Settings },
];

interface SidebarProps {
  onNavigate?: () => void;
}

/** Dashboard sidebar navigation — client component (needs usePathname). */
export function Sidebar({ onNavigate }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { logout } = useAuth();

  async function handleLogout() {
    onNavigate?.();
    await logout();
    router.push("/");
  }

  return (
    <nav className="flex flex-col gap-0.5">
      {NAV_ITEMS.map(({ href, label, Icon }) => {
        const isActive = pathname === href || pathname.startsWith(href + "/");
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
              isActive
                ? "bg-[#FFF7ED] text-[#F97316]"
                : "text-[#64748B] hover:bg-[#F8FAFC] hover:text-[#1E293B]"
            )}
          >
            <Icon
              className={cn(
                "h-4 w-4 shrink-0",
                isActive ? "text-[#F97316]" : "text-[#94A3B8]"
              )}
            />
            {label}
          </Link>
        );
      })}

      <hr className="border-[#E2E8F0] my-2" />

      <button
        onClick={handleLogout}
        className={cn(
          "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
          "text-[#64748B] hover:bg-red-50 hover:text-red-600"
        )}
      >
        <LogOut className="h-4 w-4 shrink-0 text-[#94A3B8]" />
        Log out
      </button>
    </nav>
  );
}
