import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { PurchaseService, PurchaseOrder } from '../../../core/services/purchase.service';
import { InvoiceService } from '../../../core/services/invoice.service';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-purchase-view',
    standalone: true,
    imports: [CommonModule, RouterModule, FormsModule],
    templateUrl: './purchase-view.component.html',
    styleUrls: ['./purchase-view.component.scss']
})
export class PurchaseViewComponent implements OnInit {
    private cdr = inject(ChangeDetectorRef);

    purchase: PurchaseOrder | null = null;
    loading = false;
    receiveMode = false;
    receiveQuantities: { [itemId: string]: number } = {};
    receiveDetails: { [itemId: string]: { lot_number: string; expiry_date: string; serial_numbers: string } } = {};

    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private purchaseService = inject(PurchaseService);
    private invoiceService = inject(InvoiceService);

    ngOnInit() {
        this.route.paramMap.subscribe(params => {
            const id = params.get('id');
            if (id) this.loadPurchase(id);
        });
    }

    loadPurchase(id: string) {
        this.loading = true;
        this.purchaseService.getPurchase(id).subscribe({
            next: (purchase) => {
                this.purchase = purchase;
                this.loading = false;
                this.cdr.detectChanges();
            },
            error: (err) => {
                console.error(err);
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Error', 'No se pudo cargar la orden', 'error');
            }
        });
    }

    toggleReceiveMode() {
        this.receiveMode = !this.receiveMode;
        if (this.receiveMode && this.purchase?.items) {
            this.receiveQuantities = {};
            this.receiveDetails = {};
            for (const item of this.purchase.items) {
                const remaining = item.quantity - (item.received_qty || 0);
                this.receiveQuantities[item.id!] = remaining > 0 ? remaining : 0;
                this.receiveDetails[item.id!] = { lot_number: '', expiry_date: '', serial_numbers: '' };
            }
        }
    }

    confirmReceive() {
        if (!this.purchase) return;

        const items = Object.entries(this.receiveQuantities)
            .filter((entry) => entry[1] > 0)
            .map(([item_id, qty_received]) => {
                const details = this.receiveDetails[item_id];
                return {
                    item_id,
                    qty_received,
                    lot_number: details?.lot_number || undefined,
                    expiry_date: details?.expiry_date || undefined,
                    serial_numbers: details?.serial_numbers
                        ? details.serial_numbers.split(/[\n,]+/).map(serial => serial.trim()).filter(Boolean)
                        : undefined
                };
            });

        if (items.length === 0) {
            Swal.fire('Aviso', 'No hay cantidades para recibir', 'warning');
            return;
        }

        Swal.fire({
            title: '¿Confirmar Recepción?',
            text: `Se recibirán ${items.length} producto(s). Esto actualizará el inventario.`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, recibir',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.loading = true;
                this.purchaseService.receivePurchase(this.purchase!.id, items).subscribe({
                    next: (updated) => {
                        this.purchase = updated;
                        this.receiveMode = false;
                        this.loading = false;
                        this.cdr.detectChanges();
                        Swal.fire('Recibido', 'La mercancía ha sido registrada exitosamente.', 'success');
                    },
                    error: (err) => {
                        this.loading = false;
                        this.cdr.detectChanges();
                        Swal.fire('Error', err.error?.detail || 'Error al recibir', 'error');
                    }
                });
            }
        });
    }

    getRemainingQty(item: { quantity: number; received_qty?: number }): number {
        return item.quantity - (item.received_qty || 0);
    }

    getReceiveProgress(item: { quantity: number; received_qty?: number }): number {
        if (!item.quantity) return 0;
        return ((item.received_qty || 0) / item.quantity) * 100;
    }

    updateStatus(status: 'VALIDATION' | 'CONFIRMED' | 'CANCELLED') {
        if (!this.purchase) return;

        let confirmText = '';
        let buttonText = '';

        switch (status) {
            case 'VALIDATION': confirmText = '¿Enviar a validación?'; buttonText = 'Sí, enviar'; break;
            case 'CONFIRMED': confirmText = '¿Aprobar y Confirmar Orden?'; buttonText = 'Sí, confirmar'; break;
            case 'CANCELLED': confirmText = '¿Cancelar esta orden?'; buttonText = 'Sí, cancelar'; break;
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
                this.purchaseService.updateStatus(this.purchase!.id, status).subscribe({
                    next: (updated) => {
                        this.purchase = updated;
                        this.loading = false;
                        this.cdr.detectChanges();
                        Swal.fire('Actualizado', 'El estado de la orden ha sido actualizado.', 'success');
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

    createSupplierInvoice() {
        if (!this.purchase) return;
        this.loading = true;
        this.invoiceService.createFromSource({ type: 'PURCHASE', purchase_id: this.purchase.id }).subscribe({
            next: (invoice) => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Factura de proveedor creada', `${invoice.number} quedó en borrador.`, 'success')
                    .then(() => this.router.navigate(['/invoices']));
            },
            error: (error) => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('No se pudo crear la factura', error?.error?.detail || 'Intenta de nuevo.', 'error');
            }
        });
    }
}
