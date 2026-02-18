import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { PurchaseService, PurchaseOrder } from '../../../core/services/purchase.service';
import { NgbDropdownModule } from '@ng-bootstrap/ng-bootstrap';
import Swal from 'sweetalert2';
import { ExportService } from '../../../core/services/export.service';

@Component({
    selector: 'app-purchase-list',
    standalone: true,
    imports: [CommonModule, RouterModule, NgbDropdownModule],
    templateUrl: './purchase-list.component.html',
    styleUrls: ['./purchase-list.component.scss']
})
export class PurchaseListComponent implements OnInit {
    private purchaseService = inject(PurchaseService);
    private cdr = inject(ChangeDetectorRef);
    private exportService = inject(ExportService);
    purchases: PurchaseOrder[] = [];
    loading = false;

    ngOnInit() {
        this.loadPurchases();
    }

    loadPurchases() {
        this.loading = true;
        this.cdr.detectChanges();
        this.purchaseService.getPurchases().subscribe({
            next: (data) => {
                this.purchases = data;
                this.loading = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.loading = false;
                this.cdr.detectChanges();
            }
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

    downloadPdf(id: string) {
        this.loading = true;
        this.purchaseService.downloadPdf(id).subscribe({
            next: (blob) => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `OrdenCompra_${id.substring(0, 8)}.pdf`;
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
                Swal.fire('Error', 'Error al descargar el PDF.', 'error');
            }
        });
    }

    exportData(format: 'excel' | 'csv') {
        this.exportService.download('/purchases/export', format);
    }
}
