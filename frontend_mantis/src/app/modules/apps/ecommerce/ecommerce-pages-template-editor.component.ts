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

type PageSlug = 'contact' | 'about' | 'shipping' | 'returns' | 'privacy' | 'terms';
type PageSectionType = 'page_header' | 'page_content' | 'page_contact_form';
type SidebarMode = 'sections' | 'settings' | 'section' | 'add';
type Viewport = 'desktop' | 'tablet' | 'mobile';

interface PageCopy {
  eyebrow: string;
  title: string;
  description: string;
  body: string;
}

interface PageSection {
  id: string;
  type: PageSectionType;
  enabled: boolean;
  settings: Record<string, unknown>;
  blocks: Record<string, unknown>[];
}

interface PagesTemplateDocument {
  schema_version: number;
  template: 'pages';
  settings: { pages: Record<PageSlug, PageCopy>; [key: string]: unknown };
  sections: PageSection[];
}

interface PageOption { slug: PageSlug; label: string; description: string; }
interface PageComponentDefinition extends StorefrontThemeComponent { type: PageSectionType; }

const PAGE_OPTIONS: PageOption[] = [
  { slug: 'contact', label: 'Contacto', description: 'Ayuda, soporte y formulario de contacto.' },
  { slug: 'about', label: 'Sobre nosotros', description: 'Historia, valores y propuesta de la tienda.' },
  { slug: 'shipping', label: 'Envíos y entregas', description: 'Zonas, tiempos y condiciones de entrega.' },
  { slug: 'returns', label: 'Cambios y devoluciones', description: 'Condiciones para respaldar cada compra.' },
  { slug: 'privacy', label: 'Política de privacidad', description: 'Información sobre el uso de datos.' },
  { slug: 'terms', label: 'Términos y condiciones', description: 'Reglas de uso y compra en la tienda.' },
];

const PAGE_COMPONENTS: PageComponentDefinition[] = [
  { type: 'page_header', label: 'Encabezado de la página', description: 'Título, introducción y contexto.', icon: 'heading' },
  { type: 'page_content', label: 'Contenido informativo', description: 'Texto principal de la página.', icon: 'article' },
  { type: 'page_contact_form', label: 'Formulario de contacto', description: 'Canal para recibir mensajes de clientes.', icon: 'mail' },
];

@Component({
  selector: 'app-ecommerce-pages-template-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, DragDropModule, RouterLink, EcommerceEditorPagePickerComponent],
  templateUrl: './ecommerce-pages-template-editor.component.html',
  styleUrls: ['./ecommerce-pages-template-editor.component.scss'],
})
export class EcommercePagesTemplateEditorComponent implements OnInit, OnDestroy {
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
  sidebarMode: SidebarMode = 'sections';
  selectionMode = true;
  previewReady = false;
  errorMessage = '';
  storefronts: Storefront[] = [];
  storefront: Storefront | null = null;
  selectedStorefrontId = '';
  theme: StorefrontThemeDocument | null = null;
  document: PagesTemplateDocument = this.createDocument();
  components: PageComponentDefinition[] = PAGE_COMPONENTS;
  selectedPageSlug: PageSlug = 'contact';
  selectedSectionId = '';
  previewUrl = '';
  safePreviewUrl: SafeResourceUrl | null = null;
  previewViewport: Viewport = 'desktop';

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

  ngOnDestroy(): void { window.removeEventListener('message', this.onWindowMessage); }

  get pageOptions(): PageOption[] { return PAGE_OPTIONS; }
  get selectedPage(): PageOption { return PAGE_OPTIONS.find((page) => page.slug === this.selectedPageSlug) || PAGE_OPTIONS[0]; }
  get pageCopy(): PageCopy { return this.document.settings.pages[this.selectedPageSlug]; }
  get selectedSection(): PageSection | null { return this.document.sections.find((section) => section.id === this.selectedSectionId) || null; }
  get sectionCountLabel(): string { return `${this.document.sections.length}/20`; }
  get canAddSection(): boolean { return this.document.sections.length < 20; }
  get availableComponents(): PageComponentDefinition[] { return this.components.filter((component) => !this.document.sections.some((section) => section.type === component.type)); }
  get canPublish(): boolean { return Boolean(this.theme && !this.saving && !this.publishing); }

  pageLabel(slug: string): string { return PAGE_OPTIONS.find((page) => page.slug === slug)?.label || 'Página informativa'; }
  pageIcon(slug: PageSlug): string {
    const icons: Record<PageSlug, string> = {
      contact: 'ti ti-message-circle',
      about: 'ti ti-building-store',
      shipping: 'ti ti-truck-delivery',
      returns: 'ti ti-receipt-refund',
      privacy: 'ti ti-shield-lock',
      terms: 'ti ti-file-description',
    };
    return icons[slug];
  }
  sectionLabel(section: PageSection): string { return this.components.find((component) => component.type === section.type)?.label || 'Sección informativa'; }
  componentIcon(type: string): string { return `ti ti-${this.components.find((component) => component.type === type)?.icon || 'article'}`; }

  showSections(): void { this.sidebarOpen = true; this.sidebarMode = 'sections'; this.pushPreview(); }
  showSettings(): void { this.sidebarOpen = true; this.sidebarMode = 'settings'; this.selectedSectionId = ''; this.pushPreview(); }
  openAddSections(): void { this.sidebarOpen = true; this.sidebarMode = 'add'; this.pushPreview(); }
  selectSection(section: PageSection): void { this.selectedSectionId = section.id; this.sidebarOpen = true; this.sidebarMode = 'section'; this.pushPreview(); }
  toggleSidebar(): void { this.sidebarOpen = !this.sidebarOpen; }

  selectPage(slug: PageSlug): void {
    if (this.selectedPageSlug === slug) return;
    this.selectedPageSlug = slug;
    this.onPageChange();
  }

  onPageChange(): void { this.selectedSectionId = ''; this.sidebarMode = 'sections'; this.updatePreviewUrl(); this.pushPreview(); }
  updatePageField(key: keyof PageCopy, value: string): void { this.pageCopy[key] = value; this.markDirty(); }
  setViewport(viewport: Viewport): void { this.previewViewport = viewport; }
  toggleSelectionMode(): void { this.selectionMode = !this.selectionMode; this.pushPreview(); }
  onPreviewLoad(): void { this.previewReady = false; window.setTimeout(() => this.pushPreview(), 50); }

  drop(event: CdkDragDrop<PageSection[]>): void {
    if (event.previousIndex === event.currentIndex) return;
    moveItemInArray(this.document.sections, event.previousIndex, event.currentIndex);
    this.markDirty();
  }

  addSection(type: string): void {
    if (!this.isPageSectionType(type) || !this.canAddSection || this.document.sections.some((section) => section.type === type)) return;
    const id = `${type}-${Date.now()}`;
    this.document.sections.push({ id, type, enabled: true, settings: {}, blocks: [] });
    this.selectedSectionId = id;
    this.sidebarMode = 'section';
    this.markDirty();
  }

  removeSection(section: PageSection, event?: Event): void {
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

  toggleSection(section: PageSection, event: Event): void { section.enabled = (event.target as HTMLInputElement).checked; this.markDirty(); }

  saveDraft(afterSave?: () => void, showSuccessNotification = true): void {
    if (!this.storefront || !this.theme || this.saving) return;
    this.saving = true;
    this.errorMessage = '';
    this.storefrontService.saveThemeDraft(this.storefront.id, this.serializeDocument(), this.theme.draft_version, 'pages').subscribe({
      next: (theme) => {
        this.theme = theme;
        this.document = this.normalizeDocument(theme.draft_document);
        this.dirty = false;
        this.saving = false;
        this.pushPreview();
        if (showSuccessNotification) this.swal.toast('Cambios guardados en páginas informativas', 'success');
        afterSave?.();
      },
      error: (err) => { this.saving = false; this.errorMessage = err?.error?.detail || 'No se pudo guardar la plantilla informativa.'; },
    });
  }

  publish(): void {
    if (!this.storefront || !this.theme || this.publishing) return;
    const publishNow = (): void => {
      if (!this.storefront || !this.theme) return;
      this.publishing = true;
      this.storefrontService.publishTheme(this.storefront.id, this.theme.draft_version, 'pages').subscribe({
        next: (theme) => {
          this.theme = theme;
          this.document = this.normalizeDocument(theme.draft_document);
          this.dirty = false;
          this.publishing = false;
          this.swal.success('Páginas publicadas', 'Los cambios ya están disponibles para tus clientes.');
          this.pushPreview();
        },
        error: (err) => { this.publishing = false; this.errorMessage = err?.error?.detail || 'No se pudieron publicar las páginas.'; },
      });
    };
    if (this.dirty) this.saveDraft(publishNow, false); else publishNow();
  }

  private loadStorefronts(): void {
    this.loading = true;
    this.errorMessage = '';
    this.storefrontService.getStorefronts().subscribe({
      next: (storefronts) => { this.storefronts = storefronts; this.selectedStorefrontId = this.context.resolveSelectedStorefront(storefronts); this.applySelectedStorefront(); },
      error: (err) => { this.loading = false; this.errorMessage = err?.error?.detail || 'No se pudieron cargar las tiendas.'; },
    });
  }

  onStorefrontChange(): void {
    if (this.dirty && !window.confirm('Tienes cambios sin guardar. ¿Quieres cambiar de tienda y descartarlos?')) { this.selectedStorefrontId = this.lastAppliedStorefrontId; return; }
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
    if (!this.storefront) { this.loading = false; return; }

    const storefrontId = this.storefront.id;
    this.loading = true;
    this.storefrontService.getThemeDocument(storefrontId, 'pages').subscribe({
      next: (theme) => {
        if (this.storefront?.id !== storefrontId) return;
        this.theme = theme;
        this.document = this.normalizeDocument(theme.draft_document);
        this.selectedSectionId = this.document.sections[0]?.id || '';
        this.loading = false;
        this.createPreviewSession();
      },
      error: (err) => { if (this.storefront?.id !== storefrontId) return; this.loading = false; this.errorMessage = err?.error?.detail || 'No se pudo cargar la plantilla informativa.'; },
    });
    this.storefrontService.getThemeComponents(storefrontId, 'pages').subscribe({
      next: (response) => { const remote = (response.components || []).filter((component): component is PageComponentDefinition => this.isPageSectionType(component.type)); if (remote.length) this.components = remote; },
    });
  }

  private createPreviewSession(): void {
    if (!this.storefront || !this.theme) return;
    const storefrontId = this.storefront.id;
    this.storefrontService.createThemePreviewSession(storefrontId, 'pages').subscribe({
      next: (session: StorefrontThemePreviewSession) => { if (this.storefront?.id !== storefrontId) return; this.previewSessionUrl = session.preview_url; this.updatePreviewUrl(); },
      error: (err) => { if (this.storefront?.id !== storefrontId) return; this.errorMessage = err?.error?.detail || 'No se pudo abrir la vista previa.'; },
    });
  }

  private updatePreviewUrl(): void {
    if (!this.previewSessionUrl) return;
    try {
      const url = new URL(this.previewSessionUrl);
      url.pathname = `/pages/${this.selectedPageSlug}`;
      this.previewUrl = url.toString();
      this.previewOrigin = url.origin;
      this.safePreviewUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.previewUrl);
    } catch { this.previewUrl = ''; this.safePreviewUrl = null; }
  }

  private pushPreview(): void {
    const frame = this.previewFrame?.nativeElement;
    if (!frame?.contentWindow || !this.previewUrl) return;
    this.previewRequestId += 1;
    frame.contentWindow.postMessage({ type: 'lumefy:preview:apply', template: 'pages', requestId: this.previewRequestId, pageSlug: this.selectedPageSlug, selectedSectionId: this.selectedSectionId, selectionMode: this.selectionMode, document: this.serializeDocument() }, this.previewOrigin || '*');
  }

  private serializeDocument(): Record<string, unknown> { return JSON.parse(JSON.stringify(this.document)) as Record<string, unknown>; }
  private markDirty(): void { this.dirty = true; this.errorMessage = ''; this.pushPreview(); }

  private normalizeDocument(raw: Record<string, unknown>): PagesTemplateDocument {
    const source = raw && typeof raw === 'object' ? raw : {};
    const rawSettings = source['settings'] && typeof source['settings'] === 'object' && !Array.isArray(source['settings']) ? source['settings'] as Record<string, unknown> : {};
    const rawPages = rawSettings['pages'] && typeof rawSettings['pages'] === 'object' && !Array.isArray(rawSettings['pages']) ? rawSettings['pages'] as Record<string, unknown> : {};
    const defaults = this.createDocument();
    const pages = { ...defaults.settings.pages };
    for (const option of PAGE_OPTIONS) {
      const value = rawPages[option.slug];
      if (!value || typeof value !== 'object' || Array.isArray(value)) continue;
      pages[option.slug] = { ...pages[option.slug], ...(value as Partial<PageCopy>) };
    }
    const sections = Array.isArray(source['sections']) ? source['sections'].filter((section): section is Record<string, unknown> => Boolean(section) && typeof section === 'object').map((section, index) => ({
      id: String(section['id'] || `page-section-${index + 1}`),
      type: this.isPageSectionType(section['type']) ? section['type'] : 'page_content' as PageSectionType,
      enabled: section['enabled'] !== false,
      settings: section['settings'] && typeof section['settings'] === 'object' && !Array.isArray(section['settings']) ? section['settings'] as Record<string, unknown> : {},
      blocks: Array.isArray(section['blocks']) ? section['blocks'].filter((block): block is Record<string, unknown> => Boolean(block) && typeof block === 'object') : [],
    })) : defaults.sections;
    return { schema_version: Number(source['schema_version'] || 1), template: 'pages', settings: { ...defaults.settings, ...rawSettings, pages }, sections: sections.length ? sections : defaults.sections };
  }

  private createDocument(): PagesTemplateDocument {
    const pages = {
      contact: { eyebrow: 'Estamos para ayudarte', title: 'Contacto', description: 'Cuéntanos cómo podemos ayudarte y te responderemos lo antes posible.', body: 'Nuestro equipo está disponible para resolver tus dudas sobre productos, pedidos y entregas.' },
      about: { eyebrow: 'Conoce nuestra tienda', title: 'Sobre nosotros', description: 'Una experiencia de compra pensada para ti.', body: 'Aquí puedes contar la historia de tu negocio, tus valores y lo que hace especial a tu marca.' },
      shipping: { eyebrow: 'Compra con tranquilidad', title: 'Envíos y entregas', description: 'Información clara para recibir tu pedido.', body: 'Agrega aquí las zonas de cobertura, tiempos estimados y condiciones de entrega de tu tienda.' },
      returns: { eyebrow: 'Tu compra está respaldada', title: 'Cambios y devoluciones', description: 'Consulta las condiciones para solicitar un cambio o devolución.', body: 'Describe aquí los plazos, requisitos y pasos que deben seguir tus clientes.' },
      privacy: { eyebrow: 'Tu información importa', title: 'Política de privacidad', description: 'Conoce cómo cuidamos y utilizamos tus datos.', body: 'Escribe aquí la política de privacidad de tu tienda y la forma en que gestionas la información de tus clientes.' },
      terms: { eyebrow: 'Condiciones de uso', title: 'Términos y condiciones', description: 'Las reglas que aplican a las compras en esta tienda.', body: 'Escribe aquí los términos y condiciones que deben conocer tus clientes antes de comprar.' },
    } as Record<PageSlug, PageCopy>;
    return { schema_version: 1, template: 'pages', settings: { pages }, sections: PAGE_COMPONENTS.map((component) => ({ id: component.type, type: component.type, enabled: true, settings: {}, blocks: [] })) };
  }

  private isPageSectionType(value: unknown): value is PageSectionType { return PAGE_COMPONENTS.some((component) => component.type === value); }
}
