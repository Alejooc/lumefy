import { Injectable } from '@angular/core';
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
  installed: boolean;
  is_enabled: boolean;
  config_schema: Record<string, string>;
}

export interface InstalledApp {
  install_id: string;
  app_id: string;
  slug: string;
  name: string;
  is_enabled: boolean;
  settings: Record<string, any>;
  installed_at: string;
}

export interface AppInstalledDetail extends InstalledApp {
  description: string | null;
  category: string | null;
  version: string;
  icon: string | null;
  config_schema: Record<string, string>;
}

export interface AdminAppDefinition {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  category: string | null;
  version: string;
  icon: string | null;
  config_schema: Record<string, any>;
  default_config: Record<string, any>;
  is_active: boolean;
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
  private installedChangedSource = new Subject<void>();
  installedChanged$ = this.installedChangedSource.asObservable();

  constructor(private api: ApiService) { }

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

  install(slug: string): Observable<InstalledApp> {
    return this.api.post<InstalledApp>(`/apps/install/${slug}`, {});
  }

  uninstall(slug: string): Observable<InstalledApp> {
    return this.api.post<InstalledApp>(`/apps/uninstall/${slug}`, {});
  }

  updateConfig(slug: string, settings: Record<string, any>): Observable<InstalledApp> {
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
