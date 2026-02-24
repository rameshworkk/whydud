"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search, ChevronDown, Bell, PenSquare, LogIn, Package, LogOut, LayoutDashboard } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils/index";

const CATEGORIES = [
  "Mobiles & Tablets",
  "Laptops & Computers",
  "TVs & Appliances",
  "Audio & Headphones",
  "Cameras & Accessories",
  "Air Conditioners",
  "Refrigerators",
  "Washing Machines",
  "Furniture & Decor",
  "Fashion",
  "Beauty & Personal Care",
  "Groceries & Kitchen",
];

const SEARCH_CATEGORIES = ["All Categories", ...CATEGORIES];

export function Header() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All Categories");
  const [categoryOpen, setCategoryOpen] = useState(false);
  const [browseOpen, setBrowseOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const categoryRef = useRef<HTMLDivElement>(null);
  const browseRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (categoryRef.current && !categoryRef.current.contains(e.target as Node)) {
        setCategoryOpen(false);
      }
      if (browseRef.current && !browseRef.current.contains(e.target as Node)) {
        setBrowseOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  async function handleLogout() {
    setUserMenuOpen(false);
    await logout();
    router.push("/");
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = searchQuery.trim();
    if (!q) return;
    const params = new URLSearchParams({ q });
    if (selectedCategory !== "All Categories") params.set("category", selectedCategory);
    router.push(`/search?${params.toString()}`);
  }

  const displayName = user?.name?.split(" ")[0] ?? "User";

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-[#E2E8F0] shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
      <div
        className="mx-auto flex h-16 items-center gap-3 px-4 md:px-6"
        style={{ maxWidth: "var(--max-width)" }}
      >
        {/* ── Logo ─────────────────────────────────────────────────── */}
        <Link
          href="/"
          className="flex items-center gap-2 shrink-0 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
        >
          <svg
            width="32"
            height="32"
            viewBox="0 0 32 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <rect width="32" height="32" rx="8" fill="#1E293B" />
            <path
              d="M8 11L16 7L24 11V21L16 25L8 21V11Z"
              fill="none"
              stroke="#4DB6AC"
              strokeWidth="1.5"
            />
            <path d="M8 11L16 15M16 15L24 11M16 15V25" stroke="#4DB6AC" strokeWidth="1.5" />
            <circle cx="16" cy="15" r="2.5" fill="#F97316" />
          </svg>
          <span className="hidden sm:block text-xl font-semibold text-[#1E293B] tracking-tight">
            Whydud
          </span>
        </Link>

        {/* ── Browse Categories ─────────────────────────────────────── */}
        <div ref={browseRef} className="relative hidden md:block shrink-0">
          <button
            onClick={() => setBrowseOpen((o) => !o)}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              "text-[#1E293B] hover:bg-[#F1F5F9] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
              browseOpen && "bg-[#F1F5F9]"
            )}
          >
            Browse Categories
            <ChevronDown
              className={cn(
                "h-4 w-4 transition-transform duration-150",
                browseOpen && "rotate-180"
              )}
            />
          </button>

          {browseOpen && (
            <div className="absolute left-0 top-full mt-1 w-64 rounded-lg border border-[#E2E8F0] bg-white shadow-lg py-1 z-50">
              {CATEGORIES.map((cat) => (
                <Link
                  key={cat}
                  href={`/search?category=${encodeURIComponent(cat)}`}
                  onClick={() => setBrowseOpen(false)}
                  className="block px-4 py-2 text-sm text-[#1E293B] hover:bg-[#F8FAFC] hover:text-[#F97316] transition-colors"
                >
                  {cat}
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* ── Search Bar ───────────────────────────────────────────── */}
        <form onSubmit={handleSearch} className="flex flex-1 items-stretch h-10 min-w-0">
          {/* Category prefix */}
          <div ref={categoryRef} className="relative hidden sm:block shrink-0">
            <button
              type="button"
              onClick={() => setCategoryOpen((o) => !o)}
              className={cn(
                "flex h-full items-center gap-1 rounded-l-full border border-r-0 border-[#E2E8F0]",
                "bg-[#F1F5F9] px-3 text-xs font-medium text-[#64748B]",
                "hover:bg-[#E2E8F0] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
                "whitespace-nowrap transition-colors"
              )}
            >
              <span className="max-w-[110px] truncate">{selectedCategory}</span>
              <ChevronDown
                className={cn(
                  "h-3 w-3 shrink-0 transition-transform duration-150",
                  categoryOpen && "rotate-180"
                )}
              />
            </button>

            {categoryOpen && (
              <div className="absolute left-0 top-full mt-1 w-52 rounded-lg border border-[#E2E8F0] bg-white shadow-lg py-1 z-50 max-h-64 overflow-y-auto">
                {SEARCH_CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => {
                      setSelectedCategory(cat);
                      setCategoryOpen(false);
                    }}
                    className={cn(
                      "w-full text-left px-3 py-1.5 text-sm transition-colors",
                      selectedCategory === cat
                        ? "text-[#F97316] bg-[#FFF7ED] font-medium"
                        : "text-[#1E293B] hover:bg-[#F8FAFC]"
                    )}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Search input */}
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search products, brands, and reviews…"
            className={cn(
              "flex-1 min-w-0 border border-[#E2E8F0] bg-[#F8FAFC] px-4 text-sm text-[#1E293B]",
              "placeholder:text-[#94A3B8] outline-none",
              "focus:border-[#F97316] focus:bg-white focus:ring-2 focus:ring-[#F97316]/20",
              "transition-all duration-150",
              "rounded-full sm:rounded-none"
            )}
          />

          {/* Search button */}
          <button
            type="submit"
            aria-label="Search"
            className={cn(
              "hidden sm:flex shrink-0 items-center justify-center rounded-r-full",
              "bg-[#F97316] px-4 text-white",
              "hover:bg-[#EA580C] active:bg-[#C2410C]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1",
              "transition-colors duration-150"
            )}
          >
            <Search className="h-4 w-4" />
          </button>
        </form>

        {/* ── Right nav ─────────────────────────────────────────────── */}
        <div className="flex items-center gap-1 shrink-0">
          <Link
            href="/reviews/new"
            className={cn(
              "hidden lg:flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium",
              "text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#1E293B]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
              "transition-colors"
            )}
          >
            <PenSquare className="h-4 w-4" />
            Post a Review
          </Link>

          {isLoading ? (
            <div className="h-9 w-32 rounded-full bg-[#F1F5F9] animate-pulse" />
          ) : isAuthenticated && user ? (
            <>
              <button
                aria-label="Notifications"
                className={cn(
                  "relative flex h-9 w-9 items-center justify-center rounded-md",
                  "text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#1E293B]",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
                  "transition-colors"
                )}
              >
                <Bell className="h-5 w-5" />
                <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-[#F97316]" />
              </button>

              <div ref={userMenuRef} className="relative">
                <button
                  onClick={() => setUserMenuOpen((o) => !o)}
                  className={cn(
                    "flex items-center gap-2 rounded-full pl-1 pr-3 py-1",
                    "bg-[#FFF7ED] hover:bg-[#FFE0C2]",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
                    "transition-colors"
                  )}
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#F97316] text-white text-sm font-semibold">
                    {displayName.charAt(0).toUpperCase()}
                  </span>
                  <span className="text-sm font-medium text-[#1E293B]">
                    Welcome, {displayName}
                  </span>
                  <ChevronDown
                    className={cn(
                      "h-3.5 w-3.5 text-[#64748B] transition-transform duration-150",
                      userMenuOpen && "rotate-180"
                    )}
                  />
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 top-full mt-1 w-48 rounded-lg border border-[#E2E8F0] bg-white shadow-lg py-1 z-50">
                    <Link
                      href="/dashboard"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2 text-sm text-[#1E293B] hover:bg-[#F8FAFC] transition-colors"
                    >
                      <LayoutDashboard className="h-4 w-4 text-[#64748B]" />
                      Dashboard
                    </Link>
                    <hr className="my-1 border-[#E2E8F0]" />
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                    >
                      <LogOut className="h-4 w-4" />
                      Log out
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className={cn(
                  "hidden sm:flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium",
                  "text-[#1E293B] hover:bg-[#F1F5F9]",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
                  "transition-colors"
                )}
              >
                <LogIn className="h-4 w-4" />
                Log In
              </Link>

              <Link
                href="/register"
                className={cn(
                  "flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold",
                  "bg-[#F97316] text-white shadow-[0_2px_8px_rgba(249,115,22,0.35)]",
                  "hover:bg-[#EA580C] active:bg-[#C2410C]",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2",
                  "transition-colors"
                )}
              >
                <Package className="h-4 w-4" />
                Link orders
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
