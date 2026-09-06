import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { AdminService, SaaSBillingPortfolioItem, SaaSBillingRecord, SaaSBillingRecordPayload } from '../admin.service';
import { Plan, PlanService } from '../plan.service';
import { SharedModule } from '../../../theme/shared/shared.module';

interface BillingForm extends SaaSBillingRecordPayload {
  company_id: string;
}

@Component({
  selector: 'app-admin-billing',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SharedModule],
  templateUrl: './admin-billing.component.html',
  styleUrls: ['./admin-billing.component.scss']
})
export class AdminBillingComponent implements OnInit {
  private adminService = inject(AdminService);
  private planService = inject(PlanService);

  portfolio: SaaSBillingPortfolioItem[] = [];
  plans: Plan[] = [];
  loading = false;
  saving = false;
  errorMessage = '';
  form: BillingForm = this.emptyForm();

  ngOnInit(): void {
    this.planService.getAllPlans().subscribe({
      next: (plans) => {
        this.plans = plans.filter((plan) => plan.is_active);
        this.loadPortfolio();
      },
      error: (err) => this.showError(err)
    });
  }

  loadPortfolio(): void {
    this.loading = true;
    this.adminService.getBillingPortfolio().subscribe({
      next: (portfolio) => {
        this.portfolio = portfolio;
        this.loading = false;
        this.errorMessage = '';
      },
      error: (err) => this.showError(err)
    });
  }

  selectCompany(company: SaaSBillingPortfolioItem): void {
    const plan = this.plans.find((item) => item.code === company.plan) || this.plans[0];
    this.form.company_id = company.company_id;
    this.form.plan_code = plan?.code || company.plan || '';
    this.form.currency = plan?.currency || 'USD';
    this.form.amount = plan?.price || 0;
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    const end = new Date(start);
    end.setDate(end.getDate() + (plan?.duration_days || 30));
    this.form.period_start = this.toDateTimeInput(start);
    this.form.period_end = this.toDateTimeInput(end);
  }

  onPlanChange(): void {
    const plan = this.plans.find((item) => item.code === this.form.plan_code);
    if (!plan) {
      return;
    }
    this.form.currency = plan.currency || 'USD';
    this.form.amount = plan.price || 0;
    const start = this.form.period_start ? new Date(this.form.period_start) : new Date();
    const end = new Date(start);
    end.setDate(end.getDate() + (plan.duration_days || 30));
    this.form.period_end = this.toDateTimeInput(end);
  }

  saveRecord(): void {
    if (!this.form.company_id || !this.form.plan_code || !this.form.period_start || !this.form.period_end || this.form.amount <= 0) {
      this.errorMessage = 'Completa empresa, plan, periodo e importe.';
      return;
    }
    const start = new Date(this.form.period_start);
    const end = new Date(this.form.period_end);
    if (end <= start) {
      this.errorMessage = 'El fin del periodo debe ser posterior al inicio.';
      return;
    }
    this.saving = true;
    this.errorMessage = '';
    const payload: SaaSBillingRecordPayload = {
      plan_code: this.form.plan_code,
      period_start: start.toISOString(),
      period_end: end.toISOString(),
      amount: Number(this.form.amount),
      currency: this.form.currency?.trim().toUpperCase(),
      payment_method: this.form.payment_method?.trim() || 'MANUAL_TRANSFER',
      reference: this.form.reference?.trim() || null,
      proof_url: this.form.proof_url?.trim() || null,
      notes: this.form.notes?.trim() || null
    };
    this.adminService.createBillingRecord(this.form.company_id, payload).subscribe({
      next: () => {
        this.saving = false;
        this.form = this.emptyForm();
        this.loadPortfolio();
        Swal.fire('Registrado', 'El cobro quedó pendiente de verificación.', 'success');
      },
      error: (err) => {
        this.saving = false;
        this.showError(err);
      }
    });
  }

  approve(record: SaaSBillingRecord): void {
    Swal.fire({
      title: '¿Aprobar cobro?',
      text: 'La aprobación renovará la suscripción de la empresa con este periodo.',
      input: 'text',
      inputLabel: 'Referencia del pago',
      inputValue: record.reference || '',
      inputPlaceholder: 'TRX-12345 o comprobante',
      inputValidator: (value) => (record.proof_url || value?.trim().length >= 3)
        ? undefined
        : 'Indica una referencia de al menos 3 caracteres o conserva un comprobante.',
      showCancelButton: true,
      confirmButtonText: 'Aprobar y renovar'
    }).then((result) => {
      if (!result.isConfirmed) {
        return;
      }
      this.saving = true;
      this.adminService.verifyBillingRecord(record.id, {
        status: 'PAID',
        reference: result.value?.trim() || record.reference || null
      }).subscribe({
        next: () => {
          this.saving = false;
          this.loadPortfolio();
        },
        error: (err) => {
          this.saving = false;
          this.showError(err);
        }
      });
    });
  }

  reject(record: SaaSBillingRecord): void {
    Swal.fire({
      title: 'Rechazar comprobante',
      input: 'textarea',
      inputLabel: 'Motivo',
      inputPlaceholder: 'Explica qué debe corregirse',
      inputValidator: (value) => value?.trim().length >= 3 ? undefined : 'Indica un motivo.',
      showCancelButton: true,
      confirmButtonText: 'Rechazar',
      confirmButtonColor: '#dc3545'
    }).then((result) => {
      if (!result.isConfirmed) {
        return;
      }
      this.saving = true;
      this.adminService.verifyBillingRecord(record.id, {
        status: 'REJECTED',
        rejection_reason: result.value.trim()
      }).subscribe({
        next: () => {
          this.saving = false;
          this.loadPortfolio();
        },
        error: (err) => {
          this.saving = false;
          this.showError(err);
        }
      });
    });
  }

  stateLabel(state: SaaSBillingPortfolioItem['billing_state']): string {
    return {
      PAID: 'Pagado',
      PENDING: 'Pendiente',
      OVERDUE: 'Vencido',
      DUE_SOON: 'Por vencer',
      NO_RECORD: 'Sin registro'
    }[state];
  }

  stateClass(state: SaaSBillingPortfolioItem['billing_state']): string {
    return {
      PAID: 'text-bg-success',
      PENDING: 'text-bg-warning',
      OVERDUE: 'text-bg-danger',
      DUE_SOON: 'text-bg-info',
      NO_RECORD: 'text-bg-secondary'
    }[state];
  }

  private emptyForm(): BillingForm {
    return {
      company_id: '',
      plan_code: this.plans[0]?.code || '',
      period_start: this.toDateTimeInput(new Date()),
      period_end: this.toDateTimeInput(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)),
      amount: this.plans[0]?.price || 0,
      currency: this.plans[0]?.currency || 'USD',
      payment_method: 'MANUAL_TRANSFER',
      reference: '',
      proof_url: '',
      notes: ''
    };
  }

  private toDateTimeInput(date: Date): string {
    const pad = (value: number) => value.toString().padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }

  private showError(err: { error?: { detail?: string } }): void {
    this.loading = false;
    this.saving = false;
    this.errorMessage = err?.error?.detail || 'No se pudo completar la operación de cobro.';
  }
}
