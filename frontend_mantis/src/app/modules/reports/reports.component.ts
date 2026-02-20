import { Component, Inject, OnInit, ChangeDetectorRef } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';

import {
    ApexNonAxisChartSeries,
    ApexResponsive,
    ApexChart,
    ApexPlotOptions,
    ApexAxisChartSeries,
    ApexXAxis,
    ApexYAxis,
    ApexTooltip,
    ApexFill,
    ApexLegend,
    ApexStroke,
    ApexDataLabels
} from 'ng-apexcharts';

export type ChartOptions = {
    series: ApexNonAxisChartSeries | ApexAxisChartSeries | any;
    chart: ApexChart;
    responsive?: ApexResponsive[];
    labels?: any;
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

@Component({
    selector: 'app-reports',
    templateUrl: './reports.component.html',
    styleUrls: ['./reports.component.scss'],
    standalone: false
})
export class ReportsComponent implements OnInit {

    // Filters
    filterDays: string = "30";
    filterStartDate: string = "";
    filterEndDate: string = "";
    filterBranchId: string = "";

    branches: any[] = [];
    activeTab: string = "general"; // general, finanzas, inventario

    // Charts
    salesChartOptions: Partial<ChartOptions>;
    topProductsChartOptions: Partial<ChartOptions>;
    categoryChartOptions: Partial<ChartOptions>;

    // Data
    salesSummary: any[] = [];
    topProducts: any[] = [];
    inventoryValue: any = { total_items: 0, total_value: 0, low_stock_items: 0 };
    financialSummary: any = { revenue: 0, cost: 0, profit: 0, margin: 0 };
    inventoryTurnover: any[] = [];
    salesByCategory: any[] = [];

    isLoading = false;
    currencySymbol = '$';

    constructor(
        @Inject(ApiService) private api: ApiService,
        @Inject(AuthService) private auth: AuthService,
        private cdr: ChangeDetectorRef
    ) {
        this.initCharts();
    }

    ngOnInit(): void {
        this.auth.currentCompany.subscribe(company => {
            if (company && company.currency_symbol) {
                this.currencySymbol = company.currency_symbol;
            }
            this.cdr.detectChanges();
        });

        this.loadBranches();
        this.loadData();
    }

    initCharts() {
        this.salesChartOptions = {
            series: [{ name: "Ingresos", data: [] }],
            chart: { type: "area", height: 350 },
            dataLabels: { enabled: false },
            stroke: { curve: "smooth", width: 2 },
            xaxis: { categories: [] },
            yaxis: { title: { text: "Ingresos" } },
            fill: { type: "gradient", gradient: { shadeIntensity: 1, opacityFrom: 0.7, opacityTo: 0.9, stops: [0, 90, 100] } },
            tooltip: { y: { formatter: (val) => this.currencySymbol + " " + parseFloat(val as unknown as string).toFixed(2) } },
            colors: ['#0d6efd']
        };

        this.topProductsChartOptions = {
            series: [],
            chart: { type: "donut", height: 350 },
            labels: [],
            responsive: [{ breakpoint: 480, options: { chart: { width: 200 }, legend: { position: "bottom" } } }]
        };

        this.categoryChartOptions = {
            series: [],
            chart: { type: "pie", height: 350 },
            labels: [],
            responsive: [{ breakpoint: 480, options: { chart: { width: 200 }, legend: { position: "bottom" } } }]
        };
    }

    loadBranches() {
        this.api.get<any>('/branches?limit=100').subscribe({
            next: (data) => {
                this.branches = data.items || [];
            },
            error: () => { }
        });
    }

    applyFilters() {
        this.loadData();
    }

    clearDateFilters() {
        this.filterStartDate = "";
        this.filterEndDate = "";
        if (this.filterDays === "custom") {
            this.filterDays = "30";
        }
        this.loadData();
    }

    getQueryParams() {
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
            requestsCompleted++;
            if (requestsCompleted >= totalRequests) {
                this.isLoading = false;
                this.cdr.detectChanges();
            }
        };

        // 1. Sales Summary
        this.api.get<any[]>(`/reports/sales-summary${params}`).subscribe(data => {
            this.salesSummary = data;
            this.salesChartOptions = {
                ...this.salesChartOptions,
                series: [{ name: "Ingresos", data: data.map(x => x.total.toFixed(2)) }],
                xaxis: { categories: data.map(x => x.date) }
            };
            checkCompleted();
        });

        // 2. Top Products
        this.api.get<any[]>(`/reports/top-products${params}&limit=5`).subscribe(data => {
            this.topProducts = data;
            this.topProductsChartOptions = {
                ...this.topProductsChartOptions,
                series: data.map(x => x.quantity),
                labels: data.map(x => x.name)
            };
            checkCompleted();
        });

        // 3. Inventory Value (Only uses branch filter, not dates usually, but we pass params)
        this.api.get<any>(`/reports/inventory-value${this.filterBranchId ? '?branch_id=' + this.filterBranchId : ''}`).subscribe(data => {
            this.inventoryValue = data;
            checkCompleted();
        });

        // 4. Financial Summary
        this.api.get<any>(`/reports/financial-summary${params}`).subscribe(data => {
            this.financialSummary = data;
            checkCompleted();
        });

        // 5. Inventory Turnover
        this.api.get<any[]>(`/reports/inventory-turnover${params}&limit=10&sort_by=highest`).subscribe(data => {
            this.inventoryTurnover = data;
            checkCompleted();
        });

        // 6. Sales By Category
        this.api.get<any[]>(`/reports/sales-by-category${params}`).subscribe(data => {
            this.salesByCategory = data;
            this.categoryChartOptions = {
                ...this.categoryChartOptions,
                series: data.map(x => x.revenue),
                labels: data.map(x => x.category_name)
            };
            checkCompleted();
        });
    }

    setTab(tab: string) {
        this.activeTab = tab;
    }

    exportToCSV(type: string) {
        let columns: string[] = [];
        let rows: any[] = [];
        let filename = '';

        if (type === 'top-products') {
            columns = ['Producto', 'Cantidad Vendida', 'Ingresos'];
            rows = this.topProducts.map(p => [p.name, p.quantity, p.revenue]);
            filename = 'top_productos';
        } else if (type === 'inventory-turnover') {
            columns = ['Producto', 'Stock Actual', 'Cantidad Vendida', 'Tasa de Rotación'];
            rows = this.inventoryTurnover.map(p => [p.product_name, p.stock, p.sold_quantity, p.turnover_rate.toFixed(2)]);
            filename = 'rotacion_inventario';
        } else if (type === 'sales-by-category') {
            columns = ['Categoría', 'Ingresos'];
            rows = this.salesByCategory.map(c => [c.category_name, c.revenue]);
            filename = 'ventas_categorias';
        }

        if (columns.length === 0) return;

        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += columns.join(",") + "\n";

        rows.forEach(row => {
            csvContent += row.join(",") + "\n";
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `${filename}_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link); // Required for FF
        link.click();
        document.body.removeChild(link);
    }
}
