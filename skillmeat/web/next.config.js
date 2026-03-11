/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Output standalone build for production
  output: 'standalone',

  // Ignore ESLint errors during build
  eslint: {
    ignoreDuringBuilds: true,
  },

  // Ignore TypeScript errors during build (development only)
  typescript: {
    ignoreBuildErrors: true,
  },

  // Configure rewrites to proxy API requests to FastAPI backend.
  // INTERNAL_API_URL is set as a Docker build ARG (defaults to http://skillmeat-api:8080)
  // so the correct internal hostname is baked into the standalone build.
  // Falls back to localhost for local dev outside Docker.
  async rewrites() {
    const apiUrl =
      process.env.INTERNAL_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8080';
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },

  // Enable experimental features
  experimental: {
    serverActions: {
      bodySizeLimit: '10mb',
    },
  },

  // Image optimization configuration
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.githubusercontent.com',
      },
    ],
  },
};

module.exports = nextConfig;
