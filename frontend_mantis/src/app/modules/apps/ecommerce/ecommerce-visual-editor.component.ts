import { CommonModule } from '@angular/common';
import { CdkDragDrop, DragDropModule, moveItemInArray } from '@angular/cdk/drag-drop';
import { Component, ElementRef, OnDestroy, OnInit, ViewChild, inject } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import {
  PublishedProduct,
  StoreCollection,
  Storefront,
  StorefrontAdminService,
  StorefrontHomeCountdownSettings,
  StorefrontHomeHeroPromo,
  StorefrontHomeHeroSlide,
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
  | 'closing_cta';

interface VisualSection extends StorefrontThemeSection {
  type: VisualSectionType;
}

interface VisualHeroSlide extends StorefrontHomeHeroSlide {
  title: string;
  description: string;
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
}

interface VisualNewsletter extends StorefrontHomeNewsletterSettings {
  enabled: boolean;
  title: string;
  description: string;
  placeholder: string;
  button_label: string;
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

interface VisualThemeDocument {
  schema_version: number;
  template: 'home';
  settings: Record<string, unknown>;
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
  imports: [CommonModule, FormsModule, DragDropModule],
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
  previewReady = false;
  storefronts: Storefront[] = [];
  collections: StoreCollection[] = [];
  publishedProducts: PublishedProduct[] = [];
  selectedStorefrontId = '';
  storefront: Storefront | null = null;
  theme: StorefrontThemeDocument | null = null;
  document: VisualThemeDocument = this.createDocument();
  components: StorefrontThemeComponent[] = [];
  revisions: StorefrontThemeRevision[] = [];
  selectedSectionId = '';
  previewUrl = '';
  safePreviewUrl: SafeResourceUrl | null = null;
  previewViewport: 'desktop' | 'tablet' | 'mobile' = 'desktop';
  errorMessage = '';
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
  private readonly onWindowMessage = (event: MessageEvent): void => {
    if (event.source !== this.previewFrame?.nativeElement.contentWindow) return;
    if (!this.previewOrigin || event.origin !== this.previewOrigin) return;
    if (event.data?.type === 'lumefy:preview:select' && typeof event.data.sectionId === 'string') {
      if (this.document.sections.some((section) => section.id === event.data.sectionId)) {
        this.selectedSectionId = event.data.sectionId;
      }
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
  }

  get selectedSection(): VisualSection | null {
    return this.document.sections.find((section) => section.id === this.selectedSectionId) || null;
  }

  get selectedComponent(): StorefrontThemeComponent | null {
    const type = this.selectedSection?.type;
    return this.components.find((component) => component.type === type) || null;
  }

  componentFor(section: VisualSection): StorefrontThemeComponent | null {
    return this.components.find((component) => component.type === section.type) || null;
  }

  sectionLabel(section: VisualSection): string {
    return this.componentFor(section)?.label || section.type.replace(/_/g, ' ');
  }

  sectionIcon(section: VisualSection): string {
    return this.componentFor(section)?.icon || 'block';
  }

  get canAddSection(): boolean {
    return this.document.sections.length < 20;
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

  setCollectionSelection(value: unknown): void {
    this.setSelectedReferences('collection_ids', value);
  }

  setProductSelection(value: unknown): void {
    this.setSelectedReferences('product_ids', value);
  }

  get firstHeroSlide(): VisualHeroSlide | null {
    return this.document.legacy_home.hero_slides[0] || null;
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

  get promoBanners(): StorefrontPromoBanner[] {
    return this.document.legacy_home.promo_banners || [];
  }

  addPromoBanner(): void {
    this.document.legacy_home.promo_banners = [
      ...this.promoBanners,
      {
        id: `home-promo-${Date.now()}`,
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
    this.markDirty();
  }

  removePromoBanner(index: number): void {
    this.document.legacy_home.promo_banners = this.promoBanners.filter((_, itemIndex) => itemIndex !== index);
    this.markDirty();
  }

  addTestimonial(): void {
    this.document.legacy_home.testimonials.items = [
      ...(this.document.legacy_home.testimonials.items || []),
      {
        id: `testimonial-${Date.now()}`,
        review: 'Una opinión real de tus clientes ayuda a generar confianza.',
        author_name: 'Cliente',
        author_role: 'Cliente verificado',
        author_image: ''
      }
    ];
    this.markDirty();
  }

  removeTestimonial(index: number): void {
    this.document.legacy_home.testimonials.items = (this.document.legacy_home.testimonials.items || [])
      .filter((_, itemIndex) => itemIndex !== index);
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
      settings: {},
      blocks: []
    };
    this.document.sections.push(section);
    this.selectedSectionId = id;
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
    this.markDirty();
  }

  removeSection(section: VisualSection, event?: Event): void {
    event?.stopPropagation();
    this.document.sections = this.document.sections.filter((item) => item.id !== section.id);
    if (this.selectedSectionId === section.id) {
      this.selectedSectionId = this.document.sections[0]?.id || '';
    }
    this.markDirty();
  }

  toggleSection(section: VisualSection, event: Event): void {
    const input = event.target as HTMLInputElement;
    section.enabled = input.checked;
    this.markDirty();
  }

  ensureHeroSlide(): VisualHeroSlide {
    if (!this.document.legacy_home.hero_slides.length) {
      this.document.legacy_home.hero_slides.push({
        id: `hero-slide-${Date.now()}`,
        title: 'Una historia que empieza en casa',
        description: 'Cuenta qué hace especial a tu tienda y por qué tus clientes deberían descubrirla.',
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
    return this.document.legacy_home.hero_slides[0];
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
    this.historyCurrent = JSON.stringify(this.document);
    this.selectedSectionId = this.document.sections.find((section) => section.id === this.selectedSectionId)?.id
      || this.document.sections[0]?.id
      || '';
    this.dirty = true;
    this.errorMessage = '';
    this.pushPreview();
  }

  saveDraft(afterSave?: () => void): void {
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
        this.dirty = false;
        this.saving = false;
        this.historyCurrent = JSON.stringify(this.document);
        this.redoStack = [];
        this.pushPreview();
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
          this.dirty = false;
          this.publishing = false;
          this.historyCurrent = JSON.stringify(this.document);
          this.redoStack = [];
          this.swal.success('Publicado', 'Los cambios ya están visibles en tu storefront.');
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
      this.saveDraft(publishNow);
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

  onPreviewLoad(): void {
    this.previewReady = false;
    window.setTimeout(() => this.pushPreview(), 50);
  }

  private applySelectedStorefront(): void {
    this.storefront = this.storefronts.find((item) => item.id === this.selectedStorefrontId) || null;
    this.lastAppliedStorefrontId = this.selectedStorefrontId;
    this.theme = null;
    this.document = this.createDocument();
    this.resetHistory();
    this.selectedSectionId = '';
    this.collections = [];
    this.publishedProducts = [];
    this.previewUrl = '';
    this.safePreviewUrl = null;
    this.previewOrigin = '';
    this.dirty = false;
    this.revisions = [];
    this.showHistory = false;
    if (!this.storefront) return;

    this.loading = true;
    this.storefrontService.getThemeComponents(this.storefront.id).subscribe({
      next: (response) => {
        this.components = response.components || [];
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
    this.storefrontService.getThemeDocument(this.storefront.id).subscribe({
      next: (theme) => {
        this.theme = theme;
        this.document = this.normalizeDocument(theme.draft_document);
        this.selectedSectionId = this.document.sections[0]?.id || '';
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
      settings: this.asObject(raw['settings']),
      legacy_home: this.normalizeHome(rawHome),
      sections: sections.length ? sections : this.defaultSections()
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

    return {
      ...base,
      ...raw,
      hero_slides: heroSlides,
      hero_promos: heroPromos,
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
      deadline: String(raw['deadline'] || fallback.deadline)
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
      button_label: String(raw['button_label'] || fallback.button_label)
    };
  }

  private normalizeTestimonials(value: unknown, fallback: VisualTestimonials): VisualTestimonials {
    const raw = this.asObject(value);
    return {
      ...fallback,
      enabled: raw['enabled'] !== false,
      eyebrow: String(raw['eyebrow'] || fallback.eyebrow),
      title: String(raw['title'] || fallback.title),
      items: Array.isArray(raw['items']) ? raw['items'] as VisualTestimonials['items'] : fallback.items
    };
  }

  private createDocument(): VisualThemeDocument {
    return {
      schema_version: 1,
      template: 'home',
      settings: {},
      legacy_home: this.createHome(),
      sections: this.defaultSections()
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
        deadline: '2026-12-31T23:59:59'
      },
      newsletter: {
        enabled: true,
        title: 'Recibe novedades y ofertas',
        description: 'Regístrate para recibir lanzamientos, descuentos y contenido de la tienda.',
        placeholder: 'Tu correo electrónico',
        button_label: 'Registrarme'
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
    return this.defaultComponents().map((component) => ({
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
      { type: 'closing_cta', label: 'Llamado final', description: 'Cierre de página con una acción principal.', icon: 'arrow-right' }
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
