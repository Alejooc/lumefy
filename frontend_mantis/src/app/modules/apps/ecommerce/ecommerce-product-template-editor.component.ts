import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnDestroy, OnInit, ViewChild, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CdkDragDrop, DragDropModule, moveItemInArray } from '@angular/cdk/drag-drop';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import {
  PublishedProduct,
  Storefront,
  StorefrontAdminService,
  StorefrontThemeComponent,
  StorefrontThemeDocument,
  StorefrontThemePreviewSession,
} from 'src/app/core/services/storefront-admin.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';
import { EcommerceEditorPagePickerComponent } from './ecommerce-editor-page-picker.component';

type ProductSectionType = 'product_gallery' | 'product_information' | 'product_description' | 'product_related';
type ProductSidebarMode = 'sections' | 'settings' | 'section' | 'add';
type ProductViewport = 'desktop' | 'tablet' | 'mobile';

interface ProductSection {
  id: string;
  type: ProductSectionType;
  enabled: boolean;
  settings: Record<string, unknown>;
  blocks: Record<string, unknown>[];
}

interface ProductContentSettings {
  breadcrumb_title: string;
  price_label: string;
  stock_in_label: string;
  stock_out_label: string;
  free_delivery_text: string;
  promo_text: string;
  description_tab_label: string;
  details_tab_label: string;
  reviews_tab_label: string;
  reviews_empty_title: string;
  reviews_empty_description: string;
  submit_review_label: string;
}

interface ProductTemplateDocument {
  schema_version: number;
  template: 'product';
  settings: { content: ProductContentSettings; [key: string]: unknown };
  sections: ProductSection[];
}

interface ProductComponentDefinition extends StorefrontThemeComponent {
  type: ProductSectionType;
}

const PRODUCT_COMPONENTS: ProductComponentDefinition[] = [
  { type: 'product_gallery', label: 'Galería del producto', description: 'Imágenes y miniaturas del producto.', icon: 'photo' },
  { type: 'product_information', label: 'Información del producto', description: 'Título, precio, variantes y compra.', icon: 'shopping-bag' },
  { type: 'product_description', label: 'Descripción y detalles', description: 'Descripción, características y reseñas.', icon: 'article' },
  { type: 'product_related', label: 'Productos relacionados', description: 'Recomendaciones para continuar la compra.', icon: 'sparkles' },
];

@Component({
  selector: 'app-ecommerce-product-template-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, DragDropModule, RouterLink, EcommerceEditorPagePickerComponent],
  templateUrl: './ecommerce-product-template-editor.component.html',
  styleUrls: ['./ecommerce-product-template-editor.component.scss'],
})
export class EcommerceProductTemplateEditorComponent implements OnInit, OnDestroy {
  private storefrontService = inject(StorefrontAdminService);
  private context = inject(EcommerceContextService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);
  private sanitizer = inject(DomSanitizer);

  @ViewChild('previewFrame') previewFrame?: ElementRef<HTMLIFrameElement>;

  loading = false;
  saving = false;
  publishing = false;
  dirty = false;
  sidebarOpen = true;
  sidebarMode: ProductSidebarMode = 'sections';
  selectionMode = true;
  previewReady = false;
  errorMessage = '';
  storefronts: Storefront[] = [];
  storefront: Storefront | null = null;
  selectedStorefrontId = '';
  publishedProducts: PublishedProduct[] = [];
  selectedProductId = '';
  theme: StorefrontThemeDocument | null = null;
  document: ProductTemplateDocument = this.createDocument();
  components: ProductComponentDefinition[] = PRODUCT_COMPONENTS;
  selectedSectionId = '';
  previewUrl = '';
  safePreviewUrl: SafeResourceUrl | null = null;
  previewViewport: ProductViewport = 'desktop';

  private previewOrigin = '';
  private previewRequestId = 0;
  private previewSessionUrl = '';
  private lastAppliedStorefrontId = '';
  private productsLoaded = false;
  private themeLoaded = false;
  private readonly onWindowMessage = (event: MessageEvent): void => {
    if (event.source !== this.previewFrame?.nativeElement.contentWindow) return;
    if (this.previewOrigin && event.origin !== this.previewOrigin) return;
    if (event.data?.type === 'lumefy:preview:select' && typeof event.data.sectionId === 'string') {
      if (!this.document.sections.some((section) => section.id === event.data.sectionId)) return;
      this.selectedSectionId = event.data.sectionId;
      this.sidebarOpen = true;
      this.sidebarMode = 'section';
      this.pushPreview();
    }
    if (event.data?.type === 'lumefy:preview:ready') {
      this.previewReady = true;
      this.pushPreview();
    }
  };

  ngOnInit(): void {
    window.addEventListener('message', this.onWindowMessage);
    if (!this.permissions.hasPermission('manage_company')) {
      this.swal.error('Sin permiso', 'No puedes administrar el diseño del ecommerce.');
      return;
    }
    this.loadStorefronts();
  }

  ngOnDestroy(): void {
    window.removeEventListener('message', this.onWindowMessage);
  }

  get selectedSection(): ProductSection | null {
    return this.document.sections.find((section) => section.id === this.selectedSectionId) || null;
  }

  get selectedProduct(): PublishedProduct | null {
    return this.publishedProducts.find((product) => product.id === this.selectedProductId) || null;
  }

  get selectedProductLabel(): string {
    const product = this.selectedProduct;
    return product ? (product.product_name || product.slug) : 'Sin productos publicados';
  }

  get productContent(): ProductContentSettings {
    return this.document.settings.content;
  }

  get selectedSectionSettings(): Record<string, unknown> {
    return this.selectedSection?.settings || {};
  }

  get sectionCountLabel(): string {
    return `${this.document.sections.length}/20`;
  }

  get canAddSection(): boolean {
    return this.document.sections.length < 20;
  }

  get canPublish(): boolean {
    return Boolean(this.theme && this.publishedProducts.length && !this.saving && !this.publishing);
  }

  getSectionSetting(key: string, fallback: boolean | number | string): boolean | number | string {
    const value = this.selectedSectionSettings[key];
    return value === undefined || value === null ? fallback : value as boolean | number | string;
  }

  sectionLabel(section: ProductSection): string {
    return this.components.find((component) => component.type === section.type)?.label || 'Sección de producto';
  }

  componentIcon(type: string): string {
    const icon = this.components.find((component) => component.type === type)?.icon || 'layout-grid';
    return `ti ti-${icon}`;
  }

  showSections(): void {
    this.sidebarOpen = true;
    this.sidebarMode = 'sections';
    this.pushPreview();
  }

  showSettings(): void {
    this.sidebarOpen = true;
    this.sidebarMode = 'settings';
    this.selectedSectionId = '';
    this.pushPreview();
  }

  openAddSections(): void {
    this.sidebarOpen = true;
    this.sidebarMode = 'add';
    this.pushPreview();
  }

  selectSection(section: ProductSection): void {
    this.selectedSectionId = section.id;
    this.sidebarOpen = true;
    this.sidebarMode = 'section';
    this.pushPreview();
  }

  toggleSidebar(): void {
    this.sidebarOpen = !this.sidebarOpen;
  }

  drop(event: CdkDragDrop<ProductSection[]>): void {
    if (event.previousIndex === event.currentIndex) return;
    moveItemInArray(this.document.sections, event.previousIndex, event.currentIndex);
    this.markDirty();
  }

  addSection(type: string): void {
    if (!this.isProductSectionType(type) || !this.canAddSection) return;
    const id = `${type}-${Date.now()}`;
    this.document.sections.push({ id, type, enabled: true, settings: {}, blocks: [] });
    this.selectedSectionId = id;
    this.sidebarMode = 'section';
    this.markDirty();
  }

  removeSection(section: ProductSection, event?: Event): void {
    event?.stopPropagation();
    if (!section || this.saving || this.publishing) return;
    this.swal.confirm('¿Eliminar esta sección?', `Se quitará “${this.sectionLabel(section)}” del borrador.`).then((result) => {
      if (!result.isConfirmed) return;
      this.document.sections = this.document.sections.filter((item) => item.id !== section.id);
      this.selectedSectionId = this.document.sections[0]?.id || '';
      this.sidebarMode = 'sections';
      this.markDirty();
    });
  }

  toggleSection(section: ProductSection, event: Event): void {
    section.enabled = (event.target as HTMLInputElement).checked;
    this.markDirty();
  }

  updateSectionSetting(key: string, value: unknown): void {
    const section = this.selectedSection;
    if (!section) return;
    section.settings[key] = value;
    this.markDirty();
  }

  updateContentSetting(key: keyof ProductContentSettings, value: string): void {
    this.productContent[key] = value;
    this.markDirty();
  }

  onProductChange(): void {
    this.updateProductPreviewUrl();
    this.pushPreview();
  }

  setViewport(viewport: ProductViewport): void {
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

  saveDraft(afterSave?: () => void, showSuccessNotification = true): void {
    if (!this.storefront || !this.theme || this.saving) return;
    this.saving = true;
    this.errorMessage = '';
    this.storefrontService.saveThemeDraft(
      this.storefront.id,
      this.serializeDocument(),
      this.theme.draft_version,
      'product',
    ).subscribe({
      next: (theme) => {
        this.theme = theme;
        this.document = this.normalizeDocument(theme.draft_document);
        this.dirty = false;
        this.saving = false;
        this.pushPreview();
        if (showSuccessNotification) this.swal.toast('Cambios guardados', 'success');
        afterSave?.();
      },
      error: (err) => {
        this.saving = false;
        this.errorMessage = err?.error?.detail || 'No se pudo guardar la plantilla de producto.';
      },
    });
  }

  publish(): void {
    if (!this.storefront || !this.theme || this.publishing) return;
    const publishNow = (): void => {
      if (!this.storefront || !this.theme) return;
      this.publishing = true;
      this.storefrontService.publishTheme(this.storefront.id, this.theme.draft_version, 'product').subscribe({
        next: (theme) => {
          this.theme = theme;
          this.document = this.normalizeDocument(theme.draft_document);
          this.dirty = false;
          this.publishing = false;
          this.swal.success('Plantilla publicada', 'El detalle de producto ya usa estos cambios.');
          this.pushPreview();
        },
        error: (err) => {
          this.publishing = false;
          this.errorMessage = err?.error?.detail || 'No se pudo publicar la plantilla de producto.';
        },
      });
    };
    if (this.dirty) this.saveDraft(publishNow, false);
    else publishNow();
  }

  loadStorefronts(): void {
    this.loading = true;
    this.errorMessage = '';
    this.storefrontService.getStorefronts().subscribe({
      next: (storefronts) => {
        this.storefronts = storefronts;
        this.selectedStorefrontId = this.context.resolveSelectedStorefront(storefronts);
        this.applySelectedStorefront();
      },
      error: (err) => {
        this.loading = false;
        this.errorMessage = err?.error?.detail || 'No se pudieron cargar las tiendas.';
      },
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

  private applySelectedStorefront(): void {
    this.storefront = this.storefronts.find((item) => item.id === this.selectedStorefrontId) || null;
    this.lastAppliedStorefrontId = this.selectedStorefrontId;
    this.document = this.createDocument();
    this.theme = null;
    this.publishedProducts = [];
    this.selectedProductId = '';
    this.selectedSectionId = '';
    this.previewUrl = '';
    this.safePreviewUrl = null;
    this.previewOrigin = '';
    this.previewSessionUrl = '';
    this.productsLoaded = false;
    this.themeLoaded = false;
    this.dirty = false;
    if (!this.storefront) {
      this.loading = false;
      return;
    }

    const storefrontId = this.storefront.id;
    this.loading = true;
    forkJoin({
      theme: this.storefrontService.getThemeDocument(storefrontId, 'product'),
      products: this.storefrontService.getPublishedProducts(storefrontId),
    }).subscribe({
      next: ({ theme, products }) => {
        if (this.storefront?.id !== storefrontId) return;
        this.theme = theme;
        this.document = this.normalizeDocument(theme.draft_document);
        this.publishedProducts = products.filter((product) => product.is_published);
        this.selectedProductId = this.publishedProducts[0]?.id || '';
        this.selectedSectionId = this.document.sections[0]?.id || '';
        this.themeLoaded = true;
        this.productsLoaded = true;
        this.loading = false;
        this.createPreviewSession();
      },
      error: (err) => {
        if (this.storefront?.id !== storefrontId) return;
        this.loading = false;
        this.errorMessage = err?.error?.detail || 'No se pudo cargar la plantilla de producto.';
      },
    });
    this.storefrontService.getThemeComponents(storefrontId, 'product').subscribe({
      next: (response) => {
        const remote = (response.components || []).filter((component): component is ProductComponentDefinition => this.isProductSectionType(component.type));
        if (remote.length) this.components = remote;
      },
    });
  }

  private createPreviewSession(): void {
    if (!this.storefront || !this.productsLoaded || !this.themeLoaded || !this.selectedProductId) return;
    const storefrontId = this.storefront.id;
    this.storefrontService.createThemePreviewSession(storefrontId, 'product').subscribe({
      next: (session: StorefrontThemePreviewSession) => {
        if (this.storefront?.id !== storefrontId) return;
        this.previewSessionUrl = session.preview_url;
        this.updateProductPreviewUrl();
      },
      error: (err) => {
        if (this.storefront?.id !== storefrontId) return;
        this.errorMessage = err?.error?.detail || 'No se pudo abrir la vista previa del producto.';
      },
    });
  }

  private updateProductPreviewUrl(): void {
    const product = this.selectedProduct;
    if (!product || !this.previewSessionUrl) return;
    try {
      const url = new URL(this.previewSessionUrl);
      url.pathname = `/products/${encodeURIComponent(product.slug)}`;
      this.previewUrl = url.toString();
      this.previewOrigin = url.origin;
      this.safePreviewUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.previewUrl);
    } catch {
      this.previewUrl = '';
      this.safePreviewUrl = null;
    }
  }

  private pushPreview(): void {
    const frame = this.previewFrame?.nativeElement;
    if (!frame?.contentWindow || !this.previewUrl) return;
    this.previewRequestId += 1;
    frame.contentWindow.postMessage({
      type: 'lumefy:preview:apply',
      template: 'product',
      requestId: this.previewRequestId,
      selectedSectionId: this.selectedSectionId,
      selectionMode: this.selectionMode,
      document: this.serializeDocument(),
    }, this.previewOrigin || '*');
  }

  private serializeDocument(): Record<string, unknown> {
    return JSON.parse(JSON.stringify(this.document)) as Record<string, unknown>;
  }

  private markDirty(): void {
    this.dirty = true;
    this.errorMessage = '';
    this.pushPreview();
  }

  private normalizeDocument(raw: Record<string, unknown>): ProductTemplateDocument {
    const source = raw && typeof raw === 'object' ? raw : {};
    const rawSettings = source['settings'] && typeof source['settings'] === 'object' && !Array.isArray(source['settings'])
      ? source['settings'] as Record<string, unknown>
      : {};
    const rawContent = rawSettings['content'] && typeof rawSettings['content'] === 'object' && !Array.isArray(rawSettings['content'])
      ? rawSettings['content'] as Record<string, unknown>
      : {};
    const defaultDocument = this.createDocument();
    const sections = Array.isArray(source['sections'])
      ? source['sections']
        .filter((section): section is Record<string, unknown> => Boolean(section) && typeof section === 'object')
        .map((section, index) => ({
          id: String(section['id'] || `product-section-${index + 1}`),
          type: this.isProductSectionType(section['type']) ? section['type'] : 'product_information',
          enabled: section['enabled'] !== false,
          settings: section['settings'] && typeof section['settings'] === 'object' && !Array.isArray(section['settings'])
            ? section['settings'] as Record<string, unknown>
            : {},
          blocks: Array.isArray(section['blocks']) ? section['blocks'].filter((block): block is Record<string, unknown> => Boolean(block) && typeof block === 'object') : [],
        }))
      : defaultDocument.sections;
    return {
      schema_version: Number(source['schema_version'] || 1),
      template: 'product',
      settings: {
        ...defaultDocument.settings,
        ...rawSettings,
        content: {
          ...defaultDocument.settings.content,
          ...rawContent,
        },
      },
      sections: sections.length ? sections : defaultDocument.sections,
    };
  }

  private createDocument(): ProductTemplateDocument {
    return {
      schema_version: 1,
      template: 'product',
      settings: {
        content: {
          breadcrumb_title: 'Detalle del producto',
          price_label: 'Precio',
          stock_in_label: 'Disponible',
          stock_out_label: 'Agotado',
          free_delivery_text: 'Entrega disponible según cobertura',
          promo_text: 'Compra segura y atención personalizada',
          description_tab_label: 'Descripción',
          details_tab_label: 'Información adicional',
          reviews_tab_label: 'Reseñas',
          reviews_empty_title: 'Reseñas próximamente',
          reviews_empty_description: 'Aún no hay reseñas publicadas para este producto.',
          submit_review_label: 'Escribir reseña',
        },
      },
      sections: PRODUCT_COMPONENTS.map((component) => ({
        id: component.type,
        type: component.type,
        enabled: true,
        settings: {},
        blocks: [],
      })),
    };
  }

  private isProductSectionType(value: unknown): value is ProductSectionType {
    return PRODUCT_COMPONENTS.some((component) => component.type === value);
  }
}
