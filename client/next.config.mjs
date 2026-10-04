/** @type {import('next').NextConfig} */
// When the app is opened through a single public address (see public.sh), the browser
// talks to /api/v1 on the same origin and Next forwards it to the Python server.
const API_ORIGIN = process.env.API_ORIGIN || 'http://127.0.0.1:8000';

const nextConfig = {
  reactStrictMode: true,
  compress: false, // keeps the streamed chat replies flowing instead of buffering them
  async rewrites() {
    return [{ source: '/api/v1/:path*', destination: `${API_ORIGIN}/api/v1/:path*` }];
  },
};

export default nextConfig;
