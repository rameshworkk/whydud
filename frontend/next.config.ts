import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { hostname: "m.media-amazon.com" },
      { hostname: "rukminim2.flixcart.com" },
      { hostname: "images.unsplash.com" },
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
    ];
  },
};

export default nextConfig;
