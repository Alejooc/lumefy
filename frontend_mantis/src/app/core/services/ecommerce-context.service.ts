import { Injectable } from '@angular/core';

import { Storefront } from './storefront-admin.service';

@Injectable({
  providedIn: 'root'
})
export class EcommerceContextService {
  private readonly storageKey = 'ecommerce_selected_storefront_id';

  getSelectedStorefrontId(): string {
    return localStorage.getItem(this.storageKey) || '';
  }

  setSelectedStorefrontId(storefrontId: string): void {
    if (!storefrontId) {
      localStorage.removeItem(this.storageKey);
      return;
    }
    localStorage.setItem(this.storageKey, storefrontId);
  }

  resolveSelectedStorefront(storefronts: Storefront[]): string {
    const savedId = this.getSelectedStorefrontId();
    const match = storefronts.find((item) => item.id === savedId);
    const selectedId = match?.id || storefronts[0]?.id || '';
    this.setSelectedStorefrontId(selectedId);
    return selectedId;
  }
}
