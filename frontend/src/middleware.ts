import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Protect dashboard routes — redirect to /login if no auth cookie is present.
 *
 * The `whydud_auth` cookie is a simple "1" flag set by setToken() in the
 * API client. It does NOT contain the actual token (that stays in localStorage).
 * This is purely a UX optimization so the redirect happens at the edge
 * before the page JS loads. The real auth check is the API call to /me.
 */
export function middleware(request: NextRequest) {
  const hasAuth = request.cookies.has("whydud_auth");

  if (!hasAuth) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
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
