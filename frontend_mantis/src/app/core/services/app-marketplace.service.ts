import { Injectable, inject } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { ApiService } from './api.service';

export interface AppCatalogItem {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  category: string | null;
  version: string;
  icon: string | null;
  is_active: boolean;
  is_listed: boolean;
  requested_scopes: string[];
  capabilities: string[];
  pricing_model: string;
  monthly_price: number;
  setup_url: string | null;
  docs_url: string | null;
  support_url: string | null;
  installed: boolean;
  is_enabled: boolean;
  config_schema: Record<string, unknown>;
}

export interface InstalledApp {
  install_id: string;
  app_id: string;
  slug: string;
  name: string;
  is_enabled: boolean;
  installed_version: string;
  granted_scopes: string[];
  api_key_prefix: string | null;
  oauth_client_id: string | null;
  webhook_url: string | null;
  billing_status: string;
  new_api_key?: string | null;
  settings: Record<string, unknown>;
  installed_at: string;
}

export interface AppInstalledDetail extends InstalledApp {
  description: string | null;
  category: string | null;
  version: string;
  icon: string | null;
  config_schema: Record<string, unknown>;
  default_config: Record<string, unknown>;
  requested_scopes: string[];
  capabilities: string[];
  setup_url: string | null;
  docs_url: string | null;
  support_url: string | null;
  pricing_model: string;
  monthly_price: number;
  api_key_prefix: string | null;
  oauth_client_id: string | null;
  webhook_url: string | null;
  billing_status: string;
}

export interface AdminAppDefinition {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  category: string | null;
  version: string;
  icon: string | null;
  requested_scopes: string[];
  capabilities: string[];
  config_schema: Record<string, unknown>;
  default_config: Record<string, unknown>;
  setup_url: string | null;
  docs_url: string | null;
  support_url: string | null;
  pricing_model: string;
  monthly_price: number;
  is_listed: boolean;
  is_active: boolean;
}

export interface AppInstallRequest {
  granted_scopes: string[];
  target_version?: string | null;
}

export interface AppInstallEvent {
  id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
  triggered_by_user_id: string | null;
}

export interface RotateApiKeyResponse {
  api_key_prefix: string;
  new_api_key: string;
  rotated_at: string;
}

export interface RotateWebhookSecretResponse {
  webhook_secret: string;
  rotated_at: string;
}

export interface RotateClientSecretResponse {
  oauth_client_id: string;
  new_client_secret: string;
  rotated_at: string;
}

export interface BillingSummary {
  slug: string;
  name: string;
  pricing_model: string;
  monthly_price: number;
  currency: string;
  billing_status: string;
  is_enabled: boolean;
  next_invoice_date: string | null;
}

export interface WebhookTestResponse {
  delivered: boolean;
  endpoint?: string | null;
  status_code?: number | null;
  signature?: string | null;
  reason?: string | null;
}

export interface WebhookDelivery {
  id: string;
  event_name: string;
  endpoint?: string | null;
  success: boolean;
  status_code?: number | null;
  error_message?: string | null;
  attempt_number: number;
  created_at: string;
}

export interface DemoHelloResponse {
  app_slug: string;
  message: string;
  configured_message: string;
}

@Injectable({
  providedIn: 'root'
})
export class AppMarketplaceService {
  private api = inject(ApiService);

  private installedChangedSource = new Subject<void>();
  installedChanged$ = this.installedChangedSource.asObservable();

  notifyInstalledChanged(): void {
    this.installedChangedSource.next();
  }

  getCatalog(): Observable<AppCatalogItem[]> {
    return this.api.get<AppCatalogItem[]>('/apps/catalog');
  }

  getInstalled(): Observable<InstalledApp[]> {
    return this.api.get<InstalledApp[]>('/apps/installed');
  }

  getInstalledDetail(slug: string): Observable<AppInstalledDetail> {
    return this.api.get<AppInstalledDetail>(`/apps/installed/${slug}`);
  }

  getInstalledEvents(slug: string, limit = 20): Observable<AppInstallEvent[]> {
    return this.api.get<AppInstallEvent[]>(`/apps/installed/${slug}/events?limit=${limit}`);
  }

  getBillingSummary(slug: string): Observable<BillingSummary> {
    return this.api.get<BillingSummary>(`/apps/installed/${slug}/billing`);
  }

  rotateApiKey(slug: string): Observable<RotateApiKeyResponse> {
    return this.api.post<RotateApiKeyResponse>(`/apps/installed/${slug}/rotate-api-key`, {});
  }

  rotateWebhookSecret(slug: string): Observable<RotateWebhookSecretResponse> {
    return this.api.post<RotateWebhookSecretResponse>(`/apps/installed/${slug}/rotate-webhook-secret`, {});
  }

  rotateClientSecret(slug: string): Observable<RotateClientSecretResponse> {
    return this.api.post<RotateClientSecretResponse>(`/apps/installed/${slug}/rotate-client-secret`, {});
  }

  sendWebhookTest(slug: string): Observable<WebhookTestResponse> {
    return this.api.post<WebhookTestResponse>(`/apps/installed/${slug}/webhooks/test`, {});
  }

  getWebhookDeliveries(slug: string, limit = 25): Observable<WebhookDelivery[]> {
    return this.api.get<WebhookDelivery[]>(`/apps/installed/${slug}/webhooks/deliveries?limit=${limit}`);
  }

  retryWebhookDelivery(slug: string, deliveryId: string): Observable<WebhookTestResponse> {
    return this.api.post<WebhookTestResponse>(`/apps/installed/${slug}/webhooks/deliveries/${deliveryId}/retry`, {});
  }

  install(slug: string, payload: AppInstallRequest): Observable<InstalledApp> {
    return this.api.post<InstalledApp>(`/apps/install/${slug}`, payload);
  }

  uninstall(slug: string): Observable<InstalledApp> {
    return this.api.post<InstalledApp>(`/apps/uninstall/${slug}`, {});
  }

  updateConfig(slug: string, settings: Record<string, unknown>): Observable<InstalledApp> {
    return this.api.put<InstalledApp>(`/apps/config/${slug}`, { settings });
  }

  runDemoHello(): Observable<DemoHelloResponse> {
    return this.api.get<DemoHelloResponse>('/apps/demo/hello');
  }

  adminGetCatalog(): Observable<AdminAppDefinition[]> {
    return this.api.get<AdminAppDefinition[]>('/apps/admin/catalog');
  }

  adminCreateApp(payload: Partial<AdminAppDefinition> & { slug: string; name: string }): Observable<AdminAppDefinition> {
    return this.api.post<AdminAppDefinition>('/apps/admin/catalog', payload);
  }

  adminUpdateApp(slug: string, payload: Partial<AdminAppDefinition>): Observable<AdminAppDefinition> {
    return this.api.put<AdminAppDefinition>(`/apps/admin/catalog/${slug}`, payload);
  }
}
