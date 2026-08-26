import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { StoreCollection, StorefrontReadiness, StorePaymentGateway, Storefront, StorefrontAdminService, StoreNavigationItem } from 'src/app/core/services/storefront-admin.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

@Component({
  selector: 'app-ecommerce-overview',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './ecommerce-overview.component.html',
  styleUrls: ['./ecommerce-shared.component.scss', './ecommerce-overview.component.scss']
})
export class EcommerceOverviewComponent implements OnInit {
  private storefrontService = inject(StorefrontAdminService);
  private context = inject(EcommerceContextService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);

  loading = false;
  storefronts: Storefront[] = [];
  selectedStorefrontId = '';
  collections: StoreCollection[] = [];
  navigationItems: StoreNavigationItem[] = [];
  paymentGateways: StorePaymentGateway[] = [];
  publishedCount = 0;
  domainsCount = 0;
  readiness: StorefrontReadiness | null = null;

  ngOnInit(): void {
    if (!this.permissions.hasPermission('manage_company')) {
      this.swal.error('Sin permiso', 'No puedes administrar ecommerce.');
      return;
    }
    this.loadData();
  }

  get selectedStorefront(): Storefront | null {
    return this.storefronts.find((item) => item.id === this.selectedStorefrontId) || null;
  }

  get visibleCollectionsCount(): number {
    return this.collections.filter((collection) => collection.is_visible).length;
  }

  get visibleNavigationCount(): number {
    return this.navigationItems.filter((item) => item.is_visible).length;
  }

  get activePaymentGatewaysCount(): number {
    return this.paymentGateways.filter((gateway) => gateway.is_enabled).length;
  }

  get sandboxPaymentGatewaysCount(): number {
    return this.paymentGateways.filter((gateway) => gateway.is_enabled && gateway.is_sandbox).length;
  }

  get verifiedDomainsCount(): number {
    return this.domainsCount;
  }

  get paymentGatewaySummary(): string {
    const activeGateways = this.paymentGateways.filter((gateway) => gateway.is_enabled);
    if (!activeGateways.length) {
      return 'Aún no hay métodos activos';
    }

    return activeGateways.slice(0, 2).map((gateway) => gateway.display_name).join(' · ');
  }

  get setupChecks(): Array<{ label: string; detail: string; done: boolean; route: string; icon: string }> {
    const storefront = this.selectedStorefront;
    const publishedProducts = this.readiness?.published_products ?? this.publishedCount;
    const activeGateways = this.readiness?.enabled_payment_gateways ?? this.activePaymentGatewaysCount;

    return [
      {
        label: 'Tienda configurada',
        detail: storefront?.is_enabled ? 'Activa y lista para recibir visitas' : 'Revisa los datos principales',
        done: Boolean(storefront?.is_enabled),
        route: '/commerce/store',
        icon: 'ti ti-building-store'
      },
      {
        label: 'Catálogo publicado',
        detail: publishedProducts ? `${publishedProducts} producto${publishedProducts === 1 ? '' : 's'} visible${publishedProducts === 1 ? '' : 's'}` : 'Publica tu primer producto',
        done: publishedProducts > 0,
        route: '/products',
        icon: 'ti ti-package'
      },
      {
        label: 'Cobros configurados',
        detail: activeGateways ? `${activeGateways} método${activeGateways === 1 ? '' : 's'} activo${activeGateways === 1 ? '' : 's'}` : 'Activa un método de pago',
        done: activeGateways > 0,
        route: '/commerce/payments',
        icon: 'ti ti-credit-card'
      },
      {
        label: 'Envíos preparados',
        detail: storefront?.fulfillment_warehouse_id ? 'Bodega de despacho asignada' : 'Asigna una bodega de despacho',
        done: Boolean(storefront?.fulfillment_warehouse_id),
        route: '/commerce/logistics',
        icon: 'ti ti-truck-delivery'
      },
      {
        label: 'Diseño y navegación',
        detail: this.visibleNavigationCount ? `${this.visibleNavigationCount} enlace${this.visibleNavigationCount === 1 ? '' : 's'} en tu tienda` : 'Organiza el menú de tu tienda',
        done: this.visibleNavigationCount > 0,
        route: '/commerce/design',
        icon: 'ti ti-palette'
      }
    ];
  }

  get setupProgress(): number {
    const checks = this.setupChecks;
    if (!checks.length) {
      return 0;
    }

    return Math.round((checks.filter((check) => check.done).length / checks.length) * 100);
  }

  loadData(): void {
    this.loading = true;
    this.storefrontService.getStorefronts().subscribe({
      next: (storefronts) => {
        this.storefronts = storefronts;
        this.selectedStorefrontId = this.context.resolveSelectedStorefront(storefronts);
        if (!this.selectedStorefrontId) {
          this.completeLoading();
          this.collections = [];
          this.navigationItems = [];
          this.paymentGateways = [];
          this.publishedCount = 0;
          this.domainsCount = 0;
          this.readiness = null;
          return;
        }
        this.loadStorefrontMetrics();
      },
      error: (err) => {
        this.completeLoading();
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar ecommerce.');
      }
    });
  }

  private loadStorefrontMetrics(): void {
    this.loading = true;
    forkJoin({
      collections: this.storefrontService.getCollections(this.selectedStorefrontId),
      gateways: this.storefrontService.getPaymentGateways(this.selectedStorefrontId),
      products: this.storefrontService.getPublishedProducts(this.selectedStorefrontId),
      navigation: this.storefrontService.getNavigation(this.selectedStorefrontId),
      domains: this.storefrontService.getDomains(this.selectedStorefrontId),
      readiness: this.storefrontService.getReadiness(this.selectedStorefrontId)
    }).subscribe({
      next: ({ collections, gateways, products, navigation, domains, readiness }) => {
        this.collections = collections;
        this.navigationItems = navigation;
        this.paymentGateways = gateways;
        this.publishedCount = products.length;
        this.domainsCount = domains.length;
        this.readiness = readiness;
        this.completeLoading();
      },
      error: (err) => {
        this.completeLoading();
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar el resumen de ecommerce.');
      }
    });
  }

  private completeLoading(): void {
    this.loading = false;
  }
}
