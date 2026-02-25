import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface PriceListItem {
    id?: string;
    product_id: string;
    min_quantity: number;
    price: number;
    product?: { id: string; name: string; sku?: string };
}

export interface PriceList {
    id: string;
    name: string;
    type: 'SALE' | 'PURCHASE';
    currency: string;
    active: boolean;
    items?: PriceListItem[];
}

export interface PriceListPayload {
    name: string;
    type: 'SALE' | 'PURCHASE';
    currency: string;
    active: boolean;
}

export interface PriceListItemPayload {
    product_id: string;
    min_quantity: number;
    price: number;
}

@Injectable({
    providedIn: 'root'
})
export class PriceListService {
    private http = inject(HttpClient);

    private apiUrl = `${environment.apiUrl}/pricelists`;

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

    createPriceList(priceList: PriceListPayload): Observable<PriceList> {
        return this.http.post<PriceList>(this.apiUrl, priceList);
    }

    updatePriceList(id: string, priceList: Partial<PriceListPayload>): Observable<PriceList> {
        return this.http.put<PriceList>(`${this.apiUrl}/${id}`, priceList);
    }

    addPriceListItem(priceListId: string, item: PriceListItemPayload): Observable<PriceListItem> {
        return this.http.post<PriceListItem>(`${this.apiUrl}/${priceListId}/items`, item);
    }
}
