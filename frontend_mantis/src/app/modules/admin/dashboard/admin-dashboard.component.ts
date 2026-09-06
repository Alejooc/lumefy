import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';

import { AdminService, AdminStats } from '../admin.service';
import { SharedModule } from '../../../theme/shared/shared.module';
import { CardComponent } from '../../../theme/shared/components/card/card.component';
import { IconDirective, IconService } from '@ant-design/icons-angular';
import { ApartmentOutline, DollarOutline, TeamOutline, TrophyOutline } from '@ant-design/icons-angular/icons';

interface SummaryCard {
  title: string;
  value: string;
  detail: string;
  icon: string;
  tone: string;
}

interface SubscriptionEntry {
  code: string;
  count: number;
}

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [SharedModule, CardComponent, IconDirective],
  templateUrl: './admin-dashboard.component.html',
  styleUrls: ['./admin-dashboard.component.scss']
})
export class AdminDashboardComponent implements OnInit {
  stats: AdminStats | null = null;
  loading = true;
  loadFailed = false;
  summaryCards: SummaryCard[] = [];
  subscriptionEntries: SubscriptionEntry[] = [];

  private adminService = inject(AdminService);
  private iconService = inject(IconService);
  private cdr = inject(ChangeDetectorRef);

  constructor() {
    this.iconService.addIcon(...[ApartmentOutline, DollarOutline, TeamOutline, TrophyOutline]);
  }

  ngOnInit() {
    this.loadStats();
  }

  loadStats() {
    this.loading = true;
    this.loadFailed = false;
    this.adminService.getStats().subscribe({
      next: (stats) => {
        this.stats = stats;
        this.subscriptionEntries = Object.entries(stats.active_subscriptions)
          .map(([code, count]) => ({ code, count }))
          .sort((a, b) => a.code.localeCompare(b.code));
        const mrrValue = stats.mrr_currency
          ? `${stats.mrr_currency} ${stats.mrr.toLocaleString('es-CO', { minimumFractionDigits: 2 })}`
          : 'Multi-moneda';
        this.summaryCards = [
          {
            title: 'MRR estimado',
            value: mrrValue,
            detail: `${stats.paid_subscription_count} suscripciones de pago · cálculo estimado`,
            icon: 'dollar',
            tone: 'text-primary bg-light-primary'
          },
          {
            title: 'Empresas activas',
            value: stats.active_companies.toString(),
            detail: `${stats.total_companies} empresas registradas`,
            icon: 'apartment',
            tone: 'text-success bg-light-success'
          },
          {
            title: 'Usuarios totales',
            value: stats.total_users.toString(),
            detail: 'Usuarios de todos los tenants',
            icon: 'team',
            tone: 'text-warning bg-light-warning'
          },
          {
            title: 'Planes de pago',
            value: stats.paid_subscription_count.toString(),
            detail: `${stats.active_subscription_count} suscripciones vigentes`,
            icon: 'trophy',
            tone: 'text-danger bg-light-danger'
          }
        ];
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.loadFailed = true;
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }
}
