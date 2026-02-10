import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface SaleItem {
    id?: string;
    product_id: string;
    quantity: number;
    price: number;
    discount: number;
    total?: number;
    product?: { name: string; sku: string };
}

export interface Payment {
    method: string;
    amount: number;
    reference?: string;
}

export interface Sale {
    id: string;
    branch_id: string;
    client_id?: string;
    user_id: string;
    status: 'QUOTE' | 'DRAFT' | 'CONFIRMED' | 'DISPATCHED' | 'DELIVERED' | 'COMPLETED' | 'CANCELLED';
    subtotal: number;
    tax: number;
    discount: number;
    shipping_cost: number;
    total: number;
    payment_method?: string;
    valid_until?: string;
    shipping_address?: string;
    notes?: string;
    created_at: string;
    updated_at?: string;
    items?: SaleItem[];
    payments?: Payment[];
    client?: { name: string; email: string; address?: string; phone?: string };
    user?: { full_name: string };
    branch?: { name: string };
}

@Injectable({
    providedIn: 'root'
})
export class SaleService {
    private apiUrl = `${environment.apiUrl}/sales`;

    constructor(private http: HttpClient) { }

    getSales(status?: string, clientId?: string): Observable<Sale[]> {
        let params: any = {};
        if (status) params.status = status;
        if (clientId) params.client_id = clientId;
        return this.http.get<Sale[]>(this.apiUrl, { params });
    }

    getSale(id: string): Observable<Sale> {
        return this.http.get<Sale>(`${this.apiUrl}/${id}`);
    }

    createSale(saleData: any): Observable<Sale> {
        return this.http.post<Sale>(this.apiUrl, saleData);
    }

    updateSale(id: string, saleData: any): Observable<Sale> {
        return this.http.put<Sale>(`${this.apiUrl}/${id}`, saleData);
    }

    updateStatus(id: string, status: string): Observable<Sale> {
        return this.http.put<Sale>(`${this.apiUrl}/${id}/status`, {}, { params: { status } });
    }
}
