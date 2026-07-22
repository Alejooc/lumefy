import { Product } from "@/types/product";
import { PublicCollection, PublicProduct } from "@/types/storefront";
import { storefrontImageUrl } from "./storefront-image";

import {
  getPublicCollections,
  getPublicProducts,
  getPublicProductBySlug,
  resolveStorefront,
} from "./storefront-api";

export type ShopFilterCategory = {
  name: string;
  slug: string;
  products: number;
  isRefined: boolean;
};

export type ShopFilterType = {
  name: string;
  value: string;
  products: number;
  isRefined: boolean;
};

export type ShopFilterFacet = {
  value: string;
  products: number;
  isRefined: boolean;
};

export type ShopViewModel = {
  items: Product[];
  categories: ShopFilterCategory[];
  collections: ShopFilterCategory[];
  brands: ShopFilterFacet[];
  productTypes: ShopFilterType[];
  sizes: ShopFilterFacet[];
  colors: ShopFilterFacet[];
  totalProducts: number;
  currentPage: number;
  pageSize: number;
  totalPages: number;
  hasPreviousPage: boolean;
  hasNextPage: boolean;
  selectedCollectionName?: string;
  searchTerm?: string;
  priceRangeMin: number;
  priceRangeMax: number;
  minPrice: number;
  maxPrice: number;
  activeSort: string;
  activeCollections: string[];
  activeCategories: string[];
  activeBrands: string[];
  activeTypes: string[];
  activeSizes: string[];
  activeColors: string[];
};

export type ShopDetailsViewModel = {
  product: Product;
  relatedItems: Product[];
};

function numericId(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) | 0;
  }
  return Math.abs(hash) || 1;
}

function fallbackImage(seed: string): string {
  return `/images/products/product-${(numericId(seed) % 8) + 1}-bg-1.png`;
}

function normalizeTypeLabel(value?: string | null): string {
  if (!value) {
    return "Other";
  }
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function toTemplateProduct(product: PublicProduct): Product {
  const previewImage =
    storefrontImageUrl(product.image_url) || storefrontImageUrl(product.gallery[0]) || fallbackImage(product.slug);
  const secondaryImage =
    storefrontImageUrl(product.gallery[1]) || storefrontImageUrl(product.image_url) || fallbackImage(`${product.slug}-alt`);
  const compare = product.compare_at_price ?? product.base_price ?? product.price;

  return {
    id: numericId(product.id),
    publishedProductId: product.id,
    title: product.title,
    description: product.description || "",
    reviews: product.is_featured ? 24 : 12,
    price: Number(compare || product.price),
    discountedPrice: Number(product.price),
    href: `/products/${encodeURIComponent(product.slug)}`,
    slug: product.slug,
    categoryName: product.category_name || undefined,
    brandName: product.brand_name || undefined,
    productType: product.product_type || undefined,
    availableSizes: product.available_sizes || [],
    availableColors: product.available_colors || [],
    inStock: product.in_stock,
    stockQuantity: product.stock_quantity ?? undefined,
    imgs: {
      thumbnails: [previewImage, secondaryImage],
      previews: [previewImage, secondaryImage],
    },
  };
}

async function loadCollections(): Promise<PublicCollection[]> {
  const storefront = await resolveStorefront();
  return getPublicCollections(storefront.id);
}

function parseMultiValue(value?: string): string[] {
  return (value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export async function loadShopViewModel(options?: {
  collectionSlug?: string;
  category?: string;
  brand?: string;
  searchTerm?: string;
  productType?: string;
  size?: string;
  color?: string;
  minPrice?: number;
  maxPrice?: number;
  sort?: string;
  page?: number;
  pageSize?: number;
}): Promise<ShopViewModel> {
  const storefront = await resolveStorefront();
  const collections = await loadCollections();
  const selectedCollections = parseMultiValue(options?.collectionSlug);
  const normalizedTypes = parseMultiValue(options?.productType).map((item) => item.toUpperCase());
  const normalizedSizes = parseMultiValue(options?.size);
  const normalizedColors = parseMultiValue(options?.color);
  const currentPage = Math.max(1, options?.page || 1);
  const requestedPageSize = Math.max(1, options?.pageSize || 12);
  const catalog = await getPublicProducts(storefront.id, {
    collection: options?.collectionSlug,
    category: options?.category,
    brand: options?.brand,
    q: options?.searchTerm,
    type: options?.productType,
    size: options?.size,
    color: options?.color,
    sort: options?.sort,
    min_price: options?.minPrice,
    max_price: options?.maxPrice,
    page: currentPage,
    page_size: requestedPageSize,
  });
  const priceRangeMin = Number(catalog.min_price || 0);
  const priceRangeMax = Number(catalog.max_price || 0);
  const minPrice = Number.isFinite(options?.minPrice) ? Number(options?.minPrice) : priceRangeMin;
  const maxPrice = Number.isFinite(options?.maxPrice)
    ? Number(options?.maxPrice)
    : priceRangeMax;
  const pageSize = Math.max(1, options?.pageSize || 12);

  return {
    items: catalog.items.map(toTemplateProduct),
    categories: catalog.categories.map((category) => ({
      name: category.name,
      slug: category.slug,
      products: category.products,
      isRefined: category.is_refined,
    })),
    collections: catalog.collections.length
      ? catalog.collections.map((collection) => ({
          name: collection.name,
          slug: collection.slug,
          products: collection.products,
          isRefined: selectedCollections.includes(collection.slug),
        }))
      : collections.map((collection) => ({
          name: collection.name,
          slug: collection.slug,
          products: 0,
          isRefined: selectedCollections.includes(collection.slug),
        })),
    brands: catalog.brands.map((entry) => ({
      value: entry.value,
      products: entry.products,
      isRefined: entry.is_refined,
    })),
    productTypes: catalog.product_types.map((entry) => ({
      name: entry.name || normalizeTypeLabel(entry.value),
      value: entry.value,
      products: entry.products,
      isRefined: entry.is_refined || normalizedTypes.includes(entry.value),
    })),
    sizes: catalog.sizes.map((entry) => ({
      value: entry.value,
      products: entry.products,
      isRefined: entry.is_refined || normalizedSizes.includes(entry.value),
    })),
    colors: catalog.colors.map((entry) => ({
      value: entry.value,
      products: entry.products,
      isRefined: entry.is_refined || normalizedColors.includes(entry.value),
    })),
    totalProducts: catalog.total_products,
    currentPage: catalog.current_page,
    pageSize: catalog.page_size || pageSize,
    totalPages: catalog.total_pages,
    hasPreviousPage: catalog.current_page > 1,
    hasNextPage: catalog.current_page < catalog.total_pages,
    selectedCollectionName: catalog.selected_collection_name || undefined,
    searchTerm: options?.searchTerm,
    priceRangeMin,
    priceRangeMax,
    minPrice,
    maxPrice,
    activeSort: options?.sort || "latest",
    activeCollections: selectedCollections,
    activeCategories: parseMultiValue(options?.category),
    activeBrands: parseMultiValue(options?.brand),
    activeTypes: normalizedTypes,
    activeSizes: parseMultiValue(options?.size),
    activeColors: parseMultiValue(options?.color),
  };
}

export async function loadShopDetailsViewModel(slug: string): Promise<ShopDetailsViewModel> {
  const storefront = await resolveStorefront();
  const product = await getPublicProductBySlug(storefront.id, slug);
  const catalog = await getPublicProducts(storefront.id, {
    page: 1,
    page_size: 9,
    sort: "latest",
  });
  const relatedItems = catalog.items
    .filter((item) => item.slug !== slug)
    .slice(0, 8)
    .map(toTemplateProduct);

  return {
    product: toTemplateProduct(product),
    relatedItems,
  };
}
