import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface POSProduct {
    id: string;
    name: string;
    sku?: string;
    barcode?: string;
    price: number;
    stock: number;
    category_id?: string;
    image_url?: string;
}

export interface POSCartItem {
    product_id: string;
    quantity: number;
    price: number;
    discount: number;
    _tempProduct?: any;
}

export interface POSCheckout {
    branch_id: string;
    client_id?: string;
    items: POSCartItem[];
    payment_method: string;
    amount_paid: number;
    notes?: string;
}

export interface POSCheckoutResponse {
    success: boolean;
    sale_id: string;
    total: number;
    change: number;
}

@Injectable({
    providedIn: 'root'
})
export class PosService {
    private apiUrl = `${environment.apiUrl}/pos`;

    constructor(private http: HttpClient) { }

    getProducts(branchId: string): Observable<POSProduct[]> {
        return this.http.get<POSProduct[]>(`${this.apiUrl}/products`, { params: { branch_id: branchId } });
    }

    checkout(data: POSCheckout): Observable<POSCheckoutResponse> {
        return this.http.post<POSCheckoutResponse>(`${this.apiUrl}/checkout`, data);
    }
}
