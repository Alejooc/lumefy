import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface ReturnItem {
    id?: string;
    sale_item_id: string;
    product_id: string;
    quantity_returned: number;
    unit_price: number;
    subtotal: number;
    product?: { name: string; sku: string };
}

export interface ReturnOrder {
    id: string;
    sale_id: string;
    created_by: string;
    return_type: 'PARTIAL' | 'TOTAL';
    status: 'PENDING' | 'APPROVED' | 'REJECTED';
    reason?: string;
    total_refund: number;
    notes?: string;
    created_at: string;
    approved_at?: string;
    items: ReturnItem[];
    creator?: { full_name: string };
    approver?: { full_name: string };
}

export interface ReturnItemCreate {
    sale_item_id: string;
    quantity: number;
}

export interface ReturnOrderCreate {
    sale_id: string;
    reason?: string;
    notes?: string;
    items: ReturnItemCreate[];
}

@Injectable({
    providedIn: 'root'
})
export class ReturnService {
    private api = inject(ApiService);
    private basePath = '/returns';

    getReturns(saleId?: string, status?: string): Observable<ReturnOrder[]> {
        let params: any = {};
        if (saleId) params.sale_id = saleId;
        if (status) params.status = status;
        const queryStr = Object.entries(params).map(([k, v]) => `${k}=${v}`).join('&');
        const path = queryStr ? `${this.basePath}?${queryStr}` : this.basePath;
        return this.api.get<ReturnOrder[]>(path);
    }

    getReturn(id: string): Observable<ReturnOrder> {
        return this.api.get<ReturnOrder>(`${this.basePath}/${id}`);
    }

    createReturn(data: ReturnOrderCreate): Observable<ReturnOrder> {
        return this.api.post<ReturnOrder>(this.basePath, data);
    }

    approveReturn(id: string): Observable<ReturnOrder> {
        return this.api.post<ReturnOrder>(`${this.basePath}/${id}/approve`, {});
    }

    rejectReturn(id: string): Observable<ReturnOrder> {
        return this.api.post<ReturnOrder>(`${this.basePath}/${id}/reject`, {});
    }
}
