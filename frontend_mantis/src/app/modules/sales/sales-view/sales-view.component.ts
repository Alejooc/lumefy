import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule, Router } from '@angular/router';
import { SaleService, Sale } from '../../../core/services/sale.service';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-sales-view',
    standalone: true,
    imports: [CommonModule, RouterModule],
    templateUrl: './sales-view.component.html'
})
export class SalesViewComponent implements OnInit {
    sale: Sale | null = null;
    loading = false;

    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private saleService = inject(SaleService);

    ngOnInit() {
        this.route.paramMap.subscribe(params => {
            const id = params.get('id');
            if (id) this.loadSale(id);
        });
    }

    loadSale(id: string) {
        this.loading = true;
        this.saleService.getSale(id).subscribe({
            next: (data) => {
                this.sale = data;
                this.loading = false;
            },
            error: (err) => {
                this.loading = false;
                Swal.fire('Error', 'No se pudo cargar la venta', 'error');
                this.router.navigate(['/sales']);
            }
        });
    }

    updateStatus(status: 'CONFIRMED' | 'DISPATCHED' | 'DELIVERED' | 'CANCELLED') {
        if (!this.sale) return;

        let confirmText = '';
        let buttonText = '';

        switch (status) {
            case 'CONFIRMED':
                confirmText = '¿Confirmar esta orden? Esto reservará el inventario.';
                buttonText = 'Sí, confirmar';
                break;
            case 'DISPATCHED':
                confirmText = '¿Marcar como despachada?';
                buttonText = 'Sí, despachar';
                break;
            case 'DELIVERED':
                confirmText = '¿Marcar como entregada?';
                buttonText = 'Sí, entregada';
                break;
            case 'CANCELLED':
                confirmText = '¿Cancelar esta orden? Esto liberará el inventario reservado.';
                buttonText = 'Sí, cancelar';
                break;
        }

        Swal.fire({
            title: '¿Estás seguro?',
            text: confirmText,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: buttonText,
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.loading = true;
                this.saleService.updateStatus(this.sale!.id, status).subscribe({
                    next: (updated) => {
                        this.sale = updated;
                        this.loading = false;
                        Swal.fire('Actualizado', 'El estado ha sido actualizado.', 'success');
                    },
                    error: (err) => {
                        this.loading = false;
                        Swal.fire('Error', 'No se pudo actualizar el estado: ' + (err.error?.detail || err.message), 'error');
                    }
                });
            }
        });
    }

    getStatusClass(status: string): string {
        switch (status) {
            case 'QUOTE': return 'badge bg-secondary';
            case 'DRAFT': return 'badge bg-light text-dark';
            case 'CONFIRMED': return 'badge bg-warning text-dark';
            case 'DISPATCHED': return 'badge bg-info text-white';
            case 'DELIVERED': return 'badge bg-success';
            case 'COMPLETED': return 'badge bg-primary';
            case 'CANCELLED': return 'badge bg-danger';
            default: return 'badge bg-secondary';
        }
    }
}
