import { Product } from "@/types/product";
import { PublicProduct } from "@/types/storefront";
import { storefrontImageUrl } from "./storefront-image";

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

/** Convert the public API shape to the card shape used by the storefront. */
export function toTemplateProduct(product: PublicProduct): Product {
  const previewImage =
    storefrontImageUrl(product.image_url) ||
    storefrontImageUrl(product.gallery[0]) ||
    fallbackImage(product.slug);
  const secondaryImage =
    storefrontImageUrl(product.gallery[1]) ||
    storefrontImageUrl(product.image_url) ||
    fallbackImage(`${product.slug}-alt`);
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
    variants: (product.variants || []).map((variant) => ({
      id: variant.id,
      name: variant.name,
      sku: variant.sku,
      attributes: variant.attributes || {},
      price: Number(variant.price),
      compareAtPrice: variant.compare_at_price == null ? undefined : Number(variant.compare_at_price),
      inStock: variant.in_stock,
      stockQuantity: variant.stock_quantity == null ? undefined : Number(variant.stock_quantity),
    })),
    inStock: product.in_stock,
    stockQuantity: product.stock_quantity ?? undefined,
    imgs: {
      thumbnails: [previewImage, secondaryImage],
      previews: [previewImage, secondaryImage],
    },
  };
}
