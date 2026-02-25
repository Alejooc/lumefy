import { Injectable, inject } from '@angular/core';
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
    category_name?: string;
    image_url?: string;
}

export interface POSCartItem {
    product_id: string;
    quantity: number;
    price: number;
    discount: number;
    _tempProduct?: POSProduct;
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

export type POSSessionStatus = 'OPEN' | 'CLOSED';

export interface POSSession {
    id: string;
    branch_id: string;
    user_id: string;
    status: POSSessionStatus;
    opened_at: string;
    closed_at?: string | null;
    opening_amount: number;
    counted_amount: number;
    expected_amount: number;
    over_short: number;
    closing_note?: string | null;
    cash_sales_total: number;
}

export interface POSVoidResponse {
    success: boolean;
    sale_id: string;
    status: string;
    detail: string;
}

export interface POSSessionListItem {
    id: string;
    branch_id: string;
    branch_name?: string;
    user_id: string;
    user_name?: string;
    status: POSSessionStatus;
    opened_at: string;
    closed_at?: string | null;
    opening_amount: number;
    expected_amount: number;
    counted_amount: number;
    over_short: number;
    cash_sales_total: number;
    total_sales: number;
    transactions_count: number;
}

export interface POSSessionStats {
    id: string;
    branch_id: string;
    branch_name?: string;
    user_id: string;
    user_name?: string;
    status: POSSessionStatus;
    opened_at: string;
    closed_at?: string | null;
    opening_amount: number;
    expected_amount: number;
    counted_amount: number;
    over_short: number;
    transactions_count: number;
    total_sales: number;
    cash_sales_total: number;
    card_sales_total: number;
    credit_sales_total: number;
    average_ticket: number;
}

export interface POSConfig {
    show_sessions_manager: boolean;
    session_visibility_scope: 'own' | 'branch' | 'company';
    allow_multiple_open_sessions_per_branch: boolean;
    allow_enter_other_user_session: boolean;
    require_manager_for_void: boolean;
}

@Injectable({
    providedIn: 'root'
})
export class PosService {
    private http = inject(HttpClient);

    private apiUrl = `${environment.apiUrl}/pos`;

    getProducts(branchId: string): Observable<POSProduct[]> {
        return this.http.get<POSProduct[]>(`${this.apiUrl}/products`, { params: { branch_id: branchId } });
    }

    getConfig(): Observable<POSConfig> {
        return this.http.get<POSConfig>(`${this.apiUrl}/config`);
    }

    getCurrentSession(branchId: string): Observable<POSSession | null> {
        return this.http.get<POSSession | null>(`${this.apiUrl}/sessions/current`, { params: { branch_id: branchId } });
    }

    listSessions(branchId?: string, status?: POSSessionStatus, limit = 50): Observable<POSSessionListItem[]> {
        const params: Record<string, string> = { limit: String(limit) };
        if (branchId) params['branch_id'] = branchId;
        if (status) params['status'] = status;
        return this.http.get<POSSessionListItem[]>(`${this.apiUrl}/sessions`, { params });
    }

    getSessionStats(sessionId: string): Observable<POSSessionStats> {
        return this.http.get<POSSessionStats>(`${this.apiUrl}/sessions/${sessionId}/stats`);
    }

    openSession(branchId: string, openingAmount: number, openingNote?: string): Observable<POSSession> {
        return this.http.post<POSSession>(`${this.apiUrl}/sessions/open`, {
            branch_id: branchId,
            opening_amount: openingAmount,
            opening_note: openingNote
        });
    }

    closeSession(sessionId: string, countedAmount: number, closingNote?: string): Observable<POSSession> {
        return this.http.post<POSSession>(`${this.apiUrl}/sessions/${sessionId}/close`, {
            counted_amount: countedAmount,
            closing_note: closingNote
        });
    }

    voidSale(saleId: string, reason?: string): Observable<POSVoidResponse> {
        return this.http.post<POSVoidResponse>(`${this.apiUrl}/sales/${saleId}/void`, { reason });
    }

    checkout(data: POSCheckout): Observable<POSCheckoutResponse> {
        return this.http.post<POSCheckoutResponse>(`${this.apiUrl}/checkout`, data);
    }
}
