// angular import
import { Component, OnInit, viewChild, Input, OnChanges, SimpleChanges } from '@angular/core';

// project import
import { ChartData } from 'src/app/core/services/dashboard.service';

// third party
import { NgApexchartsModule, ChartComponent, ApexOptions } from 'ng-apexcharts';

@Component({
  selector: 'app-monthly-bar-chart',
  standalone: true,
  imports: [NgApexchartsModule],
  templateUrl: './monthly-bar-chart.component.html',
  styleUrl: './monthly-bar-chart.component.scss'
})
export class MonthlyBarChartComponent implements OnInit, OnChanges {
  // public props
  chart = viewChild.required<ChartComponent>('chart');
  chartOptions!: Partial<ApexOptions>;
  @Input() chartData: ChartData | null = null;

  // life cycle hook
  // life cycle hook
  constructor() {
    this.chartOptions = {
      chart: {
        height: 450,
        type: 'area', // Keep area or change to bar? Original was area with 2 series.
        toolbar: {
          show: false
        },
        background: 'transparent'
      },
      dataLabels: {
        enabled: false
      },
      colors: ['#1677ff', '#0050b3'],
      series: [], // Initialize empty
      stroke: {
        curve: 'smooth',
        width: 2
      },
      xaxis: {
        categories: [],
        labels: {
          style: {
            colors: '#8c8c8c' // simplified
          }
        },
        axisBorder: {
          show: true,
          color: '#f0f0f0'
        }
      },
      yaxis: {
        labels: {
          style: {
            colors: ['#8c8c8c']
          }
        }
      },
      grid: {
        strokeDashArray: 0,
        borderColor: '#f5f5f5'
      },
      theme: {
        mode: 'light'
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

  // public method
  toggleActive(value: string) {
    // Disabled for now as we rely on input data
  }
}
