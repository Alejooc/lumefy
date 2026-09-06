import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { AuthService } from 'src/app/core/services/auth.service';
import { SharedModule } from 'src/app/theme/shared/shared.module';
import { ApiService } from 'src/app/core/services/api.service';

type SubscriptionSummary = {
  plan?: string;
  valid_until?: string | null;
  subscription_status?: string;
};

type BillingRecord = {
  id: string;
  plan_code: string;
  period_start: string;
  period_end: string;
  amount: number;
  currency: string;
  status: 'PENDING' | 'PAID' | 'REJECTED' | 'CANCELLED';
  payment_method?: string | null;
  reference?: string | null;
  proof_url?: string | null;
  rejection_reason?: string | null;
};

@Component({
    selector: 'app-billing-list',
    standalone: true,
    imports: [CommonModule, SharedModule, RouterModule],
    templateUrl: './billing-list.component.html',
    styleUrls: ['./billing-list.component.scss']
})
export class BillingListComponent implements OnInit {
    private api = inject(ApiService);
    readonly authService = inject(AuthService);
    subscription: SubscriptionSummary | null = null;
    records: BillingRecord[] = [];
    loading = true;
    billingLoading = true;

    ngOnInit(): void {
      this.api.get<SubscriptionSummary>('/companies/me').subscribe({
        next: (company) => {
          this.subscription = company;
          this.loading = false;
          this.loadBillingHistory();
        },
        error: () => {
          this.loading = false;
          this.billingLoading = false;
        }
      });
    }

    loadBillingHistory(): void {
      this.api.get<BillingRecord[]>('/companies/me/billing').subscribe({
        next: (records) => {
          this.records = records;
          this.billingLoading = false;
        },
        error: () => {
          this.records = [];
          this.billingLoading = false;
        }
      });
    }

    get subscriptionStatusLabel(): string {
      const status = this.subscription?.subscription_status || 'ACTIVE';
      return { ACTIVE: 'Activa', PAST_DUE: 'Pendiente de pago', SUSPENDED: 'Suspendida', CANCELED: 'Cancelada' }[status] || status;
    }

    get subscriptionStatusClass(): string {
      const status = this.subscription?.subscription_status || 'ACTIVE';
      return { ACTIVE: 'bg-success', PAST_DUE: 'bg-warning text-dark', SUSPENDED: 'bg-danger', CANCELED: 'bg-secondary' }[status] || 'bg-secondary';
    }

    billingStatusLabel(status: BillingRecord['status']): string {
      return { PENDING: 'Pendiente de validar', PAID: 'Pagado', REJECTED: 'Rechazado', CANCELLED: 'Cancelado' }[status] || status;
    }

    billingStatusClass(status: BillingRecord['status']): string {
      return { PENDING: 'bg-warning text-dark', PAID: 'bg-success', REJECTED: 'bg-danger', CANCELLED: 'bg-secondary' }[status] || 'bg-secondary';
    }
}
