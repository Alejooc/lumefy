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
