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
  categoryName?: string;
  brandName?: string;
  productType?: string;
  availableSizes?: string[];
  availableColors?: string[];
  imgs?: {
    thumbnails: string[];
    previews: string[];
  };
};
