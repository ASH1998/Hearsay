import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  distDir: process.env.HEARSAY_NEXT_DIST_DIR ?? ".next",
  output: "standalone",
  outputFileTracingRoot: path.join(process.cwd(), "../.."),
  turbopack: {
    root: path.join(process.cwd(), "../.."),
  },
  reactStrictMode: true,
  poweredByHeader: false,
};

export default nextConfig;
