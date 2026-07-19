import { notFound } from "next/navigation";

import { StorefrontApiError, resolveStorefront } from "@/lib/storefront-api";
import SiteShell from "./site-shell";

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
