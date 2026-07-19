import { MetadataRoute } from "next";
import { buildCanonicalUrl, getSiteUrl, PRIVATE_PATHS } from "@/lib/seo";

export default async function robots(): Promise<MetadataRoute.Robots> {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [...PRIVATE_PATHS],
      },
    ],
    sitemap: await buildCanonicalUrl("/sitemap.xml"),
    host: await getSiteUrl(),
  };
}
