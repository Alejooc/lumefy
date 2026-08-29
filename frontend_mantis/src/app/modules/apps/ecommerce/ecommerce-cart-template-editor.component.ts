import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnDestroy, OnInit, ViewChild, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CdkDragDrop, DragDropModule, moveItemInArray } from '@angular/cdk/drag-drop';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import {
  Storefront,
  StorefrontAdminService,
  StorefrontThemeComponent,
  StorefrontThemeDocument,
  StorefrontThemePreviewSession,
} from 'src/app/core/services/storefront-admin.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';
import { EcommerceEditorPagePickerComponent } from './ecommerce-editor-page-picker.component';

type CartSectionType = 'cart_header' | 'cart_items' | 'cart_summary' | 'cart_empty';
type CartSidebarMode = 'sections' | 'settings' | 'section' | 'add';
type CartViewport = 'desktop' | 'tablet' | 'mobile';

interface CartSection {
  id: string;
  type: CartSectionType;
  enabled: boolean;
  settings: Record<string, unknown>;
  blocks: Record<string, unknown>[];
}

interface CartContentSettings {
  breadcrumb_title: string;
  title: string;
  clear_cart_label: string;
  product_label: string;
  price_label: string;
  quantity_label: string;
  subtotal_label: string;
  action_label: string;
  summary_title: string;
  total_label: string;
  checkout_label: string;
  empty_title: string;
  empty_description: string;
  continue_shopping_label: string;
}

interface CartTemplateDocument {
  schema_version: number;
  template: 'cart';
  settings: { content: CartContentSettings; [key: string]: unknown };
  sections: CartSection[];
}

interface CartComponentDefinition extends StorefrontThemeComponent {
  type: CartSectionType;
}

const CART_COMPONENTS: CartComponentDefinition[] = [
  { type: 'cart_header', label: 'Encabezado del carrito', description: 'Título y acción para vaciar el carrito.', icon: 'shopping-cart' },
  { type: 'cart_items', label: 'Productos del carrito', description: 'Listado, cantidades y subtotales.', icon: 'list-details' },
  { type: 'cart_summary', label: 'Resumen del pedido', description: 'Totales y acceso al checkout.', icon: 'receipt' },
  { type: 'cart_empty', label: 'Carrito vacío', description: 'Mensaje y llamada a seguir comprando.', icon: 'shopping-cart-off' },
];

@Component({
  selector: 'app-ecommerce-cart-template-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, DragDropModule, RouterLink, EcommerceEditorPagePickerComponent],
  templateUrl: './ecommerce-cart-template-editor.component.html',
  styleUrls: ['./ecommerce-cart-template-editor.component.scss'],
})
export class EcommerceCartTemplateEditorComponent implements OnInit, OnDestroy {
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
  sidebarMode: CartSidebarMode = 'sections';
  selectionMode = true;
  previewReady = false;
  errorMessage = '';
  storefronts: Storefront[] = [];
  storefront: Storefront | null = null;
  selectedStorefrontId = '';
  theme: StorefrontThemeDocument | null = null;
  document: CartTemplateDocument = this.createDocument();
  components: CartComponentDefinition[] = CART_COMPONENTS;
  selectedSectionId = '';
  previewUrl = '';
  safePreviewUrl: SafeResourceUrl | null = null;
  previewViewport: CartViewport = 'desktop';

  private previewOrigin = '';
  private previewRequestId = 0;
  private previewSessionUrl = '';
  private lastAppliedStorefrontId = '';
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

  get selectedSection(): CartSection | null {
    return this.document.sections.find((section) => section.id === this.selectedSectionId) || null;
  }

  get content(): CartContentSettings {
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

  get availableComponents(): CartComponentDefinition[] {
    return this.components.filter((component) => !this.document.sections.some((section) => section.type === component.type));
  }

  get canPublish(): boolean {
    return Boolean(this.theme && !this.saving && !this.publishing);
  }

  getSectionSetting(key: string, fallback: boolean | number | string): boolean | number | string {
    const value = this.selectedSectionSettings[key];
    return value === undefined || value === null ? fallback : value as boolean | number | string;
  }

  sectionLabel(section: CartSection): string {
    return this.components.find((component) => component.type === section.type)?.label || 'Sección del carrito';
  }

  componentIcon(type: string): string {
    const icon = this.components.find((component) => component.type === type)?.icon || 'shopping-cart';
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

  selectSection(section: CartSection): void {
    this.selectedSectionId = section.id;
    this.sidebarOpen = true;
    this.sidebarMode = 'section';
    this.pushPreview();
  }

  toggleSidebar(): void {
    this.sidebarOpen = !this.sidebarOpen;
  }

  drop(event: CdkDragDrop<CartSection[]>): void {
    if (event.previousIndex === event.currentIndex) return;
    moveItemInArray(this.document.sections, event.previousIndex, event.currentIndex);
    this.markDirty();
  }

  addSection(type: string): void {
    if (!this.isCartSectionType(type) || !this.canAddSection || this.document.sections.some((section) => section.type === type)) return;
    const id = `${type}-${Date.now()}`;
    this.document.sections.push({ id, type, enabled: true, settings: {}, blocks: [] });
    this.selectedSectionId = id;
    this.sidebarMode = 'section';
    this.markDirty();
  }

  removeSection(section: CartSection, event?: Event): void {
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

  toggleSection(section: CartSection, event: Event): void {
    section.enabled = (event.target as HTMLInputElement).checked;
    this.markDirty();
  }

  updateSectionSetting(key: string, value: unknown): void {
    const section = this.selectedSection;
    if (!section) return;
    section.settings[key] = value;
    this.markDirty();
  }

  updateContentSetting(key: keyof CartContentSettings, value: string): void {
    this.content[key] = value;
    this.markDirty();
  }

  setViewport(viewport: CartViewport): void {
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
    this.storefrontService.saveThemeDraft(this.storefront.id, this.serializeDocument(), this.theme.draft_version, 'cart').subscribe({
      next: (theme) => {
        this.theme = theme;
        this.document = this.normalizeDocument(theme.draft_document);
        this.dirty = false;
        this.saving = false;
        this.pushPreview();
        if (showSuccessNotification) this.swal.toast('Cambios guardados en el carrito', 'success');
        afterSave?.();
      },
      error: (err) => {
        this.saving = false;
        this.errorMessage = err?.error?.detail || 'No se pudo guardar la plantilla del carrito.';
      },
    });
  }

  publish(): void {
    if (!this.storefront || !this.theme || this.publishing) return;
    const publishNow = (): void => {
      if (!this.storefront || !this.theme) return;
      this.publishing = true;
      this.storefrontService.publishTheme(this.storefront.id, this.theme.draft_version, 'cart').subscribe({
        next: (theme) => {
          this.theme = theme;
          this.document = this.normalizeDocument(theme.draft_document);
          this.dirty = false;
          this.publishing = false;
          this.swal.success('Plantilla publicada', 'La página del carrito ya usa estos cambios.');
          this.pushPreview();
        },
        error: (err) => {
          this.publishing = false;
          this.errorMessage = err?.error?.detail || 'No se pudo publicar la plantilla del carrito.';
        },
      });
    };
    if (this.dirty) this.saveDraft(publishNow, false);
    else publishNow();
  }

  private loadStorefronts(): void {
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
    this.selectedSectionId = '';
    this.previewUrl = '';
    this.safePreviewUrl = null;
    this.previewOrigin = '';
    this.previewSessionUrl = '';
    this.dirty = false;
    if (!this.storefront) {
      this.loading = false;
      return;
    }

    const storefrontId = this.storefront.id;
    this.loading = true;
    this.storefrontService.getThemeDocument(storefrontId, 'cart').subscribe({
      next: (theme) => {
        if (this.storefront?.id !== storefrontId) return;
        this.theme = theme;
        this.document = this.normalizeDocument(theme.draft_document);
        this.selectedSectionId = this.document.sections[0]?.id || '';
        this.loading = false;
        this.createPreviewSession();
      },
      error: (err) => {
        if (this.storefront?.id !== storefrontId) return;
        this.loading = false;
        this.errorMessage = err?.error?.detail || 'No se pudo cargar la plantilla del carrito.';
      },
    });
    this.storefrontService.getThemeComponents(storefrontId, 'cart').subscribe({
      next: (response) => {
        const remote = (response.components || []).filter((component): component is CartComponentDefinition => this.isCartSectionType(component.type));
        if (remote.length) this.components = remote;
      },
    });
  }

  private createPreviewSession(): void {
    if (!this.storefront || !this.theme) return;
    const storefrontId = this.storefront.id;
    this.storefrontService.createThemePreviewSession(storefrontId, 'cart').subscribe({
      next: (session: StorefrontThemePreviewSession) => {
        if (this.storefront?.id !== storefrontId) return;
        this.previewSessionUrl = session.preview_url;
        this.updatePreviewUrl();
      },
      error: (err) => {
        if (this.storefront?.id !== storefrontId) return;
        this.errorMessage = err?.error?.detail || 'No se pudo abrir la vista previa del carrito.';
      },
    });
  }

  private updatePreviewUrl(): void {
    if (!this.previewSessionUrl) return;
    try {
      const url = new URL(this.previewSessionUrl);
      url.pathname = '/cart';
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
      template: 'cart',
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

  private normalizeDocument(raw: Record<string, unknown>): CartTemplateDocument {
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
          id: String(section['id'] || `cart-section-${index + 1}`),
          type: this.isCartSectionType(section['type']) ? section['type'] : 'cart_items' as CartSectionType,
          enabled: section['enabled'] !== false,
          settings: section['settings'] && typeof section['settings'] === 'object' && !Array.isArray(section['settings']) ? section['settings'] as Record<string, unknown> : {},
          blocks: Array.isArray(section['blocks']) ? section['blocks'].filter((block): block is Record<string, unknown> => Boolean(block) && typeof block === 'object') : [],
        }))
      : defaultDocument.sections;
    return {
      schema_version: Number(source['schema_version'] || 1),
      template: 'cart',
      settings: { ...defaultDocument.settings, ...rawSettings, content: { ...defaultDocument.settings.content, ...rawContent } },
      sections: sections.length ? sections : defaultDocument.sections,
    };
  }

  private createDocument(): CartTemplateDocument {
    return {
      schema_version: 1,
      template: 'cart',
      settings: {
        content: {
          breadcrumb_title: 'Carrito',
          title: 'Tu carrito',
          clear_cart_label: 'Vaciar carrito',
          product_label: 'Producto',
          price_label: 'Precio',
          quantity_label: 'Cantidad',
          subtotal_label: 'Subtotal',
          action_label: 'Acción',
          summary_title: 'Resumen del pedido',
          total_label: 'Total',
          checkout_label: 'Ir al checkout',
          empty_title: 'Tu carrito está vacío',
          empty_description: 'Agrega productos para continuar con tu compra.',
          continue_shopping_label: 'Seguir comprando',
        },
      },
      sections: CART_COMPONENTS.map((component) => ({ id: component.type, type: component.type, enabled: true, settings: {}, blocks: [] })),
    };
  }

  private isCartSectionType(value: unknown): value is CartSectionType {
    return CART_COMPONENTS.some((component) => component.type === value);
  }
}
