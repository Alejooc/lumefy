import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { SaleService } from '../../../core/services/sale.service';
import { ProductService, Product } from '../../../core/services/product.service';
import { BranchService, Branch } from '../../../core/services/branch.service';
import { ClientService } from '../../clients/client.service';
import { Client } from '../../clients/client.model';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-sales-form',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, RouterModule],
    templateUrl: './sales-form.component.html',
    styles: [`
        .total-section { font-size: 1.2rem; font-weight: bold; }
    `]
})
export class SalesFormComponent implements OnInit {
    saleForm: FormGroup;
    products: Product[] = [];
    branches: Branch[] = [];
    clients: Client[] = [];
    loading = false;
    error = '';
    isEditMode = false;
    saleId: string | null = null;
    isQuote = false;

    private fb = inject(FormBuilder);
    private router = inject(Router);
    private route = inject(ActivatedRoute);
    private saleService = inject(SaleService);
    private productService = inject(ProductService);
    private branchService = inject(BranchService);
    private clientService = inject(ClientService);

    constructor() {
        this.saleForm = this.fb.group({
            branch_id: ['', Validators.required],
            client_id: [''], // Optional?
            status: ['DRAFT'],
            valid_until: [''], // For quotes
            payment_method: ['CASH'], // Default
            notes: [''],
            shipping_address: [''],
            items: this.fb.array([])
        });
    }

    get items() {
        return this.saleForm.get('items') as FormArray;
    }

    ngOnInit() {
        // Determine mode based on URL
        const url = this.router.url;
        if (url.includes('quote')) {
            this.isQuote = true;
            this.saleForm.patchValue({ status: 'QUOTE' });
        }

        this.loadDependencies();

        this.route.paramMap.subscribe(params => {
            const id = params.get('id');
            if (id) {
                this.isEditMode = true;
                this.saleId = id;
                this.loadSale(id);
            } else {
                this.addItem();
            }
        });
    }

    loadDependencies() {
        this.productService.getProducts().subscribe(data => this.products = data);
        this.branchService.getBranches().subscribe(data => this.branches = data);
        this.clientService.getClients().subscribe(data => this.clients = data);
    }

    loadSale(id: string) {
        this.loading = true;
        this.saleService.getSale(id).subscribe({
            next: (sale) => {
                this.saleForm.patchValue({
                    branch_id: sale.branch_id,
                    client_id: sale.client_id,
                    status: sale.status,
                    valid_until: sale.valid_until ? sale.valid_until.split('T')[0] : '', // Format date
                    payment_method: sale.payment_method,
                    notes: sale.notes,
                    shipping_address: sale.shipping_address
                });

                // Load items
                if (sale.items) {
                    sale.items.forEach(item => {
                        this.items.push(this.fb.group({
                            product_id: [item.product_id, Validators.required],
                            quantity: [item.quantity, [Validators.required, Validators.min(1)]],
                            price: [item.price, [Validators.required, Validators.min(0)]],
                            discount: [item.discount || 0, [Validators.min(0)]],
                            subtotal: [{ value: item.total, disabled: true }]
                        }));
                    });
                    this.calculateTotal();
                }

                this.loading = false;
                if (sale.status === 'QUOTE') this.isQuote = true;
            },
            error: (err) => {
                this.loading = false;
                this.error = 'Error loading sale';
                console.error(err);
            }
        });
    }

    addItem() {
        const item = this.fb.group({
            product_id: ['', Validators.required],
            quantity: [1, [Validators.required, Validators.min(1)]],
            price: [0, [Validators.required, Validators.min(0)]],
            discount: [0, [Validators.min(0)]],
            subtotal: [{ value: 0, disabled: true }]
        });

        // Listen for changes to update subtotal
        item.valueChanges.subscribe(() => {
            this.updateItemSubtotal(item);
            this.calculateTotal();
        });

        // Auto-fill price when product selected
        item.get('product_id')?.valueChanges.subscribe(prodId => {
            const product = this.products.find(p => p.id === prodId);
            if (product) {
                item.patchValue({ price: product.price }, { emitEvent: false }); // No event to avoid loop
                this.updateItemSubtotal(item);
                this.calculateTotal();
            }
        });

        this.items.push(item);
    }

    removeItem(index: number) {
        this.items.removeAt(index);
        this.calculateTotal();
    }

    updateItemSubtotal(group: any) {
        const qty = group.get('quantity')?.value || 0;
        const price = group.get('price')?.value || 0;
        const discount = group.get('discount')?.value || 0;
        const subtotal = (qty * price) - discount;
        group.get('subtotal')?.setValue(subtotal, { emitEvent: false });
    }

    get totalAmount(): number {
        return this.items.controls.reduce((acc, control) => {
            return acc + (control.get('subtotal')?.value || 0);
        }, 0);
    }

    calculateTotal() {
        // Triggered by subscriptions
    }

    onSubmit() {
        if (this.saleForm.invalid) {
            Swal.fire('Error', 'Por favor complete el formulario correctamente.', 'warning');
            return;
        }

        if (this.items.length === 0) {
            Swal.fire('Error', 'Debe agregar al menos un producto.', 'warning');
            return;
        }

        this.loading = true;
        const formValue = this.saleForm.getRawValue(); // To get values including disabled fields if any (though we used valueChanges)

        // Prepare payload (items map to SaleItemCreate)
        const payload = {
            ...formValue,
            items: formValue.items.map((item: any) => ({
                product_id: item.product_id,
                quantity: item.quantity,
                price: item.price,
                discount: item.discount
            }))
        };

        if (this.isEditMode && this.saleId) {
            // Update logic (Not implemented fully in backend yet? Backend separate update_sale content vs status)
            // Assuming update endpoint exists or just block edit for now?
            // Actually sales.py has create and update_status. It misses update content.
            // For now, let's just show alert.
            Swal.fire('Info', 'La edición de contenido no está completamente soportada en el backend aún. Solo cambio de estado.', 'info');
            this.loading = false;
        } else {
            this.saleService.createSale(payload).subscribe({
                next: (res) => {
                    this.loading = false;
                    Swal.fire('Creado', this.isQuote ? 'Cotización creada con éxito.' : 'Orden de venta creada con éxito.', 'success').then(() => {
                        this.router.navigate(['/sales']);
                    });
                },
                error: (err) => {
                    this.loading = false;
                    Swal.fire('Error', 'Error al crear venta: ' + (err.error?.detail || err.message), 'error');
                }
            });
        }
    }
}
