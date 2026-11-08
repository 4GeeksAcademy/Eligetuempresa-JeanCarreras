import type { NextConfig } from "next";
import path from "node:path";

const staticPages = ["backoffice", "backoffice/reporting", "backoffice/rfp-intake", "executive-dashboard", "knowledge-assistant", "marketing-loyalty-app", "public-website", "auth", "auth/login", "auth/forgot-password", "auth/reset-password", "auth/account/change-password"];

const nextConfig: NextConfig = {
  turbopack: { root: path.resolve(__dirname, "../..") },
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const staticOrigin = process.env.BRASALAND_STATIC_ORIGIN || "http://127.0.0.1:5510";
    const apiOrigin = process.env.BRASALAND_API_ORIGIN || "http://127.0.0.1:8000";
    return [
      ...staticPages.flatMap((page) => [
        { source: `/platform/${page}/`, destination: `${staticOrigin}/${page}/index.html` },
        { source: `/platform/${page}`, destination: `${staticOrigin}/${page}/index.html` },
      ]),
      { source: "/platform/:path*", destination: `${staticOrigin}/:path*` },
      { source: "/backend/:path*", destination: `${apiOrigin}/:path*` },
    ];
  },
};

export default nextConfig;
