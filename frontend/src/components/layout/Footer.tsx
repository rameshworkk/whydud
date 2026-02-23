import Link from "next/link";

const FOOTER_LINKS = {
  Discover: [
    { label: "Search Products", href: "/search" },
    { label: "Hot Deals", href: "/deals" },
    { label: "Compare Products", href: "/compare" },
    { label: "Write a Review", href: "/reviews/new" },
  ],
  Account: [
    { label: "Dashboard", href: "/dashboard" },
    { label: "My Inbox", href: "/inbox" },
    { label: "Wishlists", href: "/wishlists" },
    { label: "Rewards", href: "/rewards" },
  ],
  Company: [
    { label: "About Whydud", href: "/about" },
    { label: "Blog", href: "/blog" },
    { label: "Contact Us", href: "/contact" },
    { label: "Advertise with Us", href: "/advertise" },
  ],
  Legal: [
    { label: "Privacy Policy", href: "/privacy" },
    { label: "Terms of Service", href: "/terms" },
    { label: "Cookie Policy", href: "/cookies" },
    { label: "Affiliate Disclosure", href: "/affiliate-disclosure" },
  ],
};

/** Site footer — server component. */
export function Footer() {
  return (
    <footer className="border-t border-[#E2E8F0] bg-[#F8FAFC]">
      <div
        className="mx-auto px-4 md:px-6 py-12"
        style={{ maxWidth: "var(--max-width)" }}
      >
        <div className="grid grid-cols-2 gap-8 md:grid-cols-5">
          {/* Brand column */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2 mb-3">
              <svg
                width="28"
                height="28"
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
              <span className="text-lg font-semibold text-[#1E293B]">Whydud</span>
            </Link>
            <p className="text-sm text-[#64748B] leading-relaxed">
              India&apos;s product intelligence platform. Discover product truth. Shop smarter.
            </p>
            <p className="mt-4 text-xs text-[#94A3B8]">
              Prices sourced from public listings. We may earn affiliate commission.
            </p>
          </div>

          {/* Link columns */}
          {Object.entries(FOOTER_LINKS).map(([heading, links]) => (
            <div key={heading}>
              <p className="mb-3 text-sm font-semibold text-[#1E293B]">{heading}</p>
              <ul className="space-y-2">
                {links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-[#64748B] hover:text-[#F97316] transition-colors"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-[#E2E8F0] pt-6">
          <p className="text-xs text-[#94A3B8]">
            © {new Date().getFullYear()} Whydud Technologies Pvt. Ltd. All rights reserved.
          </p>
          <p className="text-xs text-[#94A3B8]">
            Made with ❤️ in India
          </p>
        </div>
      </div>
    </footer>
  );
}
