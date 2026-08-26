import { notFound } from "next/navigation";
import type { Metadata } from "next";

import { StorefrontApiError, resolveStorefront } from "@/lib/storefront-api";
import { getStorefrontBranding } from "@/lib/storefront-branding";
import SiteShell from "./site-shell";

export async function generateMetadata(): Promise<Metadata> {
  try {
    const storefront = await resolveStorefront();
    const branding = getStorefrontBranding(storefront);
    return {
      title: storefront.name,
      icons: branding.faviconUrl ? { icon: branding.faviconUrl } : undefined,
    };
  } catch {
    return {};
  }
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  try {
    await resolveStorefront();
  } catch (error) {
    if (error instanceof StorefrontApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  return <SiteShell>{children}</SiteShell>;
}
