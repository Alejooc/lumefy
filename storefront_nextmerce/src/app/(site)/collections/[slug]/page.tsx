import React from "react";
import ShopWithSidebar from "@/components/ShopWithSidebar";
import { getPublicCollectionBySlug, resolveStorefront } from "@/lib/storefront-api";
import { loadShopViewModel } from "@/lib/shop-data";
import { buildStorefrontPageMetadata } from "@/lib/seo";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

async function getCollection(slug: string) {
  const storefront = await resolveStorefront();
  return getPublicCollectionBySlug(storefront.id, slug);
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  try {
    const collection = await getCollection(slug);
    return buildStorefrontPageMetadata({
      title: collection.name,
      description: collection.description || `Explora la colección ${collection.name}.`,
      path: `/collections/${encodeURIComponent(collection.slug)}`,
    });
  } catch {
    notFound();
  }
}

export default async function CollectionPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  try {
    const collection = await getCollection(slug);
    const data = await loadShopViewModel({
      collectionSlug: collection.slug,
      page: 1,
      pageSize: 12,
    });

    return (
      <main>
        <ShopWithSidebar
          items={data.items}
          categories={data.categories}
          collections={data.collections}
          brands={data.brands}
          productTypes={data.productTypes}
          sizes={data.sizes}
          colors={data.colors}
          selectedCollectionName={collection.name}
          breadcrumbPages={["Productos", collection.name]}
          searchTerm={data.searchTerm}
          priceRangeMin={data.priceRangeMin}
          priceRangeMax={data.priceRangeMax}
          minPrice={data.minPrice}
          maxPrice={data.maxPrice}
          activeSort={data.activeSort}
          activeCollections={data.activeCollections}
          activeCategories={data.activeCategories}
          activeBrands={data.activeBrands}
          activeTypes={data.activeTypes}
          activeSizes={data.activeSizes}
          activeColors={data.activeColors}
          totalProducts={data.totalProducts}
          currentPage={data.currentPage}
          totalPages={data.totalPages}
          hasPreviousPage={data.hasPreviousPage}
          hasNextPage={data.hasNextPage}
        />
      </main>
    );
  } catch {
    notFound();
  }
}
