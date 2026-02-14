// angular import
import { Component, viewChild, Input, OnChanges, SimpleChanges, OnInit } from '@angular/core';

// project import
import { ChartData } from 'src/app/core/services/dashboard.service';

// third party
import { NgApexchartsModule, ChartComponent, ApexOptions } from 'ng-apexcharts';

@Component({
  selector: 'app-sales-report-chart',
  standalone: true,
  imports: [NgApexchartsModule],
  templateUrl: './sales-report-chart.component.html',
  styleUrl: './sales-report-chart.component.scss'
})
export class SalesReportChartComponent implements OnInit, OnChanges {
  chart = viewChild.required<ChartComponent>('chart');
  chartOptions!: Partial<ApexOptions>;
  @Input() chartData: ChartData | null = null;

  constructor() {
    this.chartOptions = {
      chart: {
        type: 'bar',
        height: 430,
        toolbar: {
          show: false
        },
        background: 'transparent'
      },
      plotOptions: {
        bar: {
          columnWidth: '30%',
          borderRadius: 4
        }
      },
      stroke: {
        show: true,
        width: 8,
        colors: ['transparent']
      },
      dataLabels: {
        enabled: false
      },
      legend: {
        position: 'top',
        horizontalAlign: 'right',
        show: true,
        fontFamily: `'Public Sans', sans-serif`,
        offsetX: 10,
        offsetY: 10,
        labels: {
          useSeriesColors: false
        },
        itemMargin: {
          horizontal: 15,
          vertical: 5
        }
      },
      series: [], // Initialize empty
      xaxis: {
        categories: [],
        labels: {
          style: {
            colors: ['#222', '#222', '#222', '#222', '#222', '#222'] // Simplified or keep
          }
        }
      },
      tooltip: {
        theme: 'light'
      },
      colors: ['#faad14', '#1677ff'], // Profit, Revenue
      grid: {
        borderColor: '#f5f5f5'
      }
    };
  }

  ngOnInit() {
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['chartData'] && this.chartData) {
      this.updateChart();
    }
  }

  updateChart() {
    if (!this.chartData) return;

    this.chartOptions = {
      ...this.chartOptions,
      series: this.chartData.series,
      xaxis: {
        ...this.chartOptions.xaxis,
        categories: this.chartData.categories
      }
    };
  }
}
