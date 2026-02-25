import { Component, OnInit, inject } from '@angular/core';

import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { SupplierService } from '../../../core/services/supplier.service';
import { PriceListService, PriceList } from '../../../core/services/pricelist.service';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-supplier-form',
    standalone: true,
    imports: [ReactiveFormsModule, RouterModule],
    templateUrl: './supplier-form.component.html',
    styleUrls: ['./supplier-form.component.scss']
})
export class SupplierFormComponent implements OnInit {
    supplierForm: FormGroup;
    priceLists: PriceList[] = [];
    isEditMode = false;
    supplierId: string | null = null;
    loading = false;
    error = '';

    private router = inject(Router);
    private route = inject(ActivatedRoute);
    private fb = inject(FormBuilder);
    private supplierService = inject(SupplierService);
    private priceListService = inject(PriceListService);

    constructor() {
        this.supplierForm = this.fb.group({
            name: ['', Validators.required],
            email: ['', [Validators.email]],
            phone: [''],
            address: [''],
            tax_id: [''],
            price_list_id: [null]
        });
    }

    ngOnInit() {
        this.loadPriceLists();
        this.route.paramMap.subscribe(params => {
            this.supplierId = params.get('id');
            if (this.supplierId) {
                this.isEditMode = true;
                this.loadSupplier(this.supplierId);
            }
        });
    }

    loadPriceLists() {
        this.priceListService.getPriceLists('PURCHASE').subscribe(data => this.priceLists = data);
    }

    loadSupplier(id: string) {
        this.supplierService.getSuppliers().subscribe(suppliers => {
            const supplier = suppliers.find(s => s.id === id);
            if (supplier) {
                this.supplierForm.patchValue(supplier);
            } else {
                this.error = 'Supplier not found';
            }
        });
    }

    onSubmit() {
        if (this.supplierForm.invalid) return;

        this.loading = true;
        const supplierData = this.supplierForm.value;

        if (this.isEditMode && this.supplierId) {
            this.supplierService.updateSupplier(this.supplierId, supplierData).subscribe({
                next: () => {
                    this.loading = false;
                    Swal.fire('Actualizado', 'Proveedor actualizado correctamente.', 'success').then(() => {
                        this.router.navigate(['/purchasing/suppliers']);
                    });
                },
                error: (err) => {
                    this.loading = false;
                    Swal.fire('Error', 'Error al actualizar proveedor: ' + (err.error?.detail || err.message), 'error');
                }
            });
        } else {
            this.supplierService.createSupplier(supplierData).subscribe({
                next: () => {
                    this.loading = false;
                    Swal.fire('Creado', 'Proveedor creado correctamente.', 'success').then(() => {
                        this.router.navigate(['/purchasing/suppliers']);
                    });
                },
                error: (err) => {
                    this.loading = false;
                    Swal.fire('Error', 'Error al crear proveedor: ' + (err.error?.detail || err.message), 'error');
                }
            });
        }
    }
}