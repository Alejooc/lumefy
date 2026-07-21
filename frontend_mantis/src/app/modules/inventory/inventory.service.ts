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
    reserved_quantity: number;
    average_cost: number;
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
    type: 'IN' | 'OUT' | 'ADJ' | 'TRF' | 'RESERVE' | 'RELEASE';
    quantity: number;
    unit_cost?: number;
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

export interface ReplenishmentSuggestion {
    product_id: string;
    product_name: string;
    sku?: string;
    branch_id: string;
    branch_name: string;
    current_quantity: number;
    minimum_quantity: number;
    suggested_quantity: number;
}

export interface InventoryValuation {
    branches: Array<{ branch_id: string; branch_name: string; stock_quantity: number; inventory_value: number }>;
    total_value: number;
}

export interface InventoryLot {
    id: string;
    product_id: string;
    product_name: string;
    branch_id: string;
    branch_name: string;
    lot_number?: string;
    serial_number?: string;
    quantity: number;
    expiry_date?: string;
    unit_cost: number;
    source_reference?: string;
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

    getReplenishmentSuggestions(branchId?: string): Observable<ReplenishmentSuggestion[]> {
        let params = new HttpParams();
        if (branchId) params = params.set('branch_id', branchId);
        return this.api.get<ReplenishmentSuggestion[]>('/inventory/replenishment', params);
    }

    getValuation(branchId?: string): Observable<InventoryValuation> {
        let params = new HttpParams();
        if (branchId) params = params.set('branch_id', branchId);
        return this.api.get<InventoryValuation>('/inventory/valuation', params);
    }

    getLots(branchId?: string): Observable<InventoryLot[]> {
        let params = new HttpParams();
        if (branchId) params = params.set('branch_id', branchId);
        return this.api.get<InventoryLot[]>('/inventory/lots', params);
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
