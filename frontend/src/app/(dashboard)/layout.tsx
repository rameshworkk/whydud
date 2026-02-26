"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { MobileNav } from "@/components/layout/MobileNav";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // Show layout shell with spinner while checking auth
  if (isLoading) {
    return (
      <>
        <Header />
        <div
          className="mx-auto px-4 md:px-6 py-6 flex gap-6"
          style={{ maxWidth: "var(--max-width)" }}
        >
          <aside className="hidden md:block w-52 shrink-0">
            <div className="sticky top-[calc(var(--header-height)+1.5rem)]">
              <Sidebar />
            </div>
          </aside>
          <main className="flex-1 min-w-0">
            <div className="flex items-center justify-center py-20">
              <div className="w-6 h-6 border-2 border-[#F97316] border-t-transparent rounded-full animate-spin" />
            </div>
          </main>
        </div>
      </>
    );
  }

  // useEffect above will redirect — render nothing while that happens
  if (!isAuthenticated) return null;

  return (
    <>
      <Header />

      <div
        className="mx-auto px-4 md:px-6 py-6 flex gap-6"
        style={{ maxWidth: "var(--max-width)" }}
      >
        {/* Desktop sidebar */}
        <aside className="hidden md:block w-52 shrink-0">
          <div className="sticky top-[calc(var(--header-height)+1.5rem)]">
            <Sidebar />
          </div>
        </aside>

        {/* Mobile nav trigger — rendered inside page header area */}
        <div className="md:hidden absolute top-4 left-4 z-40">
          <MobileNav />
        </div>

        {/* Page content */}
        <main className="flex-1 min-w-0">{children}</main>
      </div>
    </>
  );
}
