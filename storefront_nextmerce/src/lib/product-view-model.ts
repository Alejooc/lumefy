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
  // Keep every image for product detail pages. Catalog responses are already
  // compacted by the backend, while detail responses contain the full gallery.
  // De-duplicate after converting provider URLs so the primary image does not
  // appear twice when it is present in both `image_url` and `gallery`.
  const galleryImages = Array.from(
    new Set(
      [product.image_url, ...(product.gallery || [])]
        .map((value) => storefrontImageUrl(value))
        .filter((value): value is string => Boolean(value)),
    ),
  );
  const previewImage = galleryImages[0] || fallbackImage(product.slug);
  const secondaryImage = galleryImages[1] || fallbackImage(`${product.slug}-alt`);
  const images = galleryImages.length ? galleryImages : [previewImage, secondaryImage];
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
      thumbnails: images,
      previews: images,
    },
  };
}
