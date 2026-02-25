import { Injectable, inject } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { Observable } from 'rxjs';
import { HttpParams } from '@angular/common/http';
import { Branch } from 'src/app/core/services/branch.service';

export interface InventoryProduct {
    id: string;
    name: string;
    sku?: string;
}

export interface InventoryItem {
    id: string;
    product_id: string;
    branch_id: string;
    quantity: number;
    location?: string;
    batch_number?: string;
    expiry_date?: string;
    product?: InventoryProduct;
    branch?: Branch;
}

export interface InventoryMovement {
    id?: string;
    product_id: string;
    branch_id: string;
    type: 'IN' | 'OUT' | 'ADJ' | 'TRF';
    quantity: number;
    reason?: string;
    reference_id?: string;
    created_at?: string;
    user?: { id: string; full_name?: string; email?: string };
    previous_stock?: number;
    new_stock?: number;
}

export interface StockTakeItem {
    id: string;
    product_id: string;
    system_qty: number;
    counted_qty: number | null;
    difference: number;
    product?: InventoryProduct;
}

export interface StockTake {
    id: string;
    branch_id: string;
    status: 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
    created_at: string;
    notes?: string;
    item_count?: number;
    branch?: Branch;
    items: StockTakeItem[];
}

@Injectable({
    providedIn: 'root'
})
export class InventoryService {
    private api = inject(ApiService);


    getInventory(branchId?: string, productId?: string): Observable<InventoryItem[]> {
        let params = new HttpParams();
        if (branchId) params = params.set('branch_id', branchId);
        if (productId) params = params.set('product_id', productId);
        return this.api.get<InventoryItem[]>('/inventory', params);
    }

    getMovements(productId?: string, branchId?: string): Observable<InventoryMovement[]> {
        let params = new HttpParams();
        if (branchId) params = params.set('branch_id', branchId);
        if (productId) params = params.set('product_id', productId);
        return this.api.get<InventoryMovement[]>('/inventory/movements', params);
    }

    createMovement(movement: InventoryMovement): Observable<InventoryMovement> {
        return this.api.post<InventoryMovement>('/inventory/movement', movement);
    }

    // Stock Take
    getStockTakes(): Observable<StockTake[]> {
        return this.api.get<StockTake[]>('/stock-take');
    }

    createStockTake(data: { branch_id: string; notes?: string }): Observable<StockTake> {
        return this.api.post<StockTake>('/stock-take', data);
    }

    getStockTake(id: string): Observable<StockTake> {
        return this.api.get<StockTake>(`/stock-take/${id}`);
    }

    updateStockTakeCounts(id: string, items: { id: string; counted_qty: number | null }[]): Observable<StockTake> {
        return this.api.put<StockTake>(`/stock-take/${id}/count`, { items });
    }

    applyStockTake(id: string): Observable<StockTake> {
        return this.api.post<StockTake>(`/stock-take/${id}/apply`, {});
    }

    cancelStockTake(id: string): Observable<StockTake> {
        return this.api.post<StockTake>(`/stock-take/${id}/cancel`, {});
    }
}
