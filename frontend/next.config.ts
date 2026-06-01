import type { NextConfig } from "next";

const apiUrl =
  process.env.NEXT_PUBLIC_API_URL || "https://gaurav711-artha-ai.hf.space";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
