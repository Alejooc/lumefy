import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

/**
 * Provider REST image endpoints can require integration credentials. Route
 * those URLs through the backend proxy for admin previews instead of asking
 * the browser to fetch them anonymously.
 */
export function productImageUrl(value?: string | null): string {
    const normalized = (value || '').trim();
    if (!normalized) return '';
    try {
        const parsed = new URL(normalized);
        if (parsed.pathname.includes('/api/external/')) {
            return `${environment.apiUrl}/integrations/assets?url=${encodeURIComponent(normalized)}`;
        }
    } catch {
        // Keep relative uploads and local paths unchanged.
    }
    return normalized;
}

export interface ProductImage {
    id?: string;
    image_url: string;
    order: number;
}

export interface Product {
    id?: string;
    name: string;
    internal_reference?: string;
    sku?: string;
    barcode?: string;
    description?: string;
    image_url?: string;
    attributes?: Record<string, unknown>;
    product_type: string;
    price: number;
    cost: number;
    tax_rate: number;
    weight?: number;
    volume?: number;
    track_inventory: boolean;
    tracking_type?: 'NONE' | 'LOT' | 'SERIAL';
    purchase_ok?: boolean;
    min_stock: number;
    category_id?: string;
    brand_id?: string;
    category?: { id?: string; name: string };
    brand?: { id?: string; name: string };
    unit_of_measure_id?: string;
    purchase_uom_id?: string;
    visible_in_ecommerce?: boolean;
    images: ProductImage[];
    variants?: ProductVariant[]; // Added for variant support
    variant_count?: number;
}

export interface ProductVariant {
    id: string;
    product_id: string;
    name: string;
    sku?: string;
    barcode?: string;
    price_extra: number;
    cost_extra: number;
    price?: number;
    cost?: number;
    attributes?: Record<string, unknown>;
}

@Injectable({
    providedIn: 'root'
})
export class ProductService {
    private http = inject(HttpClient);

    private apiUrl = `${environment.apiUrl}/products`;

    getProducts(): Observable<Product[]> {
        return this.http.get<Product[]>(this.apiUrl);
    }
}
