import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { SaleService, Sale } from '../../../core/services/sale.service';
import { forkJoin } from 'rxjs';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-picking-list',
    standalone: true,
    imports: [CommonModule, RouterModule],
    templateUrl: './picking-list.component.html'
})
export class PickingListComponent implements OnInit {
    pendingSales: Sale[] = [];
    loading = false;

    private saleService = inject(SaleService);

    ngOnInit() {
        this.loadPendingSales();
    }

    loadPendingSales() {
        this.loading = true;
        // Fetch both CONFIRMED and PICKING orders
        forkJoin([
            this.saleService.getSales('CONFIRMED'),
            this.saleService.getSales('PICKING')
        ]).subscribe({
            next: ([confirmed, picking]) => {
                this.pendingSales = [...confirmed, ...picking];
                this.loading = false;
            },
            error: (err) => {
                console.error(err);
                this.loading = false;
            }
        });
    }

    dispatchOrder(id: string) {
        Swal.fire({
            title: '¿Despachar Orden?',
            text: 'Esto marcará la orden como enviada.',
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Sí, Despachar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.saleService.updateStatus(id, 'DISPATCHED').subscribe({
                    next: () => {
                        Swal.fire('Despachado', 'La orden ha sido marcada como despachada.', 'success');
                        this.loadPendingSales();
                    },
                    error: (err) => {
                        Swal.fire('Error', 'No se pudo actualizar: ' + err.message, 'error');
                    }
                });
            }
        });
    }
}
