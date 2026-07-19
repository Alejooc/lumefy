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
    // Commerce is scoped to the company's only storefront.  Always resolving
    // the canonical first row also clears any selector saved by older builds.
    const selectedId = storefronts[0]?.id || '';
    this.setSelectedStorefrontId(selectedId);
    return selectedId;
  }
}
