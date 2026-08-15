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
  public_config: {
    redirect_url?: string | null;
    checkout_url?: string | null;
    checkout_icon_url?: string | null;
    checkout_description?: string | null;
    checkout_accent?: string | null;
    [key: string]: unknown;
  };
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
  shipping_line1?: string | null;
  shipping_city?: string | null;
  shipping_state?: string | null;
  shipping_country?: string | null;
  shipping_postal_code?: string | null;
};

export type PublicShippingDestination = {
  id: string;
  country_code: string;
  state_code?: string | null;
  state_name: string;
  city_code?: string | null;
  city_name?: string | null;
  destination_type: string;
};

export type PublicShippingMethod = {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  method_type: string;
  sort_order: number;
  estimate_min_days?: number | null;
  estimate_max_days?: number | null;
};

export type PublicShippingConfig = {
  destinations: PublicShippingDestination[];
  methods: PublicShippingMethod[];
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
  variants: PublicProductVariant[];
  image_url?: string | null;
  gallery: string[];
  price: number;
  base_price: number;
  compare_at_price?: number | null;
  is_featured: boolean;
  show_stock: boolean;
  in_stock: boolean;
  stock_quantity?: number | null;
  seo_title?: string | null;
  seo_description?: string | null;
};

export type PublicProductVariant = {
  id: string;
  name: string;
  sku?: string | null;
  attributes: Record<string, unknown>;
  price: number;
  compare_at_price?: number | null;
  in_stock: boolean;
  stock_quantity?: number | null;
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
  collections: PublicCatalogCategory[];
  brands: PublicCatalogFacet[];
  product_types: PublicCatalogProductType[];
  sizes: PublicCatalogFacet[];
  colors: PublicCatalogFacet[];
  total_products: number;
  min_price: number;
  max_price: number;
  current_page: number;
  page_size: number;
  total_pages: number;
  selected_collection_name?: string | null;
};

export type CheckoutItemInput = {
  published_product_id: string;
  variant_id?: string | null;
  quantity: number;
};

export type CheckoutPreviewRequest = {
  items: CheckoutItemInput[];
  shipping_amount?: number;
  discount_amount?: number;
  coupon_code?: string | null;
  address?: CheckoutAddress | null;
  payment_provider?: string | null;
  shipping_method_id?: string | null;
};

export type CheckoutPreviewItem = {
  published_product_id: string;
  product_id: string;
  variant_id?: string | null;
  slug: string;
  title: string;
  variant_name?: string | null;
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
  total_weight?: number;
  shipping_method_id?: string | null;
  shipping_method_name?: string | null;
  shipping_rule_name?: string | null;
  shipping_quote_required?: boolean;
  shipping_requires_destination?: boolean;
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
  state_code?: string | null;
  city_code?: string | null;
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
  shipping_method_id?: string | null;
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
  shipping_method_id?: string | null;
  shipping_method_name?: string | null;
  shipping_quote_required?: boolean;
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
