import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { MobileNav } from "@/components/layout/MobileNav";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  // TODO Sprint 1 Week 2: redirect unauthenticated users to /login
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
