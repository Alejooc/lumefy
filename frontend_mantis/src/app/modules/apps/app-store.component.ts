import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from 'src/app/core/services/auth.service';
import {
  AppCatalogItem,
  AppInstallRequest,
  AppMarketplaceService,
  InstalledApp
} from 'src/app/core/services/app-marketplace.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

interface AppMarketMeta {
  eyebrow: string;
  tagline: string;
  accent: string;
  soft: string;
  icon: string;
  note: string;
}

@Component({
  selector: 'app-app-store',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app-store.component.html',
  styleUrl: './app-store.component.scss'
})
export class AppStoreComponent implements OnInit {
  private appService = inject(AppMarketplaceService);
  private permissionService = inject(PermissionService);
  private authService = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private swal = inject(SweetAlertService);

  private readonly curatedMeta: Record<string, AppMarketMeta> = {
    eleganthome: {
      eyebrow: 'Canal de venta',
      tagline: 'Conecta tu catálogo con el mundo mayorista.',
      accent: '#c9f146',
      soft: '#eff7d8',
      icon: 'package-export',
      note: 'Productos, inventario y órdenes en un solo flujo.'
    },
    ecommerce: {
      eyebrow: 'Canal digital',
      tagline: 'Lleva tu tienda online a una experiencia propia.',
      accent: '#ff7559',
      soft: '#fff0eb',
      icon: 'world-www',
      note: 'Diseña, publica y vende desde Jaofy.'
    },
    'google-analytics': {
      eyebrow: 'Analítica web',
      tagline: 'Entiende cada paso antes de la compra.',
      accent: '#f6a93b',
      soft: '#fff5df',
      icon: 'brand-google-analytics',
      note: 'Visitas, productos, carritos y conversiones en GA4.'
    },
    'meta-pixel': {
      eyebrow: 'Publicidad social',
      tagline: 'Convierte el recorrido de compra en mejores campañas.',
      accent: '#4d78ff',
      soft: '#eaf0ff',
      icon: 'brand-meta',
      note: 'Eventos del storefront listos para Meta Ads.'
    },
    'tiktok-pixel': {
      eyebrow: 'Social commerce',
      tagline: 'Mide lo que inspira, conecta y convierte.',
      accent: '#17171b',
      soft: '#f1f1f3',
      icon: 'brand-tiktok',
      note: 'Señales de compra para TikTok Ads y audiencias.'
    },
    pos_module: {
      eyebrow: 'Operación en tienda',
      tagline: 'Una caja rápida para cada momento de venta.',
      accent: '#75cbd1',
      soft: '#e7f7f6',
      icon: 'device-desktop-analytics',
      note: 'Cobros, sesiones y existencias conectadas.'
    }
  };

  loading = false;
  catalog: AppCatalogItem[] = [];
  installedMap: Record<string, InstalledApp> = {};
  installProgress: Record<string, number> = {};
  installingSlug: string | null = null;
  selectedApp: AppCatalogItem | null = null;
  searchQuery = '';
  selectedCategory = 'Todas';
  viewMode: 'all' | 'installed' = 'all';
  browseOpen = false;

  get categories(): string[] {
    return Array.from(new Set(this.catalog.map((app) => app.category).filter((category): category is string => !!category)));
  }

  get filteredCatalog(): AppCatalogItem[] {
    const query = this.searchQuery.trim().toLowerCase();
    return this.catalog.filter((app) => {
      const matchesCategory = this.selectedCategory === 'Todas' || app.category === this.selectedCategory;
      const matchesView = this.viewMode === 'all' || this.isInstalled(app.slug);
      const searchable = [app.name, app.description, app.category, ...(app.capabilities || [])]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return matchesCategory && matchesView && (!query || searchable.includes(query));
    });
  }

  get featuredApp(): AppCatalogItem | null {
    return this.catalog.find((app) => app.slug === 'eleganthome') || this.catalog[0] || null;
  }

  get installedCount(): number {
    return Object.values(this.installedMap).filter((app) => app.is_enabled).length;
  }

  ngOnInit(): void {
    if (this.authService.currentUserValue?.is_superuser) {
      this.router.navigate(['/apps/admin']);
      return;
    }
    if (!this.permissionService.hasPermission('manage_company')) {
      this.swal.error('Sin permiso', 'Solo administradores de empresa pueden instalar apps.');
      this.router.navigate(['/dashboard/default']);
      return;
    }
    if (this.route.snapshot.queryParamMap.get('unavailable') === 'pos_module') {
      this.swal.warning('POS no está disponible', 'Tu plan no tiene el módulo POS instalado o habilitado. Actívalo aquí para poder usarlo.');
    }
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.appService.getCatalog().subscribe({
      next: (catalog) => {
        this.catalog = catalog;
        this.appService.getInstalled().subscribe({
          next: (installed) => {
            this.installedMap = installed.reduce((acc, item) => {
              acc[item.slug] = item;
              return acc;
            }, {} as Record<string, InstalledApp>);
            this.loading = false;
          },
          error: () => {
            this.loading = false;
            this.swal.error('Error', 'No se pudo cargar el estado de apps instaladas.');
          }
        });
      },
      error: () => {
        this.loading = false;
        this.swal.error('Error', 'No se pudo cargar el catálogo de apps.');
      }
    });
  }

  isInstalled(slug: string): boolean {
    return !!this.installedMap[slug]?.is_enabled;
  }

  selectCategory(category: string): void {
    this.selectedCategory = category;
    this.browseOpen = false;
  }

  setViewMode(mode: 'all' | 'installed'): void {
    this.viewMode = mode;
  }

  categoryCount(category: string): number {
    return this.catalog.filter((app) => app.category === category).length;
  }

  openDeveloperCatalog(): void {
    this.router.navigate(['/apps/admin']);
  }

  backToPanel(): void {
    this.router.navigate(['/dashboard/default']);
  }

  clearSearch(): void {
    this.searchQuery = '';
  }

  openDetails(app: AppCatalogItem): void {
    this.selectedApp = app;
    this.browseOpen = false;
  }

  closeDetails(): void {
    this.selectedApp = null;
  }

  openInstalled(slug: string): void {
    const app = this.catalog.find((item) => item.slug === slug);
    this.router.navigateByUrl(app?.setup_url || `/apps/installed/${slug}`);
  }

  async install(slug: string): Promise<void> {
    const app = this.catalog.find((item) => item.slug === slug);
    if (!app) return;

    const requestedScopes = app.requested_scopes || [];
    const scopeText = requestedScopes.length > 0 ? requestedScopes.join(', ') : 'Sin permisos especiales';
    const confirmResult = await this.swal.confirm(
      `Instalar ${app.name}`,
      `La app solicita estos permisos: ${scopeText}`
    );

    if (!confirmResult?.isConfirmed) return;

    const payload: AppInstallRequest = {
      granted_scopes: requestedScopes,
      target_version: app.version
    };
    this.installWithSimulation(slug, payload);
  }

  installWithSimulation(slug: string, payload: AppInstallRequest): void {
    if (this.installingSlug) return;
    this.installingSlug = slug;
    this.installProgress[slug] = 0;

    const timer = setInterval(() => {
      const current = this.installProgress[slug] || 0;
      if (current >= 90) {
        clearInterval(timer);
        this.appService.install(slug, payload).subscribe({
          next: () => {
            this.installProgress[slug] = 100;
            setTimeout(() => {
              this.installingSlug = null;
              this.appService.notifyInstalledChanged();
              this.swal.success('Instalación completa');
              this.reload();
              const destination = this.catalog.find((item) => item.slug === slug)?.setup_url || `/apps/installed/${slug}`;
              this.router.navigateByUrl(destination);
            }, 350);
          },
          error: (err) => {
            clearInterval(timer);
            this.installingSlug = null;
            this.installProgress[slug] = 0;
            this.swal.error('Error de instalación', err?.error?.detail || 'No se pudo instalar la app.');
          }
        });
        return;
      }
      this.installProgress[slug] = current + 15;
    }, 180);
  }

  uninstall(slug: string): void {
    this.appService.uninstall(slug).subscribe({
      next: () => {
        this.appService.notifyInstalledChanged();
        this.swal.success('App desactivada');
        this.reload();
      },
      error: (err) => {
        this.swal.error('Error', err?.error?.detail || 'No se pudo desactivar la app.');
      }
    });
  }

  pricingLabel(app: AppCatalogItem): string {
    if (app.pricing_model === 'included') return 'Incluida en tu plan';
    if (app.monthly_price <= 0) return 'Gratis';
    return `$${app.monthly_price}/mes`;
  }

  metaFor(app: AppCatalogItem): AppMarketMeta {
    return this.curatedMeta[app.slug] || {
      eyebrow: app.category || 'Aplicación',
      tagline: app.description || 'Amplía las capacidades de tu operación.',
      accent: '#9276e8',
      soft: '#f0ecff',
      icon: app.icon || 'apps',
      note: 'Una herramienta lista para trabajar contigo.'
    };
  }

  iconClass(app: AppCatalogItem): string {
    const icon = this.metaFor(app).icon.replace(/^ti-/, '');
    return `ti ti-${icon}`;
  }
}
