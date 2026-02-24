import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Django requires trailing slashes; without this Next.js strips them (308)
  // before the rewrite fires, causing a redirect loop with Django's APPEND_SLASH.
  skipTrailingSlashRedirect: true,
  images: {
    remotePatterns: [
      { hostname: "m.media-amazon.com" },
      { hostname: "rukminim2.flixcart.com" },
      { hostname: "images.unsplash.com" },
      { hostname: "placehold.co" },
    ],
  },
  // Proxy /api/* calls to Django backend during development
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/:path*`,
      },
      {
        source: "/webhooks/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/webhooks/:path*`,
      },
      // /accounts/* and /oauth/* use route handlers instead of rewrites
      // to avoid Next.js trailing-slash issues with Django's APPEND_SLASH.
      // See: src/app/accounts/[...path]/route.ts, src/app/oauth/[...path]/route.ts
    ];
  },
};

export default nextConfig;
