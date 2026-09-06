import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from 'src/app/core/services/api.service';
import { Storefront, StorefrontAdminService } from 'src/app/core/services/storefront-admin.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

interface Coupon {
  id: string;
  storefront_id: string;
  code: string;
  discount_type: 'PERCENT' | 'FIXED';
  value: number;
  minimum_amount: number;
  starts_at: string | null;
  ends_at: string | null;
  is_enabled: boolean;
  is_active: boolean;
}

interface CouponForm {
  storefront_id: string;
  code: string;
  discount_type: 'PERCENT' | 'FIXED';
  value: number;
  minimum_amount: number;
  starts_at: string;
  ends_at: string;
  is_enabled: boolean;
}

@Component({
  selector: 'app-ecommerce-coupons',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ecommerce-coupons.component.html',
  styleUrls: ['./ecommerce-shared.component.scss', './ecommerce-coupons.component.scss']
})
export class EcommerceCouponsComponent implements OnInit {
  private api = inject(ApiService);
  private storefrontService = inject(StorefrontAdminService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);

  storefronts: Storefront[] = [];
  coupons: Coupon[] = [];
  selectedStorefrontId = '';
  editingCouponId: string | null = null;
  loading = false;
  saving = false;
  errorMessage = '';

  form: CouponForm = this.emptyForm();

  ngOnInit(): void {
    if (!this.permissions.hasPermission('manage_company')) {
      this.errorMessage = 'No tienes permiso para administrar cupones.';
      return;
    }
    this.loading = true;
    this.storefrontService.getStorefronts().subscribe({
      next: (storefronts) => {
        this.storefronts = storefronts;
        this.selectedStorefrontId = storefronts[0]?.id || '';
        this.form.storefront_id = this.selectedStorefrontId;
        this.loadCoupons();
      },
      error: (err) => this.showError(err)
    });
  }

  loadCoupons(): void {
    if (!this.selectedStorefrontId) {
      this.coupons = [];
      this.loading = false;
      return;
    }
    this.loading = true;
    this.api.get<Coupon[]>('/storefront/coupons/', { storefront_id: this.selectedStorefrontId }).subscribe({
      next: (coupons) => {
        this.coupons = coupons;
        this.loading = false;
        this.errorMessage = '';
      },
      error: (err) => this.showError(err)
    });
  }

  onStorefrontChange(): void {
    this.form.storefront_id = this.selectedStorefrontId;
    this.cancelEdit();
    this.loadCoupons();
  }

  startEdit(coupon: Coupon): void {
    this.editingCouponId = coupon.id;
    this.form = {
      storefront_id: coupon.storefront_id,
      code: coupon.code,
      discount_type: coupon.discount_type,
      value: coupon.value,
      minimum_amount: coupon.minimum_amount,
      starts_at: this.toDateTimeInput(coupon.starts_at),
      ends_at: this.toDateTimeInput(coupon.ends_at),
      is_enabled: coupon.is_enabled
    };
    this.selectedStorefrontId = coupon.storefront_id;
  }

  cancelEdit(): void {
    this.editingCouponId = null;
    this.form = this.emptyForm();
    this.form.storefront_id = this.selectedStorefrontId;
  }

  saveCoupon(): void {
    if (!this.form.storefront_id || !this.form.code.trim() || this.form.value <= 0) {
      this.errorMessage = 'Completa tienda, código y valor del cupón.';
      return;
    }
    if (this.form.discount_type === 'PERCENT' && this.form.value > 100) {
      this.errorMessage = 'El descuento porcentual no puede superar 100.';
      return;
    }
    this.saving = true;
    this.errorMessage = '';
    const payload = {
      ...this.form,
      code: this.form.code.trim().toUpperCase(),
      starts_at: this.toIsoOrNull(this.form.starts_at),
      ends_at: this.toIsoOrNull(this.form.ends_at)
    };
    const request = this.editingCouponId
      ? this.api.put<Coupon>(`/storefront/coupons/${this.editingCouponId}`, payload)
      : this.api.post<Coupon>('/storefront/coupons/', payload);
    request.subscribe({
      next: () => {
        this.saving = false;
        this.cancelEdit();
        this.loadCoupons();
      },
      error: (err) => {
        this.saving = false;
        this.showError(err);
      }
    });
  }

  disableCoupon(coupon: Coupon): void {
    this.swal.confirm(
      '¿Desactivar cupón?',
      `El código ${coupon.code} dejará de aplicarse en el checkout. Podrás conservarlo como referencia.`
    ).then((result) => {
      if (!result.isConfirmed) {
        return;
      }
      this.saving = true;
      this.api.delete<Coupon>(`/storefront/coupons/${coupon.id}`).subscribe({
        next: () => {
          this.saving = false;
          this.loadCoupons();
        },
        error: (err) => {
          this.saving = false;
          this.showError(err);
        }
      });
    });
  }

  storefrontName(storefrontId: string): string {
    return this.storefronts.find((storefront) => storefront.id === storefrontId)?.name || 'Tienda';
  }

  private emptyForm(): CouponForm {
    return {
      storefront_id: '',
      code: '',
      discount_type: 'PERCENT',
      value: 10,
      minimum_amount: 0,
      starts_at: '',
      ends_at: '',
      is_enabled: true
    };
  }

  private toDateTimeInput(value: string | null): string {
    return value ? value.slice(0, 16) : '';
  }

  private toIsoOrNull(value: string): string | null {
    return value ? new Date(value).toISOString() : null;
  }

  private showError(err: { error?: { detail?: string } }): void {
    this.loading = false;
    this.errorMessage = err?.error?.detail || 'No se pudieron cargar los cupones.';
  }
}
