import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Supplier {
    id: string;
    name: string;
    email?: string;
    phone?: string;
    address?: string;
    tax_id?: string;
    price_list_id?: string;
    credit_limit?: number;
}

export interface SupplierPayload {
    name: string;
    email?: string;
    phone?: string;
    address?: string;
    tax_id?: string;
    price_list_id?: string;
}

@Injectable({
    providedIn: 'root'
})
export class SupplierService {
    private http = inject(HttpClient);

    private apiUrl = `${environment.apiUrl}/suppliers`;

    getSuppliers(): Observable<Supplier[]> {
        return this.http.get<Supplier[]>(this.apiUrl);
    }

    createSupplier(supplier: SupplierPayload): Observable<Supplier> {
        return this.http.post<Supplier>(this.apiUrl, supplier);
    }

    updateSupplier(id: string, supplier: Partial<SupplierPayload>): Observable<Supplier> {
        return this.http.put<Supplier>(`${this.apiUrl}/${id}`, supplier);
    }

    deleteSupplier(id: string): Observable<unknown> {
        return this.http.delete<unknown>(`${this.apiUrl}/${id}`);
    }
}
