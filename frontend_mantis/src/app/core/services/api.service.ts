import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

type QueryParams = HttpParams | Record<string, string | number | boolean | null | undefined>;

@Injectable({
    providedIn: 'root'
})
export class ApiService {
    private http = inject(HttpClient);


    private getHeaders(isFormData: boolean = false): HttpHeaders {
        const token = localStorage.getItem('access_token');
        let headers = new HttpHeaders();

        if (!isFormData) {
            headers = headers.set('Content-Type', 'application/json');
        }

        if (token) {
            headers = headers.append('Authorization', `Bearer ${token}`);
        }
        return headers;
    }

    private normalizeParams(params: QueryParams = new HttpParams()): HttpParams {
        if (params instanceof HttpParams) {
            return params;
        }

        let httpParams = new HttpParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                httpParams = httpParams.set(key, String(value));
            }
        });
        return httpParams;
    }

    get<T>(path: string, params: QueryParams = new HttpParams(), suppressError: boolean = false): Observable<T> {
        let headers = this.getHeaders();
        if (suppressError) {
            headers = headers.set('X-Suppress-Error', 'true');
        }
        return this.http.get<T>(`${environment.apiUrl}${path}`, { headers, params: this.normalizeParams(params) });
    }

    post<T>(path: string, body: unknown = {}): Observable<T> {
        const isFormData = body instanceof FormData;
        return this.http.post<T>(`${environment.apiUrl}${path}`, body, { headers: this.getHeaders(isFormData) });
    }

    put<T>(path: string, body: unknown = {}): Observable<T> {
        const isFormData = body instanceof FormData;
        return this.http.put<T>(`${environment.apiUrl}${path}`, body, { headers: this.getHeaders(isFormData) });
    }

    delete<T>(path: string): Observable<T> {
        return this.http.delete<T>(`${environment.apiUrl}${path}`, { headers: this.getHeaders() });
    }
}
