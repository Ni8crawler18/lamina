/** @type {import('next').NextConfig} */
const nextConfig = {
  turbopack: {},
  serverExternalPackages: ["hashconnect", "@hashgraph/sdk"],
  experimental: {
    optimizePackageImports: [],
  },
};

export default nextConfig;
