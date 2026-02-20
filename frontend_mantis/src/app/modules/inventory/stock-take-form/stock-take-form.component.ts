import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { InventoryService } from '../inventory.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { SharedModule } from '../../../theme/shared/shared.module';

@Component({
    selector: 'app-stock-take-form',
    templateUrl: './stock-take-form.component.html',
    styleUrls: ['./stock-take-form.component.scss'],
    standalone: true,
    imports: [CommonModule, FormsModule, SharedModule]
})
export class StockTakeFormComponent implements OnInit {
    stockTake: any = null;
    isLoading = true;
    isSaving = false;
    searchTerm = '';

    constructor(
        private route: ActivatedRoute,
        private router: Router,
        private inventoryService: InventoryService,
        private swal: SweetAlertService,
        private cdr: ChangeDetectorRef
    ) { }

    ngOnInit(): void {
        const id = this.route.snapshot.paramMap.get('id');
        if (id) {
            this.loadStockTake(id);
        }
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

    get filteredItems(): any[] {
        if (!this.stockTake?.items) return [];
        if (!this.searchTerm) return this.stockTake.items;
        const term = this.searchTerm.toLowerCase();
        return this.stockTake.items.filter((item: any) => {
            const name = item.product?.name?.toLowerCase() || '';
            const sku = item.product?.sku?.toLowerCase() || '';
            return name.includes(term) || sku.includes(term);
        });
    }

    get totalItems(): number {
        return this.stockTake?.items?.length || 0;
    }

    get countedItems(): number {
        return this.stockTake?.items?.filter((i: any) => i.counted_qty !== null && i.counted_qty !== undefined).length || 0;
    }

    get itemsWithDifference(): number {
        return this.stockTake?.items?.filter((i: any) => i.difference !== 0 && i.counted_qty !== null).length || 0;
    }

    get isInProgress(): boolean {
        return this.stockTake?.status === 'IN_PROGRESS';
    }

    saveCounts() {
        if (!this.stockTake) return;
        this.isSaving = true;

        const items = this.stockTake.items
            .filter((i: any) => i.counted_qty !== null && i.counted_qty !== undefined)
            .map((i: any) => ({
                id: i.id,
                counted_qty: Number(i.counted_qty)
            }));

        this.inventoryService.updateStockTakeCounts(this.stockTake.id, items).subscribe({
            next: (data) => {
                this.stockTake = data;
                this.isSaving = false;
                this.swal.success('Guardado', 'Conteos actualizados correctamente');
                this.cdr.detectChanges();
            },
            error: (err) => {
                this.isSaving = false;
                this.swal.error('Error', err?.error?.detail || 'Error al guardar');
            }
        });
    }

    applyAdjustments() {
        this.swal.confirm(
            '¿Aplicar Ajustes?',
            'Esto generará movimientos de ajuste (ADJ) automáticos para todas las diferencias. Esta acción no se puede deshacer.'
        ).then((result: any) => {
            if (result.isConfirmed) {
                this.isSaving = true;
                this.inventoryService.applyStockTake(this.stockTake.id).subscribe({
                    next: (data) => {
                        this.stockTake = data;
                        this.isSaving = false;
                        this.swal.success('Aplicado', 'Los ajustes de inventario han sido aplicados exitosamente');
                        this.cdr.detectChanges();
                    },
                    error: (err) => {
                        this.isSaving = false;
                        this.swal.error('Error', err?.error?.detail || 'Error al aplicar');
                    }
                });
            }
        });
    }

    cancelTake() {
        this.swal.confirm(
            '¿Cancelar Toma?',
            'Esto cancelará la toma de inventario sin aplicar cambios.'
        ).then((result: any) => {
            if (result.isConfirmed) {
                this.inventoryService.cancelStockTake(this.stockTake.id).subscribe({
                    next: () => {
                        this.swal.success('Cancelada', 'Toma de inventario cancelada');
                        this.router.navigate(['/inventory/stock-take']);
                    },
                    error: (err) => {
                        this.swal.error('Error', err?.error?.detail || 'Error al cancelar');
                    }
                });
            }
        });
    }

    onCountedChange(item: any) {
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
