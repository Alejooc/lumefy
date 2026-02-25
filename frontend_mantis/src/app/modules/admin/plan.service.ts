import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Plan {
    id: string;
    name: string;
    code: string;
    description?: string;
    price: number;
    currency: string;
    duration_days: number;
    button_text?: string;
    features: string[] | Record<string, boolean | string>;
    limits: { users?: number; storage?: number; branches?: number };
    is_active: boolean;
    is_public: boolean;
}

export interface PlanPayload {
    name: string;
    code: string;
    description?: string;
    price: number;
    currency: string;
    duration_days: number;
    button_text?: string;
    features: string[] | Record<string, boolean | string>;
    limits: { users?: number; storage?: number; branches?: number };
    is_active: boolean;
    is_public: boolean;
}

@Injectable({
    providedIn: 'root'
})
export class PlanService {
    private apiUrl = `${environment.apiUrl}/plans`;
    private http = inject(HttpClient);

    getPlans(): Observable<Plan[]> {
        return this.http.get<Plan[]>(`${this.apiUrl}/`);
    }

    getAllPlans(): Observable<Plan[]> {
        return this.http.get<Plan[]>(`${this.apiUrl}/all`);
    }

    createPlan(plan: PlanPayload): Observable<Plan> {
        return this.http.post<Plan>(this.apiUrl, plan);
    }

    updatePlan(id: string, plan: Partial<PlanPayload>): Observable<Plan> {
        return this.http.put<Plan>(`${this.apiUrl}/${id}`, plan);
    }
}
