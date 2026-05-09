import { Metadata } from "next";

import { resolveStorefront } from "@/lib/storefront-api";

const DEFAULT_SITE_URL = "http://localhost:3000";

function normalizeSiteUrl(url: string | undefined): string {
  if (!url) {
    return DEFAULT_SITE_URL;
  }
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

export function getSiteUrl(): string {
  return normalizeSiteUrl(process.env.NEXT_PUBLIC_SITE_URL);
}

export function buildCanonicalUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${getSiteUrl()}${normalizedPath}`;
}

export const INDEXABLE_PATHS = ["/", "/products", "/contact"] as const;

export const PRIVATE_PATHS = [
  "/account",
  "/cart",
  "/checkout",
  "/checkout/success",
  "/login",
  "/password/reset",
  "/register",
  "/wishlist",
] as const;

type MetadataInput = {
  title: string;
  description: string;
  path: string;
  index?: boolean;
};

function normalizeStorefrontName(value: string | undefined): string {
  const trimmed = value?.trim();
  return trimmed || "Storefront";
}

export async function getStorefrontSeoName(): Promise<string> {
  try {
    const storefront = await resolveStorefront();
    return normalizeStorefrontName(storefront.name);
  } catch {
    return "Storefront";
  }
}

export async function buildStorefrontPageMetadata({
  title,
  description,
  path,
  index = true,
}: MetadataInput): Promise<Metadata> {
  const storefrontName = await getStorefrontSeoName();
  const normalizedTitle = title.trim();

  return buildPageMetadata({
    title: normalizedTitle
      ? `${normalizedTitle} | ${storefrontName}`
      : storefrontName,
    description,
    path,
    index,
  });
}

export function buildPageMetadata({
  title,
  description,
  path,
  index = true,
}: MetadataInput): Metadata {
  return {
    title,
    description,
    alternates: {
      canonical: buildCanonicalUrl(path),
    },
    robots: index
      ? {
          index: true,
          follow: true,
        }
      : {
          index: false,
          follow: false,
          googleBot: {
            index: false,
            follow: false,
          },
        },
  };
}
