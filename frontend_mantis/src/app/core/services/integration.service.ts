import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export interface JsonObject {
  [key: string]: JsonValue;
}

export interface IntegrationSource {
  id: string;
  company_id: string | null;
  name: string;
  provider_key: string;
  source_type: string;
  base_url: string;
  auth_type: string;
  credentials_configured: boolean;
  configuration: JsonObject;
  status: string;
  is_active: boolean;
  last_tested_at: string | null;
  last_synced_at: string | null;
  last_catalog_synced_at: string | null;
  last_inventory_synced_at: string | null;
  last_sync_status: string | null;
  last_error: string | null;
  inventory_sync_mode: 'MANUAL' | 'AUTOMATIC';
  inventory_sync_interval_minutes: number | null;
  next_inventory_sync_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface IntegrationSourcePayload {
  name: string;
  provider_key: string;
  source_type: string;
  base_url: string;
  auth_type: string;
  credentials: JsonObject;
  configuration: JsonObject;
}

export interface IntegrationTestResult {
  success: boolean;
  status_code: number | null;
  message: string;
  sample_count: number;
}

export interface IntegrationPreviewEntity {
  available: boolean;
  request_url: string | null;
  status_code: number | null;
  pagination_enabled: boolean;
  page: number | null;
  page_size: number | null;
  received_count: number;
  mapped: JsonObject[];
  raw: JsonObject[];
  error: string | null;
  variants_count: number;
  images_count: number;
  attributes_count: number;
}

export interface IntegrationPreview {
  success: boolean;
  source_id: string;
  message: string;
  products: IntegrationPreviewEntity;
  inventory: IntegrationPreviewEntity | null;
  errors: string[];
}

export interface IntegrationPreflightCheck {
  code: string;
  ok: boolean;
  severity: string;
  message: string;
  sample_count?: number;
  linked_count?: number;
  warehouse_configured?: boolean;
}

export interface IntegrationPreflight {
  source_id: string;
  success: boolean;
  message: string;
  checks: IntegrationPreflightCheck[];
  warnings: string[];
  errors: string[];
  catalog: { endpoint_configured: boolean; sample_count: number; mapped_count: number; linked_count: number };
  inventory: { endpoint_configured: boolean; batch_enabled: boolean; sample_count: number; mapped_count: number };
}

export interface IntegrationMappingSuggestion {
  canonical: string;
  source_path: string | null;
  confidence: number;
  required: boolean;
  kind: string;
  reason: string | null;
  candidates: string[];
}

export interface IntegrationMapping {
  source_id: string;
  success: boolean;
  message: string;
  request_url: string | null;
  sample_count: number;
  catalog_mode: string;
  detected_shape: string;
  mapping: JsonObject;
  collections: JsonObject;
  suggestions: IntegrationMappingSuggestion[];
  detected_paths: string[];
  warnings: string[];
}

export interface IntegrationSyncRun {
  id: string;
  source_id: string;
  sync_type: 'CATALOG' | 'INVENTORY' | 'FULL';
  trigger_type: 'MANUAL' | 'SCHEDULED';
  status: string;
  queued_at: string;
  started_at: string | null;
  finished_at: string | null;
  products_processed: number;
  products_created: number;
  products_updated: number;
  inventory_processed: number;
  inventory_updated: number;
  items_failed: number;
  details: JsonObject;
  error_message: string | null;
  created_at: string;
}

export interface IntegrationSyncProgress {
  stage: string;
  message: string;
  percent: number;
  current: number;
  total: number | null;
  entity: string | null;
  page: number | null;
  pages_total: number | null;
  items_received: number | null;
  items_total: number | null;
  items_failed: number | null;
  created: number | null;
  updated: number | null;
}

@Injectable({ providedIn: 'root' })
export class IntegrationService {
  private api = inject(ApiService);

  listSources(): Observable<IntegrationSource[]> {
    return this.api.get<IntegrationSource[]>('/integrations/sources');
  }

  createSource(payload: IntegrationSourcePayload): Observable<IntegrationSource> {
    return this.api.post<IntegrationSource>('/integrations/sources', payload);
  }

  updateSource(id: string, payload: Partial<IntegrationSourcePayload>): Observable<IntegrationSource> {
    return this.api.put<IntegrationSource>(`/integrations/sources/${id}`, payload);
  }

  disableSource(id: string): Observable<{ ok: boolean }> {
    return this.api.delete<{ ok: boolean }>(`/integrations/sources/${id}`);
  }

  testSource(id: string): Observable<IntegrationTestResult> {
    return this.api.post<IntegrationTestResult>(`/integrations/sources/${id}/test`, {});
  }

  previewSource(id: string): Observable<IntegrationPreview> {
    return this.api.post<IntegrationPreview>(`/integrations/sources/${id}/preview`, {});
  }

  preflightSource(id: string): Observable<IntegrationPreflight> {
    return this.api.post<IntegrationPreflight>(`/integrations/sources/${id}/preflight`, {});
  }

  suggestMapping(id: string): Observable<IntegrationMapping> {
    return this.api.post<IntegrationMapping>(`/integrations/sources/${id}/mapping-suggestion`, {});
  }

  confirmMapping(id: string, payload: { mapping: JsonObject; catalog_mode: string; collections: JsonObject }): Observable<IntegrationSource> {
    return this.api.post<IntegrationSource>(`/integrations/sources/${id}/mapping-confirm`, payload);
  }

  updateInventorySchedule(
    id: string,
    payload: { mode: 'MANUAL' | 'AUTOMATIC'; interval_minutes: number | null }
  ): Observable<IntegrationSource> {
    return this.api.put<IntegrationSource>(`/integrations/sources/${id}/inventory-schedule`, payload);
  }

  syncCatalog(id: string): Observable<IntegrationSyncRun> {
    return this.api.post<IntegrationSyncRun>(`/integrations/sources/${id}/sync/catalog`, {});
  }

  syncInventory(id: string): Observable<IntegrationSyncRun> {
    return this.api.post<IntegrationSyncRun>(`/integrations/sources/${id}/sync/inventory`, {});
  }

  listRuns(id: string): Observable<IntegrationSyncRun[]> {
    return this.api.get<IntegrationSyncRun[]>(`/integrations/sources/${id}/runs`);
  }
}
