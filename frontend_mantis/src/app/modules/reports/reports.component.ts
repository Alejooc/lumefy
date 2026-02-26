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

interface DailyCloseSummary {
    date: string;
    branch_id?: string | null;
    sales_count: number;
    gross_sales: number;
    payments_cash: number;
    payments_card: number;
    payments_credit: number;
    returns_count: number;
    total_refunds: number;
    net_sales: number;
    sessions_opened_count: number;
    sessions_closed_count: number;
    opening_amount_total: number;
    expected_amount_total: number;
    counted_amount_total: number;
    over_short_total: number;
    open_sessions_now: number;
}

interface PosOpsTopCashier {
    user_id: string;
    user_name: string;
    sessions_closed: number;
    sales_total: number;
    cash_total: number;
    card_total: number;
    credit_total: number;
}

interface PosOperationsSummary {
    date: string;
    branch_id?: string | null;
    sessions_opened: number;
    sessions_closed: number;
    sessions_reopened: number;
    sessions_open_now: number;
    expected_total: number;
    counted_total: number;
    over_short_total: number;
    alert_threshold: number;
    alert_sessions_count: number;
    payments_cash: number;
    payments_card: number;
    payments_credit: number;
    top_cashiers: PosOpsTopCashier[];
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
    dailyClose: DailyCloseSummary = {
        date: '',
        branch_id: null,
        sales_count: 0,
        gross_sales: 0,
        payments_cash: 0,
        payments_card: 0,
        payments_credit: 0,
        returns_count: 0,
        total_refunds: 0,
        net_sales: 0,
        sessions_opened_count: 0,
        sessions_closed_count: 0,
        opening_amount_total: 0,
        expected_amount_total: 0,
        counted_amount_total: 0,
        over_short_total: 0,
        open_sessions_now: 0
    };
    posOperations: PosOperationsSummary = {
        date: '',
        branch_id: null,
        sessions_opened: 0,
        sessions_closed: 0,
        sessions_reopened: 0,
        sessions_open_now: 0,
        expected_total: 0,
        counted_total: 0,
        over_short_total: 0,
        alert_threshold: 20,
        alert_sessions_count: 0,
        payments_cash: 0,
        payments_card: 0,
        payments_credit: 0,
        top_cashiers: []
    };

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
        this.api.get<BranchListResponse | Branch[]>('/branches?limit=100').subscribe({
            next: (data) => {
                if (Array.isArray(data)) {
                    this.branches = data;
                } else {
                    this.branches = data.items || [];
                }
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

    getDailyCloseParams(): string {
        const today = new Date().toISOString().split('T')[0];
        const target = this.filterDays === 'custom' && this.filterEndDate ? this.filterEndDate : today;
        let params = `?target_date=${target}`;
        if (this.filterBranchId) {
            params += `&branch_id=${this.filterBranchId}`;
        }
        return params;
    }

    getPosOperationsParams(): string {
        const today = new Date().toISOString().split('T')[0];
        const target = this.filterDays === 'custom' && this.filterEndDate ? this.filterEndDate : today;
        let params = `?target_date=${target}`;
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
        const totalRequests = 8;

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

        this.api.get<DailyCloseSummary>(`/reports/daily-close${this.getDailyCloseParams()}`).subscribe({
            next: (data) => {
                this.dailyClose = data;
                checkCompleted();
            },
            error: () => checkCompleted()
        });

        this.api.get<PosOperationsSummary>(`/reports/pos-operations${this.getPosOperationsParams()}`).subscribe({
            next: (data) => {
                this.posOperations = data;
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
        } else if (type === 'daily-close') {
            columns = ['Fecha', 'Sucursal', 'Ventas', 'Bruto', 'Efectivo', 'Tarjeta', 'Credito', 'Devoluciones', 'Total Devoluciones', 'Neto', 'Cajas Abiertas', 'Cajas Cerradas', 'Apertura Caja', 'Esperado', 'Contado', 'Diferencia', 'Cajas Abiertas Ahora'];
            rows = [[
                this.dailyClose.date,
                this.dailyClose.branch_id || 'todas',
                this.dailyClose.sales_count,
                this.dailyClose.gross_sales,
                this.dailyClose.payments_cash,
                this.dailyClose.payments_card,
                this.dailyClose.payments_credit,
                this.dailyClose.returns_count,
                this.dailyClose.total_refunds,
                this.dailyClose.net_sales,
                this.dailyClose.sessions_opened_count,
                this.dailyClose.sessions_closed_count,
                this.dailyClose.opening_amount_total,
                this.dailyClose.expected_amount_total,
                this.dailyClose.counted_amount_total,
                this.dailyClose.over_short_total,
                this.dailyClose.open_sessions_now
            ]];
            filename = 'cierre_diario';
        } else if (type === 'pos-operations') {
            columns = ['Fecha', 'Sucursal', 'Cajas Abiertas', 'Cajas Cerradas', 'Cajas Reabiertas', 'Abiertas Ahora', 'Esperado', 'Contado', 'Diferencia', 'Umbral Alerta', 'Cajas en Alerta', 'Cobro Efectivo', 'Cobro Tarjeta', 'Cobro Credito'];
            rows = [[
                this.posOperations.date,
                this.posOperations.branch_id || 'todas',
                this.posOperations.sessions_opened,
                this.posOperations.sessions_closed,
                this.posOperations.sessions_reopened,
                this.posOperations.sessions_open_now,
                this.posOperations.expected_total,
                this.posOperations.counted_total,
                this.posOperations.over_short_total,
                this.posOperations.alert_threshold,
                this.posOperations.alert_sessions_count,
                this.posOperations.payments_cash,
                this.posOperations.payments_card,
                this.posOperations.payments_credit
            ]];
            filename = 'operacion_pos';
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
