import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';

import { AdminService, AdminStats } from '../admin.service';
import { SharedModule } from '../../../theme/shared/shared.module';
import { CardComponent } from '../../../theme/shared/components/card/card.component';
import { MonthlyBarChartComponent } from '../../../theme/shared/apexchart/monthly-bar-chart/monthly-bar-chart.component';
import { IncomeOverviewChartComponent } from '../../../theme/shared/apexchart/income-overview-chart/income-overview-chart.component';
import { SalesReportChartComponent } from '../../../theme/shared/apexchart/sales-report-chart/sales-report-chart.component';
import { IconService, IconDirective } from '@ant-design/icons-angular';
import { FallOutline, GiftOutline, MessageOutline, RiseOutline, SettingOutline, DeploymentUnitOutline, UserOutline, DollarOutline, CrownOutline } from '@ant-design/icons-angular/icons';

interface AdminDashboardCard {
    title: string;
    amount: string;
    background: string;
    border: string;
    icon: string;
    percentage: string;
    color: string;
    number: string;
}

@Component({
    selector: 'app-admin-dashboard',
    standalone: true,
    imports: [
    SharedModule,
    CardComponent,
    MonthlyBarChartComponent,
    IncomeOverviewChartComponent,
    SalesReportChartComponent,
    IconDirective
],
    templateUrl: './admin-dashboard.component.html',
    styleUrls: ['./admin-dashboard.component.scss']
})
export class AdminDashboardComponent implements OnInit {
    stats: AdminStats | null = null;
    loading = true;

    // UI Data for Cards
    AnalyticEcommerce: AdminDashboardCard[] = [];

    // Mock Transaction Data (Placeholder until we have Audit Log details here)
    transaction = [
        {
            background: 'text-success bg-light-success',
            icon: 'gift',
            title: 'Nuevo Plan Enterprise',
            time: 'Hoy, 2:00 AM',
            amount: '+ $199',
            percentage: 'N/A'
        },
        {
            background: 'text-primary bg-light-primary',
            icon: 'message',
            title: 'Soporte: Ticket #984',
            time: '5 Agosto, 1:45 PM',
            amount: '',
            percentage: ''
        }
    ];

    private adminService = inject(AdminService);
    private cdr = inject(ChangeDetectorRef);
    private iconService = inject(IconService);

    constructor() {
        this.iconService.addIcon(
            ...[RiseOutline, FallOutline, SettingOutline, GiftOutline, MessageOutline, DeploymentUnitOutline, UserOutline, DollarOutline, CrownOutline]
        );
    }

    ngOnInit() {
        this.loadStats();
    }

    loadStats() {
        this.loading = true;
        this.adminService.getStats().subscribe({
            next: (data) => {
                this.stats = data;
                this.mapStatsToCards(data);
                this.updatePlanChart();
                this.cdr.detectChanges();
            },
            error: (err) => {
                console.error(err);
                this.loading = false;
                this.cdr.detectChanges();
            }
        });
    }

    planChartOptions: Record<string, unknown>;

    updatePlanChart() {
        if (!this.stats) return;

        this.planChartOptions = {
            chart: {
                type: 'donut',
                height: 300
            },
            series: [
                this.stats.active_subscriptions.FREE,
                this.stats.active_subscriptions.PRO,
                this.stats.active_subscriptions.ENTERPRISE
            ],
            labels: ['Free', 'Pro', 'Enterprise'],
            colors: ['#4680ff', '#0e9e4a', '#ff5252'],
            legend: {
                show: true,
                position: 'bottom',
            },
            plotOptions: {
                pie: {
                    donut: {
                        labels: {
                            show: true,
                            name: {
                                show: true
                            },
                            value: {
                                show: true
                            }
                        }
                    }
                }
            },
            dataLabels: {
                enabled: true,
                dropShadow: {
                    enabled: false,
                }
            },
            responsive: [{
                breakpoint: 480,
                options: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }]
        };
    }

    mapStatsToCards(stats: AdminStats) {
        this.AnalyticEcommerce = [
            {
                title: 'Total Ingresos (MRR Est.)',
                amount: `$${stats.mrr}`,
                background: 'bg-light-primary ',
                border: 'border-primary',
                icon: 'dollar',
                percentage: '+5.5%',
                color: 'text-primary',
                number: '$1,200'
            },
            {
                title: 'Empresas Activas',
                amount: stats.active_companies.toString(),
                background: 'bg-light-success ',
                border: 'border-success',
                icon: 'deployment-unit',
                percentage: '98%',
                color: 'text-success',
                number: stats.total_companies.toString() + ' Total'
            },
            {
                title: 'Usuarios Totales',
                amount: stats.total_users.toString(),
                background: 'bg-light-warning ',
                border: 'border-warning',
                icon: 'user',
                percentage: 'Growth',
                color: 'text-warning',
                number: '+12'
            },
            {
                title: 'Suscripciones Pro/Ent',
                amount: (stats.active_subscriptions.PRO + stats.active_subscriptions.ENTERPRISE).toString(),
                background: 'bg-light-danger ',
                border: 'border-danger',
                icon: 'crown',
                percentage: 'Premium',
                color: 'text-danger',
                number: 'KPI'
            }
        ];
    }
}
