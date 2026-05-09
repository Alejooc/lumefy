import React from "react";
import ShopWithSidebar from "@/components/ShopWithSidebar";
import { loadShopViewModel } from "@/lib/shop-data";
import { buildStorefrontPageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<{
    collection?: string;
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
  const params = await searchParams;
  const { page, ...rest } = params;
  const hasFilters = Object.values(rest).some((value) => Boolean(value));
  const pageNumber = Number(page || "1");
  const canonicalPath =
    Number.isFinite(pageNumber) && pageNumber > 1 ? `/products?page=${pageNumber}` : "/products";

  return buildStorefrontPageMetadata({
    title: "Productos",
    description: "Browse products",
    path: canonicalPath,
    index: !hasFilters,
  });
}

const ProductsPage = async ({
  searchParams,
}: {
  searchParams: Promise<{
    collection?: string;
    q?: string;
    type?: string;
    size?: string;
    color?: string;
    sort?: string;
    minPrice?: string;
    maxPrice?: string;
    page?: string;
  }>;
}) => {
  const { collection, q, type, size, color, sort, minPrice, maxPrice, page } =
    await searchParams;
  const currentPage = Math.max(1, Number(page || "1") || 1);
  const data = await loadShopViewModel({
    collectionSlug: collection,
    searchTerm: q,
    productType: type,
    size,
    color,
    sort,
    minPrice: minPrice ? Number(minPrice) : undefined,
    maxPrice: maxPrice ? Number(maxPrice) : undefined,
    page: currentPage,
    pageSize: 12,
  });

  return (
    <main>
      <ShopWithSidebar
        items={data.items}
        categories={data.categories}
        productTypes={data.productTypes}
        sizes={data.sizes}
        colors={data.colors}
        selectedCollectionName={data.selectedCollectionName}
        searchTerm={data.searchTerm}
        minPrice={data.minPrice}
        maxPrice={data.maxPrice}
        activeSort={data.activeSort}
        activeCollections={data.activeCollections}
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
};

export default ProductsPage;
