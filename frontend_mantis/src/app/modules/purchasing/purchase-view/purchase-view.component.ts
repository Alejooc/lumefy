import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { PurchaseService, PurchaseOrder } from '../../../core/services/purchase.service';
import { Branch } from '../../../core/services/branch.service';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-purchase-view',
    standalone: true,
    imports: [CommonModule, RouterModule],
    templateUrl: './purchase-view.component.html',
    styleUrls: ['./purchase-view.component.scss']
})
export class PurchaseViewComponent implements OnInit {
    purchase: PurchaseOrder | null = null;
    loading = false;

    private route = inject(ActivatedRoute);
    private purchaseService = inject(PurchaseService);

    ngOnInit() {
        this.route.paramMap.subscribe(params => {
            const id = params.get('id');
            if (id) this.loadPurchase(id);
        });
    }

    loadPurchase(id: string) {
        // Ideally get by ID. List gets all. 
        // Optimization: create getPurchase(id) in service. 
        // Fallback: get all and find. 
        this.loading = true;
        this.purchaseService.getPurchases().subscribe(purchases => {
            this.purchase = purchases.find(p => p.id === id) || null; // Not efficient but works for now
            this.loading = false;
        });
    }

    updateStatus(status: 'VALIDATION' | 'CONFIRMED' | 'RECEIVED' | 'CANCELLED') {
        if (!this.purchase) return;

        // Check for Branch ID if receiving
        if (status === 'RECEIVED' && !this.purchase.branch_id) {
            Swal.fire('Error', 'No se puede recibir una orden sin una Sucursal de destino. Por favor edite la orden o agregue una sucursal.', 'error');
            return;
        }

        let confirmText = '';
        let buttonText = '';

        switch (status) {
            case 'VALIDATION': confirmText = '¿Enviar a validación?'; buttonText = 'Sí, enviar'; break;
            case 'CONFIRMED': confirmText = '¿Aprobar y Confirmar Orden?'; buttonText = 'Sí, confirmar'; break;
            case 'RECEIVED': confirmText = '¿Confirmar recepción de mercancía? Esto aumentará el stock.'; buttonText = 'Sí, recibir'; break;
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
                        Swal.fire('Actualizado', 'El estado de la orden ha sido actualizado.', 'success');
                    },
                    error: (err) => {
                        this.loading = false;
                        Swal.fire('Error', 'No se pudo actualizar el estado: ' + (err.error?.detail || err.message), 'error');
                    }
                });
            }
        });
    }
}
