import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
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
    private cdr = inject(ChangeDetectorRef);

    branches: Branch[] = [];
    private branchService = inject(BranchService);

    priceLists: PriceList[] = [];

    constructor() {
        this.purchaseForm = this.fb.group({
            supplier_id: ['', Validators.required],
            branch_id: ['', Validators.required],
            price_list_id: [''], // Optional, overrides supplier default
            notes: [''],
            expected_date: [''],
            items: this.fb.array([])
        });
    }

    get items() {
        return this.purchaseForm.get('items') as FormArray;
    }

    private route = inject(ActivatedRoute); // Inject route

    ngOnInit() {
        this.loading = true;

        // Listen for changes first
        this.purchaseForm.get('supplier_id')?.valueChanges.subscribe(supplierId => {
            this.handleSupplierChange(supplierId);
        });

        this.purchaseForm.get('price_list_id')?.valueChanges.subscribe(plId => {
            if (plId) this.handlePriceListChange(plId);
        });

        this.loadDependencies();
    }

    loadDependencies() {
        this.loading = true;
        // Parallel requests
        this.supplierService.getSuppliers().subscribe({
            next: d => this.suppliers = d,
            error: e => console.error('Suppliers error', e)
        });
        this.productService.getProducts().subscribe({
            next: d => this.products = d,
            error: e => console.error('Products error', e)
        });
        this.branchService.getBranches().subscribe({
            next: d => this.branches = d,
            error: e => console.error('Branches error', e)
        });
        this.priceListService.getPriceLists().subscribe({
            next: d => {
                this.priceLists = d;
                this.loading = false; // Turn off loading when at least one finishes or lazily?
                // Actually proper way is forkJoin.
                this.cdr.detectChanges();
            },
            error: e => {
                console.error('PriceLists error', e);
                this.cdr.detectChanges();
            },
            complete: () => {
                this.loading = false;
                this.cdr.detectChanges();
            }
        });

        // Timeout safety
        setTimeout(() => this.loading = false, 3000);
    }

    loadBranches() {
        this.branchService.getBranches().subscribe(data => this.branches = data);
    }

    loadPriceLists() {
        this.priceListService.getPriceLists().subscribe(data => this.priceLists = data);
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
            this.purchaseForm.patchValue({ price_list_id: '' });
            return;
        }

        const supplier = this.suppliers.find(s => s.id === supplierId);
        if (supplier && supplier.price_list_id) {
            // Auto-select supplier's price list
            this.purchaseForm.patchValue({ price_list_id: supplier.price_list_id });
            // The valueChanges on price_list_id will trigger handlePriceListChange
        } else {
            this.currentPriceList = null;
            this.purchaseForm.patchValue({ price_list_id: '' });
        }
    }

    handlePriceListChange(priceListId: string) {
        this.priceListService.getPriceList(priceListId).subscribe({
            next: (pl) => {
                this.currentPriceList = pl;
                // Update existing items
                this.items.controls.forEach(control => {
                    this.updateItemCost(control as FormGroup);
                });
                Swal.fire({
                    toast: true,
                    position: 'top-end',
                    icon: 'info',
                    title: `Lista de precios aplicada: ${pl.name}`,
                    showConfirmButton: false,
                    timer: 2000
                });
            },
            error: (err) => console.error('Failed to load price list', err)
        });
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
            branch_id: formVal.branch_id || null,
            expected_date: formVal.expected_date || null,
            supplier_id: formVal.supplier_id || null,
            price_list_id: formVal.price_list_id || null,
        };

        this.purchaseService.createPurchase(payload).subscribe({
            next: () => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Creada', 'Orden de compra criada exitosamente.', 'success').then(() => {
                    this.router.navigate(['/purchasing/orders']);
                });
            },
            error: (err) => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Error', 'No se pudo crear la orden: ' + (err.error?.detail || err.message), 'error');
            }
        });
    }
}
