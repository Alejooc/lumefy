import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AdminStats {
    total_companies: number;
    active_companies: number;
    total_users: number;
    mrr: number;
    active_subscriptions: {
        FREE: number;
        PRO: number;
        ENTERPRISE: number;
    };
}

export interface SystemSetting {
    key: string;
    value: string;
    group: string;
    is_public: boolean;
    description?: string;
}

@Injectable({
    providedIn: 'root'
})
export class AdminService {
    private apiUrl = `${environment.apiUrl}/admin`;

    constructor(private http: HttpClient) { }

    getStats(): Observable<AdminStats> {
        return this.http.get<AdminStats>(`${this.apiUrl}/stats`);
    }

    getSettings(): Observable<SystemSetting[]> {
        return this.http.get<SystemSetting[]>(`${this.apiUrl}/settings`);
    }

    updateSettings(settings: any[]): Observable<SystemSetting[]> {
        return this.http.put<SystemSetting[]>(`${this.apiUrl}/settings/bulk`, settings);
    }

    getPublicSettings(): Observable<SystemSetting[]> {
        return this.http.get<SystemSetting[]>(`${this.apiUrl}/settings/public`);
    }

    impersonateCompany(companyId: string): Observable<any> {
        return this.http.post<any>(`${this.apiUrl}/users/impersonate-company/${companyId}`, {});
    }

    impersonateUser(userId: string): Observable<any> {
        return this.http.post<any>(`${this.apiUrl}/users/${userId}/impersonate`, {});
    }

    getUsers(): Observable<any[]> {
        return this.http.get<any[]>(`${this.apiUrl}/users`);
    }

    extendSubscription(companyId: string, data: { valid_until: string, plan?: string }): Observable<any> {
        return this.http.put<any>(`${this.apiUrl}/companies/${companyId}`, data);
    }

    getSystemHealth(): Observable<any> {
        return this.http.get<any>(`${this.apiUrl}/system/health`);
    }

    getMaintenanceStatus(): Observable<{ enabled: boolean }> {
        return this.http.get<{ enabled: boolean }>(`${this.apiUrl}/system/maintenance`);
    }

    setMaintenanceStatus(enabled: boolean): Observable<{ enabled: boolean }> {
        return this.http.post<{ enabled: boolean }>(`${this.apiUrl}/system/maintenance`, { enabled });
    }

    getDatabaseStats(): Observable<any[]> {
        return this.http.get<any[]>(`${this.apiUrl}/system/database-stats`);
    }

    getBroadcast(): Observable<any> {
        return this.http.get<any>(`${this.apiUrl}/system/broadcast`);
    }

    setBroadcast(msg: any): Observable<any> {
        return this.http.post<any>(`${this.apiUrl}/system/broadcast`, msg);
    }

    // --- Notification Admin ---
    getNotificationTemplates(): Observable<any[]> {
        return this.http.get<any[]>(`${this.apiUrl}/notifications/templates`);
    }

    createNotificationTemplate(data: any): Observable<any> {
        return this.http.post<any>(`${this.apiUrl}/notifications/templates`, data);
    }

    updateNotificationTemplate(id: string, data: any): Observable<any> {
        return this.http.put<any>(`${this.apiUrl}/notifications/templates/${id}`, data);
    }

    sendManualNotification(data: any): Observable<any> {
        return this.http.post<any>(`${this.apiUrl}/notifications/send`, data);
    }
}
