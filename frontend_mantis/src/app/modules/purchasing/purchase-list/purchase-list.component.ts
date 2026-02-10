import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { PurchaseService, PurchaseOrder } from '../../../core/services/purchase.service';

@Component({
    selector: 'app-purchase-list',
    standalone: true,
    imports: [CommonModule, RouterModule],
    templateUrl: './purchase-list.component.html',
    styleUrls: ['./purchase-list.component.scss']
})
export class PurchaseListComponent implements OnInit {
    private purchaseService = inject(PurchaseService);
    purchases: PurchaseOrder[] = [];

    ngOnInit() {
        this.loadPurchases();
    }

    loadPurchases() {
        this.purchaseService.getPurchases().subscribe(data => {
            this.purchases = data;
        });
    }

    getStatusClass(status: string): string {
        switch (status) {
            case 'DRAFT': return 'badge bg-secondary';
            case 'VALIDATION': return 'badge bg-warning text-dark';
            case 'CONFIRMED': return 'badge bg-primary';
            case 'RECEIVED': return 'badge bg-success';
            case 'CANCELLED': return 'badge bg-danger';
            default: return 'badge bg-light text-dark';
        }
    }

    getStatusLabel(status: string): string {
        switch (status) {
            case 'DRAFT': return 'Borrador';
            case 'VALIDATION': return 'Validación';
            case 'CONFIRMED': return 'Confirmada';
            case 'RECEIVED': return 'Recibida';
            case 'CANCELLED': return 'Cancelada';
            default: return status;
        }
    }
}
