import React from "react";
import ShopDetails from "@/components/ShopDetails";
import { loadShopDetailsViewModel } from "@/lib/shop-data";
import { getPublicCollectionBySlug, resolveStorefront, StorefrontApiError } from "@/lib/storefront-api";
import { buildStorefrontPageMetadata } from "@/lib/seo";
import { notFound, redirect } from "next/navigation";

export const dynamic = "force-dynamic";

function isNotFoundError(error: unknown): boolean {
  if (error instanceof StorefrontApiError) {
    return error.status === 404;
  }
  if (typeof error === "object" && error !== null && "status" in error) {
    return Number((error as { status?: unknown }).status) === 404;
  }
  return false;
}

async function redirectCollectionIfPresent(slug: string): Promise<never> {
  let collection: Awaited<ReturnType<typeof getPublicCollectionBySlug>>;
  try {
    const storefront = await resolveStorefront();
    collection = await getPublicCollectionBySlug(storefront.id, slug);
  } catch {
    notFound();
  }
  redirect(`/collections/${encodeURIComponent(collection.slug)}`);
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  try {
    const data = await loadShopDetailsViewModel(slug);
    return buildStorefrontPageMetadata({
      title: data.product.title,
      description:
        data.product.description ||
        `Compra ${data.product.title} online.`,
      path: `/products/${slug}`,
    });
  } catch (error) {
    if (isNotFoundError(error)) {
      return redirectCollectionIfPresent(slug);
    }
    return buildStorefrontPageMetadata({
      title: "Producto",
      description: "Product details",
      path: `/products/${slug}`,
      index: false,
    });
  }
}

const ProductDetailsPage = async ({
  params,
}: {
  params: Promise<{ slug: string }>;
}) => {
  const { slug } = await params;

  try {
    const data = await loadShopDetailsViewModel(slug);

    return (
      <main>
        <ShopDetails product={data.product} relatedItems={data.relatedItems} />
      </main>
    );
  } catch (error) {
    if (isNotFoundError(error)) {
      return redirectCollectionIfPresent(slug);
    }
    throw error;
  }
};

export default ProductDetailsPage;
