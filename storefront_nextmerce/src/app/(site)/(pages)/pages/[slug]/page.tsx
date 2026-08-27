import React from "react";
import InformativePage from "@/components/InformativePage";
import {
  informationalPageContent,
  informationalPageOptions,
} from "@/lib/pages-template";
import { resolveStorefront } from "@/lib/storefront-api";
import { buildStorefrontPageMetadata } from "@/lib/seo";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

function isInformationalPage(slug: string): boolean {
  return informationalPageOptions.some((page) => page.slug === slug);
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!isInformationalPage(slug)) notFound();

  const storefront = await resolveStorefront();
  const page = informationalPageContent(storefront.theme_documents?.pages || {}, slug);
  return buildStorefrontPageMetadata({
    title: page.title,
    description: page.description,
    path: `/pages/${encodeURIComponent(slug)}`,
  });
}

export default async function InformationalPageRoute({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!isInformationalPage(slug)) notFound();

  const storefront = await resolveStorefront();
  return (
    <main>
      <InformativePage
        pageSlug={slug}
        pageTemplate={storefront.theme_documents?.pages || {}}
      />
    </main>
  );
}
