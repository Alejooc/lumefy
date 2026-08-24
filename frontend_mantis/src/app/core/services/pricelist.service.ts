import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiService } from './api.service';

export interface PriceListItem {
    id?: string;
    product_id: string;
    variant_id?: string | null;
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
    source_id?: string | null;
    pricing_mode: 'FIXED' | 'MARKUP_PERCENT' | 'MARKUP_AMOUNT';
    base_source: 'INTERNAL_PRICE' | 'INTERNAL_COST' | 'EXTERNAL_PRICE' | 'EXTERNAL_COST';
    adjustment_value: number;
    rounding_step: number;
    min_margin_percent?: number | null;
    items?: PriceListItem[];
}

export interface PriceListPayload {
    name: string;
    type: 'SALE' | 'PURCHASE';
    currency: string;
    active: boolean;
    source_id?: string | null;
    pricing_mode?: PriceList['pricing_mode'];
    base_source?: PriceList['base_source'];
    adjustment_value?: number;
    rounding_step?: number;
    min_margin_percent?: number | null;
}

export interface PriceListItemPayload {
    product_id: string;
    variant_id?: string | null;
    min_quantity: number;
    price: number;
}

@Injectable({
    providedIn: 'root'
})
export class PriceListService {
    private http = inject(HttpClient);
    private api = inject(ApiService);

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

    updatePriceListItem(priceListId: string, itemId: string, item: Partial<PriceListItemPayload>): Observable<PriceListItem> {
        return this.http.put<PriceListItem>(`${this.apiUrl}/${priceListId}/items/${itemId}`, item);
    }

    deletePriceListItem(priceListId: string, itemId: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/${priceListId}/items/${itemId}`);
    }

    applyGlobalAdjustment(priceListId: string, payload: {
        percent: number;
        base_source?: PriceList['base_source'];
        preserve_overrides: boolean;
        rounding_step?: number;
        min_margin_percent?: number;
    }): Observable<PriceList> {
        return this.http.post<PriceList>(`${this.apiUrl}/${priceListId}/global-adjustment`, payload);
    }

    exportPriceList(priceListId: string): Observable<Blob> {
        return this.api.getBlob(`/pricelists/${priceListId}/export.xlsx`);
    }

    importPriceList(priceListId: string, file: File, dryRun = true): Observable<PriceListImportResult> {
        const form = new FormData();
        form.append('file', file);
        return this.http.post<PriceListImportResult>(`${this.apiUrl}/${priceListId}/import.xlsx?dry_run=${dryRun}`, form);
    }
}

export interface PriceListImportResult {
    dry_run: boolean;
    rows_received: number;
    rows_applied: number;
    rows_created: number;
    rows_updated: number;
    rows_cleared: number;
    rows_failed: number;
    errors: string[];
}
