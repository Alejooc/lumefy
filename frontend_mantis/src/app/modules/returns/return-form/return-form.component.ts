import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute, RouterModule } from '@angular/router';
import { SaleService, Sale, SaleItem } from '../../../core/services/sale.service';
import { ReturnService, ReturnItemCreate } from '../../../core/services/return.service';
import Swal from 'sweetalert2';

interface ReturnFormItem {
    saleItem: SaleItem;
    selected: boolean;
    quantity: number;
    maxQuantity: number;
}

@Component({
    selector: 'app-return-form',
    standalone: true,
    imports: [CommonModule, FormsModule, RouterModule],
    templateUrl: './return-form.component.html'
})
export class ReturnFormComponent implements OnInit {
    sale: Sale | null = null;
    saleId = '';
    reason = '';
    notes = '';
    formItems: ReturnFormItem[] = [];
    loading = false;
    searchingSale = false;

    private saleService = inject(SaleService);
    private returnService = inject(ReturnService);
    private router = inject(Router);
    private route = inject(ActivatedRoute);
    private cdr = inject(ChangeDetectorRef);

    ngOnInit() {
        const saleIdParam = this.route.snapshot.queryParamMap.get('sale_id');
        if (saleIdParam) {
            this.saleId = saleIdParam;
            this.searchSale();
        }
    }

    searchSale() {
        if (!this.saleId || this.saleId.length < 8) return;
        this.searchingSale = true;
        this.saleService.getSale(this.saleId).subscribe({
            next: (sale) => {
                this.sale = sale;
                this.searchingSale = false;
                this.formItems = (sale.items || []).map(item => ({
                    saleItem: item,
                    selected: false,
                    quantity: item.quantity,
                    maxQuantity: item.quantity,
                }));
                this.cdr.detectChanges();
            },
            error: () => {
                this.searchingSale = false;
                this.sale = null;
                this.cdr.detectChanges();
                Swal.fire('Error', 'No se encontró la venta', 'error');
            }
        });
    }

    get totalRefund(): number {
        return this.formItems
            .filter(i => i.selected)
            .reduce((sum, i) => sum + (i.quantity * i.saleItem.price), 0);
    }

    get hasSelectedItems(): boolean {
        return this.formItems.some(i => i.selected && i.quantity > 0);
    }

    selectAll(event: Event) {
        const checked = (event.target as HTMLInputElement).checked;
        this.formItems.forEach(i => {
            i.selected = checked;
            if (checked) i.quantity = i.maxQuantity;
        });
    }

    submitReturn() {
        if (!this.sale || !this.hasSelectedItems) return;

        const items: ReturnItemCreate[] = this.formItems
            .filter(i => i.selected && i.quantity > 0)
            .map(i => ({
                sale_item_id: i.saleItem.id!,
                quantity: i.quantity,
            }));

        Swal.fire({
            title: 'Crear Devolución',
            text: `Se creará una devolución por ${this.formatCurrency(this.totalRefund)}. ¿Continuar?`,
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Crear Devolución',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.loading = true;
                this.returnService.createReturn({
                    sale_id: this.sale!.id,
                    reason: this.reason || undefined,
                    notes: this.notes || undefined,
                    items
                }).subscribe({
                    next: () => {
                        Swal.fire('Creada', 'La devolución fue creada exitosamente.', 'success');
                        this.router.navigate(['/returns']);
                    },
                    error: (err) => {
                        this.loading = false;
                        this.cdr.detectChanges();
                        Swal.fire('Error', err.error?.detail || 'No se pudo crear la devolución', 'error');
                    }
                });
            }
        });
    }

    formatCurrency(value: number): string {
        return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(value);
    }
}
