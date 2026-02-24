import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
      {
        source: "/accounts/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/accounts/:path*`,
      },
    ];
  },
};

export default nextConfig;
