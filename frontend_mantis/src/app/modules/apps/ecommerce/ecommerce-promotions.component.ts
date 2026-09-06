import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import {
  PublishedProduct,
  StoreCollection,
  Storefront,
  StorefrontAdminService,
  StorefrontPromotion,
  StorefrontPromotionTargetType
} from 'src/app/core/services/storefront-admin.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

interface PromotionForm {
  storefront_id: string;
  name: string;
  target_type: StorefrontPromotionTargetType;
  collection_id: string | null;
  published_product_id: string | null;
  discount_percent: number;
  priority: number;
  starts_at: string;
  ends_at: string;
  is_enabled: boolean;
}

@Component({
  selector: 'app-ecommerce-promotions',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ecommerce-promotions.component.html',
  styleUrls: ['./ecommerce-shared.component.scss', './ecommerce-promotions.component.scss']
})
export class EcommercePromotionsComponent implements OnInit {
  private storefrontService = inject(StorefrontAdminService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);

  storefronts: Storefront[] = [];
  collections: StoreCollection[] = [];
  products: PublishedProduct[] = [];
  promotions: StorefrontPromotion[] = [];
  selectedStorefrontId = '';
  targetSearch = '';
  editingPromotionId: string | null = null;
  loading = false;
  saving = false;
  errorMessage = '';
  form: PromotionForm = this.emptyForm();

  ngOnInit(): void {
    if (!this.permissions.hasPermission('manage_company')) {
      this.errorMessage = 'No tienes permiso para administrar promociones.';
      return;
    }
    this.loading = true;
    this.storefrontService.getStorefronts().subscribe({
      next: (storefronts) => {
        this.storefronts = storefronts;
        this.selectedStorefrontId = storefronts[0]?.id || '';
        this.form.storefront_id = this.selectedStorefrontId;
        this.loadStorefrontData();
      },
      error: (err) => this.showError(err)
    });
  }

  loadStorefrontData(): void {
    if (!this.selectedStorefrontId) {
      this.collections = [];
      this.products = [];
      this.promotions = [];
      this.loading = false;
      return;
    }
    this.loading = true;
    this.storefrontService.getCollections(this.selectedStorefrontId).subscribe({
      next: (collections) => {
        this.collections = collections;
        this.storefrontService.getPublishedProducts(this.selectedStorefrontId).subscribe({
          next: (products) => {
            this.products = products;
            this.storefrontService.getPromotions(this.selectedStorefrontId).subscribe({
              next: (promotions) => {
                this.promotions = promotions;
                this.loading = false;
                this.errorMessage = '';
              },
              error: (err) => this.showError(err)
            });
          },
          error: (err) => this.showError(err)
        });
      },
      error: (err) => this.showError(err)
    });
  }

  onStorefrontChange(): void {
    this.cancelEdit();
    this.form.storefront_id = this.selectedStorefrontId;
    this.loadStorefrontData();
  }

  onTargetTypeChange(): void {
    this.targetSearch = '';
    if (this.form.target_type === 'COLLECTION') {
      this.form.published_product_id = null;
    } else {
      this.form.collection_id = null;
    }
  }

  get filteredCollections(): StoreCollection[] {
    const query = this.targetSearch.trim().toLowerCase();
    return this.collections.filter((collection) => !query || `${collection.name} ${collection.slug}`.toLowerCase().includes(query));
  }

  get filteredProducts(): PublishedProduct[] {
    const query = this.targetSearch.trim().toLowerCase();
    return this.products.filter((product) => !query || `${product.product_name || ''} ${product.slug}`.toLowerCase().includes(query));
  }

  get selectedTargetLabel(): string {
    if (this.form.target_type === 'COLLECTION') {
      return this.collections.find((collection) => collection.id === this.form.collection_id)?.name || 'Selecciona una colección';
    }
    const product = this.products.find((entry) => entry.id === this.form.published_product_id);
    return product?.product_name || product?.slug || 'Selecciona un producto';
  }

  get selectedStorefrontName(): string {
    return this.storefronts.find((storefront) => storefront.id === this.selectedStorefrontId)?.name || 'la tienda';
  }

  get previewBasePrice(): number {
    if (this.form.target_type !== 'PRODUCT') {
      return 100;
    }
    return this.products.find((product) => product.id === this.form.published_product_id)?.base_price || 0;
  }

  get previewPrice(): number {
    return Math.max(0, this.previewBasePrice * (1 - Math.min(100, Math.max(0, Number(this.form.discount_percent) || 0)) / 100));
  }

  startEdit(promotion: StorefrontPromotion): void {
    this.editingPromotionId = promotion.id;
    this.selectedStorefrontId = promotion.storefront_id;
    this.form = {
      storefront_id: promotion.storefront_id,
      name: promotion.name,
      target_type: promotion.target_type,
      collection_id: promotion.collection_id || null,
      published_product_id: promotion.published_product_id || null,
      discount_percent: promotion.discount_percent,
      priority: promotion.priority,
      starts_at: this.toDateTimeInput(promotion.starts_at),
      ends_at: this.toDateTimeInput(promotion.ends_at),
      is_enabled: promotion.is_enabled
    };
    this.targetSearch = '';
  }

  cancelEdit(): void {
    this.editingPromotionId = null;
    this.form = this.emptyForm();
    this.form.storefront_id = this.selectedStorefrontId;
    this.targetSearch = '';
  }

  savePromotion(): void {
    if (!this.form.storefront_id || !this.form.name.trim() || this.form.discount_percent <= 0 || this.form.discount_percent > 100) {
      this.errorMessage = 'Completa el nombre y un descuento entre 0,01% y 100%.';
      return;
    }
    if (this.form.target_type === 'COLLECTION' && !this.form.collection_id) {
      this.errorMessage = 'Selecciona la colección que recibirá la promoción.';
      return;
    }
    if (this.form.target_type === 'PRODUCT' && !this.form.published_product_id) {
      this.errorMessage = 'Selecciona el producto que recibirá la promoción.';
      return;
    }
    this.saving = true;
    this.errorMessage = '';
    const payload = {
      ...this.form,
      name: this.form.name.trim(),
      starts_at: this.toIsoOrNull(this.form.starts_at),
      ends_at: this.toIsoOrNull(this.form.ends_at),
      collection_id: this.form.target_type === 'COLLECTION' ? this.form.collection_id : null,
      published_product_id: this.form.target_type === 'PRODUCT' ? this.form.published_product_id : null
    };
    const request = this.editingPromotionId
      ? this.storefrontService.updatePromotion(this.editingPromotionId, payload)
      : this.storefrontService.createPromotion(payload);
    request.subscribe({
      next: () => {
        this.saving = false;
        this.cancelEdit();
        this.loadStorefrontData();
      },
      error: (err) => {
        this.saving = false;
        this.showError(err);
      }
    });
  }

  disablePromotion(promotion: StorefrontPromotion): void {
    this.swal.confirm(
      '¿Desactivar promoción?',
      `“${promotion.name}” dejará de aplicarse en el catálogo y el checkout.`
    ).then((result) => {
      if (!result.isConfirmed) {
        return;
      }
      this.saving = true;
      this.storefrontService.disablePromotion(promotion.id).subscribe({
        next: () => {
          this.saving = false;
          this.loadStorefrontData();
        },
        error: (err) => {
          this.saving = false;
          this.showError(err);
        }
      });
    });
  }

  promotionState(promotion: StorefrontPromotion): 'active' | 'scheduled' | 'expired' | 'disabled' {
    if (!promotion.is_enabled) {
      return 'disabled';
    }
    const now = Date.now();
    if (promotion.starts_at && new Date(promotion.starts_at).getTime() > now) {
      return 'scheduled';
    }
    if (promotion.ends_at && new Date(promotion.ends_at).getTime() < now) {
      return 'expired';
    }
    return 'active';
  }

  stateLabel(promotion: StorefrontPromotion): string {
    return { active: 'Activa', scheduled: 'Programada', expired: 'Finalizada', disabled: 'Desactivada' }[this.promotionState(promotion)];
  }

  private emptyForm(): PromotionForm {
    return {
      storefront_id: '',
      name: '',
      target_type: 'COLLECTION',
      collection_id: null,
      published_product_id: null,
      discount_percent: 15,
      priority: 0,
      starts_at: '',
      ends_at: '',
      is_enabled: true
    };
  }

  private toDateTimeInput(value?: string | null): string {
    return value ? value.slice(0, 16) : '';
  }

  private toIsoOrNull(value: string): string | null {
    return value ? new Date(value).toISOString() : null;
  }

  private showError(err: { error?: { detail?: string } }): void {
    this.loading = false;
    this.errorMessage = err?.error?.detail || 'No se pudieron cargar las promociones.';
  }
}
