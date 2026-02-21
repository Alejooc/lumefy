import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { SaleService, Sale } from '../../../core/services/sale.service';
import Swal from 'sweetalert2';
import { LogisticsService } from '../../logistics/logistics.service';

@Component({
    selector: 'app-sales-view',
    standalone: true,
    imports: [CommonModule, RouterModule, ReactiveFormsModule],
    templateUrl: './sales-view.component.html'
})
export class SalesViewComponent implements OnInit {
    sale: Sale | null = null;
    loading = false;
    packedQuantities: { [key: string]: number } = {};

    showDeliveryModal = false;
    isSubmittingDelivery = false;
    deliveryForm: FormGroup;

    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private saleService = inject(SaleService);
    private logisticsService = inject(LogisticsService);
    private cdr = inject(ChangeDetectorRef);
    private fb = inject(FormBuilder);

    constructor() {
        this.deliveryForm = this.fb.group({
            notes: [''],
            evidence_url: ['']
        });
    }

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
                this.cdr.detectChanges(); // Force UI update

                // Fetch packages if status warrants it (or always)
                if (['PICKING', 'PACKING', 'DISPATCHED', 'DELIVERED'].includes(this.sale.status)) {
                    this.loadPackages(id);
                }
            },
            error: (err) => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Error', 'No se pudo cargar la venta', 'error');
                this.router.navigate(['/sales']);
            }
        });
    }

    loadPackages(saleId: string) {
        this.logisticsService.getPackages(saleId).subscribe(packages => {
            this.packedQuantities = {};
            packages.forEach(pkg => {
                pkg.items.forEach(item => {
                    if (!this.packedQuantities[item.sale_item_id]) {
                        this.packedQuantities[item.sale_item_id] = 0;
                    }
                    this.packedQuantities[item.sale_item_id] += item.quantity;
                });
            });
            this.cdr.detectChanges(); // Force UI update
        });
    }

    updateStatus(status: 'CONFIRMED' | 'PICKING' | 'PACKING' | 'DISPATCHED' | 'DELIVERED' | 'COMPLETED' | 'CANCELLED') {
        if (!this.sale) return;

        let confirmText = '';
        let buttonText = '';

        switch (status) {
            case 'CONFIRMED':
                confirmText = '¿Confirmar esta orden? Esto reservará el inventario.';
                buttonText = 'Sí, confirmar';
                break;
            case 'PICKING':
                confirmText = '¿Iniciar preparación (Picking)?';
                buttonText = 'Sí, ir a Picking';
                // Override action to navigate
                Swal.fire({
                    title: 'Iniciar Picking',
                    text: confirmText,
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonText: buttonText
                }).then((result) => {
                    if (result.isConfirmed) {
                        // Update status then navigate? Or just navigate and let picking start? 
                        // Better to update status to PICKING then navigate.
                        this.saleService.updateStatus(this.sale!.id, 'PICKING').subscribe(() => {
                            this.router.navigate(['/logistics/picking', this.sale!.id]);
                        });
                    }
                });
                return; // Stop default execution
            case 'PACKING':
                confirmText = '¿Ir a Empaque?';
                buttonText = 'Sí, ir a Empaque';
                Swal.fire({
                    title: 'Empaque',
                    text: confirmText,
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonText: buttonText
                }).then((result) => {
                    if (result.isConfirmed) {
                        // Status update might happen inside packing or before, let's just go there
                        if (this.sale!.status !== 'PACKING') {
                            this.saleService.updateStatus(this.sale!.id, 'PACKING').subscribe(() => {
                                this.router.navigate(['/logistics/packing', this.sale!.id]);
                            });
                        } else {
                            this.router.navigate(['/logistics/packing', this.sale!.id]);
                        }
                    }
                });
                return;
            case 'DISPATCHED':
                confirmText = '¿Marcar como despachada (Enviada)?';
                buttonText = 'Sí, despachar';
                break;
            case 'DELIVERED':
                // Removed since we use custom modal now
                return;
            case 'COMPLETED':
                // Removed since we use completeSale method now
                Swal.fire({
                    title: 'Cerrar Venta',
                    text: '¿Marcar esta venta como completada? Esta acción es definitiva.',
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonText: 'Sí, cerrar venta',
                    cancelButtonText: 'Cancelar'
                }).then((result) => {
                    if (result.isConfirmed) {
                        this.loading = true;
                        this.saleService.completeSale(this.sale!.id).subscribe({
                            next: (updated) => {
                                this.sale = updated;
                                this.loading = false;
                                this.cdr.detectChanges();
                                Swal.fire('Completada', 'La venta ha sido cerrada exitosamente.', 'success');
                            },
                            error: (err) => {
                                this.loading = false;
                                this.cdr.detectChanges();
                                Swal.fire('Error', err.error?.detail || 'No se pudo completar la venta', 'error');
                            }
                        });
                    }
                });
                return;
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
                        this.cdr.detectChanges();
                        Swal.fire('Actualizado', 'El estado ha sido actualizado.', 'success');
                    },
                    error: (err) => {
                        this.loading = false;
                        this.cdr.detectChanges();
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
            case 'PICKING': return 'badge bg-info text-dark';
            case 'PACKING': return 'badge bg-info text-white';
            case 'DISPATCHED': return 'badge bg-primary text-white';
            case 'DELIVERED': return 'badge bg-success';
            case 'COMPLETED': return 'badge bg-success';
            case 'CANCELLED': return 'badge bg-danger';
            default: return 'badge bg-secondary';
        }
    }

    // --- Delivery Modal Flow ---

    openDeliveryModal() {
        this.deliveryForm.reset();
        this.showDeliveryModal = true;
        this.cdr.detectChanges();
    }

    closeDeliveryModal() {
        this.showDeliveryModal = false;
        this.cdr.detectChanges();
    }

    confirmDelivery() {
        if (!this.sale) return;

        this.isSubmittingDelivery = true;
        const formValue = this.deliveryForm.value;
        const payload = {
            notes: formValue.notes || null,
            evidence_url: formValue.evidence_url || null
        };

        this.saleService.confirmDelivery(this.sale.id, payload).subscribe({
            next: (updated) => {
                this.sale = updated;
                this.isSubmittingDelivery = false;
                this.closeDeliveryModal();
                Swal.fire('Entregado', 'La entrega ha sido confirmada exitosamente.', 'success');
                this.cdr.detectChanges();
            },
            error: (err) => {
                this.isSubmittingDelivery = false;
                this.cdr.detectChanges();
                Swal.fire('Error', err.error?.detail || 'No se pudo confirmar la entrega', 'error');
            }
        });
    }

    // --- Completion Flow ---

    completeSale() {
        if (!this.sale) return;

        Swal.fire({
            title: 'Cerrar Venta',
            text: '¿Marcar esta venta como completada? Esta acción es definitiva.',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, cerrar venta',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.loading = true;
                this.saleService.completeSale(this.sale!.id).subscribe({
                    next: (updated) => {
                        this.sale = updated;
                        this.loading = false;
                        this.cdr.detectChanges();
                        Swal.fire('Completada', 'La venta ha sido cerrada exitosamente.', 'success');
                    },
                    error: (err) => {
                        this.loading = false;
                        this.cdr.detectChanges();
                        Swal.fire('Error', err.error?.detail || 'No se pudo completar la venta', 'error');
                    }
                });
            }
        });
    }
}
