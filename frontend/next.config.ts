import type { NextConfig } from "next";

const apiProxyTarget = (
  process.env.TENDER_NAVIGATOR_API_PROXY_TARGET ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

const nextConfig: NextConfig = {
  experimental: {
    typedRoutes: true
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiProxyTarget}/api/v1/:path*`
      },
      {
        source: "/health",
        destination: `${apiProxyTarget}/health`
      }
    ];
  }
};

export default nextConfig;
