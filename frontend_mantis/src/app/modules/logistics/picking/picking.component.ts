import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import Swal from 'sweetalert2';
import { SaleService, Sale } from '../../../core/services/sale.service';
import { LogisticsService } from '../logistics.service';

@Component({
    selector: 'app-picking',
    standalone: true,
    imports: [CommonModule, RouterModule, FormsModule],
    templateUrl: './picking.component.html'
})
export class PickingComponent implements OnInit {
    saleId: string | null = null;
    sale: Sale | null = null;
    loading = false;

    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private saleService = inject(SaleService);
    private logisticsService = inject(LogisticsService);
    private cdr = inject(ChangeDetectorRef);

    ngOnInit() {
        this.saleId = this.route.snapshot.paramMap.get('id');
        if (this.saleId) {
            this.loadSale();
        }
    }

    loadSale() {
        this.loading = true;
        this.saleService.getSale(this.saleId!).subscribe({
            next: (data) => {
                this.sale = data;
                this.loading = false;
                this.cdr.detectChanges();
            },
            error: (err) => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Error', 'No se pudo cargar la venta', 'error');
            }
        });
    }

    updatePickedQuantity(item: any, quantity: number) {
        if (quantity < 0) return;
        if (quantity > item.quantity) {
            Swal.fire('Error', 'No puedes pickear más de lo ordenado', 'warning');
            return;
        }

        this.logisticsService.updatePickingItem({
            sale_item_id: item.id,
            quantity_picked: quantity
        }).subscribe({
            next: () => {
                item.quantity_picked = quantity;
                this.cdr.detectChanges();
                // Optional: Toast notification
            },
            error: (err) => {
                Swal.fire('Error', 'No se pudo actualizar', 'error');
                this.cdr.detectChanges();
            }
        });
    }

    finishPicking() {
        // Validate all items picked?
        const allPicked = this.sale?.items.every((i: any) => i.quantity_picked >= i.quantity);

        let message = '¿Finalizar Picking y pasar a Empaque?';
        if (!allPicked) {
            message = 'Hay ítems pendientes de pickear. ¿Deseas continuar igual?';
        }

        Swal.fire({
            title: 'Confirmar Picking',
            text: message,
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Sí, finalizar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.saleService.updateStatus(this.saleId!, 'PACKING').subscribe({
                    next: () => {
                        this.cdr.detectChanges();
                        Swal.fire('Éxito', 'Picking finalizado', 'success').then(() => {
                            this.router.navigate(['/logistics/packing', this.saleId]);
                        });
                    },
                    error: (err) => {
                        this.cdr.detectChanges();
                        Swal.fire('Error', 'No se pudo actualizar estado', 'error');
                    }
                });
            }
        });
    }
}
