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
    closing_audit?: {
        closed_at: string;
        closed_by_user_id: string;
        transactions_count: number;
        opening_amount: number;
        total_sales: number;
        cash_sales_total: number;
        card_sales_total: number;
        credit_sales_total: number;
        expected_amount: number;
        counted_amount: number;
        over_short: number;
    } | null;
    reopen_audit?: {
        reopened_at: string;
        reopened_by_user_id: string;
        reason: string;
        previous_closed_at?: string | null;
        previous_counted_amount: number;
        previous_expected_amount: number;
        previous_over_short: number;
    } | null;
    can_reopen?: boolean;
}

export interface POSSessionListFilters {
    branchId?: string;
    status?: POSSessionStatus;
    userId?: string;
    openedFrom?: string;
    openedTo?: string;
    limit?: number;
}

export interface POSConfig {
    show_sessions_manager: boolean;
    session_visibility_scope: 'own' | 'branch' | 'company';
    allow_multiple_open_sessions_per_branch: boolean;
    allow_enter_other_user_session: boolean;
    require_manager_for_void: boolean;
    allow_reopen_closed_sessions: boolean;
    over_short_alert_threshold: number;
}

export interface POSDailyCloseSummary {
    date: string;
    branch_id?: string | null;
    sales_count: number;
    gross_sales: number;
    payments_cash: number;
    payments_card: number;
    payments_credit: number;
    returns_count: number;
    total_refunds: number;
    net_sales: number;
    sessions_opened_count: number;
    sessions_closed_count: number;
    opening_amount_total: number;
    expected_amount_total: number;
    counted_amount_total: number;
    over_short_total: number;
    open_sessions_now: number;
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

    getDailyClose(targetDate: string, branchId?: string): Observable<POSDailyCloseSummary> {
        const params: Record<string, string> = { target_date: targetDate };
        if (branchId) params['branch_id'] = branchId;
        return this.http.get<POSDailyCloseSummary>(`${environment.apiUrl}/reports/daily-close`, { params });
    }

    getCurrentSession(branchId: string): Observable<POSSession | null> {
        return this.http.get<POSSession | null>(`${this.apiUrl}/sessions/current`, { params: { branch_id: branchId } });
    }

    listSessions(filters: POSSessionListFilters = {}): Observable<POSSessionListItem[]> {
        const params: Record<string, string> = { limit: String(filters.limit ?? 50) };
        if (filters.branchId) params['branch_id'] = filters.branchId;
        if (filters.status) params['status'] = filters.status;
        if (filters.userId) params['user_id'] = filters.userId;
        if (filters.openedFrom) params['opened_from'] = filters.openedFrom;
        if (filters.openedTo) params['opened_to'] = filters.openedTo;
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

    reopenSession(sessionId: string, reason: string): Observable<POSSession> {
        return this.http.post<POSSession>(`${this.apiUrl}/sessions/${sessionId}/reopen`, { reason });
    }

    voidSale(saleId: string, reason?: string): Observable<POSVoidResponse> {
        return this.http.post<POSVoidResponse>(`${this.apiUrl}/sales/${saleId}/void`, { reason });
    }

    checkout(data: POSCheckout): Observable<POSCheckoutResponse> {
        return this.http.post<POSCheckoutResponse>(`${this.apiUrl}/checkout`, data);
    }
}
