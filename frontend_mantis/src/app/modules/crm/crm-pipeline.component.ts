import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { Opportunity, OpportunityService, OpportunityStage } from '../../core/services/opportunity.service';
import { SweetAlertService } from '../../theme/shared/services/sweet-alert.service';
import { CardComponent } from '../../theme/shared/components/card/card.component';

@Component({
  selector: 'app-crm-pipeline',
  standalone: true,
  imports: [CommonModule, FormsModule, CardComponent],
  templateUrl: './crm-pipeline.component.html'
})
export class CrmPipelineComponent implements OnInit {
  private opportunitiesService = inject(OpportunityService);
  private swal = inject(SweetAlertService);

  loading = false;
  creating = false;
  opportunities: Opportunity[] = [];
  lead = this.emptyLead();
  readonly stages: Array<{ key: OpportunityStage; label: string }> = [
    { key: 'NEW', label: 'Nuevo' },
    { key: 'QUALIFIED', label: 'Calificado' },
    { key: 'PROPOSAL', label: 'Propuesta' },
    { key: 'WON', label: 'Ganado' },
    { key: 'LOST', label: 'Perdido' }
  ];

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading = true;
    this.opportunitiesService.list().subscribe({
      next: (items) => { this.opportunities = items; this.loading = false; },
      error: (error) => { this.loading = false; this.swal.error('Error', error?.error?.detail || 'No se pudo cargar el pipeline.'); }
    });
  }

  create(): void {
    if (!this.lead.name.trim()) return;
    this.creating = true;
    this.opportunitiesService.create({ ...this.lead, name: this.lead.name.trim() }).subscribe({
      next: (item) => {
        this.opportunities.unshift(item);
        this.lead = this.emptyLead();
        this.creating = false;
      },
      error: (error) => { this.creating = false; this.swal.error('Error', error?.error?.detail || 'No se pudo crear la oportunidad.'); }
    });
  }

  move(opportunity: Opportunity, stage: OpportunityStage): void {
    if (opportunity.stage === stage) return;
    const payload: Partial<Opportunity> = { stage };
    if (stage === 'LOST') {
      const reason = window.prompt('Motivo de pérdida');
      if (!reason?.trim()) return;
      payload.lost_reason = reason.trim();
    }
    this.opportunitiesService.update(opportunity.id, payload).subscribe({
      next: (updated) => Object.assign(opportunity, updated),
      error: (error) => this.swal.error('Error', error?.error?.detail || 'No se pudo actualizar la oportunidad.')
    });
  }

  items(stage: OpportunityStage): Opportunity[] { return this.opportunities.filter((item) => item.stage === stage); }
  weightedTotal(stage: OpportunityStage): number { return this.items(stage).reduce((total, item) => total + item.expected_revenue * item.probability / 100, 0); }

  private emptyLead(): Partial<Opportunity> {
    return { name: '', stage: 'NEW', expected_revenue: 0, probability: 10, contact_name: '', contact_email: '', contact_phone: '', notes: '' };
  }
}
