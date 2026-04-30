/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  // 允许 pages/ 和 app/ 共存（渐进迁移期）
  eslint: { ignoreDuringBuilds: false },
};

export default nextConfig;
