// angular import
import { Component, inject, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';

// project import
import { DashboardService, DashboardCard, RecentOrder, TransactionHistory, ChartData } from 'src/app/core/services/dashboard.service';

import { MonthlyBarChartComponent } from 'src/app/theme/shared/apexchart/monthly-bar-chart/monthly-bar-chart.component';
import { IncomeOverviewChartComponent } from 'src/app/theme/shared/apexchart/income-overview-chart/income-overview-chart.component';
import { AnalyticsChartComponent } from 'src/app/theme/shared/apexchart/analytics-chart/analytics-chart.component';
import { SalesReportChartComponent } from 'src/app/theme/shared/apexchart/sales-report-chart/sales-report-chart.component';

// icons
import { IconService, IconDirective } from '@ant-design/icons-angular';
import { FallOutline, GiftOutline, MessageOutline, RiseOutline, SettingOutline } from '@ant-design/icons-angular/icons';
import { CardComponent } from 'src/app/theme/shared/components/card/card.component';

@Component({
  selector: 'app-default',
  imports: [
    CommonModule,
    CardComponent,
    IconDirective,
    MonthlyBarChartComponent,
    IncomeOverviewChartComponent,
    AnalyticsChartComponent,
    SalesReportChartComponent
  ],
  templateUrl: './default.component.html',
  styleUrls: ['./default.component.scss']
})
export class DefaultComponent implements OnInit {
  private iconService = inject(IconService);
  private dashboardService = inject(DashboardService);
  private cdr = inject(ChangeDetectorRef);

  // Data properties
  AnalyticEcommerce: DashboardCard[] = [];
  recentOrder: RecentOrder[] = [];
  transaction: TransactionHistory[] = [];

  // Chart Data
  monthlySalesData: ChartData | null = null;
  incomeOverviewData: ChartData | null = null;
  salesReportData: ChartData | null = null;

  isLoading = true;
  errorMessage = '';

  // constructor
  constructor() {
    this.iconService.addIcon(...[RiseOutline, FallOutline, SettingOutline, GiftOutline, MessageOutline]);
  }

  ngOnInit() {
    this.isLoading = true;
    this.dashboardService.getStats().subscribe({
      next: (stats) => {
        this.AnalyticEcommerce = stats.cards;
        this.recentOrder = stats.recent_orders;
        this.transaction = stats.transactions;

        this.monthlySalesData = stats.monthly_sales;
        this.incomeOverviewData = stats.income_overview;
        this.salesReportData = stats.sales_report;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error fetching dashboard stats', error);
        this.errorMessage = 'Error cargando datos. Verifique que el servidor backend esté funcionando.';
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }
}
