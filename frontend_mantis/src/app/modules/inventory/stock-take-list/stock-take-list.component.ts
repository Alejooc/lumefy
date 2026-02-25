import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { Branch } from '../../../core/services/branch.service';
import { SharedModule } from '../../../theme/shared/shared.module';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { InventoryService, StockTake } from '../inventory.service';

@Component({
    selector: 'app-stock-take-list',
    templateUrl: './stock-take-list.component.html',
    styleUrls: ['./stock-take-list.component.scss'],
    standalone: true,
    imports: [CommonModule, SharedModule]
})
export class StockTakeListComponent implements OnInit {
    private api = inject(ApiService);
    private inventoryService = inject(InventoryService);
    private swal = inject(SweetAlertService);
    private router = inject(Router);
    private cdr = inject(ChangeDetectorRef);

    stockTakes: StockTake[] = [];
    branches: Branch[] = [];
    selectedBranch = '';
    isLoading = false;

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
            error: () => {
                this.isLoading = false;
            }
        });
    }

    loadBranches() {
        this.api.get<Branch[]>('/branches').subscribe({
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
            error: (err: { error?: { detail?: string } }) => {
                this.swal.error('Error', err?.error?.detail || 'No se pudo crear la toma');
            }
        });
    }

    viewDetail(id: string) {
        this.router.navigate(['/inventory/stock-take', id]);
    }

    getStatusLabel(status: string): string {
        const labels: Record<string, string> = {
            IN_PROGRESS: 'En Progreso',
            COMPLETED: 'Completada',
            CANCELLED: 'Cancelada'
        };
        return labels[status] || status;
    }

    getStatusClass(status: string): string {
        const classes: Record<string, string> = {
            IN_PROGRESS: 'bg-warning',
            COMPLETED: 'bg-success',
            CANCELLED: 'bg-danger'
        };
        return classes[status] || 'bg-secondary';
    }
}
