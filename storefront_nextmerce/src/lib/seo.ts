import { Metadata } from "next";

import { resolveStorefront } from "@/lib/storefront-api";
import { getStorefrontBranding } from "@/lib/storefront-branding";
import type { PublicStorefront } from "@/types/storefront";
import { normalizeStorefrontHost } from "@/lib/storefront-host";

function normalizeCanonicalHost(value: string | null | undefined): string {
  const rawHost = value?.split(",")[0]?.trim().toLowerCase() || "";
  const hostWithOptionalPort = rawHost.replace(/^https?:\/\//, "").split("/")[0].replace(/\.$/, "");
  const host = normalizeStorefrontHost(hostWithOptionalPort);
  const port = hostWithOptionalPort.match(/:(\d+)$/)?.[1];
  return port && host ? `${host}:${port}` : host;
}

export async function getSiteUrl(): Promise<string> {
  if (typeof window !== "undefined") {
    return window.location.origin;
  }

  const { headers } = await import("next/headers");
  const requestHeaders = await headers();
  const host = normalizeCanonicalHost(
    requestHeaders.get("x-forwarded-host") || requestHeaders.get("host"),
  );
  if (!host) {
    throw new Error("Missing storefront host for canonical URL generation");
  }

  const forwardedProtocol = requestHeaders.get("x-forwarded-proto")?.split(",")[0]?.trim();
  const protocol = forwardedProtocol || (host === "localhost" || host.endsWith(".localhost") ? "http" : "https");
  return `${protocol}://${host}`;
}

export async function buildCanonicalUrl(path: string): Promise<string> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${await getSiteUrl()}${normalizedPath}`;
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

export function stripHtml(value?: string | null): string {
  return (value || "")
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function truncateSeoText(value: string, maxLength: number): string {
  const normalized = value.trim();
  if (normalized.length <= maxLength) return normalized;
  const shortened = normalized.slice(0, Math.max(0, maxLength - 1)).trimEnd();
  return `${shortened}…`;
}

function stringSetting(settings: Record<string, unknown>, key: string): string {
  const value = settings[key];
  return typeof value === "string" ? value.trim() : "";
}

function booleanSetting(settings: Record<string, unknown>, key: string): boolean | undefined {
  const value = settings[key];
  if (typeof value === "boolean") return value;
  if (typeof value === "string") {
    if (value.toLowerCase() === "true") return true;
    if (value.toLowerCase() === "false") return false;
  }
  return undefined;
}

function titleWithStorefrontName(title: string, storefrontName: string): string {
  if (!title) return storefrontName;
  if (title.toLocaleLowerCase().includes(storefrontName.toLocaleLowerCase())) return title;
  return `${title} | ${storefrontName}`;
}

type MetadataInput = {
  title: string;
  description: string;
  path: string;
  index?: boolean;
  siteName?: string;
  imageUrl?: string;
  faviconUrl?: string;
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
  imageUrl,
}: MetadataInput): Promise<Metadata> {
  let storefront: PublicStorefront | null = null;
  try {
    storefront = await resolveStorefront();
  } catch {
    // The generic metadata fallback below keeps error and preview pages usable.
  }

  const storefrontName = normalizeStorefrontName(storefront?.name);
  const branding = storefront ? getStorefrontBranding(storefront) : undefined;
  const seoSettings = storefront?.seo_settings || {};
  const configuredTitle = stringSetting(seoSettings, "meta_title");
  const configuredDescription = stripHtml(stringSetting(seoSettings, "meta_description"));
  const configuredImage = stringSetting(seoSettings, "og_image_url");
  const normalizedTitle = title.trim();
  const pageTitle = normalizedTitle
    ? titleWithStorefrontName(normalizedTitle, storefrontName)
    : configuredTitle || storefrontName;
  const pageDescription = stripHtml(description) || configuredDescription ||
    `Compra online en ${storefrontName}.`;
  const configuredIndex = booleanSetting(seoSettings, "index_storefront");

  return buildPageMetadata({
    title: truncateSeoText(pageTitle, 70),
    description: truncateSeoText(pageDescription, 320),
    path,
    index: configuredIndex === false ? false : index,
    siteName: storefrontName,
    imageUrl: imageUrl || configuredImage || branding?.logoUrl,
    faviconUrl: branding?.faviconUrl,
  });
}

export async function buildPageMetadata({
  title,
  description,
  path,
  index = true,
  siteName,
  imageUrl,
  faviconUrl,
}: MetadataInput): Promise<Metadata> {
  const siteUrl = await getSiteUrl();
  const canonicalUrl = `${siteUrl}${path.startsWith("/") ? path : `/${path}`}`;
  const absoluteImageUrl = imageUrl ? new URL(imageUrl, siteUrl).toString() : undefined;

  return {
    metadataBase: new URL(siteUrl),
    title,
    description,
    alternates: {
      canonical: canonicalUrl,
    },
    icons: faviconUrl ? { icon: faviconUrl } : undefined,
    openGraph: {
      type: "website",
      locale: "es_CO",
      url: canonicalUrl,
      siteName: siteName || title,
      title,
      description,
      images: absoluteImageUrl ? [{ url: absoluteImageUrl, alt: title }] : undefined,
    },
    twitter: {
      card: absoluteImageUrl ? "summary_large_image" : "summary",
      title,
      description,
      images: absoluteImageUrl ? [absoluteImageUrl] : undefined,
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
