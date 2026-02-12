import { Component, Inject, OnInit, ViewChild, ChangeDetectorRef } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { ChartComponent } from 'ng-apexcharts';

import {
    ApexNonAxisChartSeries,
    ApexResponsive,
    ApexChart,
    ApexDataLabels,
    ApexLegend,
    ApexStroke,
    ApexPlotOptions,
    ApexAxisChartSeries,
    ApexXAxis,
    ApexYAxis,
    ApexTooltip,
    ApexFill
} from 'ng-apexcharts';

export type ChartOptions = {
    series: ApexNonAxisChartSeries | ApexAxisChartSeries | any;
    chart: ApexChart;
    responsive: ApexResponsive[];
    labels: any;
    plotOptions: ApexPlotOptions;
    stroke: ApexStroke;
    dataLabels: ApexDataLabels;
    legend: ApexLegend;
    colors: string[];
    xaxis: ApexXAxis;
    yaxis: ApexYAxis;
    tooltip: ApexTooltip;
    fill: ApexFill;
};

@Component({
    selector: 'app-reports',
    templateUrl: './reports.component.html',
    styleUrls: ['./reports.component.scss'],
    standalone: false
})
export class ReportsComponent implements OnInit {
    @ViewChild('chart') chart: ChartComponent;

    // Charts
    salesChartOptions: Partial<ChartOptions>;
    topProductsChartOptions: Partial<ChartOptions>;

    // Data
    salesSummary: any[] = [];
    topProducts: any[] = [];
    inventoryValue: any = { total_items: 0, total_value: 0, low_stock_items: 0 };

    isLoading = false;
    currencySymbol = '$';

    constructor(
        @Inject(ApiService) private api: ApiService,
        @Inject(AuthService) private auth: AuthService,
        private cdr: ChangeDetectorRef
    ) {
        // Initialize empty charts
        this.salesChartOptions = {
            series: [{ name: "Sales", data: [] }],
            chart: { type: "bar", height: 350 },
            plotOptions: { bar: { horizontal: false, columnWidth: "55%" } },
            dataLabels: { enabled: false },
            stroke: { show: true, width: 2, colors: ["transparent"] },
            xaxis: { categories: [] },
            yaxis: { title: { text: "Sales" } },
            fill: { opacity: 1 },
            tooltip: { y: { formatter: (val) => this.currencySymbol + " " + val } }
        };

        this.topProductsChartOptions = {
            series: [],
            chart: { type: "donut", height: 350 },
            labels: [],
            responsive: [{ breakpoint: 480, options: { chart: { width: 200 }, legend: { position: "bottom" } } }]
        };
    }

    ngOnInit(): void {
        this.auth.currentCompany.subscribe(company => {
            if (company && company.currency_symbol) {
                this.currencySymbol = company.currency_symbol;
                this.cdr.detectChanges();
            }
        });

        this.loadData();
    }

    loadData() {
        this.isLoading = true;

        // Load Sales Summary
        this.api.get<any[]>('/reports/sales-summary?days=7').subscribe(data => {
            this.salesSummary = data;

            // Update Chart
            this.salesChartOptions = {
                ...this.salesChartOptions,
                series: [{ name: "Ventas", data: data.map(x => x.total) }],
                xaxis: { categories: data.map(x => x.date) }
            };
            this.cdr.detectChanges();
        });

        // Load Top Products
        this.api.get<any[]>('/reports/top-products?limit=5').subscribe(data => {
            this.topProducts = data;

            // Update Donut Chart
            this.topProductsChartOptions = {
                ...this.topProductsChartOptions,
                series: data.map(x => x.quantity),
                labels: data.map(x => x.name)
            };
            this.cdr.detectChanges();
        });

        // Load Inventory Value
        this.api.get<any>('/reports/inventory-value').subscribe(data => {
            this.inventoryValue = data;
            this.isLoading = false;
            this.cdr.detectChanges();
        });
    }
}
