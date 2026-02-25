import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Branch {
    id: string;
    name: string;
    is_warehouse: boolean;
    allow_pos: boolean;
    address?: string;
    phone?: string;
}

@Injectable({
    providedIn: 'root'
})
export class BranchService {
    private http = inject(HttpClient);

    private apiUrl = `${environment.apiUrl}/branches`;

    getBranches(): Observable<Branch[]> {
        return this.http.get<Branch[]>(this.apiUrl);
    }
}
