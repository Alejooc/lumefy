import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface BomLine { component_id: string; quantity: number; }
export interface Bom { id: string; product_id: string; quantity: number; lines: BomLine[]; }
export interface ManufacturingOrder { id: string; bom_id: string; branch_id: string; quantity: number; status: 'DRAFT' | 'CONFIRMED' | 'DONE' | 'CANCELLED'; }

@Injectable({ providedIn: 'root' })
export class ManufacturingService {
  private api = inject(ApiService);
  listBoms(): Observable<Bom[]> { return this.api.get<Bom[]>('/manufacturing/boms'); }
  createBom(payload: Omit<Bom, 'id'>): Observable<Bom> { return this.api.post<Bom>('/manufacturing/boms', payload); }
  listOrders(): Observable<ManufacturingOrder[]> { return this.api.get<ManufacturingOrder[]>('/manufacturing/orders'); }
  createOrder(payload: Omit<ManufacturingOrder, 'id' | 'status'>): Observable<ManufacturingOrder> { return this.api.post<ManufacturingOrder>('/manufacturing/orders', payload); }
  completeOrder(id: string): Observable<ManufacturingOrder> { return this.api.post<ManufacturingOrder>(`/manufacturing/orders/${id}/complete`, {}); }
  confirmOrder(id: string): Observable<ManufacturingOrder> { return this.api.post<ManufacturingOrder>(`/manufacturing/orders/${id}/confirm`, {}); }
  cancelOrder(id: string): Observable<ManufacturingOrder> { return this.api.post<ManufacturingOrder>(`/manufacturing/orders/${id}/cancel`, {}); }
}
