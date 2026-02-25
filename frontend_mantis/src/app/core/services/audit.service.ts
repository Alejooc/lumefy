import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AuditLog {
    id: string;
    user_id: string;
    company_id: string;
    action: string;
    entity_type: string;
    entity_id: string;
    details: Record<string, unknown> | null;
    created_at: string;
    user?: {
        full_name: string;
        email: string;
    };
}

@Injectable({
    providedIn: 'root'
})
export class AuditService {
    private http = inject(HttpClient);

    private apiUrl = `${environment.apiUrl}/audit`;

    getAuditLogs(
        page: number = 1,
        limit: number = 50,
        filters: { user_id?: string, action?: string, entity_type?: string, date_from?: string, date_to?: string } = {}
    ): Observable<AuditLog[]> {
        let params = new HttpParams()
            .set('skip', ((page - 1) * limit).toString())
            .set('limit', limit.toString());

        if (filters.user_id) params = params.set('user_id', filters.user_id);
        if (filters.action) params = params.set('action', filters.action);
        if (filters.entity_type) params = params.set('entity_type', filters.entity_type);
        if (filters.date_from) params = params.set('date_from', filters.date_from);
        if (filters.date_to) params = params.set('date_to', filters.date_to);

        return this.http.get<AuditLog[]>(this.apiUrl, { params });
    }
}
