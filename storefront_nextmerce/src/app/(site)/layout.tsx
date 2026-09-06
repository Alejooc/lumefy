import { notFound } from "next/navigation";
import type { Metadata } from "next";

import {
  getPublicCollections,
  getPublicNavigation,
  StorefrontApiError,
  resolveStorefront,
} from "@/lib/storefront-api";
import type { PublicCollection, PublicStoreNavigationItem } from "@/types/storefront";
import { buildStorefrontPageMetadata, getSiteUrl } from "@/lib/seo";
import { buildStorefrontIdentityStructuredData } from "@/lib/structured-data";
import SiteShell from "./site-shell";

export async function generateMetadata(): Promise<Metadata> {
  return buildStorefrontPageMetadata({ title: "", description: "", path: "/" });
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  let storefront;
  try {
    storefront = await resolveStorefront();
  } catch (error) {
    if (error instanceof StorefrontApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const siteUrl = await getSiteUrl();
  const globalStructuredData = buildStorefrontIdentityStructuredData(storefront, siteUrl);
  const [navigationResult, collectionsResult] = await Promise.allSettled([
    getPublicNavigation(storefront.id),
    getPublicCollections(storefront.id),
  ]);
  const initialNavigation: PublicStoreNavigationItem[] =
    navigationResult.status === "fulfilled" ? navigationResult.value : [];
  const initialCollections: PublicCollection[] =
    collectionsResult.status === "fulfilled" ? collectionsResult.value : [];

  return (
    <SiteShell
      initialStorefront={storefront}
      initialNavigation={initialNavigation}
      initialCollections={initialCollections}
      globalStructuredData={globalStructuredData}
    >
      {children}
    </SiteShell>
  );
}
