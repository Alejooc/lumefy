import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService } from 'src/app/core/services/api.service';
import { Branch } from 'src/app/core/services/branch.service';
import {
  ChartData,
  DashboardCard,
  DashboardService,
  RecentOrder,
  TransactionHistory
} from 'src/app/core/services/dashboard.service';
import { MonthlyBarChartComponent } from 'src/app/theme/shared/apexchart/monthly-bar-chart/monthly-bar-chart.component';
import { IncomeOverviewChartComponent } from 'src/app/theme/shared/apexchart/income-overview-chart/income-overview-chart.component';
import { CardComponent } from 'src/app/theme/shared/components/card/card.component';
import { IconDirective, IconService } from '@ant-design/icons-angular';
import { FallOutline, GiftOutline, MessageOutline, RiseOutline, SettingOutline } from '@ant-design/icons-angular/icons';

type DashboardFilters = { date_from?: string; date_to?: string; branch_id?: string };

@Component({
  selector: 'app-default',
  imports: [
    CommonModule,
    RouterModule,
    CardComponent,
    IconDirective,
    MonthlyBarChartComponent,
    IncomeOverviewChartComponent,
    FormsModule
  ],
  templateUrl: './default.component.html',
  styleUrls: ['./default.component.scss']
})
export class DefaultComponent implements OnInit {
  private iconService = inject(IconService);
  private dashboardService = inject(DashboardService);
  private apiService = inject(ApiService);
  private cdr = inject(ChangeDetectorRef);

  AnalyticEcommerce: DashboardCard[] = [];
  recentOrder: RecentOrder[] = [];
  transaction: TransactionHistory[] = [];
  monthlySalesData: ChartData | null = null;
  incomeOverviewData: ChartData | null = null;
  isLoading = true;
  errorMessage = '';
  dateFrom = '';
  dateTo = '';
  selectedBranchId = '';
  branches: Branch[] = [];

  constructor() {
    this.iconService.addIcon(...[RiseOutline, FallOutline, SettingOutline, GiftOutline, MessageOutline]);
  }

  ngOnInit(): void {
    this.loadBranches();
    this.loadDashboard();
  }

  loadBranches(): void {
    this.apiService.get<Branch[]>('/branches').subscribe({
      next: (data) => {
        this.branches = data;
        this.cdr.detectChanges();
      },
      error: () => undefined
    });
  }

  loadDashboard(): void {
    this.isLoading = true;
    this.errorMessage = '';
    const filters: DashboardFilters = {};
    if (this.dateFrom) filters.date_from = this.dateFrom;
    if (this.dateTo) filters.date_to = this.dateTo;
    if (this.selectedBranchId) filters.branch_id = this.selectedBranchId;

    this.dashboardService.getStats(filters).subscribe({
      next: (stats) => {
        this.AnalyticEcommerce = stats.cards;
        this.recentOrder = stats.recent_orders;
        this.transaction = stats.transactions;
        this.monthlySalesData = stats.monthly_sales;
        this.incomeOverviewData = stats.income_overview;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error fetching dashboard stats', error);
        this.errorMessage = 'No fue posible cargar los datos del dashboard.';
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  applyFilters(): void {
    this.loadDashboard();
  }

  clearFilters(): void {
    this.dateFrom = '';
    this.dateTo = '';
    this.selectedBranchId = '';
    this.loadDashboard();
  }
}
