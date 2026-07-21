import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { Storefront, StorefrontAdminService } from 'src/app/core/services/storefront-admin.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

type CheckoutSettings = {
  allow_guest_checkout: boolean;
  checkout_mode: string;
  enable_order_notes: boolean;
  require_phone: boolean;
  show_delivery_estimate: boolean;
  flat_shipping_rate: number;
  free_shipping_threshold: number;
  tax_rate: number;
  tax_included: boolean;
  tax_shipping: boolean;
};

@Component({
  selector: 'app-ecommerce-checkout',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ecommerce-checkout.component.html',
  styleUrls: ['./ecommerce-shared.component.scss', './ecommerce-checkout.component.scss']
})
export class EcommerceCheckoutComponent implements OnInit {
  private storefrontService = inject(StorefrontAdminService);
  private context = inject(EcommerceContextService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);

  loading = false;
  saving = false;
  storefronts: Storefront[] = [];
  selectedStorefrontId = '';
  storefront: Storefront | null = null;
  form: CheckoutSettings = this.createForm();

  readonly checkoutModeOptions = [
    { value: 'guest', label: 'Invitados' },
    { value: 'optional_account', label: 'Cuenta opcional' },
    { value: 'required_account', label: 'Cuenta obligatoria' }
  ];

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
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar la configuracion de checkout.');
      }
    });
  }

  onStorefrontChange(): void {
    this.context.setSelectedStorefrontId(this.selectedStorefrontId);
    this.applySelectedStorefront();
  }

  save(): void {
    if (!this.storefront) {
      return;
    }

    this.saving = true;
    this.storefrontService
      .updateStorefront(this.storefront.id, {
        checkout_settings: { ...this.form }
      })
      .subscribe({
        next: () => {
          this.saving = false;
          this.swal.success('Checkout guardado');
          this.loadStorefronts();
        },
        error: (err) => {
          this.saving = false;
          this.swal.error('Error', err?.error?.detail || 'No se pudo guardar el checkout.');
        }
      });
  }

  private applySelectedStorefront(): void {
    this.storefront = this.storefronts.find((item) => item.id === this.selectedStorefrontId) || null;
    this.form = this.normalizeSettings(this.storefront?.checkout_settings);
  }

  private normalizeSettings(settings: Record<string, unknown> | undefined): CheckoutSettings {
    return {
      allow_guest_checkout: true,
      checkout_mode: 'guest',
      enable_order_notes: true,
      require_phone: false,
      show_delivery_estimate: true,
      flat_shipping_rate: 0,
      free_shipping_threshold: 0,
      tax_rate: 0,
      tax_included: false,
      tax_shipping: false,
      ...(settings || {})
    } as CheckoutSettings;
  }

  private createForm(): CheckoutSettings {
    return this.normalizeSettings(undefined);
  }
}
