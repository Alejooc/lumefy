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
    // Keep modern formats first for the template's local assets. Tenant media
    // uses the StorefrontImage wrapper and is optimized by /media itself.
    formats: ["image/avif", "image/webp"],
    // Include mobile widths so a 360–480px viewport does not fall back to
    // the default 640px candidate for the first hero image.
    deviceSizes: [320, 375, 414, 480, 640, 750, 828, 1080, 1200, 1440, 1920, 2400],
    minimumCacheTTL: 31536000,
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
