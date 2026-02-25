import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

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
    product_type: string;
    price: number;
    cost: number;
    tax_rate: number;
    weight?: number;
    volume?: number;
    track_inventory: boolean;
    min_stock: number;
    category_id?: string;
    brand_id?: string;
    category?: { id?: string; name: string };
    brand?: { id?: string; name: string };
    unit_of_measure_id?: string;
    purchase_uom_id?: string;
    images: ProductImage[];
    variants?: ProductVariant[]; // Added for variant support
}

export interface ProductVariant {
    id: string;
    product_id: string;
    name: string;
    sku?: string;
    barcode?: string;
    price_extra: number;
    cost_extra: number;
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
