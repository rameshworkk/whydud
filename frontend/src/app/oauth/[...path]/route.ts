import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy /oauth/* to Django. Handles the OAuth completion redirect from AllAuth.
 *
 * After Google OAuth, AllAuth redirects to LOGIN_REDIRECT_URL (/oauth/complete/).
 * This route handler proxies that to Django, forwarding the session cookie so
 * Django can authenticate the user and create the one-time code.
 */

const BACKEND_URL =
  process.env.INTERNAL_API_URL ?? "http://localhost:8000";

async function proxy(req: NextRequest) {
  const url = new URL(req.url);
  const target = `${BACKEND_URL}${url.pathname}${url.search}`;

  const headers = new Headers(req.headers);
  headers.set("X-Forwarded-Host", url.host);
  headers.set("X-Forwarded-Proto", url.protocol.replace(":", ""));

  const res = await fetch(target, {
    method: req.method,
    headers,
    body: req.body,
    redirect: "manual",
  });

  return new NextResponse(res.body, {
    status: res.status,
    headers: new Headers(res.headers),
  });
}

export const GET = proxy;
