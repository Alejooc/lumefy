import { Injectable } from '@angular/core';
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
    unit_of_measure_id?: string;
    purchase_uom_id?: string;
    images: ProductImage[];
}

@Injectable({
    providedIn: 'root'
})
export class ProductService {
    private apiUrl = `${environment.apiUrl}/products`;

    constructor(private http: HttpClient) { }

    getProducts(): Observable<Product[]> {
        return this.http.get<Product[]>(this.apiUrl);
    }
}
