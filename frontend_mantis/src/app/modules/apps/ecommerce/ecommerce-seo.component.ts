import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { Storefront, StorefrontAdminService } from 'src/app/core/services/storefront-admin.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

type SeoSettings = {
  meta_title: string;
  meta_description: string;
  index_storefront: boolean;
};

@Component({
  selector: 'app-ecommerce-seo',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ecommerce-seo.component.html',
  styleUrls: ['./ecommerce-shared.component.scss', './ecommerce-seo.component.scss']
})
export class EcommerceSeoComponent implements OnInit {
  private storefrontService = inject(StorefrontAdminService);
  private context = inject(EcommerceContextService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);

  loading = false;
  saving = false;
  editing = false;
  storefronts: Storefront[] = [];
  selectedStorefrontId = '';
  storefront: Storefront | null = null;
  form: SeoSettings = this.createForm();

  get platformStorefrontDomain(): string {
    const host = window.location.hostname.toLowerCase();
    return host.startsWith('panel.') ? host.slice('panel.'.length) : host || 'lumefy.shop';
  }

  ngOnInit(): void {
    if (!this.permissions.hasPermission('manage_company')) {
      this.swal.error('Sin permiso', 'No puedes administrar ecommerce.');
      return;
    }
    this.loadStorefronts();
  }

  loadStorefronts(): void {
    this.loading = true;
    this.storefrontService.getStorefronts().subscribe({
      next: (storefronts) => {
        this.storefronts = storefronts;
        this.selectedStorefrontId = this.context.resolveSelectedStorefront(storefronts);
        this.applySelectedStorefront();
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar la configuracion SEO.');
      }
    });
  }

  onStorefrontChange(): void {
    this.context.setSelectedStorefrontId(this.selectedStorefrontId);
    this.applySelectedStorefront();
  }

  openEditor(): void {
    this.editing = true;
  }

  closeEditor(): void {
    if (!this.saving) {
      this.applySelectedStorefront();
      this.editing = false;
    }
  }

  save(): void {
    if (!this.storefront) {
      return;
    }

    this.saving = true;
    this.storefrontService
      .updateStorefront(this.storefront.id, {
        seo_settings: { ...this.form }
      })
      .subscribe({
        next: () => {
          this.saving = false;
          this.editing = false;
          this.swal.success('SEO guardado');
          this.loadStorefronts();
        },
        error: (err) => {
          this.saving = false;
          this.swal.error('Error', err?.error?.detail || 'No se pudo guardar SEO.');
        }
      });
  }

  private applySelectedStorefront(): void {
    this.storefront = this.storefronts.find((item) => item.id === this.selectedStorefrontId) || null;
    this.form = this.normalizeSettings(this.storefront?.seo_settings);
  }

  private normalizeSettings(settings: Record<string, unknown> | undefined): SeoSettings {
    return {
      meta_title: '',
      meta_description: '',
      index_storefront: true,
      ...(settings || {})
    } as SeoSettings;
  }

  private createForm(): SeoSettings {
    return this.normalizeSettings(undefined);
  }
}
