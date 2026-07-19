import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export type InvoiceType = 'SALE' | 'PURCHASE';
export type InvoiceStatus = 'DRAFT' | 'POSTED' | 'PARTIALLY_PAID' | 'PAID' | 'CANCELLED';

export interface InvoiceItem {
  id: string;
  product_id?: string;
  description: string;
  quantity: number;
  unit_price: number;
  tax_rate: number;
  subtotal: number;
}

export interface InvoicePayment {
  id: string;
  invoice_id: string;
  amount: number;
  method: string;
  reference?: string;
  notes?: string;
  paid_at: string;
}

export interface Invoice {
  id: string;
  number: string;
  type: InvoiceType;
  status: InvoiceStatus;
  client_id?: string;
  supplier_id?: string;
  sale_id?: string;
  purchase_id?: string;
  issue_date: string;
  due_date?: string;
  total: number;
  amount_paid: number;
  notes?: string;
  items: InvoiceItem[];
  payments: InvoicePayment[];
}

@Injectable({ providedIn: 'root' })
export class InvoiceService {
  private http = inject(HttpClient);
  private readonly apiUrl = `${environment.apiUrl}/invoices`;

  list(type?: InvoiceType, status?: InvoiceStatus): Observable<Invoice[]> {
    const params: Record<string, string> = {};
    if (type) params['type'] = type;
    if (status) params['status'] = status;
    return this.http.get<Invoice[]>(this.apiUrl, { params });
  }

  createFromSource(payload: { type: InvoiceType; sale_id?: string; purchase_id?: string; due_date?: string; notes?: string }): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.apiUrl}/from-source`, payload);
  }

  post(invoiceId: string): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.apiUrl}/${invoiceId}/post`, {});
  }

  registerPayment(invoiceId: string, payload: { amount: number; method: string; reference?: string; notes?: string }): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.apiUrl}/${invoiceId}/payments`, payload);
  }

  cancel(invoiceId: string): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.apiUrl}/${invoiceId}/cancel`, {});
  }
}
