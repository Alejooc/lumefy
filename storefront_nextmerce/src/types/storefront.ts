export type PublicStorefrontBrandingPromo = {
  id: string;
  title: string;
  subtitle?: string | null;
  description?: string | null;
  cta_label?: string | null;
  cta_href?: string | null;
  image_url?: string | null;
  background_color?: string | null;
  accent_color?: string | null;
};

export type PublicStorefrontBranding = {
  logo_url?: string | null;
  support_phone?: string | null;
  support_email?: string | null;
  support_address?: string | null;
  website?: string | null;
  footer_text?: string | null;
  social_links: Record<string, string | null | undefined>;
  promo_banners: PublicStorefrontBrandingPromo[];
};

export type PublicStorefront = {
  id: string;
  name: string;
  slug: string;
  subdomain?: string | null;
  theme_key: string;
  theme_settings: Record<string, unknown>;
  checkout_settings: Record<string, unknown>;
  seo_settings: Record<string, unknown>;
  currency: string;
  language: string;
  branding: PublicStorefrontBranding;
};

export type PublicStoreNavigationItem = {
  id: string;
  parent_id?: string | null;
  label: string;
  item_type: string;
  reference_id?: string | null;
  url?: string | null;
  sort_order: number;
};

export type PublicStorePaymentGateway = {
  id: string;
  provider: string;
  display_name: string;
  is_sandbox: boolean;
  sort_order: number;
  checkout_flow: string;
  public_config: Record<string, unknown>;
};

export type PublicStorefrontAccountUser = {
  id: string;
  email: string;
  full_name?: string | null;
  created_at: string;
};

export type PublicStorefrontAuthResponse = {
  access_token: string;
  token_type: string;
  user: PublicStorefrontAccountUser;
};

export type PublicStorefrontAccountOrder = {
  order_id: string;
  order_code: string;
  created_at: string;
  status: string;
  title: string;
  total: number;
  currency: string;
};

export type PublicCollection = {
  id: string;
  storefront_id: string;
  name: string;
  slug: string;
  description?: string | null;
  image_url?: string | null;
  is_featured: boolean;
  products: PublicProduct[];
};

export type PublicProduct = {
  id: string;
  product_id: string;
  slug: string;
  title: string;
  description?: string | null;
  category_name?: string | null;
  brand_name?: string | null;
  product_type?: string | null;
  available_sizes: string[];
  available_colors: string[];
  image_url?: string | null;
  gallery: string[];
  price: number;
  base_price: number;
  compare_at_price?: number | null;
  is_featured: boolean;
  show_stock: boolean;
  seo_title?: string | null;
  seo_description?: string | null;
};

export type PublicCatalogCategory = {
  name: string;
  slug: string;
  products: number;
  is_refined: boolean;
};

export type PublicCatalogFacet = {
  value: string;
  products: number;
  is_refined: boolean;
};

export type PublicCatalogProductType = {
  name: string;
  value: string;
  products: number;
  is_refined: boolean;
};

export type PublicCatalogResponse = {
  items: PublicProduct[];
  categories: PublicCatalogCategory[];
  product_types: PublicCatalogProductType[];
  sizes: PublicCatalogFacet[];
  colors: PublicCatalogFacet[];
  total_products: number;
  current_page: number;
  page_size: number;
  total_pages: number;
  selected_collection_name?: string | null;
};

export type CheckoutItemInput = {
  published_product_id: string;
  quantity: number;
};

export type CheckoutPreviewRequest = {
  items: CheckoutItemInput[];
  shipping_amount?: number;
  discount_amount?: number;
  coupon_code?: string | null;
};

export type CheckoutPreviewItem = {
  published_product_id: string;
  product_id: string;
  slug: string;
  title: string;
  quantity: number;
  unit_price: number;
  line_subtotal: number;
};

export type CheckoutPreviewResponse = {
  currency: string;
  items: CheckoutPreviewItem[];
  subtotal: number;
  discount: number;
  shipping: number;
  tax: number;
  total: number;
};

export type CheckoutCustomer = {
  full_name: string;
  email: string;
  phone?: string | null;
  document_id?: string | null;
};

export type CheckoutAddress = {
  line1: string;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  postal_code?: string | null;
};

export type CheckoutCreateOrderRequest = {
  items: CheckoutItemInput[];
  customer: CheckoutCustomer;
  address: CheckoutAddress;
  notes?: string | null;
  payment_provider: string;
  shipping_amount?: number;
  discount_amount?: number;
  coupon_code?: string | null;
  idempotency_key?: string | null;
};

export type CheckoutCreateOrderResponse = {
  order_id: string;
  order_code: string;
  status: string;
  currency: string;
  subtotal: number;
  discount: number;
  shipping: number;
  tax: number;
  total: number;
  payment_provider: string;
  payment_status: string;
};

export type PaymentIntentRequest = {
  provider: string;
  amount: number;
  currency: string;
  order_id?: string | null;
  customer_email?: string | null;
  customer_full_name?: string | null;
  customer_phone?: string | null;
  shipping_address?: Record<string, unknown>;
  return_url?: string | null;
};

export type PaymentIntentResponse = {
  provider: string;
  flow: string;
  mode: string;
  amount: number;
  currency: string;
  external_reference: string;
  checkout_url?: string | null;
  public_key?: string | null;
  merchant_id?: string | null;
  instructions?: string | null;
  metadata: Record<string, unknown>;
  provider_payload: Record<string, unknown>;
};

export type PaymentStatusResponse = {
  provider: string;
  transaction_id: string;
  external_reference?: string | null;
  status: string;
  status_message?: string | null;
  order_id?: string | null;
  order_code?: string | null;
};
