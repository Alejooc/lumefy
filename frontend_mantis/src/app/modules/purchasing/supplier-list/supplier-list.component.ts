import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { SupplierService, Supplier } from '../../../core/services/supplier.service';

@Component({
    selector: 'app-supplier-list',
    standalone: true,
    imports: [CommonModule, RouterModule],
    templateUrl: './supplier-list.component.html',
    styleUrls: ['./supplier-list.component.scss']
})
export class SupplierListComponent implements OnInit {
    private supplierService = inject(SupplierService);
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
            },
            error: (err) => {
                console.error('Error loading suppliers', err);
                this.isLoading = false;
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
