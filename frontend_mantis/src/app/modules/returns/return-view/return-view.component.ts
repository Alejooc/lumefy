import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
// Triggering Angular recompilation
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute, Router } from '@angular/router';
import { ReturnService, ReturnOrder } from '../../../core/services/return.service';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-return-view',
    standalone: true,
    imports: [CommonModule, RouterModule],
    templateUrl: './return-view.component.html'
})
export class ReturnViewComponent implements OnInit {
    returnOrder: ReturnOrder | null = null;
    loading = false;

    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private returnService = inject(ReturnService);
    private cdr = inject(ChangeDetectorRef);

    ngOnInit() {
        this.route.paramMap.subscribe(params => {
            const id = params.get('id');
            if (id) {
                this.loadReturn(id);
            }
        });
    }

    loadReturn(id: string) {
        this.loading = true;
        this.returnService.getReturn(id).subscribe({
            next: (data) => {
                this.returnOrder = data;
                this.loading = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Error', 'No se pudo cargar la devolución', 'error');
                this.router.navigate(['/returns']);
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
                this.loading = true;
                this.returnService.approveReturn(ret.id).subscribe({
                    next: (updated) => {
                        this.returnOrder = updated;
                        this.loading = false;
                        this.cdr.detectChanges();
                        Swal.fire('Aprobada', 'La devolución fue aprobada y el inventario restaurado.', 'success');
                    },
                    error: (err) => {
                        this.loading = false;
                        this.cdr.detectChanges();
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
                this.loading = true;
                this.returnService.rejectReturn(ret.id).subscribe({
                    next: (updated) => {
                        this.returnOrder = updated;
                        this.loading = false;
                        this.cdr.detectChanges();
                        Swal.fire('Rechazada', 'La devolución fue rechazada.', 'info');
                    },
                    error: (err) => {
                        this.loading = false;
                        this.cdr.detectChanges();
                        Swal.fire('Error', err.error?.detail || 'No se pudo rechazar', 'error');
                    }
                });
            }
        });
    }

    registerRefund(ret: ReturnOrder) {
        Swal.fire({
            title: 'Registrar reembolso manual',
            text: `La devolución aprobada es por ${this.formatCurrency(ret.total_refund)}. Escribe la referencia de la transferencia o reverso realizado.`,
            input: 'text',
            inputPlaceholder: 'Referencia del reembolso',
            inputAttributes: { maxlength: '160', autocapitalize: 'off' },
            showCancelButton: true,
            confirmButtonText: 'Registrar reembolso',
            cancelButtonText: 'Cancelar',
            inputValidator: (value) => !value || value.trim().length < 3 ? 'Indica una referencia válida.' : undefined
        }).then((result) => {
            if (!result.isConfirmed || !result.value) return;
            this.loading = true;
            this.returnService.registerManualRefund(ret.id, result.value.trim()).subscribe({
                next: (updated) => {
                    this.returnOrder = updated;
                    this.loading = false;
                    this.cdr.detectChanges();
                    Swal.fire('Reembolso registrado', 'La referencia quedó asociada a la devolución y se notificó al comprador.', 'success');
                },
                error: (err) => {
                    this.loading = false;
                    this.cdr.detectChanges();
                    Swal.fire('Error', err.error?.detail || 'No se pudo registrar el reembolso', 'error');
                }
            });
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

    formatCurrency(value: number): string {
        return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(value);
    }

    getRefundStatusLabel(status?: string): string {
        return { PENDING: 'Pendiente de reembolso', REFUNDED: 'Reembolsado', NOT_REQUIRED: 'No requiere reembolso' }[status || 'NOT_REQUIRED'] || status || 'No definido';
    }

    getRefundStatusBadge(status?: string): string {
        return { PENDING: 'badge bg-warning text-dark', REFUNDED: 'badge bg-success', NOT_REQUIRED: 'badge bg-secondary' }[status || 'NOT_REQUIRED'] || 'badge bg-secondary';
    }
}
