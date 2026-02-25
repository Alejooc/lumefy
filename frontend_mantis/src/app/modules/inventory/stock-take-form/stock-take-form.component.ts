import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { SharedModule } from '../../../theme/shared/shared.module';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { InventoryService, StockTake, StockTakeItem } from '../inventory.service';

@Component({
    selector: 'app-stock-take-form',
    templateUrl: './stock-take-form.component.html',
    styleUrls: ['./stock-take-form.component.scss'],
    standalone: true,
    imports: [CommonModule, FormsModule, SharedModule]
})
export class StockTakeFormComponent implements OnInit {
    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private inventoryService = inject(InventoryService);
    private swal = inject(SweetAlertService);
    private cdr = inject(ChangeDetectorRef);

    stockTake: StockTake | null = null;
    isLoading = true;
    isSaving = false;
    searchTerm = '';

    ngOnInit(): void {
        const id = this.route.snapshot.paramMap.get('id');
        if (id) this.loadStockTake(id);
    }

    loadStockTake(id: string) {
        this.isLoading = true;
        this.inventoryService.getStockTake(id).subscribe({
            next: (data) => {
                this.stockTake = data;
                this.isLoading = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.swal.error('Error', 'No se pudo cargar la toma de inventario');
                this.router.navigate(['/inventory/stock-take']);
            }
        });
    }

    get filteredItems(): StockTakeItem[] {
        if (!this.stockTake?.items) return [];
        if (!this.searchTerm) return this.stockTake.items;
        const term = this.searchTerm.toLowerCase();
        return this.stockTake.items.filter((item) => {
            const name = item.product?.name?.toLowerCase() || '';
            const sku = item.product?.sku?.toLowerCase() || '';
            return name.includes(term) || sku.includes(term);
        });
    }

    get totalItems(): number {
        return this.stockTake?.items?.length || 0;
    }

    get countedItems(): number {
        return this.stockTake?.items?.filter((item) => item.counted_qty !== null && item.counted_qty !== undefined).length || 0;
    }

    get itemsWithDifference(): number {
        return this.stockTake?.items?.filter((item) => item.difference !== 0 && item.counted_qty !== null).length || 0;
    }

    get isInProgress(): boolean {
        return this.stockTake?.status === 'IN_PROGRESS';
    }

    saveCounts() {
        if (!this.stockTake) return;
        this.isSaving = true;

        const items = this.stockTake.items
            .filter((item) => item.counted_qty !== null && item.counted_qty !== undefined)
            .map((item) => ({
                id: item.id,
                counted_qty: Number(item.counted_qty)
            }));

        this.inventoryService.updateStockTakeCounts(this.stockTake.id, items).subscribe({
            next: (data) => {
                this.stockTake = data;
                this.isSaving = false;
                this.swal.success('Guardado', 'Conteos actualizados correctamente');
                this.cdr.detectChanges();
            },
            error: (err: { error?: { detail?: string } }) => {
                this.isSaving = false;
                this.swal.error('Error', err?.error?.detail || 'Error al guardar');
            }
        });
    }

    applyAdjustments() {
        if (!this.stockTake) return;
        this.swal
            .confirm(
                'Aplicar ajustes',
                'Esto generara movimientos de ajuste (ADJ) para todas las diferencias. Esta accion no se puede deshacer.'
            )
            .then((result) => {
                if (!result.isConfirmed || !this.stockTake) return;
                this.isSaving = true;
                this.inventoryService.applyStockTake(this.stockTake.id).subscribe({
                    next: (data) => {
                        this.stockTake = data;
                        this.isSaving = false;
                        this.swal.success('Aplicado', 'Los ajustes de inventario han sido aplicados exitosamente');
                        this.cdr.detectChanges();
                    },
                    error: (err: { error?: { detail?: string } }) => {
                        this.isSaving = false;
                        this.swal.error('Error', err?.error?.detail || 'Error al aplicar');
                    }
                });
            });
    }

    cancelTake() {
        if (!this.stockTake) return;
        this.swal.confirm('Cancelar toma', 'Esto cancelara la toma de inventario sin aplicar cambios.').then((result) => {
            if (!result.isConfirmed || !this.stockTake) return;
            this.inventoryService.cancelStockTake(this.stockTake.id).subscribe({
                next: () => {
                    this.swal.success('Cancelada', 'Toma de inventario cancelada');
                    this.router.navigate(['/inventory/stock-take']);
                },
                error: (err: { error?: { detail?: string } }) => {
                    this.swal.error('Error', err?.error?.detail || 'Error al cancelar');
                }
            });
        });
    }

    onCountedChange(item: StockTakeItem) {
        if (item.counted_qty !== null && item.counted_qty !== undefined) {
            item.difference = Number(item.counted_qty) - item.system_qty;
        } else {
            item.difference = 0;
        }
    }

    goBack() {
        this.router.navigate(['/inventory/stock-take']);
    }
}
