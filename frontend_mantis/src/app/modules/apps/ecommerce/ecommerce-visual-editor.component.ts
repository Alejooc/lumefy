import { CommonModule } from '@angular/common';
import { HttpEventType } from '@angular/common/http';
import { CdkDragDrop, DragDropModule, moveItemInArray } from '@angular/cdk/drag-drop';
import { Component, ElementRef, OnDestroy, OnInit, ViewChild, inject } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import {
  PublishedProduct,
  StoreCollection,
  Storefront,
  StorefrontAdminService,
  StorefrontMediaAsset,
  StorefrontHomeCountdownSettings,
 StorefrontHomeHeroPromo,
 StorefrontHomeHeroSlide,
  StorefrontHomeFeatureItem,
 StorefrontHomeNewsletterSettings,
 StorefrontHomeSectionCopy,
 StorefrontHomeSettings,
 StorefrontHomeTestimonialsSettings,
  StorefrontPromoBanner,
  StorefrontThemeComponent,
  StorefrontThemeDocument,
  StorefrontThemePreviewSession,
  StorefrontThemeRevision,
  StorefrontThemeSection
} from 'src/app/core/services/storefront-admin.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

type VisualSectionType =
  | 'hero'
  | 'categories'
  | 'new_arrivals'
  | 'promo_banners'
  | 'best_sellers'
  | 'countdown'
  | 'testimonials'
  | 'newsletter'
  | 'closing_cta'
  | 'custom_embed';

type VisualSectionSpacing = 'theme' | 'compact' | 'balanced' | 'airy';
type VisualSidebarMode = 'sections' | 'settings' | 'section' | 'add';
type VisualGlobalArea = 'announcement' | 'header' | 'footer';
type CustomEmbedMode = 'html' | 'iframe';
type CustomEmbedMaxWidth = 'narrow' | 'content' | 'wide' | 'full';
type CustomEmbedAlignment = 'left' | 'center' | 'right';
type SectionDesignWidth = 'theme' | 'narrow' | 'wide' | 'full';
type SectionDesignBackground = 'theme' | 'surface' | 'primary' | 'accent' | 'custom';
type SectionDesignText = 'theme' | 'inverse' | 'custom';
type SectionDesignShadow = 'none' | 'soft' | 'lifted';

type VisualMediaTarget =
 | 'branding_logo'
 | 'branding_mobile_logo'
 | 'branding_favicon'
 | 'hero'
 | 'hero_promo'
 | `hero_slide:${number}`
  | `feature:${number}`
 | 'countdown_background'
  | 'countdown_product'
  | 'newsletter_background'
  | `banner:${number}`
  | `testimonial:${number}`;

interface VisualSection extends StorefrontThemeSection {
  type: VisualSectionType;
}

interface VisualHeroSlide extends StorefrontHomeHeroSlide {
  title: string;
  description: string;
  enabled: boolean;
  cta_href: string;
  image: string;
  button_label: string;
  text_color: string;
  button_color: string;
}

interface VisualHeroPromo extends StorefrontHomeHeroPromo {
  title: string;
  offer_label: string;
  href: string;
  price_label: string;
  compare_price_label: string;
  image: string;
  background_color: string;
  background_image_url: string;
}

interface VisualSectionCopy extends StorefrontHomeSectionCopy {
  eyebrow: string;
  title: string;
  cta_label: string;
  cta_href: string;
}

interface VisualCountdown extends StorefrontHomeCountdownSettings {
  enabled: boolean;
  eyebrow: string;
  title: string;
  description: string;
  cta_label: string;
  cta_href: string;
  deadline: string;
  background_color: string;
  background_image_url: string;
  product_image_url: string;
}

interface VisualNewsletter extends StorefrontHomeNewsletterSettings {
  enabled: boolean;
  title: string;
  description: string;
  placeholder: string;
  button_label: string;
  background_image_url: string;
}

interface VisualTestimonials extends StorefrontHomeTestimonialsSettings {
  enabled: boolean;
  eyebrow: string;
  title: string;
}

interface VisualHomeSettings extends StorefrontHomeSettings {
  hero_slides: VisualHeroSlide[];
  hero_promos: VisualHeroPromo[];
  category_section: VisualSectionCopy;
  new_arrivals_section: VisualSectionCopy;
  best_sellers_section: VisualSectionCopy;
  countdown: VisualCountdown;
  newsletter: VisualNewsletter;
  testimonials: VisualTestimonials;
}

interface VisualAnnouncementSettings {
  enabled: boolean;
  text: string;
  href: string;
  background_color: string;
  text_color: string;
}

interface VisualThemeBrandingSettings {
  logo_url: string;
  mobile_logo_url: string;
  logo_alt: string;
  favicon_url: string;
}

interface VisualThemeStyleSettings {
  primary_color: string;
  accent_color: string;
  page_background_color: string;
  body_text_color: string;
  heading_text_color: string;
  body_font: 'euclid' | 'editorial' | 'humanist';
  heading_font: 'euclid' | 'editorial' | 'humanist';
  content_width: number;
  corner_radius: 'sharp' | 'soft' | 'round';
  navigation_style: 'standard' | 'minimal';
  navigation_variant: 'underline' | 'pill' | 'plain';
}

interface VisualThemeHeaderSettings {
  support_label: string;
  search_placeholder: string;
  account_heading: string;
  guest_account_label: string;
  sign_out_label: string;
  cart_heading: string;
  recently_viewed_label: string;
  wishlist_label: string;
  background_color: string;
  text_color: string;
}

interface VisualThemeFooterSettings {
  footer_text: string;
  help_title: string;
  account_title: string;
  quick_links_title: string;
  payment_title: string;
  support_phone: string;
  support_email: string;
  support_address: string;
  show_social_links: boolean;
  social_links: {
    facebook: string;
    instagram: string;
    twitter: string;
    linkedin: string;
  };
  background_color: string;
  text_color: string;
  bottom_background_color: string;
}

interface VisualThemeSettings {
  branding: VisualThemeBrandingSettings;
  styles: VisualThemeStyleSettings;
  section_spacing: VisualSectionSpacing;
  announcement: VisualAnnouncementSettings;
  header: VisualThemeHeaderSettings;
  footer: VisualThemeFooterSettings;
  [key: string]: unknown;
}

interface VisualThemeDocument {
  schema_version: number;
  template: 'home';
  settings: VisualThemeSettings;
  legacy_home: VisualHomeSettings;
  sections: VisualSection[];
}

interface VisualLinkOption {
  label: string;
  href: string;
}

@Component({
  selector: 'app-ecommerce-visual-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, DragDropModule, RouterLink],
  templateUrl: './ecommerce-visual-editor.component.html',
  styleUrls: ['./ecommerce-visual-editor.component.scss']
})
export class EcommerceVisualEditorComponent implements OnInit, OnDestroy {
  private storefrontService = inject(StorefrontAdminService);
  private context = inject(EcommerceContextService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);
  private sanitizer = inject(DomSanitizer);

  @ViewChild('previewFrame') previewFrame?: ElementRef<HTMLIFrameElement>;

  loading = false;
  saving = false;
  publishing = false;
  loadingHistory = false;
  dirty = false;
  showHistory = false;
  sidebarOpen = true;
  sidebarMode: VisualSidebarMode = 'sections';
  pendingInsertAfterId: string | null = null;
  selectionMode = true;
  previewReady = false;
  storefronts: Storefront[] = [];
  collections: StoreCollection[] = [];
  publishedProducts: PublishedProduct[] = [];
  mediaAssets: StorefrontMediaAsset[] = [];
  selectedStorefrontId = '';
  storefront: Storefront | null = null;
  theme: StorefrontThemeDocument | null = null;
  document: VisualThemeDocument = this.createDocument();
  components: StorefrontThemeComponent[] = [];
  revisions: StorefrontThemeRevision[] = [];
  selectedSectionId = '';
  selectedGlobalArea: VisualGlobalArea | null = null;
  previewUrl = '';
  safePreviewUrl: SafeResourceUrl | null = null;
  previewViewport: 'desktop' | 'tablet' | 'mobile' = 'desktop';
  errorMessage = '';
  uploadingMedia = false;
  mediaUploadProgress = 0;
  mediaTarget: VisualMediaTarget = 'hero';
  mediaPickerOpen = false;
  mediaPickerSearch = '';
  mediaPickerTarget: VisualMediaTarget | null = null;
  selectedHeroSlideIndex = 0;
  readonly internalLinkOptions: VisualLinkOption[] = [
    { label: 'Inicio', href: '/' },
    { label: 'Todos los productos', href: '/products' },
    { label: 'Tienda con filtros', href: '/shop-with-sidebar' },
    { label: 'Contacto', href: '/contact' },
    { label: 'Carrito', href: '/cart' },
    { label: 'Mi cuenta', href: '/account' },
    { label: 'Favoritos', href: '/wishlist' },
  ];

  private readonly maxHistoryEntries = 50;
  private undoStack: Record<string, unknown>[] = [];
  private redoStack: Record<string, unknown>[] = [];
  private historyCurrent = '';
  private previewRequestId = 0;
  private previewOrigin = '';
  private lastAppliedStorefrontId = '';
  private mediaPreviewUrls = new Map<string, string>();
  private mediaPreviewRequests = new Set<string>();
  private readonly onWindowMessage = (event: MessageEvent): void => {
    if (event.source !== this.previewFrame?.nativeElement.contentWindow) return;
    if (!this.previewOrigin || event.origin !== this.previewOrigin) return;
    if (event.data?.type === 'lumefy:preview:select' && (event.data.area === 'header' || event.data.area === 'footer')) {
      this.selectedSectionId = '';
      this.showSettings(event.data.area);
      return;
    }
    if (event.data?.type === 'lumefy:preview:select' && typeof event.data.sectionId === 'string') {
      if (this.document.sections.some((section) => section.id === event.data.sectionId)) {
        this.selectedSectionId = event.data.sectionId;
        this.selectedGlobalArea = null;
        this.sidebarOpen = true;
        this.sidebarMode = 'section';
        this.pendingInsertAfterId = null;
        this.ensureMediaTarget();
        this.pushPreview();
      }
      return;
    }
    if (event.data?.type === 'lumefy:preview:insert') {
      const afterSectionId = typeof event.data.afterSectionId === 'string'
        ? event.data.afterSectionId
        : null;
      if (afterSectionId && !this.document.sections.some((section) => section.id === afterSectionId)) return;
      this.openAddSections(afterSectionId);
      return;
    }
    if (event.data?.type === 'lumefy:preview:ready') {
      this.previewReady = true;
      this.pushPreview();
    }
  };
  private readonly onBeforeUnload = (event: BeforeUnloadEvent): void => {
    if (!this.dirty) return;
    event.preventDefault();
    event.returnValue = '';
  };

  ngOnInit(): void {
    window.addEventListener('message', this.onWindowMessage);
    window.addEventListener('beforeunload', this.onBeforeUnload);
    if (!this.permissions.hasPermission('manage_company')) {
      this.swal.error('Sin permiso', 'No puedes administrar el diseño del ecommerce.');
      return;
    }
    this.loadStorefronts();
  }

  ngOnDestroy(): void {
    window.removeEventListener('message', this.onWindowMessage);
    window.removeEventListener('beforeunload', this.onBeforeUnload);
    this.clearMediaPreviewUrls();
  }

  get selectedSection(): VisualSection | null {
    return this.document.sections.find((section) => section.id === this.selectedSectionId) || null;
  }

  get globalSettings(): VisualThemeSettings {
    return this.document.settings;
  }

  get selectedComponent(): StorefrontThemeComponent | null {
    const type = this.selectedSection?.type;
    return this.components.find((component) => component.type === type) || null;
  }

  get selectedSectionSpacing(): VisualSectionSpacing {
    const value = this.selectedSection?.settings?.['section_spacing'];
    return value === 'compact' || value === 'balanced' || value === 'airy' ? value : 'theme';
  }

  get sectionDesignWidth(): SectionDesignWidth {
    const value = this.sectionDesignValue('width');
    return value === 'narrow' || value === 'wide' || value === 'full' ? value : 'theme';
  }

  get sectionDesignBackground(): SectionDesignBackground {
    const value = this.sectionDesignValue('background');
    return value === 'surface' || value === 'primary' || value === 'accent' || value === 'custom' ? value : 'theme';
  }

  get sectionDesignBackgroundColor(): string {
    const value = this.sectionDesignValue('background_color');
    return typeof value === 'string' && /^#[0-9a-f]{6}$/i.test(value) ? value : '#FFFFFF';
  }

  get sectionDesignText(): SectionDesignText {
    const value = this.sectionDesignValue('text');
    return value === 'inverse' || value === 'custom' ? value : 'theme';
  }

  get sectionDesignTextColor(): string {
    const value = this.sectionDesignValue('text_color');
    return typeof value === 'string' && /^#[0-9a-f]{6}$/i.test(value) ? value : '#1C274C';
  }

  get sectionDesignRadius(): number {
    const value = this.sectionDesignValue('radius');
    const numeric = Number(value);
    return Number.isFinite(numeric) ? Math.max(0, Math.min(64, numeric)) : 16;
  }

  get sectionDesignRadiusUsesTheme(): boolean {
    const value = this.sectionDesignValue('radius');
    return value === undefined || value === null || value === 'theme';
  }

  get sectionDesignShadow(): SectionDesignShadow {
    const value = this.sectionDesignValue('shadow');
    return value === 'soft' || value === 'lifted' ? value : 'none';
  }

  get sectionDesignHideMobile(): boolean {
    return this.sectionDesignValue('hide_mobile') === true;
  }

  setSectionDesignWidth(value: string): void {
    this.updateSectionDesign('width', value === 'narrow' || value === 'wide' || value === 'full' ? value : 'theme');
  }

  setSectionDesignBackground(value: string): void {
    this.updateSectionDesign('background', value === 'surface' || value === 'primary' || value === 'accent' || value === 'custom' ? value : 'theme');
  }

  setSectionDesignBackgroundColor(value: string): void {
    this.updateSectionDesign('background_color', /^#[0-9a-f]{6}$/i.test(value) ? value.toUpperCase() : '#FFFFFF');
  }

  setSectionDesignText(value: string): void {
    this.updateSectionDesign('text', value === 'inverse' || value === 'custom' ? value : 'theme');
  }

  setSectionDesignTextColor(value: string): void {
    this.updateSectionDesign('text_color', /^#[0-9a-f]{6}$/i.test(value) ? value.toUpperCase() : '#1C274C');
  }

  setSectionDesignRadius(value: string | number): void {
    const numeric = Number(value);
    this.updateSectionDesign('radius', Number.isFinite(numeric) ? Math.max(0, Math.min(64, numeric)) : 16);
  }

  toggleSectionDesignRadius(): void {
    this.updateSectionDesign('radius', this.sectionDesignRadiusUsesTheme ? this.sectionDesignRadius : 'theme');
  }

  setSectionDesignShadow(value: string): void {
    this.updateSectionDesign('shadow', value === 'soft' || value === 'lifted' ? value : 'none');
  }

  setSectionDesignHideMobile(value: boolean): void {
    this.updateSectionDesign('hide_mobile', value);
  }

  toggleSectionDesignHideMobile(event: Event): void {
    this.setSectionDesignHideMobile((event.target as HTMLInputElement).checked);
  }

  resetSectionDesign(): void {
    if (!this.selectedSection) return;
    delete this.selectedSection.settings['design'];
    this.markDirty();
  }

  get customEmbedMode(): CustomEmbedMode {
    return this.selectedSection?.settings?.['mode'] === 'iframe' ? 'iframe' : 'html';
  }

  get customEmbedContent(): string {
    return typeof this.selectedSection?.settings?.['content'] === 'string'
      ? this.selectedSection.settings['content'] as string
      : '';
  }

  get customEmbedIframeUrl(): string {
    return typeof this.selectedSection?.settings?.['iframe_url'] === 'string'
      ? this.selectedSection.settings['iframe_url'] as string
      : '';
  }

  get customEmbedIframeTitle(): string {
    return typeof this.selectedSection?.settings?.['iframe_title'] === 'string'
      ? this.selectedSection.settings['iframe_title'] as string
      : 'Contenido integrado';
  }

  get customEmbedHeight(): number {
    const value = Number(this.selectedSection?.settings?.['iframe_height']);
    return Number.isFinite(value) ? Math.max(240, Math.min(900, value)) : 420;
  }

  get customEmbedMaxWidth(): CustomEmbedMaxWidth {
    const value = this.selectedSection?.settings?.['max_width'];
    return value === 'narrow' || value === 'wide' || value === 'full' ? value : 'content';
  }

  get customEmbedAlignment(): CustomEmbedAlignment {
    const value = this.selectedSection?.settings?.['alignment'];
    return value === 'left' || value === 'right' ? value : 'center';
  }

  setCustomEmbedMode(value: string): void {
    if (!this.selectedSection || this.selectedSection.type !== 'custom_embed') return;
    this.selectedSection.settings['mode'] = value === 'iframe' ? 'iframe' : 'html';
    this.markDirty();
  }

  setCustomEmbedContent(value: string): void {
    if (!this.selectedSection || this.selectedSection.type !== 'custom_embed') return;
    this.selectedSection.settings['content'] = value;
    this.markDirty();
  }

  setCustomEmbedIframeUrl(value: string): void {
    if (!this.selectedSection || this.selectedSection.type !== 'custom_embed') return;
    this.selectedSection.settings['iframe_url'] = value;
    this.markDirty();
  }

  setCustomEmbedIframeTitle(value: string): void {
    if (!this.selectedSection || this.selectedSection.type !== 'custom_embed') return;
    this.selectedSection.settings['iframe_title'] = value;
    this.markDirty();
  }

  setCustomEmbedHeight(value: string | number): void {
    if (!this.selectedSection || this.selectedSection.type !== 'custom_embed') return;
    const height = Number(value);
    this.selectedSection.settings['iframe_height'] = Number.isFinite(height)
      ? Math.max(240, Math.min(900, height))
      : 420;
    this.markDirty();
  }

  setCustomEmbedMaxWidth(value: string): void {
    if (!this.selectedSection || this.selectedSection.type !== 'custom_embed') return;
    this.selectedSection.settings['max_width'] = value === 'narrow' || value === 'wide' || value === 'full' ? value : 'content';
    this.markDirty();
  }

  setCustomEmbedAlignment(value: string): void {
    if (!this.selectedSection || this.selectedSection.type !== 'custom_embed') return;
    this.selectedSection.settings['alignment'] = value === 'left' || value === 'right' ? value : 'center';
    this.markDirty();
  }

  setSectionSpacing(value: string): void {
    if (!this.selectedSection) return;
    if (value === 'compact' || value === 'balanced' || value === 'airy') {
      this.selectedSection.settings['section_spacing'] = value;
    } else {
      delete this.selectedSection.settings['section_spacing'];
    }
    this.markDirty();
  }

  private sectionDesignValue(key: string): unknown {
    return this.asObject(this.selectedSection?.settings?.['design'])[key];
  }

  private updateSectionDesign(key: string, value: unknown): void {
    if (!this.selectedSection) return;
    this.selectedSection.settings['design'] = {
      ...this.asObject(this.selectedSection.settings['design']),
      [key]: value
    };
    this.markDirty();
  }

  componentFor(section: VisualSection): StorefrontThemeComponent | null {
    return this.components.find((component) => component.type === section.type) || null;
  }

  sectionLabel(section: VisualSection): string {
    return this.componentFor(section)?.label || section.type.replace(/_/g, ' ');
  }

  componentIcon(type: string): string {
    const icons: Record<VisualSectionType, string> = {
      hero: 'ti ti-carousel-horizontal',
      categories: 'ti ti-category',
      new_arrivals: 'ti ti-sparkles',
      promo_banners: 'ti ti-photo',
      best_sellers: 'ti ti-trending-up',
      countdown: 'ti ti-clock',
      testimonials: 'ti ti-message-star',
      newsletter: 'ti ti-mail',
      closing_cta: 'ti ti-click',
      custom_embed: 'ti ti-code'
    };
    return this.isSectionType(type) ? icons[type] : 'ti ti-layout';
  }

 get canAddSection(): boolean {
   return this.document.sections.length < 20;
 }

 get canAddHeroSlide(): boolean {
   return this.heroSlides.length < 6;
 }

  get canAddFeature(): boolean {
    return this.features.length < 4;
  }

  get canAddPromoBanner(): boolean {
    return this.promoBanners.length < 3;
  }

  get canAddTestimonial(): boolean {
    return (this.testimonials.items || []).length < 12;
  }

  get canUndo(): boolean {
    return this.undoStack.length > 0;
  }

  get canRedo(): boolean {
    return this.redoStack.length > 0;
  }

  get selectedCollectionIds(): string[] {
    return this.selectedReferenceIds('collection_ids');
  }

  get selectedProductIds(): string[] {
    return this.selectedReferenceIds('product_ids');
  }

  get mediaTargetOptions(): Array<{ value: VisualMediaTarget; label: string }> {
    const section = this.selectedSection;
    if (!section) return [];
    if (section.type === 'hero') {
      return [
       ...this.heroSlides.map((_, index) => ({
         value: `hero_slide:${index}` as VisualMediaTarget,
         label: `Imagen de la diapositiva ${index + 1}`,
       })),
        ...this.features.map((_, index) => ({
          value: `feature:${index}` as VisualMediaTarget,
          label: `Icono del beneficio ${index + 1}`,
        })),
       { value: 'hero_promo', label: 'Tarjeta promocional del hero' },
      ];
    }
    if (section.type === 'promo_banners') {
      return this.promoBanners.map((_, index) => ({
        value: `banner:${index}` as VisualMediaTarget,
        label: `Imagen del banner ${index + 1}`,
      }));
    }
    if (section.type === 'countdown') {
      return [
        { value: 'countdown_background', label: 'Fondo de la cuenta regresiva' },
        { value: 'countdown_product', label: 'Producto de la cuenta regresiva' },
      ];
    }
    if (section.type === 'newsletter') {
      return [{ value: 'newsletter_background', label: 'Fondo del newsletter' }];
    }
    if (section.type === 'testimonials') {
      return (this.testimonials.items || []).map((_, index) => ({
        value: `testimonial:${index}` as VisualMediaTarget,
        label: `Foto del testimonio ${index + 1}`,
      }));
    }
    return [];
  }

  get showMediaLibrary(): boolean {
    return this.mediaTargetOptions.length > 0;
  }

  get filteredMediaAssets(): StorefrontMediaAsset[] {
    const query = this.mediaPickerSearch.trim().toLowerCase();
    if (!query) return this.mediaAssets;
    return this.mediaAssets.filter((asset) =>
      [asset.original_filename, asset.alt_text || '', asset.content_type]
        .some((value) => value.toLowerCase().includes(query))
    );
  }

  mediaTargetLabel(target: VisualMediaTarget): string {
    const globalLabels: Partial<Record<VisualMediaTarget, string>> = {
      branding_logo: 'Logo principal',
      branding_mobile_logo: 'Logo para móvil',
      branding_favicon: 'Favicon',
    };
    return globalLabels[target]
      || this.mediaTargetOptions.find((option) => option.value === target)?.label
      || 'este espacio';
  }

  heroSlideMediaTarget(index: number): VisualMediaTarget {
    return `hero_slide:${index}`;
  }

  featureMediaTarget(index: number): VisualMediaTarget {
    return `feature:${index}`;
  }

  bannerMediaTarget(index: number): VisualMediaTarget {
    return `banner:${index}`;
  }

  testimonialMediaTarget(index: number): VisualMediaTarget {
    return `testimonial:${index}`;
  }

  openMediaPicker(target: VisualMediaTarget): void {
    if (!this.storefront) return;
    this.mediaTarget = target;
    this.mediaPickerTarget = target;
    this.mediaPickerSearch = '';
    this.mediaPickerOpen = true;
  }

  closeMediaPicker(): void {
    if (this.uploadingMedia) return;
    this.mediaPickerOpen = false;
    this.mediaPickerTarget = null;
    this.mediaPickerSearch = '';
  }

  selectMediaAsset(url: string): void {
    this.useMediaAsset(url);
    this.closeMediaPicker();
  }

  setCollectionSelection(value: unknown): void {
    this.setSelectedReferences('collection_ids', value);
  }

  setProductSelection(value: unknown): void {
    this.setSelectedReferences('product_ids', value);
  }

  uploadMedia(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file || !this.storefront) return;
    if (!file.type.startsWith('image/')) {
      this.errorMessage = 'Selecciona una imagen JPG, PNG, WebP o GIF.';
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      this.errorMessage = 'La imagen no puede superar los 10 MB.';
      return;
    }

    this.uploadingMedia = true;
    this.mediaUploadProgress = 0;
    this.errorMessage = '';
    const storefrontId = this.storefront.id;
    this.storefrontService.uploadMediaAssetWithProgress(storefrontId, file).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress) {
          this.mediaUploadProgress = event.total
            ? Math.round((event.loaded / event.total) * 100)
            : 0;
        } else if (event.type === HttpEventType.Response && event.body) {
          const asset = event.body;
          if (this.storefront?.id === storefrontId) {
            this.mediaAssets = [asset, ...this.mediaAssets.filter((item) => item.id !== asset.id)];
            this.loadMediaPreview(asset, storefrontId);
            this.useMediaAsset(asset.url);
          }
          this.uploadingMedia = false;
          if (this.mediaPickerOpen) this.closeMediaPicker();
        }
      },
      error: (err) => {
        this.uploadingMedia = false;
        this.mediaUploadProgress = 0;
        this.errorMessage = err?.error?.detail || 'No se pudo subir la imagen.';
      }
    });
  }

  useMediaAsset(url: string): void {
    if (this.mediaTarget === 'branding_logo') {
      this.globalSettings.branding.logo_url = url;
    } else if (this.mediaTarget === 'branding_mobile_logo') {
      this.globalSettings.branding.mobile_logo_url = url;
    } else if (this.mediaTarget === 'branding_favicon') {
      this.globalSettings.branding.favicon_url = url;
    } else if (this.mediaTarget === 'hero') {
      this.heroImage = url;
    } else if (this.mediaTarget.startsWith('hero_slide:')) {
      const index = Number(this.mediaTarget.slice('hero_slide:'.length));
      const slide = this.heroSlides[index];
      if (slide) slide.image = url;
   } else if (this.mediaTarget === 'hero_promo') {
     this.promoImage = url;
    } else if (this.mediaTarget.startsWith('feature:')) {
      const index = Number(this.mediaTarget.slice('feature:'.length));
      const feature = this.features[index];
      if (feature) feature.image = url;
   } else if (this.mediaTarget.startsWith('banner:')) {
      const index = Number(this.mediaTarget.slice('banner:'.length));
      const banner = this.promoBanners[index];
      if (banner) banner.image_url = url;
    } else if (this.mediaTarget === 'countdown_background') {
      this.countdown.background_image_url = url;
    } else if (this.mediaTarget === 'countdown_product') {
      this.countdown.product_image_url = url;
    } else if (this.mediaTarget === 'newsletter_background') {
      this.newsletter.background_image_url = url;
    } else if (this.mediaTarget.startsWith('testimonial:')) {
      const index = Number(this.mediaTarget.slice('testimonial:'.length));
      const testimonial = this.testimonials.items?.[index];
      if (testimonial) testimonial.author_image = url;
    } else {
      return;
    }
    this.markDirty();
  }

  mediaAssetPreviewUrl(asset: StorefrontMediaAsset): string {
    return this.mediaPreviewUrls.get(asset.id) || '';
  }

  private loadMediaPreviews(assets: StorefrontMediaAsset[], storefrontId: string): void {
    assets.forEach((asset) => this.loadMediaPreview(asset, storefrontId));
  }

  private loadMediaPreview(asset: StorefrontMediaAsset, storefrontId: string): void {
    if (this.mediaPreviewUrls.has(asset.id) || this.mediaPreviewRequests.has(asset.id)) return;
    this.mediaPreviewRequests.add(asset.id);
    this.storefrontService.getMediaAssetBlob(storefrontId, asset.id).subscribe({
      next: (blob) => {
        this.mediaPreviewRequests.delete(asset.id);
        const objectUrl = window.URL.createObjectURL(blob);
        if (this.storefront?.id !== storefrontId) {
          window.URL.revokeObjectURL(objectUrl);
          return;
        }
        this.mediaPreviewUrls.set(asset.id, objectUrl);
      },
      error: () => {
        this.mediaPreviewRequests.delete(asset.id);
      }
    });
  }

  private clearMediaPreviewUrls(): void {
    this.mediaPreviewUrls.forEach((url) => window.URL.revokeObjectURL(url));
    this.mediaPreviewUrls.clear();
    this.mediaPreviewRequests.clear();
  }

  get heroSlides(): VisualHeroSlide[] {
    return this.document.legacy_home.hero_slides;
  }

  get selectedHeroSlide(): VisualHeroSlide | null {
    return this.heroSlides[this.selectedHeroSlideIndex] || this.heroSlides[0] || null;
  }

  get firstHeroSlide(): VisualHeroSlide | null {
    return this.selectedHeroSlide;
  }

  get firstHeroPromo(): VisualHeroPromo | null {
    return this.document.legacy_home.hero_promos[0] || null;
  }

  private selectedReferenceIds(fieldName: 'collection_ids' | 'product_ids'): string[] {
    const value = this.selectedSection?.settings?.[fieldName];
    return Array.isArray(value)
      ? value.filter((item): item is string => typeof item === 'string')
      : [];
  }

  private setSelectedReferences(fieldName: 'collection_ids' | 'product_ids', value: unknown): void {
    if (!this.selectedSection) return;
    const values = (Array.isArray(value) ? value : value ? [value] : [])
      .filter((item): item is string => typeof item === 'string' && item.length > 0);
    this.selectedSection.settings[fieldName] = Array.from(new Set(values));
    this.markDirty();
  }

  get selectedCopy(): VisualSectionCopy | null {
    switch (this.selectedSection?.type) {
      case 'categories':
        return this.document.legacy_home.category_section;
      case 'new_arrivals':
        return this.document.legacy_home.new_arrivals_section;
      case 'best_sellers':
        return this.document.legacy_home.best_sellers_section;
      default:
        return null;
    }
  }

  get selectedCopyEyebrow(): string {
    return this.selectedCopy?.eyebrow || '';
  }

  set selectedCopyEyebrow(value: string) {
    if (this.selectedCopy) this.selectedCopy.eyebrow = value;
  }

  get selectedCopyTitle(): string {
    return this.selectedCopy?.title || '';
  }

  set selectedCopyTitle(value: string) {
    if (this.selectedCopy) this.selectedCopy.title = value;
  }

  get selectedCopyCtaLabel(): string {
    return this.selectedCopy?.cta_label || '';
  }

  set selectedCopyCtaLabel(value: string) {
    if (this.selectedCopy) this.selectedCopy.cta_label = value;
  }

  get selectedCopyCtaHref(): string {
    return this.selectedCopy?.cta_href || '';
  }

  set selectedCopyCtaHref(value: string) {
    if (this.selectedCopy) this.selectedCopy.cta_href = value;
  }

  get heroTitle(): string {
    return this.firstHeroSlide?.title || '';
  }

  set heroTitle(value: string) {
    this.ensureHeroSlide().title = value;
  }

  get heroDescription(): string {
    return this.firstHeroSlide?.description || '';
  }

  set heroDescription(value: string) {
    this.ensureHeroSlide().description = value;
  }

  get heroButtonLabel(): string {
    return this.firstHeroSlide?.button_label || '';
  }

  set heroButtonLabel(value: string) {
    this.ensureHeroSlide().button_label = value;
  }

  get heroButtonLink(): string {
    return this.firstHeroSlide?.cta_href || '/products';
  }

  set heroButtonLink(value: string) {
    this.ensureHeroSlide().cta_href = value;
  }

  get heroImage(): string {
    return this.firstHeroSlide?.image || '';
  }

  set heroImage(value: string) {
    this.ensureHeroSlide().image = value;
  }

  get promoTitle(): string {
    return this.firstHeroPromo?.title || '';
  }

  set promoTitle(value: string) {
    this.ensureHeroPromo().title = value;
  }

  get promoOfferLabel(): string {
    return this.firstHeroPromo?.offer_label || '';
  }

  set promoOfferLabel(value: string) {
    this.ensureHeroPromo().offer_label = value;
  }

  get promoImage(): string {
    return this.firstHeroPromo?.image || '';
  }

  set promoImage(value: string) {
    this.ensureHeroPromo().image = value;
  }

  get countdown(): VisualCountdown {
    return this.document.legacy_home.countdown;
  }

  get newsletter(): VisualNewsletter {
    return this.document.legacy_home.newsletter;
  }

 get testimonials(): VisualTestimonials {
   return this.document.legacy_home.testimonials;
 }

  get features(): StorefrontHomeFeatureItem[] {
    return this.document.legacy_home.features || [];
  }

 get promoBanners(): StorefrontPromoBanner[] {
   return this.document.legacy_home.promo_banners || [];
 }

  addPromoBanner(): void {
    if (!this.canAddPromoBanner) return;
    this.document.legacy_home.promo_banners = [
      ...this.promoBanners,
     {
       id: `home-promo-${Date.now()}`,
        enabled: true,
       title: 'Nueva campaña',
        subtitle: 'Un mensaje para tus clientes',
        description: '',
        cta_label: 'Ver productos',
        cta_href: '/products',
        image_url: '',
        background_color: '#F2E8DE',
        accent_color: '#B65332'
      }
    ];
    this.ensureMediaTarget();
    this.markDirty();
  }

 removePromoBanner(index: number): void {
   this.document.legacy_home.promo_banners = this.promoBanners.filter((_, itemIndex) => itemIndex !== index);
   this.ensureMediaTarget();
   this.markDirty();
 }

  togglePromoBanner(index: number, event: Event): void {
    const input = event.target as HTMLInputElement;
    const banner = this.promoBanners[index];
    if (!banner) return;
    banner.enabled = input.checked;
    this.markDirty();
  }

  duplicatePromoBanner(index: number): void {
    const source = this.promoBanners[index];
    if (!source || !this.canAddPromoBanner) return;
    this.promoBanners.splice(index + 1, 0, {
      ...source,
      id: `home-promo-${Date.now()}-${index + 2}`,
    });
    this.ensureMediaTarget();
    this.markDirty();
  }

  movePromoBanner(index: number, direction: -1 | 1): void {
    const targetIndex = index + direction;
    if (!this.promoBanners[index] || targetIndex < 0 || targetIndex >= this.promoBanners.length) return;
    const [banner] = this.promoBanners.splice(index, 1);
    this.promoBanners.splice(targetIndex, 0, banner);
    this.ensureMediaTarget();
    this.markDirty();
  }

  addTestimonial(): void {
    if (!this.canAddTestimonial) return;
    this.document.legacy_home.testimonials.items = [
     ...(this.document.legacy_home.testimonials.items || []),
     {
       id: `testimonial-${Date.now()}`,
        enabled: true,
       review: 'Una opinión real de tus clientes ayuda a generar confianza.',
       author_name: 'Cliente',
       author_role: 'Cliente verificado',
       author_image: ''
     }
   ];
   this.ensureMediaTarget();
   this.markDirty();
 }

 removeTestimonial(index: number): void {
   this.document.legacy_home.testimonials.items = (this.document.legacy_home.testimonials.items || [])
     .filter((_, itemIndex) => itemIndex !== index);
   this.ensureMediaTarget();
   this.markDirty();
 }

  toggleTestimonial(index: number, event: Event): void {
    const input = event.target as HTMLInputElement;
    const testimonial = this.testimonials.items?.[index];
    if (!testimonial) return;
    testimonial.enabled = input.checked;
    this.markDirty();
  }

  duplicateTestimonial(index: number): void {
    const items = this.testimonials.items || [];
    const source = items[index];
    if (!source || !this.canAddTestimonial) return;
    items.splice(index + 1, 0, {
      ...source,
      id: `testimonial-${Date.now()}-${index + 2}`,
    });
    this.testimonials.items = items;
    this.ensureMediaTarget();
    this.markDirty();
  }

  moveTestimonial(index: number, direction: -1 | 1): void {
    const items = this.testimonials.items || [];
    const targetIndex = index + direction;
    if (!items[index] || targetIndex < 0 || targetIndex >= items.length) return;
    const [testimonial] = items.splice(index, 1);
    items.splice(targetIndex, 0, testimonial);
    this.testimonials.items = items;
    this.ensureMediaTarget();
    this.markDirty();
  }

  get featuresForEditing(): StorefrontHomeFeatureItem[] {
    return this.document.legacy_home.features || [];
  }

  addFeature(): void {
    if (!this.canAddFeature) return;
    this.document.legacy_home.features = [
      ...this.featuresForEditing,
      {
        id: `home-feature-${Date.now()}`,
        enabled: true,
        title: 'Nuevo beneficio',
        description: 'Un motivo para elegir tu tienda',
        image: '',
      },
    ];
    this.ensureMediaTarget();
    this.markDirty();
  }

  removeFeature(index: number): void {
    this.document.legacy_home.features = this.featuresForEditing.filter((_, itemIndex) => itemIndex !== index);
    this.ensureMediaTarget();
    this.markDirty();
  }

  toggleFeature(index: number, event: Event): void {
    const input = event.target as HTMLInputElement;
    const feature = this.featuresForEditing[index];
    if (!feature) return;
    feature.enabled = input.checked;
    this.markDirty();
  }

  duplicateFeature(index: number): void {
    const source = this.featuresForEditing[index];
    if (!source || !this.canAddFeature) return;
    this.featuresForEditing.splice(index + 1, 0, {
      ...source,
      id: `home-feature-${Date.now()}-${index + 2}`,
    });
    this.ensureMediaTarget();
    this.markDirty();
  }

  moveFeature(index: number, direction: -1 | 1): void {
    const targetIndex = index + direction;
    if (!this.featuresForEditing[index] || targetIndex < 0 || targetIndex >= this.featuresForEditing.length) return;
    const [feature] = this.featuresForEditing.splice(index, 1);
    this.featuresForEditing.splice(targetIndex, 0, feature);
    this.ensureMediaTarget();
    this.markDirty();
  }

  loadStorefronts(): void {
    this.loading = true;
    this.errorMessage = '';
    this.storefrontService.getStorefronts().subscribe({
      next: (storefronts) => {
        this.storefronts = storefronts;
        this.selectedStorefrontId = this.context.resolveSelectedStorefront(storefronts);
        this.applySelectedStorefront();
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.errorMessage = err?.error?.detail || 'No se pudieron cargar las tiendas.';
      }
    });
  }

  onStorefrontChange(): void {
    if (this.dirty && !window.confirm('Tienes cambios sin guardar. ¿Quieres cambiar de tienda y descartarlos?')) {
      this.selectedStorefrontId = this.lastAppliedStorefrontId;
      return;
    }
    this.context.setSelectedStorefrontId(this.selectedStorefrontId);
    this.applySelectedStorefront();
  }

  selectSection(section: VisualSection): void {
    this.selectedSectionId = section.id;
    this.selectedGlobalArea = null;
    this.sidebarOpen = true;
    this.sidebarMode = 'section';
    this.pendingInsertAfterId = null;
    this.ensureMediaTarget();
    this.pushPreview();
  }

  showSections(): void {
    this.sidebarOpen = true;
    this.sidebarMode = 'sections';
    this.selectedSectionId = '';
    this.selectedGlobalArea = null;
    this.pendingInsertAfterId = null;
    this.pushPreview();
  }

  showSettings(area: VisualGlobalArea | null = null): void {
    this.sidebarOpen = true;
    this.sidebarMode = 'settings';
    this.selectedSectionId = '';
    this.selectedGlobalArea = area;
    this.pendingInsertAfterId = null;
    if (area) this.focusGlobalArea(area);
    this.pushPreview();
  }

  private focusGlobalArea(area: VisualGlobalArea): void {
    window.setTimeout(() => {
      window.document
        .getElementById(`visual-editor-settings-${area}`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  openAddSections(afterSectionId: string | null = null): void {
    this.sidebarOpen = true;
    this.sidebarMode = 'add';
    this.selectedSectionId = '';
    this.selectedGlobalArea = null;
    this.pendingInsertAfterId = afterSectionId;
    this.pushPreview();
  }

  toggleSidebar(): void {
    this.sidebarOpen = !this.sidebarOpen;
  }

  drop(event: CdkDragDrop<VisualSection[]>): void {
    if (event.previousIndex === event.currentIndex) return;
    moveItemInArray(this.document.sections, event.previousIndex, event.currentIndex);
    this.markDirty();
  }

  addSection(type: string): void {
    if (!this.isSectionType(type)) return;
    const id = `${type}-${Date.now()}`;
    const section: VisualSection = {
      id,
      type,
      enabled: true,
      settings: type === 'custom_embed' ? {
        mode: 'html',
        content: '',
        iframe_url: '',
        iframe_title: 'Contenido integrado',
        iframe_height: 420,
        max_width: 'content',
        alignment: 'center'
      } : {},
      blocks: []
    };
    const afterIndex = this.pendingInsertAfterId
      ? this.document.sections.findIndex((item) => item.id === this.pendingInsertAfterId)
      : -1;
    if (afterIndex >= 0) {
      this.document.sections.splice(afterIndex + 1, 0, section);
    } else {
      this.document.sections.push(section);
    }
    this.selectedSectionId = id;
    this.selectedGlobalArea = null;
    this.sidebarMode = 'section';
    this.pendingInsertAfterId = null;
    this.ensureMediaTarget();
    if (type === 'hero' && !this.firstHeroSlide) this.ensureHeroSlide();
    if (type === 'promo_banners' && !this.document.legacy_home.promo_banners?.length) {
      this.document.legacy_home.promo_banners = [];
    }
    this.markDirty();
  }

  duplicateSection(section: VisualSection, event?: Event): void {
    event?.stopPropagation();
    const copy: VisualSection = {
      ...section,
      id: `${section.type}-${Date.now()}`,
      settings: { ...(section.settings || {}) },
      blocks: (section.blocks || []).map((block) => ({ ...block }))
    };
    const index = this.document.sections.findIndex((item) => item.id === section.id);
    this.document.sections.splice(index + 1, 0, copy);
    this.selectedSectionId = copy.id;
    this.selectedGlobalArea = null;
    this.sidebarMode = 'section';
    this.markDirty();
  }

  removeSection(section: VisualSection, event?: Event): void {
    event?.stopPropagation();
    if (!section || this.saving || this.publishing) return;

    this.swal.confirm(
      '¿Eliminar esta sección?',
      `Se quitará “${this.sectionLabel(section)}” del borrador de la tienda.`
    ).then((result) => {
      if (!result.isConfirmed) return;

      this.document.sections = this.document.sections.filter((item) => item.id !== section.id);
      if (this.selectedSectionId === section.id) {
        this.selectedSectionId = this.document.sections[0]?.id || '';
        this.ensureMediaTarget();
      }
      this.sidebarMode = 'sections';
      this.selectedGlobalArea = null;
      this.markDirty();
    });
  }

  toggleSection(section: VisualSection, event: Event): void {
    const input = event.target as HTMLInputElement;
    section.enabled = input.checked;
    this.markDirty();
  }

  toggleHeroSlide(index: number, event: Event): void {
    const input = event.target as HTMLInputElement;
    const slide = this.heroSlides[index];
    if (!slide) return;
    slide.enabled = input.checked;
    this.markDirty();
  }

 ensureHeroSlide(): VisualHeroSlide {
    if (!this.document.legacy_home.hero_slides.length) {
      this.document.legacy_home.hero_slides.push({
        id: `hero-slide-${Date.now()}`,
        title: 'Una historia que empieza en casa',
        description: 'Cuenta qué hace especial a tu tienda y por qué tus clientes deberían descubrirla.',
        enabled: true,
        cta_href: '/products',
        image: '',
        overlay_opacity: 0.3,
        image_position: 'center',
        content_alignment: 'left',
        text_color: '#1C274C',
        button_label: 'Descubrir la colección',
        button_color: '#1C274C'
      });
    }
    this.selectedHeroSlideIndex = Math.min(
      this.selectedHeroSlideIndex,
      Math.max(this.heroSlides.length - 1, 0),
    );
    this.mediaTarget = `hero_slide:${this.selectedHeroSlideIndex}`;
    return this.heroSlides[this.selectedHeroSlideIndex];
  }

  selectHeroSlide(index: number): void {
    if (!Number.isInteger(index) || index < 0 || index >= this.heroSlides.length) return;
    this.selectedHeroSlideIndex = index;
    this.mediaTarget = `hero_slide:${index}`;
    this.ensureMediaTarget();
  }

 addHeroSlide(): void {
   if (!this.canAddHeroSlide) return;
   const index = this.heroSlides.length;
    this.heroSlides.push({
      id: `hero-slide-${Date.now()}-${index + 1}`,
      title: index ? "Una nueva historia para tu tienda" : "Una historia que empieza en casa",
      description: "Cuenta qué hace especial a tu tienda y por qué tus clientes deberían descubrirla.",
      enabled: true,
     cta_href: "/products",
     image: "",
     overlay_opacity: 0.3,
     image_position: "center",
     content_alignment: "left",
     text_color: "#1C274C",
     button_label: "Descubrir la colección",
     button_color: "#1C274C",
   });
    this.selectedHeroSlideIndex = index;
    this.mediaTarget = `hero_slide:${index}`;
    this.markDirty();
  }

  duplicateHeroSlide(index = this.selectedHeroSlideIndex): void {
    const source = this.heroSlides[index];
    if (!source || !this.canAddHeroSlide) return;
    const copy: VisualHeroSlide = {
      ...source,
      id: `hero-slide-${Date.now()}-${index + 2}`,
    };
    this.heroSlides.splice(index + 1, 0, copy);
    this.selectedHeroSlideIndex = index + 1;
    this.mediaTarget = `hero_slide:${this.selectedHeroSlideIndex}`;
    this.markDirty();
  }

  removeHeroSlide(index = this.selectedHeroSlideIndex): void {
    if (!this.heroSlides[index]) return;
    this.heroSlides.splice(index, 1);
    this.selectedHeroSlideIndex = Math.min(index, Math.max(this.heroSlides.length - 1, 0));
    this.ensureMediaTarget();
    this.markDirty();
  }

  moveHeroSlide(index: number, direction: -1 | 1): void {
    const targetIndex = index + direction;
    if (!this.heroSlides[index] || targetIndex < 0 || targetIndex >= this.heroSlides.length) return;
    const [slide] = this.heroSlides.splice(index, 1);
    this.heroSlides.splice(targetIndex, 0, slide);
    this.selectedHeroSlideIndex = targetIndex;
    this.mediaTarget = `hero_slide:${targetIndex}`;
    this.markDirty();
  }

  ensureHeroPromo(): VisualHeroPromo {
    if (!this.document.legacy_home.hero_promos.length) {
      this.document.legacy_home.hero_promos.push({
        id: `hero-promo-${Date.now()}`,
        title: 'Una selección para disfrutar más',
        offer_label: 'Colección destacada',
        href: '/products',
        price_label: 'Descubrir',
        compare_price_label: '',
        image: '',
        background_color: '#DDE6DE',
        background_image_url: ''
      });
    }
    return this.document.legacy_home.hero_promos[0];
  }

  markDirty(): void {
    this.dirty = true;
    this.errorMessage = '';
    this.recordHistory();
    this.pushPreview();
  }

  undo(): void {
    if (!this.canUndo || this.saving || this.publishing) return;
    const current = this.snapshot(this.document);
    const previous = this.undoStack.pop();
    if (!previous) return;
    this.redoStack.push(current);
    this.document = this.normalizeDocument(previous);
    this.clampHeroSlideSelection();
    this.historyCurrent = JSON.stringify(this.document);
    this.selectedSectionId = this.document.sections.find((section) => section.id === this.selectedSectionId)?.id
      || this.document.sections[0]?.id
      || '';
    this.dirty = true;
    this.errorMessage = '';
    this.pushPreview();
  }

  redo(): void {
    if (!this.canRedo || this.saving || this.publishing) return;
    const current = this.snapshot(this.document);
    const next = this.redoStack.pop();
    if (!next) return;
    this.undoStack.push(current);
    this.document = this.normalizeDocument(next);
    this.clampHeroSlideSelection();
    this.historyCurrent = JSON.stringify(this.document);
    this.selectedSectionId = this.document.sections.find((section) => section.id === this.selectedSectionId)?.id
      || this.document.sections[0]?.id
      || '';
    this.dirty = true;
    this.errorMessage = '';
    this.pushPreview();
  }

  saveDraft(afterSave?: () => void, showSuccessNotification = true): void {
    if (!this.storefront || !this.theme || this.saving) return;
    this.saving = true;
    this.errorMessage = '';
    this.storefrontService.saveThemeDraft(
      this.storefront.id,
      this.serializeDocument(),
      this.theme.draft_version
    ).subscribe({
      next: (theme) => {
        this.theme = theme;
        this.document = this.normalizeDocument(theme.draft_document);
        this.clampHeroSlideSelection();
        this.dirty = false;
        this.saving = false;
        this.historyCurrent = JSON.stringify(this.document);
        this.redoStack = [];
        this.pushPreview();
        if (showSuccessNotification) {
          this.swal.toast('Cambios guardados', 'success');
        }
        afterSave?.();
      },
      error: (err) => {
        this.saving = false;
        this.errorMessage = err?.error?.detail || 'No se pudo guardar el borrador.';
      }
    });
  }

  publish(): void {
    if (!this.storefront || !this.theme || this.publishing) return;
    const publishNow = (): void => {
      if (!this.storefront || !this.theme) return;
      this.publishing = true;
      this.storefrontService.publishTheme(this.storefront.id, this.theme.draft_version).subscribe({
        next: (theme) => {
          this.theme = theme;
          this.document = this.normalizeDocument(theme.draft_document);
          this.clampHeroSlideSelection();
          this.dirty = false;
          this.publishing = false;
          this.historyCurrent = JSON.stringify(this.document);
          this.redoStack = [];
          this.swal.success('Tienda publicada', 'Tu tienda ya está visible para tus clientes.');
          this.pushPreview();
          this.loadHistory(false);
        },
        error: (err) => {
          this.publishing = false;
          this.errorMessage = err?.error?.detail || 'No se pudo publicar el diseño.';
        }
      });
    };

    if (this.dirty) {
      this.saveDraft(publishNow, false);
    } else {
      publishNow();
    }
  }

  loadHistory(toggle = true): void {
    if (!this.storefront) return;
    this.showHistory = toggle ? !this.showHistory : this.showHistory;
    if (!this.showHistory || this.loadingHistory) return;
    this.loadingHistory = true;
    this.storefrontService.getThemeRevisions(this.storefront.id).subscribe({
      next: (revisions) => {
        this.revisions = revisions;
        this.loadingHistory = false;
      },
      error: (err) => {
        this.loadingHistory = false;
        this.errorMessage = err?.error?.detail || 'No se pudo cargar el historial.';
      }
    });
  }

  restoreRevision(revision: StorefrontThemeRevision): void {
    if (!this.storefront || !this.theme || this.saving) return;
    this.saving = true;
    this.storefrontService.restoreThemeRevision(
      this.storefront.id,
      revision.id,
      this.theme.draft_version
    ).subscribe({
      next: (theme) => {
        this.theme = theme;
        this.replaceDocument(theme.draft_document);
        this.dirty = true;
        this.saving = false;
        this.showHistory = false;
        this.pushPreview();
        this.swal.success('Borrador restaurado', 'Revisa el diseño y publícalo cuando estés listo.');
      },
      error: (err) => {
        this.saving = false;
        this.errorMessage = err?.error?.detail || 'No se pudo restaurar la versión.';
      }
    });
  }

  setViewport(viewport: 'desktop' | 'tablet' | 'mobile'): void {
    this.previewViewport = viewport;
  }

  toggleSelectionMode(): void {
    this.selectionMode = !this.selectionMode;
    this.pushPreview();
  }

  onPreviewLoad(): void {
    this.previewReady = false;
    window.setTimeout(() => this.pushPreview(), 50);
  }

  private applySelectedStorefront(): void {
    this.storefront = this.storefronts.find((item) => item.id === this.selectedStorefrontId) || null;
    this.lastAppliedStorefrontId = this.selectedStorefrontId;
    this.theme = null;
    this.document = this.createDocument();
    this.selectedHeroSlideIndex = 0;
    this.resetHistory();
    this.selectedSectionId = '';
    this.selectedGlobalArea = null;
    this.sidebarOpen = true;
    this.sidebarMode = 'sections';
    this.pendingInsertAfterId = null;
    this.collections = [];
    this.publishedProducts = [];
    this.clearMediaPreviewUrls();
    this.mediaAssets = [];
    this.previewUrl = '';
    this.safePreviewUrl = null;
    this.previewOrigin = '';
    this.mediaTarget = 'hero';
    this.mediaPickerOpen = false;
    this.mediaPickerTarget = null;
    this.mediaPickerSearch = '';
    this.dirty = false;
    this.revisions = [];
    this.showHistory = false;
    if (!this.storefront) return;

    this.loading = true;
    this.storefrontService.getThemeComponents(this.storefront.id).subscribe({
      next: (response) => {
        const remoteComponents = Array.isArray(response.components) ? response.components : [];
        const remoteByType = new Map(remoteComponents.map((component) => [component.type, component]));
        const localComponents = this.defaultComponents().map((component) => remoteByType.get(component.type) || component);
        const localTypes = new Set(localComponents.map((component) => component.type));
        this.components = [
          ...localComponents,
          ...remoteComponents.filter((component) => !localTypes.has(component.type))
        ];
      },
      error: () => {
        this.components = this.defaultComponents();
      }
    });
    const storefrontId = this.storefront.id;
    this.storefrontService.getCollections(storefrontId).subscribe({
      next: (collections) => {
        if (this.storefront?.id === storefrontId) this.collections = collections;
      }
    });
    this.storefrontService.getPublishedProducts(storefrontId).subscribe({
      next: (products) => {
        if (this.storefront?.id === storefrontId) {
          this.publishedProducts = products.filter((product) => product.is_published);
        }
      }
    });
    this.storefrontService.getMediaAssets(storefrontId).subscribe({
      next: (assets) => {
        if (this.storefront?.id === storefrontId) {
          this.mediaAssets = assets;
          this.loadMediaPreviews(assets, storefrontId);
        }
      },
      error: () => {
        if (this.storefront?.id === storefrontId) this.mediaAssets = [];
      }
    });
    this.storefrontService.getThemeDocument(this.storefront.id).subscribe({
      next: (theme) => {
        this.theme = theme;
        this.document = this.normalizeDocument(theme.draft_document);
        this.selectedHeroSlideIndex = 0;
        this.selectedSectionId = this.document.sections[0]?.id || '';
        this.ensureMediaTarget();
        this.resetHistory();
        this.createPreviewSession(theme);
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.errorMessage = err?.error?.detail || 'No se pudo cargar el editor visual.';
      }
    });
  }

  private createPreviewSession(theme: StorefrontThemeDocument): void {
    if (!this.storefront) return;
    const storefrontId = this.storefront.id;
    this.storefrontService.createThemePreviewSession(storefrontId).subscribe({
      next: (session: StorefrontThemePreviewSession) => {
        if (this.storefront?.id !== storefrontId) return;
        this.setPreviewUrl(session.preview_url);
      },
      error: (err) => {
        if (this.storefront?.id !== storefrontId) return;
        // Keep active storefronts usable if the session endpoint is briefly
        // unavailable; disabled storefronts must remain closed to public traffic.
        if (this.storefront.is_enabled && theme.preview_url) {
          this.setPreviewUrl(this.withPreviewFlag(theme.preview_url));
        } else {
          this.previewUrl = '';
          this.safePreviewUrl = null;
          this.errorMessage = err?.error?.detail || 'No se pudo abrir la sesión segura de previsualización.';
        }
      }
    });
  }

  private setPreviewUrl(value: string): void {
    this.previewUrl = value;
    try {
      this.previewOrigin = value ? new URL(value).origin : '';
    } catch {
      this.previewOrigin = '';
    }
    this.safePreviewUrl = value
      ? this.sanitizer.bypassSecurityTrustResourceUrl(value)
      : null;
  }

  private ensureMediaTarget(): void {
    this.clampHeroSlideSelection();
    const options = this.mediaTargetOptions;
    if (!options.some((option) => option.value === this.mediaTarget)) {
      this.mediaTarget = options[0]?.value || 'hero';
    }
  }

  private clampHeroSlideSelection(): void {
    this.selectedHeroSlideIndex = this.heroSlides.length
      ? Math.min(this.selectedHeroSlideIndex, this.heroSlides.length - 1)
      : 0;
  }

  private pushPreview(): void {
    const frame = this.previewFrame?.nativeElement;
    if (!frame?.contentWindow || !this.previewUrl) return;
    let targetOrigin = '*';
    try {
      targetOrigin = new URL(this.previewUrl).origin;
    } catch {
      return;
    }
    this.previewRequestId += 1;
    frame.contentWindow.postMessage({
      type: 'lumefy:preview:apply',
      template: 'home',
      requestId: this.previewRequestId,
      selectedSectionId: this.selectedSectionId,
      selectedGlobalArea: this.selectedGlobalArea,
      selectionMode: this.selectionMode,
      document: this.serializeDocument()
    }, targetOrigin);
  }

  private serializeDocument(): Record<string, unknown> {
    return this.snapshot(this.document);
  }

  private snapshot(value: unknown): Record<string, unknown> {
    return JSON.parse(JSON.stringify(value)) as Record<string, unknown>;
  }

  private resetHistory(): void {
    this.undoStack = [];
    this.redoStack = [];
    this.historyCurrent = JSON.stringify(this.document);
  }

  private recordHistory(): void {
    const current = JSON.stringify(this.document);
    if (!this.historyCurrent) {
      this.historyCurrent = current;
      return;
    }
    if (current === this.historyCurrent) return;
    this.undoStack.push(JSON.parse(this.historyCurrent) as Record<string, unknown>);
    if (this.undoStack.length > this.maxHistoryEntries) this.undoStack.shift();
    this.redoStack = [];
    this.historyCurrent = current;
  }

  private replaceDocument(input: Record<string, unknown>): void {
    const next = this.normalizeDocument(input);
    const nextSerialized = JSON.stringify(next);
    if (this.historyCurrent && this.historyCurrent !== nextSerialized) {
      this.undoStack.push(JSON.parse(this.historyCurrent) as Record<string, unknown>);
      if (this.undoStack.length > this.maxHistoryEntries) this.undoStack.shift();
    }
    this.document = next;
    this.clampHeroSlideSelection();
    this.historyCurrent = nextSerialized;
    this.redoStack = [];
  }

  private normalizeDocument(input: Record<string, unknown>): VisualThemeDocument {
    const raw = input && typeof input === 'object' ? input : {};
    const rawHome = this.asObject(raw['legacy_home']);
    const rawSections = Array.isArray(raw['sections']) ? raw['sections'] : [];
    const sections = rawSections
      .filter((section): section is Record<string, unknown> => Boolean(section) && typeof section === 'object')
      .map((section, index) => ({
        id: String(section['id'] || `section-${index + 1}`),
        type: this.isSectionType(String(section['type'] || '')) ? String(section['type']) as VisualSectionType : 'hero',
        enabled: section['enabled'] !== false,
        settings: this.asObject(section['settings']),
        blocks: Array.isArray(section['blocks'])
          ? section['blocks'].filter((block): block is Record<string, unknown> => Boolean(block) && typeof block === 'object')
          : []
      }));

    return {
      schema_version: Number(raw['schema_version'] || 1),
      template: 'home',
      settings: this.normalizeThemeSettings(raw['settings']),
      legacy_home: this.normalizeHome(rawHome),
      sections: sections.length ? sections : this.defaultSections()
    };
  }

  private normalizeThemeSettings(value: unknown): VisualThemeSettings {
    const raw = this.asObject(value);
    const base = this.createThemeSettings();
    const legacy = this.legacyThemeSettings();
    const branding = { ...legacy.branding, ...this.asObject(raw['branding']) };
    const styles = { ...legacy.styles, ...this.asObject(raw['styles']) };
    const announcement = { ...legacy.announcement, ...this.asObject(raw['announcement']) };
    const header = { ...legacy.header, ...this.asObject(raw['header']) };
    const footer = { ...legacy.footer, ...this.asObject(raw['footer']) };
    const socialLinks = this.asObject(footer['social_links']);

    return {
      ...base,
      ...raw,
      section_spacing: this.themeSectionSpacing(
        raw['section_spacing'],
        this.themeSectionSpacing(legacy.section_spacing, base.section_spacing)
      ),
      branding: {
        ...base.branding,
        ...branding,
        logo_url: String(branding['logo_url'] || ''),
        mobile_logo_url: String(branding['mobile_logo_url'] || ''),
        logo_alt: String(branding['logo_alt'] || base.branding.logo_alt),
        favicon_url: String(branding['favicon_url'] || '')
      },
      styles: {
        ...base.styles,
        ...styles,
        primary_color: String(styles['primary_color'] || base.styles.primary_color),
        accent_color: String(styles['accent_color'] || base.styles.accent_color),
        page_background_color: String(styles['page_background_color'] || base.styles.page_background_color),
        body_text_color: String(styles['body_text_color'] || base.styles.body_text_color),
        heading_text_color: String(styles['heading_text_color'] || base.styles.heading_text_color),
        body_font: this.themeFont(styles['body_font'], base.styles.body_font),
        heading_font: this.themeFont(styles['heading_font'], base.styles.heading_font),
        content_width: this.themeContentWidth(styles['content_width'], base.styles.content_width),
        corner_radius: this.themeRadius(styles['corner_radius'], base.styles.corner_radius),
        navigation_style: styles['navigation_style'] === 'minimal' ? 'minimal' : 'standard',
        navigation_variant: this.themeNavigationVariant(styles['navigation_variant'], base.styles.navigation_variant)
      },
      announcement: {
        ...base.announcement,
        ...announcement,
        enabled: announcement['enabled'] === true,
        text: String(announcement['text'] || ''),
        href: String(announcement['href'] || ''),
        background_color: String(announcement['background_color'] || base.announcement.background_color),
        text_color: String(announcement['text_color'] || base.announcement.text_color)
      },
      header: {
        ...base.header,
        ...header,
        support_label: String(header['support_label'] || base.header.support_label),
        search_placeholder: String(header['search_placeholder'] || base.header.search_placeholder),
        account_heading: String(header['account_heading'] || base.header.account_heading),
        guest_account_label: String(header['guest_account_label'] || base.header.guest_account_label),
        sign_out_label: String(header['sign_out_label'] || base.header.sign_out_label),
        cart_heading: String(header['cart_heading'] || base.header.cart_heading),
        recently_viewed_label: String(header['recently_viewed_label'] || base.header.recently_viewed_label),
        wishlist_label: String(header['wishlist_label'] || base.header.wishlist_label),
        background_color: String(header['background_color'] || base.header.background_color),
        text_color: String(header['text_color'] || base.header.text_color)
      },
      footer: {
        ...base.footer,
        ...footer,
        footer_text: String(footer['footer_text'] || ''),
        help_title: String(footer['help_title'] || base.footer.help_title),
        account_title: String(footer['account_title'] || base.footer.account_title),
        quick_links_title: String(footer['quick_links_title'] || base.footer.quick_links_title),
        payment_title: String(footer['payment_title'] || base.footer.payment_title),
        support_phone: String(footer['support_phone'] || ''),
        support_email: String(footer['support_email'] || ''),
        support_address: String(footer['support_address'] || ''),
        show_social_links: footer['show_social_links'] === true,
        social_links: {
          ...base.footer.social_links,
          ...socialLinks,
          facebook: String(socialLinks['facebook'] || ''),
          instagram: String(socialLinks['instagram'] || ''),
          twitter: String(socialLinks['twitter'] || ''),
          linkedin: String(socialLinks['linkedin'] || '')
        },
        background_color: String(footer['background_color'] || base.footer.background_color),
        text_color: String(footer['text_color'] || base.footer.text_color),
        bottom_background_color: String(footer['bottom_background_color'] || base.footer.bottom_background_color)
      }
    };
  }

  private themeFont(value: unknown, fallback: VisualThemeStyleSettings['body_font']): VisualThemeStyleSettings['body_font'] {
    return value === 'editorial' || value === 'humanist' || value === 'euclid' ? value : fallback;
  }

  private themeContentWidth(value: unknown, fallback: number): number {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? Math.min(1440, Math.max(960, Math.round(parsed))) : fallback;
  }

  private themeRadius(value: unknown, fallback: VisualThemeStyleSettings['corner_radius']): VisualThemeStyleSettings['corner_radius'] {
    return value === 'sharp' || value === 'round' || value === 'soft' ? value : fallback;
  }

  private themeNavigationVariant(
    value: unknown,
    fallback: VisualThemeStyleSettings['navigation_variant']
  ): VisualThemeStyleSettings['navigation_variant'] {
    return value === 'pill' || value === 'plain' || value === 'underline' ? value : fallback;
  }

  private themeSectionSpacing(
    value: unknown,
    fallback: VisualSectionSpacing
  ): VisualSectionSpacing {
    if (value === 'compact' || value === 'balanced' || value === 'airy') return value;
    if (value === 'comfortable') return 'balanced';
    return value === 'theme' ? 'theme' : fallback;
  }

  private legacyThemeSettings(): {
    branding: Record<string, unknown>;
    styles: Record<string, unknown>;
    section_spacing: unknown;
    announcement: Record<string, unknown>;
    header: Record<string, unknown>;
    footer: Record<string, unknown>;
  } {
    const themeSettings = this.asObject(this.storefront?.theme_settings);
    const branding = this.asObject(themeSettings['branding']);
    const footer = this.asObject(themeSettings['footer']);
    const legacySocialLinks = {
      ...this.asObject(themeSettings['social_links']),
      ...this.asObject(branding['social_links']),
      ...this.asObject(footer['social_links'])
    };
    return {
      section_spacing: themeSettings['section_spacing'],
      branding: {
        ...branding,
        logo_url: branding['logo_url'] || themeSettings['logo_url'] || '',
        mobile_logo_url: branding['mobile_logo_url'] || themeSettings['mobile_logo_url'] || '',
        logo_alt: branding['logo_alt'] || this.storefront?.name || 'Tienda online',
        favicon_url: branding['favicon_url'] || themeSettings['favicon_url'] || ''
      },
      styles: {
        ...this.asObject(themeSettings['styles']),
        ...this.asObject(this.asObject(themeSettings['global'])['styles'])
      },
      announcement: this.asObject(themeSettings['announcement']),
      header: this.asObject(themeSettings['header']),
      footer: {
        ...footer,
        footer_text: footer['footer_text'] || branding['footer_text'] || themeSettings['footer_text'] || '',
        support_phone: footer['support_phone'] || branding['support_phone'] || themeSettings['support_phone'] || '',
        support_email: footer['support_email'] || branding['support_email'] || themeSettings['support_email'] || '',
        support_address: footer['support_address'] || branding['support_address'] || themeSettings['support_address'] || '',
        social_links: legacySocialLinks
      }
    };
  }

  private normalizeHome(raw: Record<string, unknown>): VisualHomeSettings {
    const base = this.createHome();
    const heroSlides = this.asArray(raw['hero_slides']).map((item, index) => {
      const value = this.asObject(item);
      return {
        id: String(value['id'] || `hero-slide-${index + 1}`),
        title: String(value['title'] || ''),
        description: String(value['description'] || ''),
        enabled: value['enabled'] !== false,
        cta_href: String(value['cta_href'] || '/products'),
        image: String(value['image'] || ''),
        overlay_opacity: Number(value['overlay_opacity'] ?? 0.3),
        image_position: String(value['image_position'] || 'center'),
        content_alignment: String(value['content_alignment'] || 'left'),
        text_color: String(value['text_color'] || '#1C274C'),
        button_label: String(value['button_label'] || 'Ver productos'),
        button_color: String(value['button_color'] || '#1C274C')
      };
    });
    const heroPromos = this.asArray(raw['hero_promos']).map((item, index) => {
      const value = this.asObject(item);
      return {
        id: String(value['id'] || `hero-promo-${index + 1}`),
        enabled: value['enabled'] !== false,
        title: String(value['title'] || ''),
        offer_label: String(value['offer_label'] || 'Colección destacada'),
        href: String(value['href'] || '/products'),
        price_label: String(value['price_label'] || ''),
        compare_price_label: String(value['compare_price_label'] || ''),
        image: String(value['image'] || ''),
        background_color: String(value['background_color'] || '#DDE6DE'),
       background_image_url: String(value['background_image_url'] || '')
     };
   });
    const features = this.asArray(raw['features']).map((item, index) => {
      const value = this.asObject(item);
      return {
        id: String(value['id'] || `home-feature-${index + 1}`),
        enabled: value['enabled'] !== false,
        title: String(value['title'] || ''),
        description: String(value['description'] || ''),
        image: String(value['image'] || ''),
      };
    });
    const promoBanners = this.asArray(raw['promo_banners']).map((item, index) => {
      const value = this.asObject(item);
      return {
        id: String(value['id'] || `home-promo-${index + 1}`),
        enabled: value['enabled'] !== false,
        title: String(value['title'] || ''),
        subtitle: String(value['subtitle'] || ''),
        description: String(value['description'] || ''),
        cta_label: String(value['cta_label'] || 'Ver productos'),
        cta_href: String(value['cta_href'] || '/products'),
        image_url: String(value['image_url'] || ''),
        background_color: String(value['background_color'] || '#F2E8DE'),
        accent_color: String(value['accent_color'] || '#B65332'),
      };
    });

   return {
      ...base,
      ...raw,
     hero_slides: heroSlides,
     hero_promos: heroPromos,
      features,
      promo_banners: promoBanners,
     category_section: this.normalizeCopy(raw['category_section'], base.category_section),
      new_arrivals_section: this.normalizeCopy(raw['new_arrivals_section'], base.new_arrivals_section),
      best_sellers_section: this.normalizeCopy(raw['best_sellers_section'], base.best_sellers_section),
      countdown: this.normalizeCountdown(raw['countdown'], base.countdown),
      newsletter: this.normalizeNewsletter(raw['newsletter'], base.newsletter),
      testimonials: this.normalizeTestimonials(raw['testimonials'], base.testimonials)
    };
  }

  private normalizeCopy(value: unknown, fallback: VisualSectionCopy): VisualSectionCopy {
    const raw = this.asObject(value);
    return {
      ...fallback,
      eyebrow: String(raw['eyebrow'] || fallback.eyebrow),
      title: String(raw['title'] || fallback.title),
      cta_label: String(raw['cta_label'] || fallback.cta_label),
      cta_href: String(raw['cta_href'] || fallback.cta_href)
    };
  }

  private normalizeCountdown(value: unknown, fallback: VisualCountdown): VisualCountdown {
    const raw = this.asObject(value);
    return {
      ...fallback,
      enabled: raw['enabled'] !== false,
      eyebrow: String(raw['eyebrow'] || fallback.eyebrow),
      title: String(raw['title'] || fallback.title),
      description: String(raw['description'] || fallback.description),
      cta_label: String(raw['cta_label'] || fallback.cta_label),
      cta_href: String(raw['cta_href'] || fallback.cta_href),
      deadline: String(raw['deadline'] || fallback.deadline),
      background_color: String(raw['background_color'] || fallback.background_color),
      background_image_url: String(raw['background_image_url'] || fallback.background_image_url),
      product_image_url: String(raw['product_image_url'] || fallback.product_image_url)
    };
  }

  private normalizeNewsletter(value: unknown, fallback: VisualNewsletter): VisualNewsletter {
    const raw = this.asObject(value);
    return {
      ...fallback,
      enabled: raw['enabled'] !== false,
      title: String(raw['title'] || fallback.title),
      description: String(raw['description'] || fallback.description),
      placeholder: String(raw['placeholder'] || fallback.placeholder),
      button_label: String(raw['button_label'] || fallback.button_label),
      background_image_url: String(raw['background_image_url'] || fallback.background_image_url)
    };
  }

 private normalizeTestimonials(value: unknown, fallback: VisualTestimonials): VisualTestimonials {
   const raw = this.asObject(value);
   const items = Array.isArray(raw['items'])
     ? this.asArray(raw['items']).map((item, index) => {
       const testimonial = this.asObject(item);
       return {
         id: String(testimonial['id'] || `testimonial-${index + 1}`),
         enabled: testimonial['enabled'] !== false,
         review: String(testimonial['review'] || ''),
         author_name: String(testimonial['author_name'] || ''),
         author_role: String(testimonial['author_role'] || ''),
         author_image: String(testimonial['author_image'] || ''),
       };
     })
     : fallback.items;
   return {
     ...fallback,
     enabled: raw['enabled'] !== false,
     eyebrow: String(raw['eyebrow'] || fallback.eyebrow),
     title: String(raw['title'] || fallback.title),
      items
   };
 }

  private createDocument(): VisualThemeDocument {
    return {
      schema_version: 1,
      template: 'home',
      settings: this.createThemeSettings(),
      legacy_home: this.createHome(),
      sections: this.defaultSections()
    };
  }

  private createThemeSettings(): VisualThemeSettings {
    return {
      branding: {
        logo_url: '',
        mobile_logo_url: '',
        logo_alt: this.storefront?.name || 'Tienda online',
        favicon_url: ''
      },
      styles: {
        primary_color: '#3C50E0',
        accent_color: '#B65332',
        page_background_color: '#FFFFFF',
        body_text_color: '#5D6881',
        heading_text_color: '#1C274C',
        body_font: 'euclid',
        heading_font: 'euclid',
        content_width: 1170,
        corner_radius: 'soft',
        navigation_style: 'standard',
        navigation_variant: 'underline'
      },
      section_spacing: 'theme',
      announcement: {
        enabled: false,
        text: '',
        href: '',
        background_color: '#1C274C',
        text_color: '#FFFFFF'
      },
      header: {
        support_label: 'Atención al cliente',
        search_placeholder: 'Buscar productos...',
        account_heading: 'cuenta',
        guest_account_label: 'Ingresar',
        sign_out_label: 'Cerrar sesión',
        cart_heading: 'carrito',
        recently_viewed_label: 'Vistos recientemente',
        wishlist_label: 'Favoritos',
        background_color: '#FFFFFF',
        text_color: '#1C274C'
      },
      footer: {
        footer_text: '',
        help_title: 'Ayuda y contacto',
        account_title: 'Cuenta',
        quick_links_title: 'Enlaces',
        payment_title: 'Medios de pago:',
        support_phone: '',
        support_email: '',
        support_address: '',
        show_social_links: false,
        social_links: {
          facebook: '',
          instagram: '',
          twitter: '',
          linkedin: ''
        },
        background_color: '#FFFFFF',
        text_color: '#1C274C',
        bottom_background_color: '#F3F4F6'
      }
    };
  }

  private createHome(): VisualHomeSettings {
    return {
      content_version: 2,
      hero_slides: [],
      hero_promos: [],
      category_section: { eyebrow: 'Explora', title: 'Compra por categoría', cta_label: '', cta_href: '' },
      category_cards: [],
      new_arrivals_section: { eyebrow: 'Recién llegados', title: 'Novedades', cta_label: 'Ver todos', cta_href: '/products' },
      best_sellers_section: { eyebrow: 'Lo más elegido', title: 'Productos destacados', cta_label: 'Ver todos', cta_href: '/products' },
      features: [],
      promo_banners: [],
      countdown: {
        enabled: true,
        eyebrow: 'Oferta especial',
        title: 'No te pierdas esta oportunidad',
        description: 'Descubre productos seleccionados para ti.',
        cta_label: 'Ver oferta',
        cta_href: '/products',
        deadline: '2026-12-31T23:59:59',
        background_color: '#D0E9F3',
        background_image_url: '',
        product_image_url: ''
      },
      newsletter: {
        enabled: true,
        title: 'Recibe novedades y ofertas',
        description: 'Regístrate para recibir lanzamientos, descuentos y contenido de la tienda.',
        placeholder: 'Tu correo electrónico',
        button_label: 'Registrarme',
        background_image_url: ''
      },
      testimonials: {
        enabled: true,
        eyebrow: 'Testimonios',
        title: 'Lo que dicen nuestros clientes',
        items: []
      }
    };
  }

  private defaultSections(): VisualSection[] {
    return this.defaultComponents()
      .filter((component) => component.type !== 'custom_embed')
      .map((component) => ({
      id: component.type,
      type: component.type as VisualSectionType,
      enabled: true,
      settings: {},
      blocks: []
      }));
  }

  private defaultComponents(): StorefrontThemeComponent[] {
    return [
      { type: 'hero', label: 'Hero y promociones', description: 'Mensaje principal y promociones destacadas.', icon: 'sparkles' },
      { type: 'categories', label: 'Categorías', description: 'Accesos visuales a colecciones y categorías.', icon: 'grid' },
      { type: 'new_arrivals', label: 'Novedades', description: 'Productos publicados recientemente.', icon: 'star' },
      { type: 'promo_banners', label: 'Banners editoriales', description: 'Mensajes y campañas de la tienda.', icon: 'megaphone' },
      { type: 'best_sellers', label: 'Productos destacados', description: 'Los productos que quieres priorizar.', icon: 'trending-up' },
      { type: 'countdown', label: 'Cuenta regresiva', description: 'Promoción con fecha de finalización.', icon: 'clock' },
      { type: 'testimonials', label: 'Testimonios', description: 'Historias y reseñas de clientes.', icon: 'quote' },
      { type: 'newsletter', label: 'Newsletter', description: 'Captura suscripciones y novedades.', icon: 'mail' },
      { type: 'closing_cta', label: 'Llamado final', description: 'Cierre de página con una acción principal.', icon: 'arrow-right' },
      { type: 'custom_embed', label: 'Código personalizado', description: 'HTML seguro o contenido integrado.', icon: 'code' }
    ];
  }

  private isSectionType(value: string): value is VisualSectionType {
    return this.defaultComponents().some((component) => component.type === value);
  }

  private asObject(value: unknown): Record<string, unknown> {
    return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
  }

  private asArray(value: unknown): unknown[] {
    return Array.isArray(value) ? value : [];
  }

  private withPreviewFlag(value: string): string {
    if (!value) return '';
    try {
      const url = new URL(value);
      url.searchParams.set('lumefy_preview', '1');
      return url.toString();
    } catch {
      return '';
    }
  }
}
