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
        this.summaryCards = [
          {
            title: 'MRR estimado',
            value: `$${stats.mrr.toLocaleString('es-CO')}`,
            detail: `${stats.active_subscriptions.PRO + stats.active_subscriptions.ENTERPRISE} suscripciones de pago`,
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
            value: (stats.active_subscriptions.PRO + stats.active_subscriptions.ENTERPRISE).toString(),
            detail: `${stats.active_subscriptions.FREE} suscripciones Free`,
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
