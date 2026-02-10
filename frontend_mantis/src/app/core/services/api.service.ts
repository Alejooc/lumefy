import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
    providedIn: 'root'
})
export class ApiService {
    constructor(private http: HttpClient) { }

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

    get<T>(path: string, params: HttpParams = new HttpParams()): Observable<T> {
        return this.http.get<T>(`${environment.apiUrl}${path}`, { headers: this.getHeaders(), params });
    }

    post<T>(path: string, body: any = {}): Observable<T> {
        const isFormData = body instanceof FormData;
        return this.http.post<T>(`${environment.apiUrl}${path}`, body, { headers: this.getHeaders(isFormData) });
    }

    put<T>(path: string, body: any = {}): Observable<T> {
        const isFormData = body instanceof FormData;
        return this.http.put<T>(`${environment.apiUrl}${path}`, body, { headers: this.getHeaders(isFormData) });
    }

    delete<T>(path: string): Observable<T> {
        return this.http.delete<T>(`${environment.apiUrl}${path}`, { headers: this.getHeaders() });
    }
}
