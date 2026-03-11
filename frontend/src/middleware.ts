import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Marketplace domains recognized in the URL path-prefix pattern.
 * e.g. whydud.com/amazon.in/dp/B085GGQSMC → /lookup?url=https://amazon.in/dp/B085GGQSMC
 */
const MARKETPLACE_DOMAINS = new Set([
  "amazon.in",
  "www.amazon.in",
  "flipkart.com",
  "www.flipkart.com",
  "myntra.com",
  "www.myntra.com",
  "nykaa.com",
  "www.nykaa.com",
  "snapdeal.com",
  "www.snapdeal.com",
  "croma.com",
  "www.croma.com",
  "reliancedigital.in",
  "www.reliancedigital.in",
  "ajio.com",
  "www.ajio.com",
  "meesho.com",
  "www.meesho.com",
  "tatacliq.com",
  "www.tatacliq.com",
  "jiomart.com",
  "www.jiomart.com",
  "vijaysales.com",
  "www.vijaysales.com",
  "firstcry.com",
  "www.firstcry.com",
  "giva.co",
  "www.giva.co",
]);

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  // --- Domain-prefix redirect: whydud.com/amazon.in/... → /lookup?url=... ---
  // Extract the first path segment (e.g. "amazon.in" from "/amazon.in/dp/B085GGQSMC")
  const firstSlash = pathname.indexOf("/", 1);
  const firstSegment = firstSlash === -1 ? pathname.slice(1) : pathname.slice(1, firstSlash);

  if (firstSegment && MARKETPLACE_DOMAINS.has(firstSegment)) {
    const restOfPath = firstSlash === -1 ? "" : pathname.slice(firstSlash);
    const marketplaceUrl = `https://${firstSegment}${restOfPath}${search}`;
    const lookupUrl = new URL("/lookup", request.url);
    lookupUrl.searchParams.set("url", marketplaceUrl);
    return NextResponse.redirect(lookupUrl, 302);
  }

  // --- Auth guard for dashboard routes ---
  const hasAuth = request.cookies.has("whydud_auth");

  if (!hasAuth) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Marketplace domain-prefix patterns
    "/amazon.in/:path*",
    "/www.amazon.in/:path*",
    "/flipkart.com/:path*",
    "/www.flipkart.com/:path*",
    "/myntra.com/:path*",
    "/www.myntra.com/:path*",
    "/nykaa.com/:path*",
    "/www.nykaa.com/:path*",
    "/snapdeal.com/:path*",
    "/www.snapdeal.com/:path*",
    "/croma.com/:path*",
    "/www.croma.com/:path*",
    "/reliancedigital.in/:path*",
    "/www.reliancedigital.in/:path*",
    "/ajio.com/:path*",
    "/www.ajio.com/:path*",
    "/meesho.com/:path*",
    "/www.meesho.com/:path*",
    "/tatacliq.com/:path*",
    "/www.tatacliq.com/:path*",
    "/jiomart.com/:path*",
    "/www.jiomart.com/:path*",
    "/vijaysales.com/:path*",
    "/www.vijaysales.com/:path*",
    "/firstcry.com/:path*",
    "/www.firstcry.com/:path*",
    "/giva.co/:path*",
    "/www.giva.co/:path*",
    // Auth-protected routes
    "/dashboard/:path*",
    "/inbox/:path*",
    "/wishlists/:path*",
    "/purchases/:path*",
    "/refunds/:path*",
    "/subscriptions/:path*",
    "/rewards/:path*",
    "/settings/:path*",
    "/notifications/:path*",
    "/my-reviews/:path*",
    "/alerts/:path*",
    "/product/:slug/review",
  ],
};
