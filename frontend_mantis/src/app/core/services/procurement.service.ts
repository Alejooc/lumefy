import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface ProcurementItem { id?: string; product_id: string; quantity: number; product?: { name: string }; }
export interface SupplierQuoteItem { id?: string; product_id: string; quantity: number; unit_cost: number; subtotal?: number; }
export interface SupplierQuote { id: string; request_id: string; supplier_id: string; status: string; reference_number?: string; total_amount: number; items: SupplierQuoteItem[]; supplier?: { name: string }; }
export interface PurchaseRequest { id: string; branch_id: string; requested_by_id: string; purchase_order_id?: string; status: string; priority: string; notes?: string; created_at: string; items: ProcurementItem[]; quotes: SupplierQuote[]; }

@Injectable({ providedIn: 'root' })
export class ProcurementService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${environment.apiUrl}/procurement`;

  listRequests(): Observable<PurchaseRequest[]> { return this.http.get<PurchaseRequest[]>(`${this.apiUrl}/requests`); }
  createRequest(payload: { branch_id: string; priority: string; notes?: string; items: Array<{ product_id: string; quantity: number }> }): Observable<PurchaseRequest> { return this.http.post<PurchaseRequest>(`${this.apiUrl}/requests`, payload); }
  updateRequestStatus(id: string, status: string): Observable<PurchaseRequest> { return this.http.put<PurchaseRequest>(`${this.apiUrl}/requests/${id}/status`, { status }); }
  createQuote(requestId: string, payload: { supplier_id: string; reference_number?: string; items: Array<{ product_id: string; quantity: number; unit_cost: number }> }): Observable<SupplierQuote> { return this.http.post<SupplierQuote>(`${this.apiUrl}/requests/${requestId}/quotes`, payload); }
  acceptQuote(quoteId: string): Observable<{ purchase_id: string }> { return this.http.post<{ purchase_id: string }>(`${this.apiUrl}/quotes/${quoteId}/accept`, {}); }
}
