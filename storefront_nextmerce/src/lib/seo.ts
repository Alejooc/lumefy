import { Metadata } from "next";

import { resolveStorefront } from "@/lib/storefront-api";
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

export async function buildPageMetadata({
  title,
  description,
  path,
  index = true,
}: MetadataInput): Promise<Metadata> {
  return {
    title,
    description,
    alternates: {
      canonical: await buildCanonicalUrl(path),
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
