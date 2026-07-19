import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { StoreCollection, StorefrontReadiness, StorePaymentGateway, Storefront, StorefrontAdminService } from 'src/app/core/services/storefront-admin.service';
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
  paymentGateways: StorePaymentGateway[] = [];
  publishedCount = 0;
  navigationCount = 0;
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

  loadData(): void {
    this.loading = true;
    this.storefrontService.getStorefronts().subscribe({
      next: (storefronts) => {
        this.storefronts = storefronts;
        this.selectedStorefrontId = this.context.resolveSelectedStorefront(storefronts);
        if (!this.selectedStorefrontId) {
          this.completeLoading();
          this.collections = [];
          this.paymentGateways = [];
          this.publishedCount = 0;
          this.navigationCount = 0;
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
        this.paymentGateways = gateways;
        this.publishedCount = products.length;
        this.navigationCount = navigation.length;
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
