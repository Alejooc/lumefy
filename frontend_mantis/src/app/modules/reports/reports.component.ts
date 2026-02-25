import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import {
    ApexAxisChartSeries,
    ApexChart,
    ApexDataLabels,
    ApexFill,
    ApexLegend,
    ApexNonAxisChartSeries,
    ApexPlotOptions,
    ApexResponsive,
    ApexStroke,
    ApexTooltip,
    ApexXAxis,
    ApexYAxis
} from 'ng-apexcharts';
import { Branch } from '../../core/services/branch.service';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';

type ReportChartOptions = {
    series: ApexNonAxisChartSeries | ApexAxisChartSeries;
    chart: ApexChart;
    responsive?: ApexResponsive[];
    labels?: string[];
    plotOptions?: ApexPlotOptions;
    xaxis?: ApexXAxis;
    yaxis?: ApexYAxis;
    tooltip?: ApexTooltip;
    fill?: ApexFill;
    stroke?: ApexStroke;
    colors?: string[];
    dataLabels?: ApexDataLabels;
    legend?: ApexLegend;
};

interface SalesSummaryRow {
    date: string;
    total: number;
}

interface TopProductRow {
    name: string;
    quantity: number;
    revenue: number;
}

interface InventoryValueSummary {
    total_items: number;
    total_value: number;
    low_stock_items: number;
}

interface FinancialSummary {
    revenue: number;
    cost: number;
    profit: number;
    margin: number;
}

interface InventoryTurnoverRow {
    product_name: string;
    stock: number;
    sold_quantity: number;
    turnover_rate: number;
}

interface SalesByCategoryRow {
    category_name: string;
    revenue: number;
}

interface BranchListResponse {
    items?: Branch[];
}

@Component({
    selector: 'app-reports',
    templateUrl: './reports.component.html',
    styleUrls: ['./reports.component.scss'],
    standalone: false
})
export class ReportsComponent implements OnInit {
    private api = inject(ApiService);
    private auth = inject(AuthService);
    private cdr = inject(ChangeDetectorRef);

    filterDays = '30';
    filterStartDate = '';
    filterEndDate = '';
    filterBranchId = '';

    branches: Branch[] = [];
    activeTab = 'general';

    salesChartOptions: Partial<ReportChartOptions>;
    topProductsChartOptions: Partial<ReportChartOptions>;
    categoryChartOptions: Partial<ReportChartOptions>;

    salesSummary: SalesSummaryRow[] = [];
    topProducts: TopProductRow[] = [];
    inventoryValue: InventoryValueSummary = { total_items: 0, total_value: 0, low_stock_items: 0 };
    financialSummary: FinancialSummary = { revenue: 0, cost: 0, profit: 0, margin: 0 };
    inventoryTurnover: InventoryTurnoverRow[] = [];
    salesByCategory: SalesByCategoryRow[] = [];

    isLoading = false;
    currencySymbol = '$';

    constructor() {
        this.salesChartOptions = {};
        this.topProductsChartOptions = {};
        this.categoryChartOptions = {};
        this.initCharts();
    }

    ngOnInit(): void {
        this.auth.currentCompany.subscribe((company) => {
            if (company?.currency_symbol) {
                this.currencySymbol = company.currency_symbol;
            }
            this.cdr.detectChanges();
        });

        this.loadBranches();
        this.loadData();
    }

    initCharts() {
        this.salesChartOptions = {
            series: [{ name: 'Ingresos', data: [] }],
            chart: { type: 'area', height: 350 },
            dataLabels: { enabled: false },
            stroke: { curve: 'smooth', width: 2 },
            xaxis: { categories: [] },
            yaxis: { title: { text: 'Ingresos' } },
            fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.7, opacityTo: 0.9, stops: [0, 90, 100] } },
            tooltip: { y: { formatter: (value: number) => `${this.currencySymbol} ${Number(value).toFixed(2)}` } },
            colors: ['#0d6efd']
        };

        this.topProductsChartOptions = {
            series: [],
            chart: { type: 'donut', height: 350 },
            labels: [],
            responsive: [{ breakpoint: 480, options: { chart: { width: 200 }, legend: { position: 'bottom' } } }]
        };

        this.categoryChartOptions = {
            series: [],
            chart: { type: 'pie', height: 350 },
            labels: [],
            responsive: [{ breakpoint: 480, options: { chart: { width: 200 }, legend: { position: 'bottom' } } }]
        };
    }

    loadBranches() {
        this.api.get<BranchListResponse>('/branches?limit=100').subscribe({
            next: (data) => {
                this.branches = data.items || [];
            },
            error: () => undefined
        });
    }

    applyFilters() {
        this.loadData();
    }

    clearDateFilters() {
        this.filterStartDate = '';
        this.filterEndDate = '';
        if (this.filterDays === 'custom') {
            this.filterDays = '30';
        }
        this.loadData();
    }

    getQueryParams(): string {
        let params = `?days=${this.filterDays !== 'custom' ? this.filterDays : 30}`;
        if (this.filterDays === 'custom') {
            if (this.filterStartDate) params += `&start_date=${this.filterStartDate}T00:00:00Z`;
            if (this.filterEndDate) params += `&end_date=${this.filterEndDate}T23:59:59Z`;
        }
        if (this.filterBranchId) {
            params += `&branch_id=${this.filterBranchId}`;
        }
        return params;
    }

    loadData() {
        this.isLoading = true;
        this.cdr.detectChanges();

        const params = this.getQueryParams();
        let requestsCompleted = 0;
        const totalRequests = 6;

        const checkCompleted = () => {
            requestsCompleted += 1;
            if (requestsCompleted >= totalRequests) {
                this.isLoading = false;
                this.cdr.detectChanges();
            }
        };

        this.api.get<SalesSummaryRow[]>(`/reports/sales-summary${params}`).subscribe({
            next: (data) => {
                this.salesSummary = data;
                this.salesChartOptions = {
                    ...this.salesChartOptions,
                    series: [{ name: 'Ingresos', data: data.map((row) => row.total) }],
                    xaxis: { categories: data.map((row) => row.date) }
                };
                checkCompleted();
            },
            error: () => checkCompleted()
        });

        this.api.get<TopProductRow[]>(`/reports/top-products${params}&limit=5`).subscribe({
            next: (data) => {
                this.topProducts = data;
                this.topProductsChartOptions = {
                    ...this.topProductsChartOptions,
                    series: data.map((row) => row.quantity),
                    labels: data.map((row) => row.name)
                };
                checkCompleted();
            },
            error: () => checkCompleted()
        });

        this.api
            .get<InventoryValueSummary>(`/reports/inventory-value${this.filterBranchId ? '?branch_id=' + this.filterBranchId : ''}`)
            .subscribe({
                next: (data) => {
                    this.inventoryValue = data;
                    checkCompleted();
                },
                error: () => checkCompleted()
            });

        this.api.get<FinancialSummary>(`/reports/financial-summary${params}`).subscribe({
            next: (data) => {
                this.financialSummary = data;
                checkCompleted();
            },
            error: () => checkCompleted()
        });

        this.api.get<InventoryTurnoverRow[]>(`/reports/inventory-turnover${params}&limit=10&sort_by=highest`).subscribe({
            next: (data) => {
                this.inventoryTurnover = data;
                checkCompleted();
            },
            error: () => checkCompleted()
        });

        this.api.get<SalesByCategoryRow[]>(`/reports/sales-by-category${params}`).subscribe({
            next: (data) => {
                this.salesByCategory = data;
                this.categoryChartOptions = {
                    ...this.categoryChartOptions,
                    series: data.map((row) => row.revenue),
                    labels: data.map((row) => row.category_name)
                };
                checkCompleted();
            },
            error: () => checkCompleted()
        });
    }

    setTab(tab: string) {
        this.activeTab = tab;
    }

    exportToCSV(type: string) {
        let columns: string[] = [];
        let rows: Array<Array<string | number>> = [];
        let filename = '';

        if (type === 'top-products') {
            columns = ['Producto', 'Cantidad Vendida', 'Ingresos'];
            rows = this.topProducts.map((item) => [item.name, item.quantity, item.revenue]);
            filename = 'top_productos';
        } else if (type === 'inventory-turnover') {
            columns = ['Producto', 'Stock Actual', 'Cantidad Vendida', 'Tasa de Rotacion'];
            rows = this.inventoryTurnover.map((item) => [item.product_name, item.stock, item.sold_quantity, item.turnover_rate.toFixed(2)]);
            filename = 'rotacion_inventario';
        } else if (type === 'sales-by-category') {
            columns = ['Categoria', 'Ingresos'];
            rows = this.salesByCategory.map((item) => [item.category_name, item.revenue]);
            filename = 'ventas_categorias';
        }

        if (columns.length === 0) return;

        let csvContent = 'data:text/csv;charset=utf-8,';
        csvContent += columns.join(',') + '\n';
        rows.forEach((row) => {
            csvContent += row.join(',') + '\n';
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement('a');
        link.setAttribute('href', encodedUri);
        link.setAttribute('download', `${filename}_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}
