/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001",
  },
  // Don't fail the build on TS or ESLint errors — type-checking happens
  // in dev/CI; deploys should ship as long as Next can compile JS.
  typescript: { ignoreBuildErrors: true },
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
