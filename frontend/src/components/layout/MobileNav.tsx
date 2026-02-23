"use client";

import { useState } from "react";
import { Menu, X } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Sidebar } from "./Sidebar";
import { cn } from "@/lib/utils/index";

/** Hamburger button + slide-out Sheet for dashboard mobile navigation. */
export function MobileNav() {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <button
          aria-label="Open navigation menu"
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-md md:hidden",
            "text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#1E293B]",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
            "transition-colors"
          )}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </SheetTrigger>

      <SheetContent side="left" className="w-64 p-0">
        <SheetHeader className="border-b border-[#E2E8F0] px-4 py-4">
          <SheetTitle className="text-left text-base font-semibold text-[#1E293B]">
            My Account
          </SheetTitle>
        </SheetHeader>

        <div className="p-3">
          <Sidebar onNavigate={() => setOpen(false)} />
        </div>
      </SheetContent>
    </Sheet>
  );
}
