import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { NgbDropdownModule } from '@ng-bootstrap/ng-bootstrap';
import Swal from 'sweetalert2';
import { SaleService, Sale } from '../../../core/services/sale.service';
import { ClientService } from '../../clients/client.service';

@Component({
    selector: 'app-sales-list',
    standalone: true,
    imports: [CommonModule, RouterModule, FormsModule, NgbDropdownModule],
    templateUrl: './sales-list.component.html',
    styles: [`
        .status-badge { font-size: 0.8rem; padding: 5px 10px; border-radius: 4px; }
        .bg-quote { background-color: #6c757d; color: white; }
        .bg-confirmed { background-color: #ffc107; color: black; }
        .bg-dispatched { background-color: #17a2b8; color: white; }
        .bg-delivered { background-color: #28a745; color: white; }
        .bg-cancelled { background-color: #dc3545; color: white; }
    `]
})
export class SalesListComponent implements OnInit {
    sales: Sale[] = [];
    loading = false;
    filterStatus = '';

    // Inject services
    private saleService = inject(SaleService);
    private cdr = inject(ChangeDetectorRef);

    ngOnInit() {
        this.loadSales();
    }

    loadSales() {
        this.loading = true;
        this.saleService.getSales(this.filterStatus).subscribe({
            next: (data) => {
                this.sales = data;
                this.loading = false;
                this.cdr.detectChanges(); // Force UI update
            },
            error: (e) => {
                console.error(e);
                this.loading = false;
                this.cdr.detectChanges();
            }
        });
    }

    getStatusClass(status: string): string {
        switch (status) {
            case 'QUOTE': return 'badge bg-secondary';
            case 'DRAFT': return 'badge bg-light text-dark';
            case 'CONFIRMED': return 'badge bg-warning text-dark';
            case 'PICKING': return 'badge bg-info text-dark';
            case 'PACKING': return 'badge bg-info text-white';
            case 'DISPATCHED': return 'badge bg-primary text-white';
            case 'DELIVERED': return 'badge bg-success';
            case 'COMPLETED': return 'badge bg-success';
            case 'CANCELLED': return 'badge bg-danger';
            default: return 'badge bg-secondary';
        }
    }

    getStatusLabel(status: string): string {
        switch (status) {
            case 'QUOTE': return 'Cotización';
            case 'DRAFT': return 'Borrador';
            case 'CONFIRMED': return 'Confirmada';
            case 'PICKING': return 'En Picking';
            case 'PACKING': return 'Empacando';
            case 'DISPATCHED': return 'Despachada';
            case 'DELIVERED': return 'Entregada';
            case 'COMPLETED': return 'Completada';
            case 'CANCELLED': return 'Cancelada';
            default: return status;
        }
    }

    deleteSale(id: string) {
        Swal.fire({
            title: '¿Estás seguro?',
            text: 'Esta acción no se puede deshacer. Solo se pueden eliminar borradores o canceladas.',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.loading = true;
                this.saleService.deleteSale(id).subscribe({
                    next: () => {
                        this.sales = this.sales.filter(s => s.id !== id);
                        this.loading = false;
                        this.cdr.detectChanges();
                        Swal.fire('Eliminado', 'La venta ha sido eliminada.', 'success');
                    },
                    error: (err) => {
                        this.loading = false;
                        this.cdr.detectChanges();
                        Swal.fire('Error', 'No se pudo eliminar: ' + (err.error?.detail || err.message), 'error');
                    }
                });
            }
        });
    }

    downloadPdf(id: string, type: string) {
        this.loading = true;
        this.saleService.downloadPdf(id, type).subscribe({
            next: (blob) => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${type}_${id.substring(0, 8)}.pdf`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                this.loading = false;
                this.cdr.detectChanges();
            },
            error: (err) => {
                console.error('Download error:', err);
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Error', 'Error al descargar el PDF. Verifique el estado de la venta.', 'error');
            }
        });
    }
}
