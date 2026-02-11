import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface PurchaseOrderItem {
    id?: string;
    product_id: string;
    quantity: number;
    unit_cost: number;
    subtotal?: number;
    product?: { name: string; sku: string };
}

export interface PurchaseOrder {
    id: string;
    supplier_id: string;
    branch_id?: string;
    status: 'DRAFT' | 'VALIDATION' | 'CONFIRMED' | 'RECEIVED' | 'CANCELLED';
    total_amount: number;
    notes?: string;
    expected_date?: string;
    created_at: string;
    items?: PurchaseOrderItem[];
    supplier?: { name: string };
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
}
