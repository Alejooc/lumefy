import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface PriceListItem {
    id?: string;
    product_id: string;
    min_quantity: number;
    price: number;
    product?: any; // To hold product details
}

export interface PriceList {
    id: string;
    name: string;
    type: 'SALE' | 'PURCHASE';
    currency: string;
    active: boolean;
    items?: PriceListItem[];
}

@Injectable({
    providedIn: 'root'
})
export class PriceListService {
    private apiUrl = `${environment.apiUrl}/pricelists`;

    constructor(private http: HttpClient) { }

    getPriceLists(type?: 'SALE' | 'PURCHASE'): Observable<PriceList[]> {
        let url = this.apiUrl;
        if (type) {
            url += `?type=${type}`;
        }
        return this.http.get<PriceList[]>(url);
    }

    getPriceList(id: string): Observable<PriceList> {
        return this.http.get<PriceList>(`${this.apiUrl}/${id}`);
    }

    createPriceList(priceList: any): Observable<PriceList> {
        return this.http.post<PriceList>(this.apiUrl, priceList);
    }

    updatePriceList(id: string, priceList: any): Observable<PriceList> {
        return this.http.put<PriceList>(`${this.apiUrl}/${id}`, priceList);
    }

    addPriceListItem(priceListId: string, item: any): Observable<PriceListItem> {
        return this.http.post<PriceListItem>(`${this.apiUrl}/${priceListId}/items`, item);
    }
}
