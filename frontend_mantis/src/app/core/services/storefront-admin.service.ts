import { Injectable, inject } from '@angular/core';
import { HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';
import { shareReplay, tap } from 'rxjs/operators';

import { ApiService } from './api.service';

export interface StorefrontSocialLinks {
  facebook?: string | null;
  instagram?: string | null;
  twitter?: string | null;
  linkedin?: string | null;
}

export interface StorefrontPromoBanner {
  id: string;
  enabled?: boolean | null;
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
  enabled?: boolean | null;
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
  enabled?: boolean | null;
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
  enabled?: boolean | null;
  title: string;
  description?: string | null;
  image?: string | null;
}

export interface StorefrontHomeTestimonialItem {
  id: string;
  enabled?: boolean | null;
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
  content_version?: number;
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

export interface StorefrontThemeSection {
  id: string;
  type: string;
  enabled: boolean;
  settings: Record<string, unknown>;
  blocks: Record<string, unknown>[];
}

export interface StorefrontThemeDocument {
  id: string;
  storefront_id: string;
  company_id: string;
  template_key: string;
  draft_document: Record<string, unknown>;
  published_document: Record<string, unknown>;
  draft_version: number;
  published_version: number;
  published_at?: string | null;
  preview_url?: string | null;
}

export type StorefrontThemeTemplateKey = 'home' | 'product' | 'collection' | 'search' | 'cart' | 'pages';

export interface StorefrontThemePreviewSession {
  token: string;
  expires_at: string;
  preview_url: string;
  template_key: string;
}

export interface StorefrontMediaAsset {
  id: string;
  storefront_id: string;
  company_id: string;
  url: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  width?: number | null;
  height?: number | null;
  alt_text?: string | null;
  created_at: string;
}

export interface StorefrontThemeComponent {
  type: string;
  label: string;
  description: string;
  icon?: string;
}

export interface StorefrontThemeRevision {
  id: string;
  storefront_id: string;
  template_key: string;
  version: number;
  document: Record<string, unknown>;
  operation: string;
  created_at: string;
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
  price_list_id?: string | null;
  fulfillment_warehouse_id?: string | null;
}

export interface StorefrontDomain {
  id: string;
  storefront_id: string;
  domain: string;
  is_primary: boolean;
  is_verified: boolean;
  verification_token?: string | null;
  verification_record?: string | null;
  verification_value?: string | null;
  verified_at?: string | null;
  provisioning_status: string;
  provisioning_attempts: number;
  provisioning_error?: string | null;
  provisioning_next_attempt_at?: string | null;
  provisioning_last_attempt_at?: string | null;
  provisioned_at?: string | null;
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
  collection_mode: 'manual' | 'automated';
  rule_match: 'all' | 'any';
}

export type CollectionRuleField =
  | 'title'
  | 'description'
  | 'vendor'
  | 'brand'
  | 'product_type'
  | 'category'
  | 'tag'
  | 'sku'
  | 'price'
  | 'inventory'
  | 'status'
  | 'variant_title';

export type CollectionRuleOperator =
  | 'equals'
  | 'not_equals'
  | 'contains'
  | 'not_contains'
  | 'starts_with'
  | 'ends_with'
  | 'greater_than'
  | 'less_than'
  | 'greater_or_equal'
  | 'less_or_equal';

export interface StoreCollectionRule {
  id?: string;
  collection_id?: string;
  field: CollectionRuleField;
  operator: CollectionRuleOperator;
  value: string;
  position?: number;
}

export interface CollectionRulesApplyResponse {
  matched_count: number;
  added_count: number;
  removed_count: number;
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
  seo_title?: string | null;
  seo_description?: string | null;
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

export interface StorefrontShippingDestination {
  id: string;
  storefront_id: string;
  country_code: string;
  state_code?: string | null;
  state_name: string;
  city_code?: string | null;
  city_name?: string | null;
  destination_type: string;
  sort_order: number;
  is_active: boolean;
}

export interface StorefrontShippingMethod {
  id: string;
  storefront_id: string;
  code: string;
  name: string;
  description?: string | null;
  method_type: string;
  is_enabled: boolean;
  sort_order: number;
  estimate_min_days?: number | null;
  estimate_max_days?: number | null;
  is_active: boolean;
}

export interface StorefrontShippingRule {
  id: string;
  storefront_id: string;
  method_id: string;
  name: string;
  priority: number;
  is_enabled: boolean;
  destination_type: string;
  country_code?: string | null;
  state_code?: string | null;
  state_name?: string | null;
  city_code?: string | null;
  city_name?: string | null;
  payment_provider?: string | null;
  min_subtotal?: number | null;
  max_subtotal?: number | null;
  min_weight?: number | null;
  max_weight?: number | null;
  charge_type: string;
  amount: number;
  rate_per_kg: number;
  estimate_min_days?: number | null;
  estimate_max_days?: number | null;
  is_active: boolean;
}

export interface StorefrontShippingConfig {
  destinations: StorefrontShippingDestination[];
  methods: StorefrontShippingMethod[];
  rules: StorefrontShippingRule[];
}

export interface StorefrontShippingDestinationImportResult {
  success: boolean;
  count: number;
  created: number;
  updated: number;
  skipped: number;
  error_count: number;
  errors: string[];
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
  address?: PublicCheckoutAddress | null;
  payment_provider?: string | null;
  shipping_method_id?: string | null;
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
  total_weight?: number;
  shipping_method_id?: string | null;
  shipping_method_name?: string | null;
  shipping_rule_name?: string | null;
  shipping_quote_required?: boolean;
  shipping_requires_destination?: boolean;
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
  state_code?: string | null;
  city_code?: string | null;
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
  shipping_method_id?: string | null;
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
  shipping_method_id?: string | null;
  shipping_method_name?: string | null;
  shipping_quote_required?: boolean;
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
  private storefrontsRequest$: Observable<Storefront[]> | null = null;
  private collectionsRequests = new Map<string, Observable<StoreCollection[]>>();
  private navigationRequests = new Map<string, Observable<StoreNavigationItem[]>>();

  getStorefronts(): Observable<Storefront[]> {
    if (!this.storefrontsRequest$) {
      this.storefrontsRequest$ = this.api.get<Storefront[]>('/storefront/').pipe(
        shareReplay({ bufferSize: 1, refCount: false }),
      );
    }
    return this.storefrontsRequest$;
  }

  getReadiness(storefrontId: string): Observable<StorefrontReadiness> {
    return this.api.get<StorefrontReadiness>(`/storefront/${storefrontId}/readiness`);
  }

  getThemeDocument(storefrontId: string, templateKey = 'home'): Observable<StorefrontThemeDocument> {
    return this.api.get<StorefrontThemeDocument>(`/storefront/${storefrontId}/theme/${templateKey}`);
  }

  getThemeComponents(storefrontId: string, templateKey: StorefrontThemeTemplateKey = 'home'): Observable<{ template_key: string; components: StorefrontThemeComponent[] }> {
    return this.api.get<{ template_key: string; components: StorefrontThemeComponent[] }>(`/storefront/${storefrontId}/theme/components`, { template_key: templateKey });
  }

  createThemePreviewSession(storefrontId: string, templateKey = 'home'): Observable<StorefrontThemePreviewSession> {
    return this.api.post<StorefrontThemePreviewSession>(`/storefront/${storefrontId}/theme/${templateKey}/preview-session`, {});
  }

  getMediaAssets(storefrontId: string): Observable<StorefrontMediaAsset[]> {
    return this.api.get<StorefrontMediaAsset[]>(`/storefront/${storefrontId}/media`);
  }

  getMediaAssetBlob(storefrontId: string, assetId: string): Observable<Blob> {
    return this.api.getBlob(`/storefront/${storefrontId}/media/${assetId}`);
  }

  uploadMediaAsset(storefrontId: string, file: File): Observable<StorefrontMediaAsset> {
    const formData = new FormData();
    formData.append('file', file);
    return this.api.post<StorefrontMediaAsset>(`/storefront/${storefrontId}/media`, formData);
  }

  uploadMediaAssetWithProgress(storefrontId: string, file: File): Observable<HttpEvent<StorefrontMediaAsset>> {
    const formData = new FormData();
    formData.append('file', file);
    return this.api.postWithProgress<StorefrontMediaAsset>(`/storefront/${storefrontId}/media`, formData);
  }

  saveThemeDraft(
    storefrontId: string,
    document: Record<string, unknown>,
    expectedDraftVersion: number,
    templateKey = 'home'
  ): Observable<StorefrontThemeDocument> {
    return this.api.put<StorefrontThemeDocument>(`/storefront/${storefrontId}/theme/${templateKey}/draft`, {
      document,
      expected_draft_version: expectedDraftVersion
    });
  }

  publishTheme(
    storefrontId: string,
    expectedDraftVersion?: number,
    templateKey = 'home'
  ): Observable<StorefrontThemeDocument> {
    return this.api.post<StorefrontThemeDocument>(`/storefront/${storefrontId}/theme/${templateKey}/publish`, {
      ...(expectedDraftVersion === undefined ? {} : { expected_draft_version: expectedDraftVersion })
    });
  }

  getThemeRevisions(storefrontId: string, templateKey = 'home'): Observable<StorefrontThemeRevision[]> {
    return this.api.get<StorefrontThemeRevision[]>(`/storefront/${storefrontId}/theme/${templateKey}/revisions`);
  }

  restoreThemeRevision(
    storefrontId: string,
    revisionId: string,
    expectedDraftVersion?: number,
    templateKey = 'home'
  ): Observable<StorefrontThemeDocument> {
    return this.api.post<StorefrontThemeDocument>(`/storefront/${storefrontId}/theme/${templateKey}/restore/${revisionId}`, {
      ...(expectedDraftVersion === undefined ? {} : { expected_draft_version: expectedDraftVersion })
    });
  }

  createStorefront(payload: Partial<Storefront>): Observable<Storefront> {
    return this.api.post<Storefront>('/storefront/', payload).pipe(
      tap(() => this.storefrontsRequest$ = null),
    );
  }

  updateStorefront(id: string, payload: Partial<Storefront>): Observable<Storefront> {
    return this.api.put<Storefront>(`/storefront/${id}`, payload).pipe(
      tap(() => this.storefrontsRequest$ = null),
    );
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

  verifyDomain(id: string): Observable<StorefrontDomain> {
    return this.api.post<StorefrontDomain>(`/storefront/domains/${id}/verify`, {});
  }

  provisionDomain(id: string): Observable<StorefrontDomain> {
    return this.api.post<StorefrontDomain>(`/storefront/domains/${id}/provision`, {});
  }

  deleteDomain(id: string): Observable<{ ok: boolean }> {
    return this.api.delete<{ ok: boolean }>(`/storefront/domains/${id}`);
  }

  getCollections(storefrontId?: string): Observable<StoreCollection[]> {
    const cacheKey = storefrontId || '__all__';
    let request$ = this.collectionsRequests.get(cacheKey);
    if (!request$) {
      request$ = this.api
        .get<StoreCollection[]>('/storefront/collections', storefrontId ? { storefront_id: storefrontId } : {})
        .pipe(shareReplay({ bufferSize: 1, refCount: false }));
      this.collectionsRequests.set(cacheKey, request$);
    }
    return request$;
  }

  createCollection(payload: Partial<StoreCollection>): Observable<StoreCollection> {
    return this.api.post<StoreCollection>('/storefront/collections', payload).pipe(
      tap(() => this.collectionsRequests.clear()),
    );
  }

  updateCollection(id: string, payload: Partial<StoreCollection>): Observable<StoreCollection> {
    return this.api.put<StoreCollection>(`/storefront/collections/${id}`, payload).pipe(
      tap(() => this.collectionsRequests.clear()),
    );
  }

  getCollectionRules(collectionId: string): Observable<StoreCollectionRule[]> {
    return this.api.get<StoreCollectionRule[]>(`/storefront/collections/${collectionId}/rules`);
  }

  updateCollectionRules(
    collectionId: string,
    payload: { collection_mode: 'manual' | 'automated'; rule_match: 'all' | 'any'; rules: StoreCollectionRule[] }
  ): Observable<CollectionRulesApplyResponse> {
    return this.api.put<CollectionRulesApplyResponse>(`/storefront/collections/${collectionId}/rules`, payload).pipe(
      tap(() => this.collectionsRequests.clear()),
    );
  }

  applyCollectionRules(collectionId: string): Observable<CollectionRulesApplyResponse> {
    return this.api.post<CollectionRulesApplyResponse>(`/storefront/collections/${collectionId}/rules/apply`, {}).pipe(
      tap(() => this.collectionsRequests.clear()),
    );
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
    return this.api.post<StoreCollectionProduct>(`/storefront/collections/${collectionId}/products`, payload).pipe(
      tap(() => this.collectionsRequests.clear()),
    );
  }

  getCollectionProducts(collectionId: string): Observable<StoreCollectionProduct[]> {
    return this.api.get<StoreCollectionProduct[]>(`/storefront/collections/${collectionId}/products`);
  }

  removeProductFromCollection(collectionId: string, publishedProductId: string): Observable<{ ok: boolean }> {
    return this.api.delete<{ ok: boolean }>(`/storefront/collections/${collectionId}/products/${publishedProductId}`).pipe(
      tap(() => this.collectionsRequests.clear()),
    );
  }

  getNavigation(storefrontId?: string): Observable<StoreNavigationItem[]> {
    const cacheKey = storefrontId || '__all__';
    let request$ = this.navigationRequests.get(cacheKey);
    if (!request$) {
      request$ = this.api
        .get<StoreNavigationItem[]>('/storefront/navigation', storefrontId ? { storefront_id: storefrontId } : {})
        .pipe(shareReplay({ bufferSize: 1, refCount: false }));
      this.navigationRequests.set(cacheKey, request$);
    }
    return request$;
  }

  createNavigationItem(payload: Partial<StoreNavigationItem>): Observable<StoreNavigationItem> {
    return this.api.post<StoreNavigationItem>('/storefront/navigation', payload).pipe(
      tap(() => this.navigationRequests.clear()),
    );
  }

  updateNavigationItem(id: string, payload: Partial<StoreNavigationItem>): Observable<StoreNavigationItem> {
    return this.api.put<StoreNavigationItem>(`/storefront/navigation/${id}`, payload).pipe(
      tap(() => this.navigationRequests.clear()),
    );
  }

  deleteNavigationItem(id: string): Observable<{ ok: boolean }> {
    return this.api.delete<{ ok: boolean }>(`/storefront/navigation/${id}`).pipe(
      tap(() => this.navigationRequests.clear()),
    );
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

  getShippingConfig(storefrontId: string): Observable<StorefrontShippingConfig> {
    return this.api.get<StorefrontShippingConfig>('/storefront/shipping/config', { storefront_id: storefrontId });
  }

  createShippingDestination(payload: Partial<StorefrontShippingDestination>): Observable<StorefrontShippingDestination> {
    return this.api.post<StorefrontShippingDestination>('/storefront/shipping/destinations', payload);
  }

  importShippingDestinations(storefrontId: string, file: File): Observable<StorefrontShippingDestinationImportResult> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    return this.api.post<StorefrontShippingDestinationImportResult>(`/storefront/shipping/destinations/import?storefront_id=${encodeURIComponent(storefrontId)}`, formData);
  }

  updateShippingDestination(id: string, payload: Partial<StorefrontShippingDestination>): Observable<StorefrontShippingDestination> {
    return this.api.put<StorefrontShippingDestination>(`/storefront/shipping/destinations/${id}`, payload);
  }

  deleteShippingDestination(id: string): Observable<{ ok: boolean }> {
    return this.api.delete<{ ok: boolean }>(`/storefront/shipping/destinations/${id}`);
  }

  createShippingMethod(payload: Partial<StorefrontShippingMethod>): Observable<StorefrontShippingMethod> {
    return this.api.post<StorefrontShippingMethod>('/storefront/shipping/methods', payload);
  }

  updateShippingMethod(id: string, payload: Partial<StorefrontShippingMethod>): Observable<StorefrontShippingMethod> {
    return this.api.put<StorefrontShippingMethod>(`/storefront/shipping/methods/${id}`, payload);
  }

  deleteShippingMethod(id: string): Observable<{ ok: boolean }> {
    return this.api.delete<{ ok: boolean }>(`/storefront/shipping/methods/${id}`);
  }

  createShippingRule(payload: Partial<StorefrontShippingRule>): Observable<StorefrontShippingRule> {
    return this.api.post<StorefrontShippingRule>('/storefront/shipping/rules', payload);
  }

  updateShippingRule(id: string, payload: Partial<StorefrontShippingRule>): Observable<StorefrontShippingRule> {
    return this.api.put<StorefrontShippingRule>(`/storefront/shipping/rules/${id}`, payload);
  }

  deleteShippingRule(id: string): Observable<{ ok: boolean }> {
    return this.api.delete<{ ok: boolean }>(`/storefront/shipping/rules/${id}`);
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
