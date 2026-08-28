export type ProductVariant = {
  id: string;
  name: string;
  sku?: string | null;
  attributes: Record<string, unknown>;
  price: number;
  compareAtPrice?: number;
  inStock: boolean;
  stockQuantity?: number;
};

export type Product = {
  title: string;
  reviews: number;
  price: number;
  discountedPrice: number;
  id: number;
  publishedProductId?: string;
  href?: string;
  slug?: string;
  description?: string;
  seoTitle?: string;
  seoDescription?: string;
  categoryName?: string;
  brandName?: string;
  productType?: string;
  availableSizes?: string[];
  availableColors?: string[];
  variants?: ProductVariant[];
  inStock?: boolean;
  stockQuantity?: number;
  imgs?: {
    thumbnails: string[];
    previews: string[];
  };
};
