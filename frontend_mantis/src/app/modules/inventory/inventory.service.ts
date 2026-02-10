import { Injectable } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { Observable } from 'rxjs';
import { HttpParams } from '@angular/common/http';

export interface InventoryItem {
    id: string;
    product_id: string;
    branch_id: string;
    quantity: number;
    location?: string;
    batch_number?: string;
    expiry_date?: string;
    product?: any;
    branch?: any;
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
    user?: any;
    previous_stock?: number;
    new_stock?: number;
}

@Injectable({
    providedIn: 'root'
})
export class InventoryService {

    constructor(private api: ApiService) { }

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
}
