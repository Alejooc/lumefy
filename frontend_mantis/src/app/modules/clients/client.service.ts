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
}
