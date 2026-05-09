import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { StoreCollection, StorePaymentGateway, Storefront, StorefrontAdminService } from 'src/app/core/services/storefront-admin.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

@Component({
  selector: 'app-ecommerce-overview',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
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

  readonly sections = [
    {
      group: 'Base',
      title: 'General',
      description: 'Tema, subdominio, idioma, moneda, dominios y estado operativo.',
      route: '/apps/ecommerce/settings',
      action: 'Abrir general'
    },
    {
      group: 'Base',
      title: 'Branding',
      description: 'Logo, contacto, redes sociales y promos globales del storefront.',
      route: '/apps/ecommerce/branding',
      action: 'Abrir branding'
    },
    {
      group: 'Contenido',
      title: 'Home',
      description: 'Hero, banners, secciones, countdown y newsletter del home.',
      route: '/apps/ecommerce/home',
      action: 'Editar home'
    },
    {
      group: 'Catalogo',
      title: 'Productos publicados',
      description: 'Selecciona productos internos, define slug y precio web.',
      route: '/products',
      action: 'Ir a productos'
    },
    {
      group: 'Catalogo',
      title: 'Colecciones',
      description: 'Agrupa productos para menus y merchandising tipo Shopify.',
      route: '/apps/ecommerce/collections',
      action: 'Administrar colecciones'
    },
    {
      group: 'Catalogo',
      title: 'Menu',
      description: 'Construye navegacion apuntando a colecciones, categorias o URLs.',
      route: '/apps/ecommerce/navigation',
      action: 'Administrar menu'
    },
    {
      group: 'Operacion',
      title: 'Pagos',
      description: 'Activa pasarelas por empresa y carga credenciales por proveedor.',
      route: '/apps/ecommerce/payments',
      action: 'Administrar pagos'
    }
  ];

  readonly groups = [
    { key: 'Base', title: 'Base del storefront', description: 'Identidad, estructura y presencia general.' },
    { key: 'Contenido', title: 'Contenido', description: 'Bloques visuales y mensajes del storefront.' },
    { key: 'Catalogo', title: 'Catalogo y navegacion', description: 'Lo que el cliente ve y como lo recorre.' },
    { key: 'Operacion', title: 'Operacion', description: 'Cobro y configuracion transaccional.' }
  ];

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
          this.loading = false;
          this.collections = [];
          this.paymentGateways = [];
          this.publishedCount = 0;
          this.navigationCount = 0;
          this.domainsCount = 0;
          return;
        }
        this.loadStorefrontMetrics();
      },
      error: (err) => {
        this.loading = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar ecommerce.');
      }
    });
  }

  onStorefrontChange(): void {
    this.context.setSelectedStorefrontId(this.selectedStorefrontId);
    this.loadStorefrontMetrics();
  }

  sectionsByGroup(group: string) {
    return this.sections.filter((section) => section.group === group);
  }

  private loadStorefrontMetrics(): void {
    this.loading = true;
    forkJoin({
      collections: this.storefrontService.getCollections(this.selectedStorefrontId),
      gateways: this.storefrontService.getPaymentGateways(this.selectedStorefrontId),
      products: this.storefrontService.getPublishedProducts(this.selectedStorefrontId),
      navigation: this.storefrontService.getNavigation(this.selectedStorefrontId),
      domains: this.storefrontService.getDomains(this.selectedStorefrontId)
    }).subscribe({
      next: ({ collections, gateways, products, navigation, domains }) => {
        this.collections = collections;
        this.paymentGateways = gateways;
        this.publishedCount = products.length;
        this.navigationCount = navigation.length;
        this.domainsCount = domains.length;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar el resumen de ecommerce.');
      }
    });
  }
}
