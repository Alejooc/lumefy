import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';

export type OpportunityStage = 'NEW' | 'QUALIFIED' | 'PROPOSAL' | 'WON' | 'LOST';

export interface Opportunity {
  id: string;
  name: string;
  stage: OpportunityStage;
  client_id?: string | null;
  client_name?: string | null;
  owner_name?: string | null;
  expected_revenue: number;
  probability: number;
  expected_close_date?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  notes?: string | null;
  lost_reason?: string | null;
}

@Injectable({ providedIn: 'root' })
export class OpportunityService {
  private api = inject(ApiService);

  list(): Observable<Opportunity[]> {
    return this.api.get<Opportunity[]>('/crm/opportunities/');
  }

  create(payload: Partial<Opportunity>): Observable<Opportunity> {
    return this.api.post<Opportunity>('/crm/opportunities/', payload);
  }

  update(id: string, payload: Partial<Opportunity>): Observable<Opportunity> {
    return this.api.put<Opportunity>(`/crm/opportunities/${id}`, payload);
  }
}
