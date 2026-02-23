import { Injectable } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { Observable } from 'rxjs';
import { Client } from './client.model';

@Injectable({
    providedIn: 'root'
})
export class ClientService {

    constructor(private api: ApiService) { }

    getClients(params: any = {}): Observable<Client[]> {
        let query = '';
        if (params) {
            query = '?' + new URLSearchParams(params).toString();
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
    getStatement(id: string): Observable<any> {
        return this.api.get<any>(`/clients/${id}/statement`);
    }

    registerPayment(id: string, payment: any): Observable<any> {
        return this.api.post<any>(`/clients/${id}/payments`, payment);
    }

    // Activities
    getActivities(id: string): Observable<any[]> {
        return this.api.get<any[]>(`/clients/${id}/activities`);
    }

    createActivity(id: string, activity: any): Observable<any> {
        return this.api.post<any>(`/clients/${id}/activities`, activity);
    }

    // Timeline & Stats
    getTimeline(id: string): Observable<any[]> {
        return this.api.get<any[]>(`/clients/${id}/timeline`);
    }

    getStats(id: string): Observable<any> {
        return this.api.get<any>(`/clients/${id}/stats`);
    }

    getSales(id: string, params: any = {}): Observable<any> {
        const query = '?' + new URLSearchParams(params).toString();
        return this.api.get<any>(`/clients/${id}/sales` + query);
    }
}
