import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy all /accounts/* requests to Django's AllAuth endpoints.
 *
 * We use a route handler instead of a Next.js rewrite because rewrites
 * strip trailing slashes, causing an infinite 301 loop with Django's
 * APPEND_SLASH. This handler preserves the URL exactly as-is.
 */

const BACKEND_URL =
  process.env.INTERNAL_API_URL ?? "http://localhost:8000";

async function proxy(req: NextRequest) {
  // Reconstruct the full path including trailing slash and query string
  const url = new URL(req.url);
  const target = `${BACKEND_URL}${url.pathname}${url.search}`;

  // Forward the request to Django, including cookies (session cookie is critical for OAuth state)
  const headers = new Headers(req.headers);
  // Override Host so Django's request.build_absolute_uri() generates
  // callback URLs pointing to localhost:3000 (matching Google Console config).
  // The fetch API won't send our Host header to a different host, so use
  // X-Forwarded-Host which Django can read via USE_X_FORWARDED_HOST.
  headers.set("X-Forwarded-Host", url.host);
  headers.set("X-Forwarded-Proto", url.protocol.replace(":", ""));

  const res = await fetch(target, {
    method: req.method,
    headers,
    body: req.body,
    redirect: "manual", // Don't follow redirects — pass them through to the browser
  });

  // Forward the response including Set-Cookie headers and redirects
  const responseHeaders = new Headers(res.headers);

  // For redirects, return them as-is so the browser follows them
  if (res.status >= 300 && res.status < 400) {
    return new NextResponse(null, {
      status: res.status,
      headers: responseHeaders,
    });
  }

  return new NextResponse(res.body, {
    status: res.status,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
