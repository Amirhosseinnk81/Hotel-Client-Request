import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The operator offline-mode service worker (public/sw.js) must never be
  // served from a cache, or a fixed version would never reach browsers.
  async headers() {
    return [
      {
        source: "/sw.js",
        headers: [
          { key: "Content-Type", value: "application/javascript; charset=utf-8" },
          { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
        ],
      },
    ];
  },
};

export default nextConfig;
