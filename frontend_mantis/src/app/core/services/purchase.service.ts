import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface PurchaseOrderItem {
    id?: string;
    product_id: string;
    quantity: number;
    received_qty?: number;
    unit_cost: number;
    subtotal?: number;
    product?: { name: string; sku: string };
    variant?: { name: string; sku?: string };
}

// Assuming Supplier and Branch interfaces might be defined elsewhere or need a basic definition
// If they are defined in other files, you would import them.
// For this change, we'll define them simply to ensure the code is syntactically correct.
export interface Supplier {
    id: string;
    name: string;
    // ... other supplier properties
}

export interface Branch {
    id: string;
    name: string;
    // ... other branch properties
}

export interface PurchaseOrder {
    id: string;
    supplier_id: string;
    branch_id: string;
    status: string;
    payment_method: string;
    total_amount: number;
    notes?: string;
    expected_date?: string;
    order_date?: string;
    reference_number?: string;
    created_at: string;
    items: PurchaseOrderItem[];
    supplier?: Supplier;
    branch?: Branch;
}

@Injectable({
    providedIn: 'root'
})
export class PurchaseService {
    private apiUrl = `${environment.apiUrl}/purchases`;

    constructor(private http: HttpClient) { }

    getPurchases(): Observable<PurchaseOrder[]> {
        return this.http.get<PurchaseOrder[]>(this.apiUrl);
    }

    getPurchase(id: string): Observable<PurchaseOrder> {
        return this.http.get<PurchaseOrder>(`${this.apiUrl}/${id}`);
    }

    createPurchase(purchase: any): Observable<PurchaseOrder> {
        return this.http.post<PurchaseOrder>(this.apiUrl, purchase);
    }

    updateStatus(id: string, status: string): Observable<PurchaseOrder> {
        return this.http.put<PurchaseOrder>(`${this.apiUrl}/${id}/status`, null, { params: { status } });
    }

    downloadPdf(id: string): Observable<Blob> {
        return this.http.get(`${this.apiUrl}/${id}/pdf/order`, { responseType: 'blob' });
    }

    receivePurchase(id: string, items: { item_id: string; qty_received: number }[]): Observable<PurchaseOrder> {
        return this.http.post<PurchaseOrder>(`${this.apiUrl}/${id}/receive`, { items });
    }
}
