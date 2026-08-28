import { MetadataRoute } from "next";
import {
  getPublicCollections,
  getPublicProducts,
  resolveStorefront,
} from "@/lib/storefront-api";
import { getSiteUrl } from "@/lib/seo";

const SITEMAP_PAGE_SIZE = 48;
const SITEMAP_BATCH_SIZE = 8;

function nowIso(): string {
  return new Date().toISOString();
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const lastModified = nowIso();
  const siteUrl = await getSiteUrl();
  const canonicalUrl = (path: string) => new URL(path, siteUrl).toString();
  const homeUrl = canonicalUrl("/");
  const productsUrl = canonicalUrl("/products");
  const contactUrl = canonicalUrl("/contact");
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
    for (const collection of collections) {
      entries.push({
        url: canonicalUrl(`/collections/${encodeURIComponent(collection.slug)}`),
        lastModified,
        changeFrequency: "weekly",
        priority: 0.8,
      });
    }

    // Collection summaries intentionally do not include products. Walk the
    // public catalog pages so every published, available product has a
    // crawlable URL in the sitemap, even when it belongs to no collection.
    const firstPage = await getPublicProducts(storefront.id, {
      page: 1,
      page_size: SITEMAP_PAGE_SIZE,
      sort: "latest",
      include_facets: "false",
    });
    const catalogPages = [firstPage];
    const remainingPages = Array.from(
      { length: Math.max(0, firstPage.total_pages - 1) },
      (_, index) => index + 2,
    );

    for (let offset = 0; offset < remainingPages.length; offset += SITEMAP_BATCH_SIZE) {
      const batch = remainingPages.slice(offset, offset + SITEMAP_BATCH_SIZE);
      const results = await Promise.all(
        batch.map(async (page) => {
          try {
            return await getPublicProducts(storefront.id, {
              page,
              page_size: SITEMAP_PAGE_SIZE,
              sort: "latest",
              include_facets: "false",
            });
          } catch {
            return null;
          }
        }),
      );
      catalogPages.push(...results.filter((result): result is typeof firstPage => Boolean(result)));
    }

    const seenProducts = new Set<string>();
    for (const catalog of catalogPages) {
      for (const product of catalog.items) {
        if (!product.slug || seenProducts.has(product.slug)) continue;
        seenProducts.add(product.slug);
        entries.push({
          url: canonicalUrl(`/products/${encodeURIComponent(product.slug)}`),
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
