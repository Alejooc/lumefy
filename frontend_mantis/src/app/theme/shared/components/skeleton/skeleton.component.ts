import { Component, Input } from '@angular/core';


@Component({
    selector: 'app-skeleton',
    standalone: true,
    imports: [],
    template: `
        <!-- Table skeleton -->
        @if (type === 'table') {
          <div class="skeleton-table">
            @for (col of cols; track col) {
              <div class="skeleton-row header">
                <div class="skeleton-cell skeleton-pulse" [style.width.%]="getRandomWidth()"></div>
              </div>
            }
            @for (row of rows; track row) {
              <div class="skeleton-table-row">
                @for (col of cols; track col) {
                  <div class="skeleton-cell skeleton-pulse"
                  [style.width.%]="getRandomWidth()"></div>
                }
              </div>
            }
          </div>
        }
        
        <!-- Card skeleton -->
        @if (type === 'card') {
          <div class="skeleton-card">
            <div class="skeleton-card-header">
              <div class="skeleton-pulse" style="width: 40%; height: 20px;"></div>
            </div>
            <div class="skeleton-card-body">
              <div class="skeleton-pulse mb-2" style="width: 80%; height: 14px;"></div>
              <div class="skeleton-pulse mb-2" style="width: 60%; height: 14px;"></div>
              <div class="skeleton-pulse" style="width: 70%; height: 14px;"></div>
            </div>
          </div>
        }
        
        <!-- List skeleton -->
        @if (type === 'list') {
          <div class="skeleton-list">
            @for (row of rows; track row) {
              <div class="skeleton-list-item">
                <div class="skeleton-avatar skeleton-pulse"></div>
                <div class="skeleton-content">
                  <div class="skeleton-pulse mb-1" style="width: 60%; height: 14px;"></div>
                  <div class="skeleton-pulse" style="width: 40%; height: 12px;"></div>
                </div>
              </div>
            }
          </div>
        }
        `,
    styles: [`
        .skeleton-pulse {
            background: linear-gradient(90deg, #e9ecef 25%, #f8f9fa 50%, #e9ecef 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite ease-in-out;
            border-radius: 4px;
            min-height: 12px;
        }

        @keyframes shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        .skeleton-table {
            padding: 0;
        }

        .skeleton-row.header {
            padding: 12px 16px;
            border-bottom: 2px solid #e9ecef;
        }

        .skeleton-table-row {
            display: flex;
            gap: 16px;
            padding: 12px 16px;
            border-bottom: 1px solid #f0f0f0;
        }

        .skeleton-cell {
            height: 16px;
            flex: 1;
        }

        .skeleton-list-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid #f0f0f0;
        }

        .skeleton-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            flex-shrink: 0;
        }

        .skeleton-content {
            flex: 1;
        }

        .skeleton-card {
            border: 1px solid #e9ecef;
            border-radius: 8px;
            overflow: hidden;
        }

        .skeleton-card-header {
            padding: 16px;
            border-bottom: 1px solid #e9ecef;
        }

        .skeleton-card-body {
            padding: 16px;
        }
    `]
})
export class SkeletonComponent {
    @Input() type: 'table' | 'card' | 'list' = 'table';
    @Input() rowCount = 5;
    @Input() colCount = 4;

    get rows(): number[] {
        return Array(this.rowCount).fill(0);
    }

    get cols(): number[] {
        return Array(this.colCount).fill(0);
    }

    getRandomWidth(): number {
        return 50 + Math.random() * 40;
    }
}
