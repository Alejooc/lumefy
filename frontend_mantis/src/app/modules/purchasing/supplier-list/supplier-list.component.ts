import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';

import { RouterModule } from '@angular/router';
import { SupplierService, Supplier } from '../../../core/services/supplier.service';

@Component({
    selector: 'app-supplier-list',
    standalone: true,
    imports: [RouterModule],
    templateUrl: './supplier-list.component.html',
    styleUrls: ['./supplier-list.component.scss']
})
export class SupplierListComponent implements OnInit {
    private supplierService = inject(SupplierService);
    private cdr = inject(ChangeDetectorRef);
    suppliers: Supplier[] = [];
    isLoading = false;

    ngOnInit() {
        this.loadSuppliers();
    }

    loadSuppliers() {
        this.isLoading = true;
        this.supplierService.getSuppliers().subscribe({
            next: (data) => {
                this.suppliers = data;
                this.isLoading = false;
                this.cdr.detectChanges();
            },
            error: (err) => {
                console.error('Error loading suppliers', err);
                this.isLoading = false;
                this.cdr.detectChanges();
            }
        });
    }

    deleteSupplier(id: string) {
        if (confirm('Are you sure you want to delete this supplier?')) {
            this.supplierService.deleteSupplier(id).subscribe(() => {
                this.loadSuppliers();
            });
        }
    }
}
