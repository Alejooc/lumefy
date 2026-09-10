import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import {
  PublishedProduct,
  StoreCollection,
  Storefront,
  StorefrontAdminService,
  StorefrontPromotion,
  StorefrontPromotionCustomerEligibility,
  StorefrontPromotionDiscountType,
  StorefrontPromotionGetDiscountType,
  StorefrontPromotionKind,
  StorefrontPromotionMethod,
  StorefrontPromotionMinimumRequirement,
  StorefrontPromotionRewardTargetType,
  StorefrontPromotionTargetType
} from 'src/app/core/services/storefront-admin.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

interface PromotionForm {
  storefront_id: string;
  name: string;
  method: StorefrontPromotionMethod;
  code: string;
  promotion_type: StorefrontPromotionKind;
  target_type: StorefrontPromotionTargetType;
  collection_id: string | null;
  published_product_id: string | null;
  reward_target_type: StorefrontPromotionRewardTargetType | null;
  reward_collection_id: string | null;
  reward_published_product_id: string | null;
  buy_quantity: number;
  get_quantity: number;
  get_discount_type: StorefrontPromotionGetDiscountType;
  get_discount_value: number;
  discount_type: StorefrontPromotionDiscountType;
  discount_value: number;
  priority: number;
  minimum_requirement: StorefrontPromotionMinimumRequirement;
  minimum_amount: number;
  minimum_quantity: number;
  customer_eligibility: StorefrontPromotionCustomerEligibility;
  usage_limit: number | null;
  once_per_customer: boolean;
  combines_with_product: boolean;
  combines_with_order: boolean;
  combines_with_shipping: boolean;
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
  rewardSearch = '';
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

  onMethodChange(): void {
    if (this.form.method === 'AUTOMATIC') {
      this.form.code = '';
    }
  }

  onPromotionTypeChange(): void {
    if (this.form.promotion_type === 'BUY_X_GET_Y') {
      if (!['COLLECTION', 'PRODUCT'].includes(this.form.target_type)) {
        this.form.target_type = 'COLLECTION';
      }
      this.form.discount_type = 'PERCENT';
      this.form.discount_value = 100;
      this.form.get_discount_type = 'PERCENT';
      this.form.get_discount_value = 100;
      this.form.reward_target_type = this.form.target_type === 'PRODUCT' ? 'PRODUCT' : 'COLLECTION';
      this.form.reward_collection_id = this.form.target_type === 'COLLECTION' ? this.form.collection_id : null;
      this.form.reward_published_product_id = this.form.target_type === 'PRODUCT' ? this.form.published_product_id : null;
    }
    this.onTargetTypeChange();
  }

  onTargetTypeChange(): void {
    this.targetSearch = '';
    if (this.form.target_type === 'COLLECTION') {
      this.form.published_product_id = null;
    } else if (this.form.target_type === 'PRODUCT') {
      this.form.collection_id = null;
    } else {
      this.form.collection_id = null;
      this.form.published_product_id = null;
    }
    if (this.form.promotion_type === 'BUY_X_GET_Y') {
      this.form.discount_type = 'PERCENT';
      this.form.discount_value = 100;
      if (!this.form.reward_target_type) {
        this.form.reward_target_type = this.form.target_type === 'PRODUCT' ? 'PRODUCT' : 'COLLECTION';
      }
      if (this.form.reward_target_type === this.form.target_type) {
        if (this.form.reward_target_type === 'COLLECTION' && !this.form.reward_collection_id) {
          this.form.reward_collection_id = this.form.collection_id;
        }
        if (this.form.reward_target_type === 'PRODUCT' && !this.form.reward_published_product_id) {
          this.form.reward_published_product_id = this.form.published_product_id;
        }
      }
    } else if (this.form.target_type === 'SHIPPING') {
      this.form.discount_type = 'FREE_SHIPPING';
      this.form.discount_value = 0;
    } else if (this.form.discount_type === 'FREE_SHIPPING') {
      this.form.discount_type = 'PERCENT';
      this.form.discount_value = 15;
    }
  }

  onRewardTargetTypeChange(): void {
    this.rewardSearch = '';
    if (this.form.reward_target_type === 'COLLECTION') {
      this.form.reward_published_product_id = null;
    } else {
      this.form.reward_collection_id = null;
    }
  }

  onDiscountTypeChange(): void {
    if (this.form.promotion_type === 'BUY_X_GET_Y') {
      this.form.discount_type = 'PERCENT';
      this.form.discount_value = 100;
      return;
    }
    if (this.form.discount_type === 'FREE_SHIPPING') {
      this.form.target_type = 'SHIPPING';
      this.onTargetTypeChange();
    } else if (this.form.target_type === 'SHIPPING') {
      this.form.target_type = 'ORDER';
    }
  }

  generateCode(): void {
    const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    const bytes = new Uint32Array(8);
    crypto.getRandomValues(bytes);
    this.form.code = Array.from(bytes, (value) => alphabet[value % alphabet.length]).join('');
  }

  get filteredCollections(): StoreCollection[] {
    const query = this.targetSearch.trim().toLowerCase();
    return this.collections.filter((collection) => !query || `${collection.name} ${collection.slug}`.toLowerCase().includes(query));
  }

  get filteredProducts(): PublishedProduct[] {
    const query = this.targetSearch.trim().toLowerCase();
    return this.products.filter((product) => !query || `${product.product_name || ''} ${product.slug}`.toLowerCase().includes(query));
  }

  get filteredRewardCollections(): StoreCollection[] {
    const query = this.rewardSearch.trim().toLowerCase();
    return this.collections.filter((collection) => !query || `${collection.name} ${collection.slug}`.toLowerCase().includes(query));
  }

  get filteredRewardProducts(): PublishedProduct[] {
    const query = this.rewardSearch.trim().toLowerCase();
    return this.products.filter((product) => !query || `${product.product_name || ''} ${product.slug}`.toLowerCase().includes(query));
  }

  get selectedTargetLabel(): string {
    if (this.form.target_type === 'ORDER') return 'Pedido completo';
    if (this.form.target_type === 'SHIPPING') return 'Envío';
    if (this.form.target_type === 'COLLECTION') {
      return this.collections.find((collection) => collection.id === this.form.collection_id)?.name || 'Selecciona una colección';
    }
    const product = this.products.find((entry) => entry.id === this.form.published_product_id);
    return product?.product_name || product?.slug || 'Selecciona un producto';
  }

  get selectedRewardLabel(): string {
    if (this.form.reward_target_type === 'COLLECTION') {
      return this.collections.find((collection) => collection.id === this.form.reward_collection_id)?.name || 'Selecciona una colección';
    }
    const product = this.products.find((entry) => entry.id === this.form.reward_published_product_id);
    return product?.product_name || product?.slug || 'Selecciona un producto';
  }

  get selectedStorefrontName(): string {
    return this.storefronts.find((storefront) => storefront.id === this.selectedStorefrontId)?.name || 'la tienda';
  }

  get targetNeedsSelection(): boolean {
    return this.form.target_type === 'COLLECTION' || this.form.target_type === 'PRODUCT';
  }

  get previewBasePrice(): number {
    if (this.form.target_type !== 'PRODUCT') return 100;
    return this.products.find((product) => product.id === this.form.published_product_id)?.base_price || 0;
  }

  get previewPrice(): number {
    if (this.form.discount_type === 'FREE_SHIPPING') return 0;
    const value = Math.max(0, Number(this.form.discount_value) || 0);
    if (this.form.discount_type === 'FIXED') return Math.max(0, this.previewBasePrice - value);
    return Math.max(0, this.previewBasePrice * (1 - Math.min(100, value) / 100));
  }

  get previewDiscountLabel(): string {
    if (this.form.promotion_type === 'BUY_X_GET_Y') {
      const reward = this.form.get_discount_type === 'PERCENT'
        ? (this.form.get_discount_value >= 100 ? 'gratis' : `${this.form.get_discount_value || 0}% de descuento`)
        : `${this.form.get_discount_value || 0} de descuento fijo`;
      return `Compra ${this.form.buy_quantity || 0} y lleva ${this.form.get_quantity || 0} ${reward}`;
    }
    if (this.form.discount_type === 'FREE_SHIPPING') return 'Envío gratis';
    return this.form.discount_type === 'FIXED'
      ? `${this.form.discount_value || 0} de descuento fijo`
      : `${this.form.discount_value || 0}% de descuento`;
  }

  startEdit(promotion: StorefrontPromotion): void {
    this.editingPromotionId = promotion.id;
    this.selectedStorefrontId = promotion.storefront_id;
    this.form = {
      storefront_id: promotion.storefront_id,
      name: promotion.name,
      method: promotion.method || 'AUTOMATIC',
      code: promotion.code || '',
      promotion_type: promotion.promotion_type || 'AMOUNT_OFF',
      target_type: promotion.target_type,
      collection_id: promotion.collection_id || null,
      published_product_id: promotion.published_product_id || null,
      reward_target_type: promotion.reward_target_type || null,
      reward_collection_id: promotion.reward_collection_id || null,
      reward_published_product_id: promotion.reward_published_product_id || null,
      buy_quantity: promotion.buy_quantity || 1,
      get_quantity: promotion.get_quantity || 1,
      get_discount_type: promotion.get_discount_type || 'PERCENT',
      get_discount_value: promotion.get_discount_value ?? 100,
      discount_type: promotion.discount_type || 'PERCENT',
      discount_value: promotion.discount_value ?? promotion.discount_percent ?? 15,
      priority: promotion.priority,
      minimum_requirement: promotion.minimum_requirement || 'NONE',
      minimum_amount: promotion.minimum_amount || 0,
      minimum_quantity: promotion.minimum_quantity || 0,
      customer_eligibility: promotion.customer_eligibility || 'ALL',
      usage_limit: promotion.usage_limit ?? null,
      once_per_customer: promotion.once_per_customer || false,
      combines_with_product: promotion.combines_with_product || false,
      combines_with_order: promotion.combines_with_order || false,
      combines_with_shipping: promotion.combines_with_shipping || false,
      starts_at: this.toDateTimeInput(promotion.starts_at),
      ends_at: this.toDateTimeInput(promotion.ends_at),
      is_enabled: promotion.is_enabled
    };
    this.targetSearch = '';
    this.rewardSearch = '';
  }

  cancelEdit(): void {
    this.editingPromotionId = null;
    this.form = this.emptyForm();
    this.form.storefront_id = this.selectedStorefrontId;
    this.targetSearch = '';
    this.rewardSearch = '';
  }

  savePromotion(): void {
    const value = Number(this.form.discount_value);
    const isBuyXGetY = this.form.promotion_type === 'BUY_X_GET_Y';
    const rewardValue = Number(this.form.get_discount_value);
    if (!this.form.storefront_id || !this.form.name.trim()) {
      this.errorMessage = 'Completa el nombre de la promoción.';
      return;
    }
    if (this.form.method === 'CODE' && !this.form.code.trim()) {
      this.errorMessage = 'Indica el código que usará el cliente en el checkout.';
      return;
    }
    if (isBuyXGetY && (!(Number(this.form.buy_quantity) > 0) || !(Number(this.form.get_quantity) > 0))) {
      this.errorMessage = 'Indica cuántas unidades debe comprar y cuántas recibirá como beneficio.';
      return;
    }
    if (isBuyXGetY && this.form.get_discount_type === 'PERCENT' && (!(rewardValue > 0) || rewardValue > 100)) {
      this.errorMessage = 'El porcentaje de la recompensa debe estar entre 0,01% y 100%.';
      return;
    }
    if (isBuyXGetY && this.form.get_discount_type === 'FIXED' && !(rewardValue > 0)) {
      this.errorMessage = 'El descuento fijo de la recompensa debe ser mayor que cero.';
      return;
    }
    if (!isBuyXGetY && this.form.discount_type === 'PERCENT' && (!(value > 0) || value > 100)) {
      this.errorMessage = 'El porcentaje debe estar entre 0,01% y 100%.';
      return;
    }
    if (!isBuyXGetY && this.form.discount_type === 'FIXED' && !(value > 0)) {
      this.errorMessage = 'El descuento fijo debe ser mayor que cero.';
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
    if (isBuyXGetY && this.form.reward_target_type === 'COLLECTION' && !this.form.reward_collection_id) {
      this.errorMessage = 'Selecciona la colección que recibirá el beneficio.';
      return;
    }
    if (isBuyXGetY && this.form.reward_target_type === 'PRODUCT' && !this.form.reward_published_product_id) {
      this.errorMessage = 'Selecciona el producto que recibirá el beneficio.';
      return;
    }
    if (this.form.minimum_requirement === 'AMOUNT' && !(Number(this.form.minimum_amount) > 0)) {
      this.errorMessage = 'Indica un monto mínimo mayor que cero.';
      return;
    }
    if (this.form.minimum_requirement === 'QUANTITY' && !(Number(this.form.minimum_quantity) > 0)) {
      this.errorMessage = 'Indica una cantidad mínima mayor que cero.';
      return;
    }
    this.saving = true;
    this.errorMessage = '';
    const payload = {
       ...this.form,
       name: this.form.name.trim(),
       code: this.form.method === 'CODE' ? this.form.code.trim().toUpperCase() : null,
       promotion_type: this.form.promotion_type,
       reward_target_type: isBuyXGetY ? this.form.reward_target_type : null,
       reward_collection_id: isBuyXGetY && this.form.reward_target_type === 'COLLECTION' ? this.form.reward_collection_id : null,
       reward_published_product_id: isBuyXGetY && this.form.reward_target_type === 'PRODUCT' ? this.form.reward_published_product_id : null,
       discount_type: isBuyXGetY ? 'PERCENT' : this.form.discount_type,
       discount_value: isBuyXGetY ? 100 : (this.form.discount_type === 'FREE_SHIPPING' ? 0 : value),
       discount_percent: isBuyXGetY || this.form.discount_type === 'PERCENT' ? (isBuyXGetY ? 100 : value) : null,
       get_discount_value: isBuyXGetY ? rewardValue : this.form.get_discount_value,
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
      if (!result.isConfirmed) return;
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

  duplicatePromotion(promotion: StorefrontPromotion): void {
    this.swal.confirm(
      '¿Duplicar promoción?',
      `Se creará una copia desactivada de “${promotion.name}” para que puedas ajustarla.`
    ).then((result) => {
      if (!result.isConfirmed) return;
      this.saving = true;
      this.storefrontService.duplicatePromotion(promotion.id).subscribe({
        next: (duplicate) => {
          this.saving = false;
          this.startEdit(duplicate);
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
    if (!promotion.is_enabled) return 'disabled';
    const now = Date.now();
    if (promotion.starts_at && new Date(promotion.starts_at).getTime() > now) return 'scheduled';
    if (promotion.ends_at && new Date(promotion.ends_at).getTime() < now) return 'expired';
    return 'active';
  }

  stateLabel(promotion: StorefrontPromotion): string {
    return { active: 'Activa', scheduled: 'Programada', expired: 'Finalizada', disabled: 'Desactivada' }[this.promotionState(promotion)];
  }

  promotionValueLabel(promotion: StorefrontPromotion): string {
    if (promotion.promotion_type === 'BUY_X_GET_Y') {
      const reward = promotion.get_discount_type === 'PERCENT'
        ? (promotion.get_discount_value >= 100 ? 'gratis' : `${promotion.get_discount_value}%`)
        : `${promotion.get_discount_value} fijo`;
      return `${promotion.buy_quantity} + ${promotion.get_quantity} ${reward}`;
    }
    if (promotion.discount_type === 'FREE_SHIPPING') return 'Envío gratis';
    return promotion.discount_type === 'FIXED'
      ? `${promotion.discount_value} fijo`
      : `${promotion.discount_value}%`;
  }

  targetTypeLabel(targetType: StorefrontPromotionTargetType): string {
    return { COLLECTION: 'Colección', PRODUCT: 'Producto', ORDER: 'Pedido', SHIPPING: 'Envío' }[targetType];
  }

  methodLabel(method: StorefrontPromotionMethod): string {
    return method === 'CODE' ? 'Código' : 'Automática';
  }

  customerEligibilityLabel(eligibility: StorefrontPromotionCustomerEligibility): string {
    return {
      ALL: 'Todos los clientes',
      NEW_CUSTOMERS: 'Clientes nuevos',
      RETURNING_CUSTOMERS: 'Clientes recurrentes'
    }[eligibility];
  }

  private emptyForm(): PromotionForm {
    return {
      storefront_id: '',
      name: '',
      method: 'AUTOMATIC',
      code: '',
      promotion_type: 'AMOUNT_OFF',
      target_type: 'COLLECTION',
      collection_id: null,
      published_product_id: null,
      reward_target_type: 'COLLECTION',
      reward_collection_id: null,
      reward_published_product_id: null,
      buy_quantity: 1,
      get_quantity: 1,
      get_discount_type: 'PERCENT',
      get_discount_value: 100,
      discount_type: 'PERCENT',
      discount_value: 15,
      priority: 0,
      minimum_requirement: 'NONE',
      minimum_amount: 0,
      minimum_quantity: 0,
      customer_eligibility: 'ALL',
      usage_limit: null,
      once_per_customer: false,
      combines_with_product: false,
      combines_with_order: false,
      combines_with_shipping: false,
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
