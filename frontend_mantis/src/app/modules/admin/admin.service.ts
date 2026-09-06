import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AdminStats {
    total_companies: number;
    active_companies: number;
    total_users: number;
    mrr: number;
    mrr_currency: string | null;
    mrr_by_currency: Record<string, number>;
    mrr_is_estimate: boolean;
    active_subscription_count: number;
    paid_subscription_count: number;
    unpriced_active_subscriptions: number;
    active_subscriptions: Record<string, number>;
    subscription_statuses: Record<string, number>;
}

export interface SystemSetting {
    key: string;
    value: string;
    group: string;
    is_public: boolean;
    description?: string;
}

export interface AdminUser {
    id: string;
    email: string;
    full_name: string;
    role?: { name: string } | null;
    is_active?: boolean;
    is_superuser?: boolean;
    company_id?: string;
    company?: { name: string } | null;
}

export interface ImpersonationResponse {
    access_token: string;
    user: { email: string };
    session_id: string;
    started_at: string;
}

export type SaaSBillingState = 'PAID' | 'PENDING' | 'OVERDUE' | 'DUE_SOON' | 'NO_RECORD';

export interface SaaSBillingRecord {
    id: string;
    company_id: string;
    plan_code: string;
    period_start: string;
    period_end: string;
    amount: number;
    currency: string;
    status: 'PENDING' | 'PAID' | 'REJECTED' | 'CANCELLED';
    payment_method?: string | null;
    reference?: string | null;
    proof_url?: string | null;
    notes?: string | null;
    rejection_reason?: string | null;
    paid_at?: string | null;
    verified_at?: string | null;
}

export interface SaaSBillingPortfolioItem {
    company_id: string;
    company_name: string;
    plan?: string | null;
    subscription_status?: string | null;
    valid_until?: string | null;
    is_active: boolean;
    billing_state: SaaSBillingState;
    latest_record?: SaaSBillingRecord | null;
}

export interface SaaSBillingRecordPayload {
    plan_code: string;
    period_start: string;
    period_end: string;
    amount: number;
    currency?: string | null;
    payment_method?: string | null;
    reference?: string | null;
    proof_url?: string | null;
    notes?: string | null;
}

export interface SystemHealth {
    cpu: { percent: number; count: number };
    memory: { percent: number; used: number; total: number };
    disk: { percent: number; free: number; total?: number };
    uptime_seconds: number;
}

export interface DatabaseStat {
    table_name: string;
    row_count: number;
    total_size: string;
    total_size_bytes: number;
}

export interface BroadcastConfig {
    message?: string;
    is_active?: boolean;
    type?: 'info' | 'warning' | 'danger' | 'success';
    [key: string]: unknown;
}

export interface NotificationTemplate {
    id: string;
    code: string;
    name: string;
    type: 'info' | 'success' | 'warning' | 'danger';
    title_template: string;
    body_template: string;
    is_active: boolean;
}

export interface ManualNotificationPayload {
    target_all: boolean;
    user_id: string | null;
    title: string;
    message: string;
    type: 'info' | 'success' | 'warning' | 'danger';
    link?: string;
}

export interface ManualNotificationResponse {
    message: string;
}

@Injectable({
    providedIn: 'root'
})
export class AdminService {
    private http = inject(HttpClient);

    private apiUrl = `${environment.apiUrl}/admin`;

    getStats(): Observable<AdminStats> {
        return this.http.get<AdminStats>(`${this.apiUrl}/stats`);
    }

    getSettings(): Observable<SystemSetting[]> {
        return this.http.get<SystemSetting[]>(`${this.apiUrl}/settings`);
    }

    updateSettings(settings: Array<Pick<SystemSetting, 'key' | 'value' | 'group' | 'is_public'>>): Observable<SystemSetting[]> {
        return this.http.put<SystemSetting[]>(`${this.apiUrl}/settings/bulk`, settings);
    }

    getPublicSettings(): Observable<SystemSetting[]> {
        return this.http.get<SystemSetting[]>(`${this.apiUrl}/settings/public`);
    }

    impersonateCompany(companyId: string, reason: string): Observable<ImpersonationResponse> {
        return this.http.post<ImpersonationResponse>(`${this.apiUrl}/users/impersonate-company/${companyId}`, { reason });
    }

    impersonateUser(userId: string, reason: string): Observable<ImpersonationResponse> {
        return this.http.post<ImpersonationResponse>(`${this.apiUrl}/users/${userId}/impersonate`, { reason });
    }

    getUsers(search: string = ''): Observable<AdminUser[]> {
        let params = '';
        if (search) params = `?search=${search}`;
        return this.http.get<AdminUser[]>(`${this.apiUrl}/users${params}`);
    }

    extendSubscription(companyId: string, data: { valid_until: string, plan?: string }): Observable<unknown> {
        return this.http.put<unknown>(`${this.apiUrl}/companies/${companyId}`, data);
    }

    getBillingPortfolio(): Observable<SaaSBillingPortfolioItem[]> {
        return this.http.get<SaaSBillingPortfolioItem[]>(`${this.apiUrl}/billing`);
    }

    getCompanyBillingRecords(companyId: string): Observable<SaaSBillingRecord[]> {
        return this.http.get<SaaSBillingRecord[]>(`${this.apiUrl}/companies/${companyId}/billing`);
    }

    createBillingRecord(companyId: string, payload: SaaSBillingRecordPayload): Observable<SaaSBillingRecord> {
        return this.http.post<SaaSBillingRecord>(`${this.apiUrl}/companies/${companyId}/billing`, payload);
    }

    verifyBillingRecord(
        recordId: string,
        payload: { status: 'PAID' | 'REJECTED' | 'CANCELLED'; reference?: string | null; proof_url?: string | null; rejection_reason?: string | null }
    ): Observable<SaaSBillingRecord> {
        return this.http.post<SaaSBillingRecord>(`${this.apiUrl}/billing/${recordId}/verify`, payload);
    }

    getSystemHealth(): Observable<SystemHealth> {
        return this.http.get<SystemHealth>(`${environment.apiUrl}/system/health`);
    }

    getMaintenanceStatus(): Observable<{ enabled: boolean }> {
        return this.http.get<{ enabled: boolean }>(`${environment.apiUrl}/system/maintenance`);
    }

    setMaintenanceStatus(enabled: boolean): Observable<{ enabled: boolean }> {
        return this.http.post<{ enabled: boolean }>(`${environment.apiUrl}/system/maintenance`, { enabled });
    }

    getDatabaseStats(): Observable<DatabaseStat[]> {
        return this.http.get<DatabaseStat[]>(`${environment.apiUrl}/system/database-stats`);
    }

    getBroadcast(): Observable<BroadcastConfig> {
        return this.http.get<BroadcastConfig>(`${environment.apiUrl}/system/broadcast`, {
            headers: new HttpHeaders({ 'X-Suppress-Error': 'true' })
        });
    }

    setBroadcast(msg: BroadcastConfig): Observable<BroadcastConfig> {
        return this.http.post<BroadcastConfig>(`${environment.apiUrl}/system/broadcast`, msg);
    }

    // --- Notification Admin ---
    getNotificationTemplates(): Observable<NotificationTemplate[]> {
        return this.http.get<NotificationTemplate[]>(`${this.apiUrl}/notifications/templates`);
    }

    createNotificationTemplate(data: Omit<NotificationTemplate, 'id'>): Observable<NotificationTemplate> {
        return this.http.post<NotificationTemplate>(`${this.apiUrl}/notifications/templates`, data);
    }

    updateNotificationTemplate(id: string, data: Partial<Omit<NotificationTemplate, 'id'>>): Observable<NotificationTemplate> {
        return this.http.put<NotificationTemplate>(`${this.apiUrl}/notifications/templates/${id}`, data);
    }

    sendManualNotification(data: ManualNotificationPayload): Observable<ManualNotificationResponse> {
        return this.http.post<ManualNotificationResponse>(`${this.apiUrl}/notifications/send`, data);
    }
}
