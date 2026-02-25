import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface SaleItem {
    id?: string;
    product_id: string;
    quantity: number;
    quantity_picked?: number; // Added for logistics
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
    status: 'QUOTE' | 'DRAFT' | 'CONFIRMED' | 'PICKING' | 'PACKING' | 'DISPATCHED' | 'DELIVERED' | 'COMPLETED' | 'CANCELLED';
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
    delivered_at?: string;
    delivery_notes?: string;
    delivery_evidence_url?: string;
    completed_at?: string;
    items?: SaleItem[];
    payments?: Payment[];
    client?: { name: string; email: string; address?: string; phone?: string };
    user?: { full_name: string };
    branch?: { name: string };
}

export interface SalePayload {
    branch_id: string;
    client_id?: string;
    status?: Sale['status'];
    subtotal: number;
    tax: number;
    discount: number;
    shipping_cost: number;
    total: number;
    payment_method?: string;
    valid_until?: string;
    shipping_address?: string;
    notes?: string;
    items?: SaleItem[];
    payments?: Payment[];
}

@Injectable({
    providedIn: 'root'
})
export class SaleService {
    private http = inject(HttpClient);

    private apiUrl = `${environment.apiUrl}/sales`;

    getSales(status?: string, clientId?: string): Observable<Sale[]> {
        const params: Record<string, string> = {};
        if (status) params['status'] = status;
        if (clientId) params['client_id'] = clientId;
        return this.http.get<Sale[]>(this.apiUrl, { params });
    }

    getSale(id: string): Observable<Sale> {
        return this.http.get<Sale>(`${this.apiUrl}/${id}`);
    }

    createSale(saleData: SalePayload): Observable<Sale> {
        return this.http.post<Sale>(this.apiUrl, saleData);
    }

    updateSale(id: string, saleData: Partial<SalePayload>): Observable<Sale> {
        return this.http.put<Sale>(`${this.apiUrl}/${id}`, saleData);
    }

    updateStatus(id: string, status: string): Observable<Sale> {
        return this.http.put<Sale>(`${this.apiUrl}/${id}/status`, {}, { params: { status } });
    }
    deleteSale(id: string): Observable<Sale> {
        return this.http.delete<Sale>(`${this.apiUrl}/${id}`);
    }

    downloadPdf(id: string, type: string): Observable<Blob> {
        return this.http.get(`${this.apiUrl}/${id}/pdf/${type}`, { responseType: 'blob' });
    }

    confirmDelivery(id: string, data: { notes?: string; evidence_url?: string }): Observable<Sale> {
        return this.http.post<Sale>(`${this.apiUrl}/${id}/deliver`, data);
    }

    completeSale(id: string): Observable<Sale> {
        return this.http.post<Sale>(`${this.apiUrl}/${id}/complete`, {});
    }
}
