import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdminService, DatabaseStat } from 'src/app/modules/admin/admin.service';

@Component({
    selector: 'app-database-stats',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './database-stats.component.html',
    styles: [`
    .progress { height: 6px; }
  `]
})
export class DatabaseStatsComponent implements OnInit {
    private adminService = inject(AdminService);
    private cdr = inject(ChangeDetectorRef); // Injected

    stats: DatabaseStat[] = [];
    loading = false;
    totalDatabaseSize = 0;

    ngOnInit() {
        this.loadStats();
    }

    loadStats() {
        this.loading = true;
        this.adminService.getDatabaseStats().subscribe({
            next: (data) => {
                this.stats = data;
                this.loading = false;
                this.totalDatabaseSize = data.reduce((acc, curr) => acc + (curr.total_size_bytes || 0), 0);
                this.cdr.detectChanges();
            },
            error: (error: unknown) => {
                console.error(error);
                this.loading = false;
                this.cdr.detectChanges();
            }
        });
    }

    maxSizeBytes(): number {
        if (this.stats.length === 0) return 0;
        return Math.max(...this.stats.map((s) => s.total_size_bytes || 0));
    }

    getPercent(bytes: number): number {
        const max = this.maxSizeBytes();
        if (max === 0) return 0;
        return (bytes / max) * 100;
    }
}
