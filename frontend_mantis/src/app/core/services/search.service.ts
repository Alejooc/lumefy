import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface SearchItem {
    id: string;
    title: string;
    subtitle: string;
    url: string; // Internal route
    icon: string; // Feather icon name
}

export interface SearchResult {
    products: SearchItem[];
    clients: SearchItem[];
    sales: SearchItem[];
    users: SearchItem[];
}

@Injectable({
    providedIn: 'root'
})
export class SearchService {
    private apiUrl = `${environment.apiUrl}/search`;

    constructor(private http: HttpClient) { }

    search(query: string): Observable<SearchResult> {
        return this.http.get<SearchResult>(this.apiUrl, { params: { q: query } });
    }
}
