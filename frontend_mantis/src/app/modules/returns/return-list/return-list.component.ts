import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ReturnService, ReturnOrder } from '../../../core/services/return.service';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-return-list',
    standalone: true,
    imports: [CommonModule, RouterModule, FormsModule],
    templateUrl: './return-list.component.html'
})
export class ReturnListComponent implements OnInit {
    returns: ReturnOrder[] = [];
    loading = false;
    filterStatus = '';

    private returnService = inject(ReturnService);
    private router = inject(Router);
    private cdr = inject(ChangeDetectorRef);

    ngOnInit() {
        this.loadReturns();
    }

    loadReturns() {
        this.loading = true;
        this.returnService.getReturns(undefined, this.filterStatus || undefined).subscribe({
            next: (data) => {
                this.returns = data;
                this.loading = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.loading = false;
                this.cdr.detectChanges();
            }
        });
    }

    approveReturn(ret: ReturnOrder) {
        Swal.fire({
            title: 'Aprobar Devolución',
            text: `¿Aprobar esta devolución por ${this.formatCurrency(ret.total_refund)}? El inventario será restaurado.`,
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Sí, aprobar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.returnService.approveReturn(ret.id).subscribe({
                    next: (updated) => {
                        const idx = this.returns.findIndex(r => r.id === ret.id);
                        if (idx >= 0) this.returns[idx] = updated;
                        this.cdr.detectChanges();
                        Swal.fire('Aprobada', 'La devolución fue aprobada y el inventario restaurado.', 'success');
                    },
                    error: (err) => {
                        Swal.fire('Error', err.error?.detail || 'No se pudo aprobar', 'error');
                    }
                });
            }
        });
    }

    rejectReturn(ret: ReturnOrder) {
        Swal.fire({
            title: 'Rechazar Devolución',
            text: '¿Estás seguro de rechazar esta devolución?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, rechazar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.returnService.rejectReturn(ret.id).subscribe({
                    next: (updated) => {
                        const idx = this.returns.findIndex(r => r.id === ret.id);
                        if (idx >= 0) this.returns[idx] = updated;
                        this.cdr.detectChanges();
                        Swal.fire('Rechazada', 'La devolución fue rechazada.', 'info');
                    },
                    error: (err) => {
                        Swal.fire('Error', err.error?.detail || 'No se pudo rechazar', 'error');
                    }
                });
            }
        });
    }

    getStatusBadge(status: string): string {
        switch (status) {
            case 'PENDING': return 'badge bg-warning text-dark';
            case 'APPROVED': return 'badge bg-success';
            case 'REJECTED': return 'badge bg-danger';
            default: return 'badge bg-secondary';
        }
    }

    getStatusLabel(status: string): string {
        switch (status) {
            case 'PENDING': return 'Pendiente';
            case 'APPROVED': return 'Aprobada';
            case 'REJECTED': return 'Rechazada';
            default: return status;
        }
    }

    getTypeLabel(type: string): string {
        return type === 'TOTAL' ? 'Total' : 'Parcial';
    }

    formatCurrency(value: number): string {
        return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(value);
    }

    createReturn() {
        this.router.navigate(['/returns/new']);
    }
}
