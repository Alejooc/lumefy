import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription, map, switchMap, takeWhile, timer } from 'rxjs';
import {
  IntegrationMapping,
  IntegrationPreview,
  IntegrationService,
  IntegrationSource,
  IntegrationSourcePayload,
  IntegrationSyncRun,
  JsonObject
} from '../../core/services/integration.service';
import { SweetAlertService } from '../../theme/shared/services/sweet-alert.service';

interface IntegrationForm {
  name: string;
  base_url: string;
  auth_type: string;
  token: string;
  api_key_header: string;
  products_path: string;
  products_data_path: string;
  inventory_path: string;
  inventory_data_path: string;
  pagination_enabled: boolean;
  page_param: string;
  per_page_param: string;
  per_page: number;
  start_page: number;
  max_pages: number;
  product_id_field: string;
  product_name_field: string;
  product_sku_field: string;
  product_price_field: string;
  product_cost_field: string;
  inventory_id_field: string;
  inventory_sku_field: string;
  inventory_quantity_field: string;
}

interface InventoryScheduleDraft {
  mode: 'MANUAL' | 'AUTOMATIC';
  interval_minutes: number;
}

@Component({
  selector: 'app-integration-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './integration-list.component.html',
  styleUrls: ['./integration-list.component.scss']
})
export class IntegrationListComponent implements OnInit, OnDestroy {
  private integrationService = inject(IntegrationService);
  private swal = inject(SweetAlertService);

  sources: IntegrationSource[] = [];
  loading = false;
  saving = false;
  showForm = false;
  editingId: string | null = null;
  testingId: string | null = null;
  previewingId: string | null = null;
  previewResult: IntegrationPreview | null = null;
  previewSourceName: string | null = null;
  mappingDraft: IntegrationMapping | null = null;
  mappingSourceName: string | null = null;
  mappingValues: JsonObject = {};
  mappingSourceId: string | null = null;
  mappingRunningId: string | null = null;
  confirmingMapping = false;
  editingConfiguration: JsonObject = {};
  scheduleDrafts: Record<string, InventoryScheduleDraft> = {};
  scheduleSavingId: string | null = null;
  activeRuns: Record<string, IntegrationSyncRun> = {};
  readonly inventoryIntervals = [5, 15, 30, 60, 180, 360, 720, 1440];
  private readonly polling = new Subscription();

  form: IntegrationForm = this.emptyForm();

  ngOnInit(): void {
    this.loadSources();
  }

  ngOnDestroy(): void {
    this.polling.unsubscribe();
  }

  emptyForm(): IntegrationForm {
    return {
      name: '',
      base_url: '',
      auth_type: 'bearer',
      token: '',
      api_key_header: 'X-API-Key',
      products_path: '/products',
      products_data_path: '',
      inventory_path: '/inventory',
      inventory_data_path: '',
      pagination_enabled: false,
      page_param: 'page',
      per_page_param: 'per_page',
      per_page: 50,
      start_page: 1,
      max_pages: 1000,
      product_id_field: 'id',
      product_name_field: 'name',
      product_sku_field: 'sku',
      product_price_field: 'price',
      product_cost_field: 'cost',
      inventory_id_field: 'product_id',
      inventory_sku_field: 'sku',
      inventory_quantity_field: 'quantity'
    };
  }

  loadSources(): void {
    this.loading = true;
    this.integrationService.listSources().subscribe({
      next: (sources) => {
        this.sources = sources;
        for (const source of sources) {
          this.scheduleDrafts[source.id] ??= {
            mode: source.inventory_sync_mode,
            interval_minutes: source.inventory_sync_interval_minutes || 15
          };
        }
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.swal.error('Error', 'No se pudieron cargar los orígenes de datos.');
      }
    });
  }

  openCreate(): void {
    this.editingId = null;
    this.editingConfiguration = {};
    this.form = this.emptyForm();
    this.showForm = true;
  }

  openEdit(source: IntegrationSource): void {
    const config = source.configuration || {};
    const endpoints = this.objectValue(config['endpoints']);
    const products = this.objectValue(endpoints['products']);
    const inventory = this.objectValue(endpoints['inventory']);
    const pagination = this.objectValue(products['pagination']);
    const fieldMap = this.objectValue(config['field_map']);
    this.editingId = source.id;
    this.editingConfiguration = config;
    this.form = {
      ...this.emptyForm(),
      name: source.name,
      base_url: source.base_url,
      auth_type: source.auth_type,
      api_key_header: this.stringValue(config['api_key_header'], 'X-API-Key'),
      products_path: this.stringValue(products['path']),
      products_data_path: this.stringValue(products['data_path']),
      inventory_path: this.stringValue(inventory['path']),
      inventory_data_path: this.stringValue(inventory['data_path']),
      pagination_enabled: pagination['enabled'] === true,
      page_param: this.stringValue(pagination['page_param'], 'page'),
      per_page_param: this.stringValue(pagination['per_page_param'], 'per_page'),
      per_page: Number(pagination['per_page'] || 50),
      start_page: Number(pagination['start_page'] || 1),
      max_pages: Number(pagination['max_pages'] || 1000),
      product_id_field: this.stringValue(fieldMap['product.external_id'], 'id'),
      product_name_field: this.stringValue(fieldMap['product.name'], 'name'),
      product_sku_field: this.stringValue(fieldMap['product.sku'], 'sku'),
      product_price_field: this.stringValue(fieldMap['product.price'], 'price'),
      product_cost_field: this.stringValue(fieldMap['product.cost'], 'cost'),
      inventory_id_field: this.stringValue(fieldMap['inventory.external_id'], 'product_id'),
      inventory_sku_field: this.stringValue(fieldMap['inventory.sku'], 'sku'),
      inventory_quantity_field: this.stringValue(fieldMap['inventory.quantity'], 'quantity')
    };
    this.showForm = true;
  }

  closeForm(): void {
    this.showForm = false;
    this.editingId = null;
    this.editingConfiguration = {};
  }

  save(): void {
    if (!this.form.name.trim() || !this.form.base_url.trim() || !this.form.products_path.trim()) {
      this.swal.warning('Datos incompletos', 'Completa nombre, URL base y endpoint de productos.');
      return;
    }
    this.saving = true;
    const payload = this.buildPayload();
    const editingId = this.editingId;
    const wasEditing = !!editingId;
    const request = editingId
      ? this.integrationService.updateSource(editingId, payload)
      : this.integrationService.createSource(payload);
    request.subscribe({
      next: () => {
        this.saving = false;
        this.closeForm();
        this.swal.success(wasEditing ? 'Origen actualizado' : 'Origen creado');
        this.loadSources();
      },
      error: (error) => {
        this.saving = false;
        this.swal.error('Error', error?.error?.detail || 'No se pudo guardar el origen.');
      }
    });
  }

  private buildPayload(): IntegrationSourcePayload {
    const pagination = {
      enabled: this.form.pagination_enabled,
      type: 'page',
      page_param: this.form.page_param.trim() || 'page',
      per_page_param: this.form.per_page_param.trim() || 'per_page',
      per_page: Math.max(1, Number(this.form.per_page) || 50),
      start_page: Math.max(1, Number(this.form.start_page) || 1),
      max_pages: Math.max(1, Number(this.form.max_pages) || 1000)
    };
    const existingEndpoints = this.objectValue(this.editingConfiguration['endpoints']);
    const endpoints: JsonObject = {
      products: {
        ...this.objectValue(existingEndpoints['products']),
        path: this.form.products_path.trim(),
        data_path: this.form.products_data_path.trim(),
        pagination
      }
    };
    if (this.form.inventory_path.trim()) {
      endpoints['inventory'] = {
        ...this.objectValue(existingEndpoints['inventory']),
        path: this.form.inventory_path.trim(),
        data_path: this.form.inventory_data_path.trim()
      };
    }
    const credentials: JsonObject = {};
    if (this.form.token.trim()) {
      credentials[this.form.auth_type === 'api_key' ? 'api_key' : 'token'] = this.form.token.trim();
    }
    const existingFieldMap = this.objectValue(this.editingConfiguration['field_map']);
    const mappingConfirmed = this.editingConfiguration['mapping_status'] === 'confirmed';
    const fieldMap = mappingConfirmed ? existingFieldMap : {
      'product.external_id': this.form.product_id_field.trim(),
      'product.name': this.form.product_name_field.trim(),
      'product.sku': this.form.product_sku_field.trim(),
      'product.price': this.form.product_price_field.trim(),
      'product.cost': this.form.product_cost_field.trim(),
      'inventory.external_id': this.form.inventory_id_field.trim(),
      'inventory.sku': this.form.inventory_sku_field.trim(),
      'inventory.quantity': this.form.inventory_quantity_field.trim()
    };
    return {
      name: this.form.name.trim(),
      provider_key: 'custom_rest',
      source_type: 'REST',
      base_url: this.form.base_url.trim(),
      auth_type: this.form.auth_type,
      credentials,
      configuration: {
        ...this.editingConfiguration,
        api_key_header: this.form.api_key_header.trim() || 'X-API-Key',
        endpoints,
        field_map: fieldMap
      }
    };
  }

  test(source: IntegrationSource): void {
    this.testingId = source.id;
    this.integrationService.testSource(source.id).subscribe({
      next: (result) => {
        this.testingId = null;
        if (result.success) {
          this.swal.success('Conexión exitosa', `${result.sample_count} registros detectados.`);
        } else {
          this.swal.error('La conexión falló', result.message);
        }
        this.loadSources();
      },
      error: (error) => {
        this.testingId = null;
        this.swal.error('Error', error?.error?.detail || 'No se pudo probar la conexión.');
      }
    });
  }

  preview(source: IntegrationSource): void {
    this.previewingId = source.id;
    this.previewSourceName = source.name;
    this.previewResult = null;
    this.integrationService.previewSource(source.id).subscribe({
      next: (result) => {
        this.previewingId = null;
        this.previewResult = result;
      },
      error: (error) => {
        this.previewingId = null;
        this.swal.error('Error', error?.error?.detail || 'No se pudo obtener la vista previa.');
      }
    });
  }

  detectMapping(source: IntegrationSource): void {
    this.mappingRunningId = source.id;
    this.mappingSourceId = source.id;
    this.mappingSourceName = source.name;
    this.mappingDraft = null;
    this.integrationService.suggestMapping(source.id).subscribe({
      next: (result) => {
        this.mappingRunningId = null;
        this.mappingDraft = result;
        this.mappingValues = { ...result.mapping };
      },
      error: (error) => {
        this.mappingRunningId = null;
        this.swal.error('Error', error?.error?.detail || 'No se pudo detectar el mapeo automáticamente.');
      }
    });
  }

  confirmMapping(): void {
    if (!this.mappingDraft || !this.mappingSourceId) return;
    this.confirmingMapping = true;
    const mapping = Object.fromEntries(
      Object.entries(this.mappingValues).filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== '')
    );
    this.integrationService.confirmMapping(this.mappingSourceId, {
      mapping,
      catalog_mode: this.mappingDraft.catalog_mode,
      collections: this.mappingDraft.collections
    }).subscribe({
      next: (updated) => {
        this.confirmingMapping = false;
        this.sources = this.sources.map((source) => source.id === updated.id ? updated : source);
        this.mappingDraft = null;
        this.swal.success('Mapeo confirmado', 'La sincronización utilizará esta homologación.');
      },
      error: (error) => {
        this.confirmingMapping = false;
        this.swal.error('Error', error?.error?.detail || 'No se pudo guardar el mapeo.');
      }
    });
  }

  closeMapping(): void {
    this.mappingDraft = null;
    this.mappingSourceId = null;
    this.mappingSourceName = null;
    this.mappingValues = {};
  }

  canonicalLabel(canonical: string): string {
    const labels: Record<string, string> = {
      'product.external_id': 'ID externo del producto',
      'product.name': 'Nombre del producto',
      'product.description': 'Descripción',
      'product.sku': 'SKU del producto',
      'product.barcode': 'Código de barras',
      'product.price': 'Precio del producto',
      'product.cost': 'Costo del producto',
      'product.category.external_id': 'ID externo de categoría',
      'product.category.name': 'Nombre de categoría',
      'product.supplier.external_id': 'ID externo de proveedor',
      'product.supplier.name': 'Nombre de proveedor',
      'product.images': 'Imágenes',
      'variant.external_id': 'ID externo de variante',
      'variant.sku': 'SKU de variante',
      'variant.name': 'Nombre de variante',
      'variant.barcode': 'Código de barras de variante',
      'variant.price': 'Precio de variante',
      'variant.cost': 'Costo de variante',
      'variant.stock': 'Inventario de variante',
      'variant.stock_temp': 'Inventario temporal',
      'variant.attributes': 'Atributos de variante'
    };
    if (canonical.startsWith('product.attributes.')) {
      return `Atributo: ${canonical.replace('product.attributes.', '')}`;
    }
    return labels[canonical] || canonical;
  }

  mappingConfidenceClass(confidence: number): string {
    if (confidence >= 90) return 'text-success';
    if (confidence >= 70) return 'text-warning';
    return 'text-danger';
  }

  mappingStatus(source: IntegrationSource): string {
    return source.configuration?.['mapping_status'] === 'confirmed' ? 'Mapeo confirmado' : 'Mapeo pendiente';
  }

  saveInventorySchedule(source: IntegrationSource): void {
    const draft = this.scheduleDrafts[source.id];
    if (!draft) return;
    this.scheduleSavingId = source.id;
    this.integrationService.updateInventorySchedule(source.id, {
      mode: draft.mode,
      interval_minutes: draft.mode === 'AUTOMATIC' ? Number(draft.interval_minutes) : null
    }).subscribe({
      next: (updated) => {
        this.scheduleSavingId = null;
        this.sources = this.sources.map((item) => item.id === updated.id ? updated : item);
        this.swal.success(
          'Programación guardada',
          draft.mode === 'AUTOMATIC' ? 'El inventario se ejecutará automáticamente.' : 'El inventario quedó en modo manual.'
        );
      },
      error: (error) => {
        this.scheduleSavingId = null;
        this.swal.error('Error', error?.error?.detail || 'No se pudo guardar la programación.');
      }
    });
  }

  syncCatalog(source: IntegrationSource): void {
    this.queueSync(source, 'CATALOG');
  }

  syncInventory(source: IntegrationSource): void {
    this.queueSync(source, 'INVENTORY');
  }

  isSyncActive(source: IntegrationSource, syncType: 'CATALOG' | 'INVENTORY'): boolean {
    const status = this.activeRuns[this.runKey(source.id, syncType)]?.status;
    return status === 'QUEUED' || status === 'RUNNING';
  }

  syncStatus(source: IntegrationSource, syncType: 'CATALOG' | 'INVENTORY'): string | null {
    const run = this.activeRuns[this.runKey(source.id, syncType)];
    if (!run) return null;
    const labels: Record<string, string> = {
      QUEUED: 'En cola',
      RUNNING: 'Ejecutando',
      SUCCESS: 'Completada',
      PARTIAL: 'Completada con alertas',
      FAILED: 'Falló'
    };
    return labels[run.status] || run.status;
  }

  intervalLabel(minutes: number | null): string {
    if (!minutes) return 'Manual';
    if (minutes < 60) return `Cada ${minutes} min`;
    if (minutes === 60) return 'Cada hora';
    if (minutes < 1440) return `Cada ${minutes / 60} h`;
    return 'Cada día';
  }

  private queueSync(source: IntegrationSource, syncType: 'CATALOG' | 'INVENTORY'): void {
    const request = syncType === 'CATALOG'
      ? this.integrationService.syncCatalog(source.id)
      : this.integrationService.syncInventory(source.id);
    request.subscribe({
      next: (run) => {
        this.activeRuns[this.runKey(source.id, syncType)] = run;
        this.swal.success('Sincronización en cola', 'Puedes seguir trabajando mientras Lumefy procesa los datos.');
        this.pollRun(source, run);
      },
      error: (error) => {
        this.swal.error('Error', error?.error?.detail || 'No se pudo poner la sincronización en cola.');
      }
    });
  }

  private pollRun(source: IntegrationSource, queuedRun: IntegrationSyncRun): void {
    const key = this.runKey(source.id, queuedRun.sync_type === 'FULL' ? 'CATALOG' : queuedRun.sync_type);
    const terminalStatuses = new Set(['SUCCESS', 'PARTIAL', 'FAILED']);
    const subscription = timer(1000, 2000).pipe(
      switchMap(() => this.integrationService.listRuns(source.id)),
      map((runs) => runs.find((run) => run.id === queuedRun.id) || queuedRun),
      takeWhile((run) => !terminalStatuses.has(run.status), true)
    ).subscribe({
      next: (run) => {
        this.activeRuns[key] = run;
        if (!terminalStatuses.has(run.status)) return;
        this.loadSources();
        if (run.status === 'FAILED') {
          this.swal.error('Sincronización fallida', run.error_message || 'Revisa la configuración del origen.');
        } else if (run.status === 'PARTIAL') {
          this.swal.warning('Sincronización parcial', `${run.items_failed} registros no pudieron procesarse.`);
        } else if (run.sync_type === 'CATALOG') {
          this.swal.success('Catálogo actualizado', `${run.products_created} creados y ${run.products_updated} actualizados.`);
        } else {
          this.swal.success('Inventario actualizado', `${run.inventory_updated} existencias actualizadas.`);
        }
      },
      error: () => {
        delete this.activeRuns[key];
        this.swal.error('Seguimiento interrumpido', 'Actualiza la página para consultar el resultado.');
      }
    });
    this.polling.add(subscription);
  }

  private runKey(sourceId: string, syncType: 'CATALOG' | 'INVENTORY'): string {
    return `${sourceId}:${syncType}`;
  }

  private objectValue(value: unknown): JsonObject {
    return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as JsonObject : {};
  }

  private stringValue(value: unknown, fallback = ''): string {
    return typeof value === 'string' ? value : fallback;
  }

  async disable(source: IntegrationSource): Promise<void> {
    const result = await this.swal.confirm('Desactivar origen', `¿Desactivar ${source.name}?`);
    if (!result.isConfirmed) return;
    this.integrationService.disableSource(source.id).subscribe({
      next: () => {
        this.swal.success('Origen desactivado');
        this.loadSources();
      },
      error: () => this.swal.error('Error', 'No se pudo desactivar el origen.')
    });
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      DRAFT: 'Borrador',
      CONNECTED: 'Conectado',
      ERROR: 'Error',
      DISABLED: 'Desactivado'
    };
    return labels[status] || status;
  }
}
