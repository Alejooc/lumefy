import { Injectable, inject } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { Observable } from 'rxjs';
import { Client } from './client.model';

export interface ClientListParams {
    q?: string;
    status?: string;
}

export interface ClientStatement {
    current_balance: number;
    entries: ClientStatementEntry[];
}

export interface ClientStatementEntry {
    created_at: string;
    type: 'CHARGE' | 'PAYMENT' | 'REFUND' | string;
    description: string;
    amount: number;
    balance_after: number;
}

export interface ClientPaymentPayload {
    amount: number;
    reference_id?: string;
    description: string;
}

export interface ClientActivity {
    id?: string;
    type: string;
    content: string;
    created_at?: string;
    [key: string]: unknown;
}

export interface ClientStats {
    total_sales: number;
    order_count: number;
    average_order_value: number;
    last_sale_at?: string | null;
}

export interface ClientTimelineEntry {
    id?: string;
    category: 'CALL' | 'EMAIL' | 'MEETING' | 'NOTE' | 'SYSTEM' | 'CHARGE' | 'SALE' | 'PAYMENT' | 'REFUND' | string;
    content: string;
    created_at: string;
    amount?: number;
}

export interface ClientSaleItem {
    id: string;
    created_at: string;
    branch_id: string;
    items?: unknown[];
    status: string;
    total: number;
}

export interface ClientSalesResponse {
    items: ClientSaleItem[];
    [key: string]: unknown;
}

@Injectable({
    providedIn: 'root'
})
export class ClientService {
    private api = inject(ApiService);


    getClients(params: ClientListParams = {}): Observable<Client[]> {
        let query = '';
        if (params) {
            query = '?' + new URLSearchParams(params as Record<string, string>).toString();
        }
        return this.api.get<Client[]>('/clients' + query);
    }

    getClient(id: string): Observable<Client> {
        return this.api.get<Client>(`/clients/${id}`);
    }

    createClient(client: Partial<Client>): Observable<Client> {
        return this.api.post<Client>('/clients', client);
    }

    updateClient(id: string, client: Partial<Client>): Observable<Client> {
        return this.api.put<Client>(`/clients/${id}`, client);
    }

    deleteClient(id: string): Observable<Client> {
        return this.api.delete<Client>(`/clients/${id}`);
    }

    // CRM / Statement
    getStatement(id: string): Observable<ClientStatement> {
        return this.api.get<ClientStatement>(`/clients/${id}/statement`);
    }

    registerPayment(id: string, payment: ClientPaymentPayload): Observable<ClientStatement> {
        return this.api.post<ClientStatement>(`/clients/${id}/payments`, payment);
    }

    // Activities
    getActivities(id: string): Observable<ClientActivity[]> {
        return this.api.get<ClientActivity[]>(`/clients/${id}/activities`);
    }

    createActivity(id: string, activity: ClientActivity): Observable<ClientActivity> {
        return this.api.post<ClientActivity>(`/clients/${id}/activities`, activity);
    }

    // Timeline & Stats
    getTimeline(id: string): Observable<ClientTimelineEntry[]> {
        return this.api.get<ClientTimelineEntry[]>(`/clients/${id}/timeline`);
    }

    getStats(id: string): Observable<ClientStats> {
        return this.api.get<ClientStats>(`/clients/${id}/stats`);
    }

    getSales(id: string, params: Record<string, string> = {}): Observable<ClientSalesResponse> {
        const query = '?' + new URLSearchParams(params).toString();
        return this.api.get<ClientSalesResponse>(`/clients/${id}/sales` + query);
    }
}
