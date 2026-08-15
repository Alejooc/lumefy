import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface IntegrationSource {
  id: string;
  company_id: string | null;
  name: string;
  provider_key: string;
  source_type: string;
  base_url: string;
  auth_type: string;
  credentials_configured: boolean;
  configuration: Record<string, any>;
  status: string;
  is_active: boolean;
  last_tested_at: string | null;
  last_synced_at: string | null;
  last_sync_status: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface IntegrationSourcePayload {
  name: string;
  provider_key: string;
  source_type: string;
  base_url: string;
  auth_type: string;
  credentials: Record<string, any>;
  configuration: Record<string, any>;
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
  mapped: Record<string, any>[];
  raw: Record<string, any>[];
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
  mapping: Record<string, any>;
  collections: Record<string, any>;
  suggestions: IntegrationMappingSuggestion[];
  detected_paths: string[];
  warnings: string[];
}

export interface IntegrationSyncRun {
  id: string;
  source_id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  products_processed: number;
  products_created: number;
  products_updated: number;
  inventory_processed: number;
  inventory_updated: number;
  items_failed: number;
  details: Record<string, any>;
  error_message: string | null;
  created_at: string;
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

  suggestMapping(id: string): Observable<IntegrationMapping> {
    return this.api.post<IntegrationMapping>(`/integrations/sources/${id}/mapping-suggestion`, {});
  }

  confirmMapping(id: string, payload: { mapping: Record<string, any>; catalog_mode: string; collections: Record<string, any> }): Observable<IntegrationSource> {
    return this.api.post<IntegrationSource>(`/integrations/sources/${id}/mapping-confirm`, payload);
  }

  syncSource(id: string): Observable<IntegrationSyncRun> {
    return this.api.post<IntegrationSyncRun>(`/integrations/sources/${id}/sync`, {});
  }

  listRuns(id: string): Observable<IntegrationSyncRun[]> {
    return this.api.get<IntegrationSyncRun[]>(`/integrations/sources/${id}/runs`);
  }
}
