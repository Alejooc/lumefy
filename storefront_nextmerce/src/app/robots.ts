import { MetadataRoute } from "next";
import { buildCanonicalUrl, getSiteUrl, PRIVATE_PATHS } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [...PRIVATE_PATHS],
      },
    ],
    sitemap: buildCanonicalUrl("/sitemap.xml"),
    host: getSiteUrl(),
  };
}
