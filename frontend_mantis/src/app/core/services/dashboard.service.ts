import { Injectable } from '@angular/core';
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
    private apiUrl = `${environment.apiUrl}/dashboard`;

    constructor(private http: HttpClient) { }

    getStats(): Observable<DashboardStats> {
        return this.http.get<DashboardStats>(this.apiUrl);
    }

    getHealth(): Observable<DashboardHealth> {
        return this.http.get<DashboardHealth>(`${this.apiUrl}/health`);
    }
}
