import { Injectable } from '@angular/core';
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
    details: any;
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
    private apiUrl = `${environment.apiUrl}/audit`;

    constructor(private http: HttpClient) { }

    getAuditLogs(
        page: number = 1,
        limit: number = 20,
        filters: { user_id?: string, action?: string, entity_type?: string } = {}
    ): Observable<AuditLog[]> {
        let params = new HttpParams()
            .set('skip', ((page - 1) * limit).toString())
            .set('limit', limit.toString());

        if (filters.user_id) params = params.set('user_id', filters.user_id);
        if (filters.action) params = params.set('action', filters.action);
        if (filters.entity_type) params = params.set('entity_type', filters.entity_type);

        return this.http.get<AuditLog[]>(this.apiUrl, { params });
    }
}
