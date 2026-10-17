import type { NextConfig } from "next";

// built to static files that FastAPI serves; `next dev` forwards the API and fonts to a running gateway
const dev = process.env.NODE_ENV === "development";
const gateway = process.env.GATEWAY_URL || "http://127.0.0.1:8000";

const config: NextConfig = dev
  ? { rewrites: async () => [{ source: "/api/:path*", destination: `${gateway}/api/:path*` },
      { source: "/static/:path*", destination: `${gateway}/static/:path*` }] }
  : { output: "export", poweredByHeader: false };

export default config;
