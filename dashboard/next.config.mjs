/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    // Allow server-side postgres connections
    serverComponentsExternalPackages: ["postgres"],
  },
};

export default nextConfig;
