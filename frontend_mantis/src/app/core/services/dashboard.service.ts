import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface DashboardCard {
    title: string;
    amount: string;
    background: string;
    border: string;
    icon: string;
    percentage: string;
    color: string;
    number: string;
}

export interface RecentOrder {
    id: string;
    name: string;
    status: string;
    status_type: string;
    quantity: number;
    amount: string;
}

export interface TransactionHistory {
    background: string;
    icon: string;
    title: string;
    time: string;
    amount: string;
    percentage: string;
}

export interface ChartData {
    categories: string[];
    series: { name: string; data: number[] }[];
}

export interface DashboardStats {
    cards: DashboardCard[];
    recent_orders: RecentOrder[];
    transactions: TransactionHistory[];
    monthly_sales: ChartData;
    income_overview: ChartData;
    sales_report: ChartData;
}

export interface DashboardHealth {
    backend_ok: boolean;
    db_ok: boolean;
    db_message: string | null;
    current_revision: string | null;
    expected_head: string | null;
    migration_up_to_date: boolean | null;
    checked_at: string;
}

@Injectable({
    providedIn: 'root'
})
export class DashboardService {
    private http = inject(HttpClient);

    private apiUrl = `${environment.apiUrl}/dashboard`;

    getStats(filters?: { date_from?: string; date_to?: string; branch_id?: string }): Observable<DashboardStats> {
        const params: Record<string, string> = {};
        if (filters) {
            if (filters.date_from) params['date_from'] = filters.date_from;
            if (filters.date_to) params['date_to'] = filters.date_to;
            if (filters.branch_id) params['branch_id'] = filters.branch_id;
        }
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${this.apiUrl}?${queryString}` : this.apiUrl;
        return this.http.get<DashboardStats>(url);
    }

    getHealth(): Observable<DashboardHealth> {
        return this.http.get<DashboardHealth>(`${this.apiUrl}/health`);
    }
}
