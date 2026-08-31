import React from "react";
import ShopDetails from "@/components/ShopDetails";
import { loadShopDetailsViewModel } from "@/lib/shop-data";
import { getPublicCollectionBySlug, resolveStorefront, StorefrontApiError } from "@/lib/storefront-api";
import { buildStorefrontPageMetadata } from "@/lib/seo";
import { buildBreadcrumbStructuredData, buildProductStructuredData } from "@/lib/structured-data";
import StructuredData from "@/components/Seo/StructuredData";
import { getSiteUrl } from "@/lib/seo";
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
    collection = await getPublicCollectionBySlug(storefront.id, slug, { includeProducts: false });
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
      title: data.product.seoTitle || data.product.title,
      description:
        data.product.seoDescription ||
        data.product.description ||
        `Compra ${data.product.title} online.`,
      path: `/products/${slug}`,
      imageUrl: data.product.imgs?.previews?.[0],
    });
  } catch (error) {
    if (isNotFoundError(error)) {
      return redirectCollectionIfPresent(slug);
    }
    return buildStorefrontPageMetadata({
      title: "Producto",
      description: "Detalle del producto",
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
    const storefront = await resolveStorefront();
    const siteUrl = await getSiteUrl();

    return (
      <main>
        <StructuredData
          data={buildProductStructuredData(data.product, siteUrl, storefront.currency)}
        />
        <StructuredData
          data={buildBreadcrumbStructuredData(siteUrl, [
            { name: "Inicio", path: "/" },
            { name: "Productos", path: "/products" },
            { name: data.product.title, path: `/products/${encodeURIComponent(data.product.slug || slug)}` },
          ])}
        />
        <ShopDetails
          product={data.product}
          relatedItems={data.relatedItems}
          productTemplate={data.productTemplate}
          addiWidget={data.addiWidget}
        />
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
