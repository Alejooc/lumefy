import { MetadataRoute } from "next";
import {
  getPublicCollectionBySlug,
  getPublicCollections,
  resolveStorefront,
} from "@/lib/storefront-api";
import { buildCanonicalUrl } from "@/lib/seo";

function nowIso(): string {
  return new Date().toISOString();
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const lastModified = nowIso();
  const homeUrl = await buildCanonicalUrl("/");
  const productsUrl = await buildCanonicalUrl("/products");
  const contactUrl = await buildCanonicalUrl("/contact");
  const entries: MetadataRoute.Sitemap = [
    {
      url: homeUrl,
      lastModified,
      changeFrequency: "daily",
      priority: 1,
    },
    {
      url: productsUrl,
      lastModified,
      changeFrequency: "daily",
      priority: 0.9,
    },
    {
      url: contactUrl,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.5,
    },
  ];

  try {
    const storefront = await resolveStorefront();
    const collections = await getPublicCollections(storefront.id);
    const detailedCollections = await Promise.all(
      collections.map(async (collection) => {
        try {
          return await getPublicCollectionBySlug(storefront.id, collection.slug);
        } catch {
          return collection;
        }
      }),
    );

    const seenProducts = new Set<string>();

    for (const collection of detailedCollections) {
      entries.push({
        url: await buildCanonicalUrl(`/collections/${encodeURIComponent(collection.slug)}`),
        lastModified,
        changeFrequency: "weekly",
        priority: 0.8,
      });
      for (const product of collection.products || []) {
        if (!product.slug || seenProducts.has(product.slug)) {
          continue;
        }

        seenProducts.add(product.slug);
        entries.push({
          url: await buildCanonicalUrl(`/products/${product.slug}`),
          lastModified,
          changeFrequency: "weekly",
          priority: product.is_featured ? 0.85 : 0.75,
        });
      }
    }
  } catch {
    // Keep sitemap generation resilient even if the API is temporarily unavailable.
  }

  return entries;
}
