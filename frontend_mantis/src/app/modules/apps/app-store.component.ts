import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { Router } from '@angular/router';
import { AppCatalogItem, AppMarketplaceService, InstalledApp } from 'src/app/core/services/app-marketplace.service';
import { AuthService } from 'src/app/core/services/auth.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

@Component({
  selector: 'app-app-store',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app-store.component.html',
  styleUrl: './app-store.component.scss'
})
export class AppStoreComponent implements OnInit {
  private appService = inject(AppMarketplaceService);
  private permissionService = inject(PermissionService);
  private authService = inject(AuthService);
  private router = inject(Router);
  private swal = inject(SweetAlertService);

  loading = false;
  catalog: AppCatalogItem[] = [];
  installedMap: Record<string, InstalledApp> = {};
  installProgress: Record<string, number> = {};
  installingSlug: string | null = null;

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
        this.swal.error('Error', 'No se pudo cargar el catalogo de apps.');
      }
    });
  }

  isInstalled(slug: string): boolean {
    return !!this.installedMap[slug]?.is_enabled;
  }

  openInstalled(slug: string): void {
    this.router.navigate(['/apps/installed', slug]);
  }

  installWithSimulation(slug: string): void {
    if (this.installingSlug) return;
    this.installingSlug = slug;
    this.installProgress[slug] = 0;

    const timer = setInterval(() => {
      const current = this.installProgress[slug] || 0;
      if (current >= 90) {
        clearInterval(timer);
        this.appService.install(slug).subscribe({
          next: () => {
            this.installProgress[slug] = 100;
            setTimeout(() => {
              this.installingSlug = null;
              this.appService.notifyInstalledChanged();
              this.swal.success('Instalacion completa');
              this.reload();
              this.router.navigate(['/apps/installed', slug]);
            }, 350);
          },
          error: (err) => {
            clearInterval(timer);
            this.installingSlug = null;
            this.installProgress[slug] = 0;
            this.swal.error('Error de instalacion', err?.error?.detail || 'No se pudo instalar la app.');
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
}
