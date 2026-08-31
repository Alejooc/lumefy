import React from "react";
import ShopWithSidebar from "@/components/ShopWithSidebar";
import { getPublicCollectionBySlug, resolveStorefront } from "@/lib/storefront-api";
import { loadShopViewModel } from "@/lib/shop-data";
import { buildStorefrontPageMetadata, getSiteUrl } from "@/lib/seo";
import { buildBreadcrumbStructuredData } from "@/lib/structured-data";
import StructuredData from "@/components/Seo/StructuredData";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

async function getCollection(slug: string) {
  const storefront = await resolveStorefront();
  return getPublicCollectionBySlug(storefront.id, slug, { includeProducts: false });
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
      imageUrl: collection.image_url || undefined,
    });
  } catch {
    notFound();
  }
}

export default async function CollectionPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{
    category?: string;
    brand?: string;
    q?: string;
    type?: string;
    size?: string;
    color?: string;
    sort?: string;
    minPrice?: string;
    maxPrice?: string;
    page?: string;
  }>;
}) {
  const { slug } = await params;
  const { category, brand, q, type, size, color, sort, minPrice, maxPrice, page } = await searchParams;

  try {
    const collection = await getCollection(slug);
    const data = await loadShopViewModel({
      collectionSlug: collection.slug,
      category,
      brand,
      searchTerm: q,
      productType: type,
      size,
      color,
      sort,
      minPrice: minPrice ? Number(minPrice) : undefined,
      maxPrice: maxPrice ? Number(maxPrice) : undefined,
      page: Math.max(1, Number(page || "1") || 1),
      pageSize: 12,
    });
    const siteUrl = await getSiteUrl();

    return (
      <main>
        <StructuredData
          data={buildBreadcrumbStructuredData(siteUrl, [
            { name: "Inicio", path: "/" },
            { name: "Productos", path: "/products" },
            { name: collection.name, path: `/collections/${encodeURIComponent(collection.slug)}` },
          ])}
        />
        <ShopWithSidebar
          items={data.items}
          categories={data.categories}
          collections={data.collections}
          brands={data.brands}
          productTypes={data.productTypes}
          sizes={data.sizes}
          colors={data.colors}
          selectedCollectionName={collection.name}
          selectedCollectionDescription={collection.description || undefined}
          collectionSlug={collection.slug}
          collectionTemplate={data.collectionTemplate}
          templateKey="collection"
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
          hasNextPage={data.hasNextPage}
        />
      </main>
    );
  } catch {
    notFound();
  }
}
