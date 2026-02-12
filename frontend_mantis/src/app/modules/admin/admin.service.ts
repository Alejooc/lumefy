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
}
