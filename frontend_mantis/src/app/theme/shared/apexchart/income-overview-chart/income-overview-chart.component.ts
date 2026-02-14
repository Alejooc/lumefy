// angular import
import { Component, OnInit, viewChild, Input, OnChanges, SimpleChanges } from '@angular/core';

// project import
import { ChartData } from 'src/app/core/services/dashboard.service';

// third party
import { NgApexchartsModule, ChartComponent, ApexOptions } from 'ng-apexcharts';
import { CardComponent } from 'src/app/theme/shared/components/card/card.component';

@Component({
  selector: 'app-income-overview-chart',
  standalone: true,
  imports: [CardComponent, NgApexchartsModule],
  templateUrl: './income-overview-chart.component.html',
  styleUrl: './income-overview-chart.component.scss'
})
export class IncomeOverviewChartComponent implements OnInit, OnChanges {
  // public props
  chart = viewChild.required<ChartComponent>('chart');
  chartOptions!: Partial<ApexOptions>;
  @Input() chartData: ChartData | null = null;

  // life cycle hook
  // life cycle hook
  constructor() {
    this.chartOptions = {
      chart: {
        type: 'bar',
        height: 365,
        toolbar: {
          show: false
        },
        background: 'transparent'
      },
      plotOptions: {
        bar: {
          columnWidth: '45%',
          borderRadius: 4
        }
      },
      dataLabels: {
        enabled: false
      },
      series: [], // Initialize empty
      stroke: {
        curve: 'smooth',
        width: 2
      },
      xaxis: {
        categories: [],
        axisBorder: {
          show: false
        },
        axisTicks: {
          show: false
        },
        labels: {
          style: {
            colors: '#8c8c8c' // simplified
          }
        }
      },
      yaxis: {
        show: false
      },
      colors: ['#5cdbd3'],
      grid: {
        show: false
      },
      tooltip: {
        theme: 'light'
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
