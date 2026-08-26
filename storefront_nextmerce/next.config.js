const allowLocalIp =
  process.env.NODE_ENV !== "production" ||
  process.env.NEXT_IMAGE_ALLOW_LOCAL_IP === "true";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async redirects() {
    return [
      {
        source: "/signin",
        destination: "/login",
        permanent: true,
      },
      {
        source: "/signup",
        destination: "/register",
        permanent: true,
      },
      {
        source: "/my-account",
        destination: "/account",
        permanent: true,
      },
      {
        source: "/reset-password",
        destination: "/password/reset",
        permanent: true,
      },
      {
        source: "/mail-success",
        destination: "/checkout/success",
        permanent: true,
      },
      {
        source: "/shop-with-sidebar",
        destination: "/products",
        permanent: true,
      },
      {
        source: "/shop-without-sidebar",
        destination: "/products",
        permanent: true,
      },
    ];
  },
  images: {
    // Storefront media is served through a tenant-aware same-origin route.
    // Next's server-side optimizer does not retain the storefront host while
    // fetching that route, so it can return an empty response for valid media
    // selected in the visual editor. Keep the browser request on /media/...;
    // the backend still enforces the tenant boundary for every asset.
    unoptimized: true,
    dangerouslyAllowLocalIP: allowLocalIp,
    remotePatterns: [
      { protocol: "http", hostname: "localhost" },
      { protocol: "http", hostname: "127.0.0.1" },
      { protocol: "http", hostname: "::1" },
      { protocol: "http", hostname: "**" },
      { protocol: "https", hostname: "**" },
    ],
  },
};

module.exports = nextConfig;
