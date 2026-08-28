import type { Product } from "@/types/product";
import type { PublicStorefront } from "@/types/storefront";
import { getStorefrontBranding } from "@/lib/storefront-branding";

export type JsonLdDocument = Record<string, unknown>;

function stripMarkup(value?: string | null): string {
  return (value || "")
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function absoluteUrl(value: string | undefined, siteUrl: string): string | undefined {
  const normalized = value?.trim();
  if (!normalized) return undefined;

  try {
    return new URL(normalized, `${siteUrl.replace(/\/$/, "")}/`).toString();
  } catch {
    return undefined;
  }
}

function cleanText(value?: string | null, maxLength = 320): string | undefined {
  const normalized = stripMarkup(value);
  if (!normalized) return undefined;
  return normalized.length > maxLength ? `${normalized.slice(0, maxLength - 1).trimEnd()}…` : normalized;
}

function compactObject<T extends Record<string, unknown>>(value: T): T {
  return Object.fromEntries(
    Object.entries(value).filter(([, entry]) => {
      if (entry === undefined || entry === null || entry === "") return false;
      return !(Array.isArray(entry) && entry.length === 0);
    }),
  ) as T;
}

function schemaAttributeName(key: string): "color" | "size" | undefined {
  const normalized = key
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
  if (normalized.includes("color") || normalized.includes("colour")) return "color";
  if (
    normalized.includes("size") ||
    normalized.includes("talla") ||
    normalized.includes("medida") ||
    normalized.includes("tamano")
  ) {
    return "size";
  }
  return undefined;
}

function variantAttributes(variant: NonNullable<Product["variants"]>[number]): Record<string, string> {
  return Object.fromEntries(
    Object.entries(variant.attributes || {})
      .map(([key, value]) => [key, String(value ?? "").trim()])
      .filter(([, value]) => Boolean(value)),
  );
}

function productBrand(product: Product): JsonLdDocument | undefined {
  return product.brandName
    ? { "@type": "Brand", name: product.brandName }
    : undefined;
}

function offer(
  url: string,
  price: number,
  currency: string,
  inStock: boolean,
  sku?: string | null,
): JsonLdDocument {
  return compactObject({
    "@type": "Offer",
    url,
    priceCurrency: currency,
    price: Number.isFinite(price) ? price : 0,
    availability: `https://schema.org/${inStock ? "InStock" : "OutOfStock"}`,
    itemCondition: "https://schema.org/NewCondition",
    sku: sku?.trim() || undefined,
  });
}

export function serializeJsonLd(data: JsonLdDocument): string {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}

export function buildStorefrontIdentityStructuredData(
  storefront: PublicStorefront,
  siteUrl: string,
): JsonLdDocument {
  const branding = getStorefrontBranding(storefront);
  const organizationId = `${siteUrl.replace(/\/$/, "")}/#organization`;
  const logo = absoluteUrl(branding.logoUrl, siteUrl);
  const socialLinks = branding.socialLinks.map((item) => item.href).filter(Boolean);
  const contactPoint = compactObject({
    "@type": "ContactPoint",
    contactType: "customer service",
    telephone: branding.supportPhone || undefined,
    email: branding.supportEmail || undefined,
    availableLanguage: ["es"],
  });
  const organization = compactObject({
    "@type": "Organization",
    "@id": organizationId,
    name: storefront.name,
    url: siteUrl,
    logo,
    email: branding.supportEmail || undefined,
    telephone: branding.supportPhone || undefined,
    address: branding.supportAddress
      ? { "@type": "PostalAddress", streetAddress: branding.supportAddress }
      : undefined,
    contactPoint: Object.keys(contactPoint).length > 2 ? [contactPoint] : undefined,
    sameAs: socialLinks.length ? socialLinks : undefined,
  });
  const seoSettings = storefront.seo_settings || {};
  const website = compactObject({
    "@type": "WebSite",
    "@id": `${siteUrl.replace(/\/$/, "")}/#website`,
    name: storefront.name,
    url: siteUrl,
    description: cleanText(
      typeof seoSettings.meta_description === "string" ? seoSettings.meta_description : undefined,
    ),
    publisher: { "@id": organizationId },
    potentialAction: {
      "@type": "SearchAction",
      target: {
        "@type": "EntryPoint",
        urlTemplate: `${siteUrl.replace(/\/$/, "")}/products?q={search_term_string}`,
      },
      "query-input": "required name=search_term_string",
    },
  });

  return {
    "@context": "https://schema.org",
    "@graph": [organization, website],
  };
}

export function buildBreadcrumbStructuredData(
  siteUrl: string,
  items: Array<{ name: string; path?: string }>,
): JsonLdDocument {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) =>
      compactObject({
        "@type": "ListItem",
        position: index + 1,
        name: item.name,
        item: item.path ? absoluteUrl(item.path, siteUrl) : undefined,
      }),
    ),
  };
}

export function buildProductStructuredData(
  product: Product,
  siteUrl: string,
  currency: string,
): JsonLdDocument {
  const baseUrl = siteUrl.replace(/\/$/, "");
  const productUrl = `${baseUrl}/products/${encodeURIComponent(product.slug || "")}`;
  const images = Array.from(
    new Set((product.imgs?.previews || []).map((image) => absoluteUrl(image, siteUrl)).filter(Boolean)),
  ) as string[];
  const variants = product.variants || [];
  const brand = productBrand(product);
  const description = cleanText(product.seoDescription || product.description);

  if (variants.length > 1) {
    const variantProducts = variants.map((variant) => {
      const attributes = variantAttributes(variant);
      const mappedAttributes = Object.fromEntries(
        Object.entries(attributes)
          .map(([key, value]) => [schemaAttributeName(key), value])
          .filter(([key]) => Boolean(key)),
      );
      const additionalProperty = Object.entries(attributes).map(([name, value]) => ({
        "@type": "PropertyValue",
        name,
        value,
      }));
      return compactObject({
        "@type": "Product",
        "@id": `${productUrl}#variant-${variant.id}`,
        name: variant.name ? `${product.title} - ${variant.name}` : product.title,
        sku: variant.sku || undefined,
        isVariantOf: { "@id": productUrl },
        ...mappedAttributes,
        additionalProperty: additionalProperty.length ? additionalProperty : undefined,
        offers: offer(
          `${productUrl}#variant-${variant.id}`,
          variant.price,
          currency,
          variant.inStock,
          variant.sku,
        ),
      });
    });
    const prices = variants.map((variant) => variant.price).filter((price) => Number.isFinite(price));
    return compactObject({
      "@context": "https://schema.org",
      "@type": "ProductGroup",
      "@id": productUrl,
      name: product.title,
      description,
      url: productUrl,
      image: images.length ? images : undefined,
      productGroupID: product.publishedProductId || product.slug,
      brand,
      category: product.categoryName || undefined,
      variesBy: Array.from(
        new Set(
          variants.flatMap((variant) =>
            Object.keys(variant.attributes || {})
              .map(schemaAttributeName)
              .filter((value): value is "color" | "size" => Boolean(value)),
          ),
        ),
      ).map((value) => `https://schema.org/${value}`),
      offers: prices.length
        ? {
            "@type": "AggregateOffer",
            priceCurrency: currency,
            lowPrice: Math.min(...prices),
            highPrice: Math.max(...prices),
            offerCount: variants.length,
          }
        : undefined,
      hasVariant: variantProducts,
    });
  }

  const variant = variants[0];
  const price = variant?.price ?? product.discountedPrice ?? product.price;
  const inStock = variant?.inStock ?? Boolean(product.inStock);
  const attributes = variant ? variantAttributes(variant) : {};
  const mappedAttributes = Object.fromEntries(
    Object.entries(attributes)
      .map(([key, value]) => [schemaAttributeName(key), value])
      .filter(([key]) => Boolean(key)),
  );

  return compactObject({
    "@context": "https://schema.org",
    "@type": "Product",
    "@id": productUrl,
    name: product.title,
    description,
    url: productUrl,
    image: images.length ? images : undefined,
    sku: variant?.sku || undefined,
    brand,
    category: product.categoryName || undefined,
    ...mappedAttributes,
    offers: offer(productUrl, price, currency, inStock, variant?.sku),
  });
}
