import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { PurchaseService } from '../../../core/services/purchase.service';
import { SupplierService, Supplier } from '../../../core/services/supplier.service';
import { ProductService, Product } from '../../../core/services/product.service';
import { PriceListService, PriceList, PriceListItem } from '../../../core/services/pricelist.service';
import { BranchService, Branch } from '../../../core/services/branch.service'; // Assuming exist
import Swal from 'sweetalert2';

@Component({
    selector: 'app-purchase-form',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, RouterModule],
    templateUrl: './purchase-form.component.html',
    styleUrls: ['./purchase-form.component.scss']
})
export class PurchaseFormComponent implements OnInit {
    purchaseForm: FormGroup;
    suppliers: Supplier[] = [];
    products: Product[] = [];
    currentPriceList: PriceList | null = null;
    loading = false;
    error = '';

    private router = inject(Router);
    private fb = inject(FormBuilder);
    private purchaseService = inject(PurchaseService);
    private supplierService = inject(SupplierService);
    private productService = inject(ProductService);
    private priceListService = inject(PriceListService);

    branches: Branch[] = [];
    private branchService = inject(BranchService);

    constructor() {
        this.purchaseForm = this.fb.group({
            supplier_id: ['', Validators.required],
            branch_id: ['', Validators.required], // Required for inventory
            notes: [''],
            expected_date: [''],
            items: this.fb.array([])
        });
    }

    get items() {
        return this.purchaseForm.get('items') as FormArray;
    }

    ngOnInit() {
        this.loadSuppliers();
        this.loadProducts();
        this.loadBranches();

        // Listen for supplier changes
        this.purchaseForm.get('supplier_id')?.valueChanges.subscribe(supplierId => {
            this.handleSupplierChange(supplierId);
        });
    }

    loadBranches() {
        this.branchService.getBranches().subscribe(data => this.branches = data);
    }

    loadSuppliers() {
        this.supplierService.getSuppliers().subscribe(data => this.suppliers = data);
    }

    loadProducts() {
        this.productService.getProducts().subscribe(data => this.products = data);
    }

    handleSupplierChange(supplierId: string) {
        if (!supplierId) {
            this.currentPriceList = null;
            return;
        }

        const supplier = this.suppliers.find(s => s.id === supplierId);
        if (supplier && supplier.price_list_id) {
            this.priceListService.getPriceList(supplier.price_list_id).subscribe({
                next: (pl) => {
                    this.currentPriceList = pl;
                    console.log('Loaded Price List:', pl);
                    // Update existing items
                    this.items.controls.forEach(control => {
                        this.updateItemCost(control as FormGroup);
                    });
                    Swal.fire({
                        toast: true,
                        position: 'top-end',
                        icon: 'info',
                        title: `Lista de precios cargada: ${pl.name}`,
                        showConfirmButton: false,
                        timer: 3000
                    });
                },
                error: (err) => console.error('Failed to load price list', err)
            });
        } else {
            this.currentPriceList = null;
        }
    }

    getCostFromPriceList(productId: string): number | null {
        if (!this.currentPriceList || !this.currentPriceList.items) return null;
        const item = this.currentPriceList.items.find((i: PriceListItem) => i.product_id === productId);
        return item ? item.price : null;
    }

    addItem() {
        const itemGroup = this.fb.group({
            product_id: ['', Validators.required],
            quantity: [1, [Validators.required, Validators.min(1)]],
            unit_cost: [0, [Validators.required, Validators.min(0)]],
            subtotal: [{ value: 0, disabled: true }]
        });

        // Subscribe to changes to update subtotal
        itemGroup.valueChanges.subscribe(val => {
            const q = val.quantity || 0;
            const c = val.unit_cost || 0;
            itemGroup.patchValue({ subtotal: q * c }, { emitEvent: false });
        });

        // Subscribe to product change to update cost
        itemGroup.get('product_id')?.valueChanges.subscribe(productId => {
            if (productId) {
                this.updateItemCost(itemGroup);
            }
        });

        this.items.push(itemGroup);
    }

    updateItemCost(group: FormGroup) {
        const productId = group.get('product_id')?.value;
        if (productId && this.currentPriceList) {
            const cost = this.getCostFromPriceList(productId);
            if (cost !== null) {
                group.patchValue({ unit_cost: cost });
            }
        }
    }

    removeItem(index: number) {
        this.items.removeAt(index);
    }

    get totalAmount() {
        return this.items.controls.reduce((acc, control) => {
            const val = control.value;
            return acc + (val.quantity * val.unit_cost);
        }, 0);
    }

    onSubmit() {
        if (this.purchaseForm.invalid) return;

        // Check items
        if (this.items.length === 0) {
            Swal.fire('Advertencia', 'Por favor agregue al menos un producto.', 'warning');
            return;
        }

        this.loading = true;
        const formVal = this.purchaseForm.value;

        // Prepare payload
        const payload = {
            ...formVal,
            branch_id: formVal.branch_id || null, // Should be filled now
            expected_date: formVal.expected_date || null,
        };

        this.purchaseService.createPurchase(payload).subscribe({
            next: () => {
                this.loading = false;
                Swal.fire('Creada', 'Orden de compra creada exitosamente.', 'success').then(() => {
                    this.router.navigate(['/purchasing/orders']);
                });
            },
            error: (err) => {
                this.loading = false;
                Swal.fire('Error', 'No se pudo crear la orden: ' + (err.error?.detail || err.message), 'error');
            }
        });
    }
}
