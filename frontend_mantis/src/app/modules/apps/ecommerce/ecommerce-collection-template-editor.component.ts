import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnDestroy, OnInit, ViewChild, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CdkDragDrop, DragDropModule, moveItemInArray } from '@angular/cdk/drag-drop';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import {
  StoreCollection,
  Storefront,
  StorefrontAdminService,
  StorefrontThemeComponent,
  StorefrontThemeDocument,
  StorefrontThemePreviewSession,
} from 'src/app/core/services/storefront-admin.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';
import { EcommerceEditorPagePickerComponent } from './ecommerce-editor-page-picker.component';

type CatalogSectionType = 'collection_header' | 'collection_filters' | 'collection_grid' | 'search_header' | 'search_filters' | 'search_grid';
type CollectionSidebarMode = 'sections' | 'settings' | 'section' | 'add';
type CollectionViewport = 'desktop' | 'tablet' | 'mobile';

interface CollectionSection {
  id: string;
  type: CatalogSectionType;
  enabled: boolean;
  settings: Record<string, unknown>;
  blocks: Record<string, unknown>[];
}

interface CollectionContentSettings {
  breadcrumb_title: string;
  products_label: string;
  filters_label: string;
  sort_label: string;
  clear_filters_label: string;
  empty_title: string;
  empty_description: string;
}

interface CollectionTemplateDocument {
  schema_version: number;
  template: 'collection' | 'search';
  settings: { content: CollectionContentSettings; [key: string]: unknown };
  sections: CollectionSection[];
}

interface CollectionComponentDefinition extends StorefrontThemeComponent {
  type: CatalogSectionType;
}

const COLLECTION_COMPONENTS: CollectionComponentDefinition[] = [
  { type: 'collection_header', label: 'Encabezado de colección', description: 'Nombre y descripción de la colección.', icon: 'heading' },
  { type: 'collection_filters', label: 'Filtros y orden', description: 'Filtros, ordenamiento y navegación.', icon: 'adjustments' },
  { type: 'collection_grid', label: 'Grilla de productos', description: 'Productos, columnas y estado vacío.', icon: 'layout-grid' },
];

const SEARCH_COMPONENTS: CollectionComponentDefinition[] = [
  { type: 'search_header', label: 'Encabezado de búsqueda', description: 'Título y contexto de los resultados.', icon: 'search' },
  { type: 'search_filters', label: 'Filtros y orden', description: 'Filtros, ordenamiento y navegación.', icon: 'adjustments' },
  { type: 'search_grid', label: 'Grilla de resultados', description: 'Resultados, columnas y estado vacío.', icon: 'layout-grid' },
];

@Component({
  selector: 'app-ecommerce-collection-template-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, DragDropModule, RouterLink, EcommerceEditorPagePickerComponent],
  templateUrl: './ecommerce-collection-template-editor.component.html',
  styleUrls: ['./ecommerce-collection-template-editor.component.scss'],
})
export class EcommerceCollectionTemplateEditorComponent implements OnInit, OnDestroy {
  private storefrontService = inject(StorefrontAdminService);
  private context = inject(EcommerceContextService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);
  private sanitizer = inject(DomSanitizer);
  private route = inject(ActivatedRoute);

  @ViewChild('previewFrame') previewFrame?: ElementRef<HTMLIFrameElement>;

  loading = false;
  saving = false;
  publishing = false;
  dirty = false;
  sidebarOpen = true;
  sidebarMode: CollectionSidebarMode = 'sections';
  selectionMode = true;
  previewReady = false;
  errorMessage = '';
  storefronts: Storefront[] = [];
  storefront: Storefront | null = null;
  selectedStorefrontId = '';
  collections: StoreCollection[] = [];
  selectedCollectionId = '';
  theme: StorefrontThemeDocument | null = null;
  document: CollectionTemplateDocument = this.createDocument();
  components: CollectionComponentDefinition[] = COLLECTION_COMPONENTS;
  templateKey: 'collection' | 'search' = 'collection';
  selectedSectionId = '';
  previewUrl = '';
  safePreviewUrl: SafeResourceUrl | null = null;
  previewViewport: CollectionViewport = 'desktop';

  private previewOrigin = '';
  private previewRequestId = 0;
  private previewSessionUrl = '';
  private lastAppliedStorefrontId = '';
  private collectionsLoaded = false;
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
    this.templateKey = this.route.snapshot.data['templateKey'] === 'search' ? 'search' : 'collection';
    this.components = this.templateComponents;
    this.document = this.createDocument();
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

  get selectedSection(): CollectionSection | null {
    return this.document.sections.find((section) => section.id === this.selectedSectionId) || null;
  }

  get selectedCollection(): StoreCollection | null {
    return this.collections.find((collection) => collection.id === this.selectedCollectionId) || null;
  }

  get isSearchTemplate(): boolean {
    return this.templateKey === 'search';
  }

  get templateComponents(): CollectionComponentDefinition[] {
    return this.isSearchTemplate ? SEARCH_COMPONENTS : COLLECTION_COMPONENTS;
  }

  get templateTitle(): string {
    return this.isSearchTemplate ? 'Resultados de búsqueda' : 'Colección';
  }

  get templateDescription(): string {
    return this.isSearchTemplate
      ? 'Organiza cómo tus clientes encuentran productos.'
      : 'Organiza cómo tus clientes exploran el catálogo.';
  }

  get content(): CollectionContentSettings {
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

  get availableComponents(): CollectionComponentDefinition[] {
    return this.components.filter((component) => !this.document.sections.some((section) => section.type === component.type));
  }

  get canPublish(): boolean {
    return Boolean(this.theme && (this.isSearchTemplate || this.selectedCollection) && !this.saving && !this.publishing);
  }

  getSectionSetting(key: string, fallback: boolean | number | string): boolean | number | string {
    const value = this.selectedSectionSettings[key];
    return value === undefined || value === null ? fallback : value as boolean | number | string;
  }

  sectionLabel(section: CollectionSection): string {
    return this.components.find((component) => component.type === section.type)?.label || 'Sección de colección';
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

  selectSection(section: CollectionSection): void {
    this.selectedSectionId = section.id;
    this.sidebarOpen = true;
    this.sidebarMode = 'section';
    this.pushPreview();
  }

  toggleSidebar(): void {
    this.sidebarOpen = !this.sidebarOpen;
  }

  drop(event: CdkDragDrop<CollectionSection[]>): void {
    if (event.previousIndex === event.currentIndex) return;
    moveItemInArray(this.document.sections, event.previousIndex, event.currentIndex);
    this.markDirty();
  }

  addSection(type: string): void {
    if (!this.isCatalogSectionType(type) || !this.canAddSection || this.document.sections.some((section) => section.type === type)) return;
    const id = `${type}-${Date.now()}`;
    this.document.sections.push({ id, type, enabled: true, settings: {}, blocks: [] });
    this.selectedSectionId = id;
    this.sidebarMode = 'section';
    this.markDirty();
  }

  removeSection(section: CollectionSection, event?: Event): void {
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

  toggleSection(section: CollectionSection, event: Event): void {
    section.enabled = (event.target as HTMLInputElement).checked;
    this.markDirty();
  }

  updateSectionSetting(key: string, value: unknown): void {
    const section = this.selectedSection;
    if (!section) return;
    section.settings[key] = value;
    this.markDirty();
  }

  updateContentSetting(key: keyof CollectionContentSettings, value: string): void {
    this.content[key] = value;
    this.markDirty();
  }

  onCollectionChange(): void {
    this.updateCollectionPreviewUrl();
    this.pushPreview();
  }

  setViewport(viewport: CollectionViewport): void {
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
      this.templateKey,
    ).subscribe({
      next: (theme) => {
        this.theme = theme;
        this.document = this.normalizeDocument(theme.draft_document);
        this.dirty = false;
        this.saving = false;
        this.pushPreview();
        if (showSuccessNotification) this.swal.toast(`Cambios guardados en ${this.templateTitle.toLowerCase()}`, 'success');
        afterSave?.();
      },
      error: (err) => {
        this.saving = false;
        this.errorMessage = err?.error?.detail || `No se pudo guardar la plantilla de ${this.templateTitle.toLowerCase()}.`;
      },
    });
  }

  publish(): void {
    if (!this.storefront || !this.theme || this.publishing) return;
    const publishNow = (): void => {
      if (!this.storefront || !this.theme) return;
      this.publishing = true;
      this.storefrontService.publishTheme(this.storefront.id, this.theme.draft_version, this.templateKey).subscribe({
        next: (theme) => {
          this.theme = theme;
          this.document = this.normalizeDocument(theme.draft_document);
          this.dirty = false;
          this.publishing = false;
          this.swal.success('Plantilla publicada', `La página de ${this.templateTitle.toLowerCase()} ya usa estos cambios.`);
          this.pushPreview();
        },
        error: (err) => {
          this.publishing = false;
          this.errorMessage = err?.error?.detail || `No se pudo publicar la plantilla de ${this.templateTitle.toLowerCase()}.`;
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
    this.collections = [];
    this.selectedCollectionId = '';
    this.selectedSectionId = '';
    this.previewUrl = '';
    this.safePreviewUrl = null;
    this.previewOrigin = '';
    this.previewSessionUrl = '';
    this.collectionsLoaded = false;
    this.themeLoaded = false;
    this.dirty = false;
    if (!this.storefront) {
      this.loading = false;
      return;
    }

    const storefrontId = this.storefront.id;
    this.loading = true;
    forkJoin({
      theme: this.storefrontService.getThemeDocument(storefrontId, this.templateKey),
      collections: this.storefrontService.getCollections(storefrontId),
    }).subscribe({
      next: ({ theme, collections }) => {
        if (this.storefront?.id !== storefrontId) return;
        this.theme = theme;
        this.document = this.normalizeDocument(theme.draft_document);
        this.collections = collections.filter((collection) => collection.is_visible);
        this.selectedCollectionId = this.collections[0]?.id || '';
        this.selectedSectionId = this.document.sections[0]?.id || '';
        this.themeLoaded = true;
        this.collectionsLoaded = true;
        this.loading = false;
        this.createPreviewSession();
      },
      error: (err) => {
        if (this.storefront?.id !== storefrontId) return;
        this.loading = false;
        this.errorMessage = err?.error?.detail || `No se pudo cargar la plantilla de ${this.templateTitle.toLowerCase()}.`;
      },
    });
    this.storefrontService.getThemeComponents(storefrontId, this.templateKey).subscribe({
      next: (response) => {
        const remote = (response.components || []).filter((component): component is CollectionComponentDefinition => this.isCatalogSectionType(component.type));
        if (remote.length) this.components = remote;
      },
    });
  }

  private createPreviewSession(): void {
    if (!this.storefront || !this.collectionsLoaded || !this.themeLoaded || (!this.isSearchTemplate && !this.selectedCollectionId)) return;
    const storefrontId = this.storefront.id;
    this.storefrontService.createThemePreviewSession(storefrontId, this.templateKey).subscribe({
      next: (session: StorefrontThemePreviewSession) => {
        if (this.storefront?.id !== storefrontId) return;
        this.previewSessionUrl = session.preview_url;
        this.updateCollectionPreviewUrl();
      },
      error: (err) => {
        if (this.storefront?.id !== storefrontId) return;
        this.errorMessage = err?.error?.detail || `No se pudo abrir la vista previa de ${this.templateTitle.toLowerCase()}.`;
      },
    });
  }

  private updateCollectionPreviewUrl(): void {
    const collection = this.selectedCollection;
    if ((!this.isSearchTemplate && !collection) || !this.previewSessionUrl) return;
    try {
      const url = new URL(this.previewSessionUrl);
      url.pathname = this.isSearchTemplate ? '/products' : `/collections/${encodeURIComponent(collection!.slug)}`;
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
      template: this.templateKey,
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

  private normalizeDocument(raw: Record<string, unknown>): CollectionTemplateDocument {
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
          id: String(section['id'] || `collection-section-${index + 1}`),
          type: this.isCatalogSectionType(section['type']) ? section['type'] : this.templateComponents[this.templateComponents.length - 1].type,
          enabled: section['enabled'] !== false,
          settings: section['settings'] && typeof section['settings'] === 'object' && !Array.isArray(section['settings'])
            ? section['settings'] as Record<string, unknown>
            : {},
          blocks: Array.isArray(section['blocks']) ? section['blocks'].filter((block): block is Record<string, unknown> => Boolean(block) && typeof block === 'object') : [],
        }))
      : defaultDocument.sections;
    return {
      schema_version: Number(source['schema_version'] || 1),
      template: this.templateKey,
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

  private createDocument(): CollectionTemplateDocument {
    return {
      schema_version: 1,
      template: this.templateKey,
      settings: {
        content: {
          breadcrumb_title: this.isSearchTemplate ? 'Resultados de búsqueda' : 'Colección',
          products_label: 'productos',
          filters_label: 'Filtros',
          sort_label: 'Ordenar por',
          clear_filters_label: 'Limpiar filtros',
          empty_title: this.isSearchTemplate ? 'No encontramos resultados' : 'No encontramos productos',
          empty_description: this.isSearchTemplate ? 'Prueba con otra búsqueda o ajusta los filtros.' : 'Prueba cambiar los filtros o explorar otra colección.',
        },
      },
      sections: this.templateComponents.map((component) => ({
        id: component.type,
        type: component.type,
        enabled: true,
        settings: {},
        blocks: [],
      })),
    };
  }

  private isCatalogSectionType(value: unknown): value is CatalogSectionType {
    return this.templateComponents.some((component) => component.type === value);
  }
}
