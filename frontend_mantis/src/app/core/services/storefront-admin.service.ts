import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';

export interface StorefrontSocialLinks {
  facebook?: string | null;
  instagram?: string | null;
  twitter?: string | null;
  linkedin?: string | null;
}

export interface StorefrontPromoBanner {
  id: string;
  title: string;
  subtitle?: string | null;
  description?: string | null;
  cta_label?: string | null;
  cta_href?: string | null;
  image_url?: string | null;
  background_color?: string | null;
  accent_color?: string | null;
}

export interface StorefrontHomeHeroSlide {
  id: string;
  title: string;
  description?: string | null;
  cta_href?: string | null;
  image?: string | null;
  overlay_opacity?: number | null;
  image_position?: string | null;
  content_alignment?: string | null;
  text_color?: string | null;
  button_label?: string | null;
  button_color?: string | null;
}

export interface StorefrontHomeHeroPromo {
  id: string;
  title: string;
  offer_label?: string | null;
  href?: string | null;
  price_label?: string | null;
  compare_price_label?: string | null;
  image?: string | null;
  background_color?: string | null;
  background_image_url?: string | null;
}

export interface StorefrontHomeSectionCopy {
  eyebrow?: string | null;
  title?: string | null;
  cta_label?: string | null;
  cta_href?: string | null;
}

export interface StorefrontHomeCategoryCard {
  id: string;
  title: string;
  href?: string | null;
  image?: string | null;
  background_color?: string | null;
  overlay_opacity?: number | null;
  image_position?: string | null;
}

export interface StorefrontHomeCountdownSettings {
  enabled?: boolean | null;
  eyebrow?: string | null;
  title?: string | null;
  description?: string | null;
  cta_label?: string | null;
  cta_href?: string | null;
  deadline?: string | null;
  background_color?: string | null;
  background_image_url?: string | null;
  product_image_url?: string | null;
}

export interface StorefrontHomeNewsletterSettings {
  enabled?: boolean | null;
  title?: string | null;
  description?: string | null;
  placeholder?: string | null;
  button_label?: string | null;
  background_image_url?: string | null;
}

export interface StorefrontHomeFeatureItem {
  id: string;
  title: string;
  description?: string | null;
  image?: string | null;
}

export interface StorefrontHomeTestimonialItem {
  id: string;
  review: string;
  author_name: string;
  author_role?: string | null;
  author_image?: string | null;
}

export interface StorefrontHomeTestimonialsSettings {
  enabled?: boolean | null;
  eyebrow?: string | null;
  title?: string | null;
  items?: StorefrontHomeTestimonialItem[];
}

export interface StorefrontHomeSettings {
  hero_slides?: StorefrontHomeHeroSlide[];
  hero_promos?: StorefrontHomeHeroPromo[];
  category_section?: StorefrontHomeSectionCopy;
  category_cards?: StorefrontHomeCategoryCard[];
  new_arrivals_section?: StorefrontHomeSectionCopy;
  best_sellers_section?: StorefrontHomeSectionCopy;
  features?: StorefrontHomeFeatureItem[];
  promo_banners?: StorefrontPromoBanner[];
  countdown?: StorefrontHomeCountdownSettings;
  newsletter?: StorefrontHomeNewsletterSettings;
  testimonials?: StorefrontHomeTestimonialsSettings;
}

export interface StorefrontBrandingSettings {
  logo_url?: string | null;
  support_phone?: string | null;
  support_email?: string | null;
  support_address?: string | null;
  website?: string | null;
  footer_text?: string | null;
  social_links?: StorefrontSocialLinks;
  promo_banners?: StorefrontPromoBanner[];
}

export interface StorefrontCurrencySettings {
  show_decimals?: boolean | null;
}

export interface StorefrontHeaderSettings {
  support_label?: string | null;
  search_placeholder?: string | null;
  account_heading?: string | null;
  guest_account_label?: string | null;
  sign_out_label?: string | null;
  cart_heading?: string | null;
  recently_viewed_label?: string | null;
  wishlist_label?: string | null;
}

export interface StorefrontFooterLink {
  label: string;
  href?: string | null;
}

export interface StorefrontFooterPaymentMethod {
  label: string;
  icon_url?: string | null;
  href?: string | null;
}

export interface StorefrontFooterSettings {
  help_title?: string | null;
  account_title?: string | null;
  quick_links_title?: string | null;
  app_title?: string | null;
  app_description?: string | null;
  app_store_subtitle?: string | null;
  app_store_label?: string | null;
  app_store_url?: string | null;
  play_store_subtitle?: string | null;
  play_store_label?: string | null;
  play_store_url?: string | null;
  payment_title?: string | null;
  show_social_links?: boolean | null;
  show_app_downloads?: boolean | null;
  show_payment_methods?: boolean | null;
  account_links?: StorefrontFooterLink[];
  quick_links?: StorefrontFooterLink[];
  payment_methods?: StorefrontFooterPaymentMethod[];
}

export interface StorefrontCommonContentSettings {
  continue_shopping_label?: string | null;
  add_to_cart_label?: string | null;
  add_to_wishlist_label?: string | null;
  quantity_label?: string | null;
}

export interface StorefrontProductDetailContentSettings {
  breadcrumb_title?: string | null;
  missing_product_message?: string | null;
  price_label?: string | null;
  stock_in_label?: string | null;
  stock_out_label?: string | null;
  free_delivery_text?: string | null;
  promo_text?: string | null;
  description_tab_label?: string | null;
  details_tab_label?: string | null;
  reviews_tab_label?: string | null;
  reviews_empty_title?: string | null;
  reviews_empty_description?: string | null;
  submit_review_label?: string | null;
}

export interface StorefrontCheckoutContentSettings {
  breadcrumb_title?: string | null;
  empty_cart_title?: string | null;
  empty_cart_description?: string | null;
  billing_details_title?: string | null;
  order_title?: string | null;
  payment_method_title?: string | null;
  shipping_fee_label?: string | null;
  calculated_later_label?: string | null;
  notes_label?: string | null;
  notes_placeholder?: string | null;
  update_summary_label?: string | null;
  processing_summary_label?: string | null;
  submit_order_label?: string | null;
  submitting_order_label?: string | null;
}

export interface StorefrontCartContentSettings {
  breadcrumb_title?: string | null;
  page_title?: string | null;
  clear_cart_label?: string | null;
  empty_title?: string | null;
  empty_description?: string | null;
  table_product_label?: string | null;
  table_price_label?: string | null;
  table_quantity_label?: string | null;
  table_subtotal_label?: string | null;
  table_action_label?: string | null;
  summary_title?: string | null;
  checkout_button_label?: string | null;
}

export interface StorefrontWishlistContentSettings {
  breadcrumb_title?: string | null;
  page_title?: string | null;
  clear_wishlist_label?: string | null;
  empty_title?: string | null;
  empty_description?: string | null;
  table_product_label?: string | null;
  table_unit_price_label?: string | null;
  table_stock_label?: string | null;
  table_action_label?: string | null;
}

export interface StorefrontContactContentSettings {
  breadcrumb_title?: string | null;
  sidebar_title?: string | null;
  first_name_label?: string | null;
  last_name_label?: string | null;
  email_label?: string | null;
  phone_label?: string | null;
  subject_label?: string | null;
  message_label?: string | null;
  first_name_placeholder?: string | null;
  last_name_placeholder?: string | null;
  email_placeholder?: string | null;
  phone_placeholder?: string | null;
  subject_placeholder?: string | null;
  message_placeholder?: string | null;
  submit_label?: string | null;
  submitting_label?: string | null;
  error_fallback?: string | null;
}

export interface StorefrontQuickViewContentSettings {
  description_fallback?: string | null;
  price_label?: string | null;
  quantity_label?: string | null;
  view_details_label?: string | null;
  available_label?: string | null;
}

export interface StorefrontContentSettings {
  common?: StorefrontCommonContentSettings;
  product_detail?: StorefrontProductDetailContentSettings;
  checkout?: StorefrontCheckoutContentSettings;
  cart?: StorefrontCartContentSettings;
  wishlist?: StorefrontWishlistContentSettings;
  contact?: StorefrontContactContentSettings;
  quick_view?: StorefrontQuickViewContentSettings;
}

export interface Storefront {
  id: string;
  name: string;
  slug: string;
  subdomain?: string | null;
  is_enabled: boolean;
  theme_key: string;
  theme_settings: Record<string, unknown>;
  checkout_settings: Record<string, unknown>;
  seo_settings: Record<string, unknown>;
  currency: string;
  language: string;
}

export interface StorefrontDomain {
  id: string;
  storefront_id: string;
  domain: string;
  is_primary: boolean;
  is_verified: boolean;
}

export interface StoreCollection {
  id: string;
  storefront_id: string;
  name: string;
  slug: string;
  description?: string | null;
  image_url?: string | null;
  is_visible: boolean;
  is_featured: boolean;
  sort_order: number;
}

export interface PublishedProduct {
  id: string;
  storefront_id: string;
  product_id: string;
  base_price?: number | null;
  product_name?: string | null;
  product_description?: string | null;
  slug: string;
  is_published: boolean;
  is_featured: boolean;
  sort_order: number;
}

export interface StoreCollectionProduct {
  id: string;
  collection_id: string;
  published_product_id: string;
  sort_order: number;
}

export interface StoreNavigationItem {
  id: string;
  storefront_id: string;
  parent_id?: string | null;
  label: string;
  item_type: string;
  reference_id?: string | null;
  url?: string | null;
  sort_order: number;
  is_visible: boolean;
}

export interface StorePaymentGateway {
  id: string;
  storefront_id: string;
  provider: string;
  display_name: string;
  is_enabled: boolean;
  is_sandbox: boolean;
  public_key?: string | null;
  secret_key_encrypted?: string | null;
  merchant_id?: string | null;
  extra_config: Record<string, unknown>;
  sort_order: number;
}

export interface StorefrontReadiness {
  ready: boolean;
  published_products: number;
  out_of_stock_products: number;
  enabled_payment_gateways: number;
  issues: string[];
}

export interface CatalogProduct {
  id: string;
  name: string;
  sku?: string | null;
  price?: number | null;
}

export interface PublicCheckoutItemInput {
  published_product_id: string;
  quantity: number;
}

export interface PublicCheckoutPreviewRequest {
  items: PublicCheckoutItemInput[];
  shipping_amount?: number;
  discount_amount?: number;
  coupon_code?: string | null;
}

export interface PublicCheckoutPreviewItem {
  published_product_id: string;
  product_id: string;
  slug: string;
  title: string;
  quantity: number;
  unit_price: number;
  line_subtotal: number;
}

export interface PublicCheckoutPreviewResponse {
  currency: string;
  items: PublicCheckoutPreviewItem[];
  subtotal: number;
  discount: number;
  shipping: number;
  tax: number;
  total: number;
}

export interface PublicCheckoutCustomer {
  full_name: string;
  email: string;
  phone?: string | null;
  document_id?: string | null;
}

export interface PublicCheckoutAddress {
  line1: string;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  postal_code?: string | null;
}

export interface PublicCheckoutCreateOrderRequest {
  items: PublicCheckoutItemInput[];
  customer: PublicCheckoutCustomer;
  address: PublicCheckoutAddress;
  notes?: string | null;
  payment_provider: string;
  shipping_amount?: number;
  discount_amount?: number;
  coupon_code?: string | null;
}

export interface PublicCheckoutCreateOrderResponse {
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
}

export interface PublicPaymentIntentRequest {
  provider: string;
  amount: number;
  currency: string;
  order_id?: string | null;
  customer_email?: string | null;
}

export interface PublicPaymentIntentResponse {
  provider: string;
  mode: string;
  amount: number;
  currency: string;
  external_reference: string;
  checkout_url?: string | null;
  public_key?: string | null;
  merchant_id?: string | null;
  instructions?: string | null;
  metadata: Record<string, unknown>;
}

@Injectable({
  providedIn: 'root'
})
export class StorefrontAdminService {
  private api = inject(ApiService);

  getStorefronts(): Observable<Storefront[]> {
    return this.api.get<Storefront[]>('/storefront');
  }

  getReadiness(storefrontId: string): Observable<StorefrontReadiness> {
    return this.api.get<StorefrontReadiness>(`/storefront/${storefrontId}/readiness`);
  }

  createStorefront(payload: Partial<Storefront>): Observable<Storefront> {
    return this.api.post<Storefront>('/storefront', payload);
  }

  updateStorefront(id: string, payload: Partial<Storefront>): Observable<Storefront> {
    return this.api.put<Storefront>(`/storefront/${id}`, payload);
  }

  getDomains(storefrontId?: string): Observable<StorefrontDomain[]> {
    return this.api.get<StorefrontDomain[]>('/storefront/domains', storefrontId ? { storefront_id: storefrontId } : {});
  }

  createDomain(payload: Partial<StorefrontDomain>): Observable<StorefrontDomain> {
    return this.api.post<StorefrontDomain>('/storefront/domains', payload);
  }

  updateDomain(id: string, payload: Partial<StorefrontDomain>): Observable<StorefrontDomain> {
    return this.api.put<StorefrontDomain>(`/storefront/domains/${id}`, payload);
  }

  deleteDomain(id: string): Observable<{ ok: boolean }> {
    return this.api.delete<{ ok: boolean }>(`/storefront/domains/${id}`);
  }

  getCollections(storefrontId?: string): Observable<StoreCollection[]> {
    return this.api.get<StoreCollection[]>('/storefront/collections', storefrontId ? { storefront_id: storefrontId } : {});
  }

  createCollection(payload: Partial<StoreCollection>): Observable<StoreCollection> {
    return this.api.post<StoreCollection>('/storefront/collections', payload);
  }

  updateCollection(id: string, payload: Partial<StoreCollection>): Observable<StoreCollection> {
    return this.api.put<StoreCollection>(`/storefront/collections/${id}`, payload);
  }

  getPublishedProducts(storefrontId?: string): Observable<PublishedProduct[]> {
    return this.api.get<PublishedProduct[]>('/storefront/published-products', storefrontId ? { storefront_id: storefrontId } : {});
  }

  createPublishedProduct(payload: Partial<PublishedProduct>): Observable<PublishedProduct> {
    return this.api.post<PublishedProduct>('/storefront/published-products', payload);
  }

  updatePublishedProduct(id: string, payload: Partial<PublishedProduct>): Observable<PublishedProduct> {
    return this.api.put<PublishedProduct>(`/storefront/published-products/${id}`, payload);
  }

  addProductToCollection(collectionId: string, payload: Partial<StoreCollectionProduct>): Observable<StoreCollectionProduct> {
    return this.api.post<StoreCollectionProduct>(`/storefront/collections/${collectionId}/products`, payload);
  }

  getCollectionProducts(collectionId: string): Observable<StoreCollectionProduct[]> {
    return this.api.get<StoreCollectionProduct[]>(`/storefront/collections/${collectionId}/products`);
  }

  removeProductFromCollection(collectionId: string, publishedProductId: string): Observable<{ ok: boolean }> {
    return this.api.delete<{ ok: boolean }>(`/storefront/collections/${collectionId}/products/${publishedProductId}`);
  }

  getNavigation(storefrontId?: string): Observable<StoreNavigationItem[]> {
    return this.api.get<StoreNavigationItem[]>('/storefront/navigation', storefrontId ? { storefront_id: storefrontId } : {});
  }

  createNavigationItem(payload: Partial<StoreNavigationItem>): Observable<StoreNavigationItem> {
    return this.api.post<StoreNavigationItem>('/storefront/navigation', payload);
  }

  updateNavigationItem(id: string, payload: Partial<StoreNavigationItem>): Observable<StoreNavigationItem> {
    return this.api.put<StoreNavigationItem>(`/storefront/navigation/${id}`, payload);
  }

  deleteNavigationItem(id: string): Observable<{ ok: boolean }> {
    return this.api.delete<{ ok: boolean }>(`/storefront/navigation/${id}`);
  }

  getPaymentGateways(storefrontId?: string): Observable<StorePaymentGateway[]> {
    return this.api.get<StorePaymentGateway[]>('/storefront/payment-gateways', storefrontId ? { storefront_id: storefrontId } : {});
  }

  createPaymentGateway(payload: Partial<StorePaymentGateway>): Observable<StorePaymentGateway> {
    return this.api.post<StorePaymentGateway>('/storefront/payment-gateways', payload);
  }

  updatePaymentGateway(id: string, payload: Partial<StorePaymentGateway>): Observable<StorePaymentGateway> {
    return this.api.put<StorePaymentGateway>(`/storefront/payment-gateways/${id}`, payload);
  }

  getProducts(): Observable<CatalogProduct[]> {
    return this.api.get<CatalogProduct[]>('/products');
  }

  previewPublicCheckout(storefrontId: string, payload: PublicCheckoutPreviewRequest): Observable<PublicCheckoutPreviewResponse> {
    return this.api.post<PublicCheckoutPreviewResponse>(`/storefront/public/${storefrontId}/checkout/preview`, payload);
  }

  createPublicCheckoutOrder(storefrontId: string, payload: PublicCheckoutCreateOrderRequest): Observable<PublicCheckoutCreateOrderResponse> {
    return this.api.post<PublicCheckoutCreateOrderResponse>(`/storefront/public/${storefrontId}/checkout/orders`, payload);
  }

  createPublicPaymentIntent(storefrontId: string, payload: PublicPaymentIntentRequest): Observable<PublicPaymentIntentResponse> {
    return this.api.post<PublicPaymentIntentResponse>(`/storefront/public/${storefrontId}/checkout/payment-intent`, payload);
  }
}
