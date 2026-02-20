import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { InventoryService } from '../inventory.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { SharedModule } from '../../../theme/shared/shared.module';

@Component({
    selector: 'app-stock-take-list',
    templateUrl: './stock-take-list.component.html',
    styleUrls: ['./stock-take-list.component.scss'],
    standalone: true,
    imports: [CommonModule, SharedModule]
})
export class StockTakeListComponent implements OnInit {
    stockTakes: any[] = [];
    branches: any[] = [];
    selectedBranch: string = '';
    isLoading = false;

    constructor(
        private api: ApiService,
        private inventoryService: InventoryService,
        private swal: SweetAlertService,
        private router: Router,
        private cdr: ChangeDetectorRef
    ) { }

    ngOnInit(): void {
        this.loadStockTakes();
        this.loadBranches();
    }

    loadStockTakes() {
        this.isLoading = true;
        this.inventoryService.getStockTakes().subscribe({
            next: (data) => {
                this.stockTakes = data;
                this.isLoading = false;
                this.cdr.detectChanges();
            },
            error: () => this.isLoading = false
        });
    }

    loadBranches() {
        this.api.get<any[]>('/branches').subscribe({
            next: (data) => {
                this.branches = data;
                if (data.length === 1) {
                    this.selectedBranch = data[0].id;
                }
                this.cdr.detectChanges();
            }
        });
    }

    createNew() {
        if (!this.selectedBranch) {
            this.swal.error('Error', 'Seleccione una sucursal');
            return;
        }
        this.inventoryService.createStockTake({ branch_id: this.selectedBranch }).subscribe({
            next: (result) => {
                this.swal.success('Creada', 'Toma de inventario iniciada');
                this.router.navigate(['/inventory/stock-take', result.id]);
            },
            error: (err) => {
                this.swal.error('Error', err?.error?.detail || 'No se pudo crear la toma');
            }
        });
    }

    viewDetail(id: string) {
        this.router.navigate(['/inventory/stock-take', id]);
    }

    getStatusLabel(status: string): string {
        const labels: any = {
            IN_PROGRESS: 'En Progreso',
            COMPLETED: 'Completada',
            CANCELLED: 'Cancelada'
        };
        return labels[status] || status;
    }

    getStatusClass(status: string): string {
        const classes: any = {
            IN_PROGRESS: 'bg-warning',
            COMPLETED: 'bg-success',
            CANCELLED: 'bg-danger'
        };
        return classes[status] || 'bg-secondary';
    }
}
