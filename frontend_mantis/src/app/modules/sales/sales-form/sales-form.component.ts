import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { SaleService } from '../../../core/services/sale.service';
import { ProductService, Product } from '../../../core/services/product.service';
import { BranchService, Branch } from '../../../core/services/branch.service';
import { ClientService } from '../../clients/client.service';
import { Client } from '../../clients/client.model';
import { SharedModule } from '../../../theme/shared/shared.module';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-sales-form',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, RouterModule, SharedModule],
    templateUrl: './sales-form.component.html',
    styles: [`
        .total-section { font-size: 1.2rem; font-weight: bold; }
        .item-row { border-bottom: 1px solid #eee; padding-bottom: 8px; margin-bottom: 8px; }
        .item-row:last-child { border-bottom: none; }
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

    paymentMethods = [
        { value: 'CASH', label: 'Efectivo' },
        { value: 'CARD', label: 'Tarjeta' },
        { value: 'TRANSFER', label: 'Transferencia' },
        { value: 'CREDIT', label: 'Crédito' },
        { value: 'MIXED', label: 'Mixto' }
    ];

    private fb = inject(FormBuilder);
    private router = inject(Router);
    private route = inject(ActivatedRoute);
    private saleService = inject(SaleService);
    private productService = inject(ProductService);
    private branchService = inject(BranchService);
    private clientService = inject(ClientService);
    private cdr = inject(ChangeDetectorRef);

    constructor() {
        this.saleForm = this.fb.group({
            branch_id: ['', Validators.required],
            client_id: [null],
            status: ['DRAFT'],
            valid_until: [null],
            payment_method: ['CASH'],
            notes: [''],
            shipping_address: [''],
            items: this.fb.array([])
        });
    }

    get items() {
        return this.saleForm.get('items') as FormArray;
    }

    ngOnInit() {
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
        this.productService.getProducts().subscribe({
            next: data => { this.products = data; this.cdr.detectChanges(); },
            error: err => console.error('Error loading products', err)
        });
        this.branchService.getBranches().subscribe({
            next: data => {
                this.branches = data;
                if (data.length === 1) {
                    this.saleForm.patchValue({ branch_id: data[0].id });
                }
                this.cdr.detectChanges();
            },
            error: err => console.error('Error loading branches', err)
        });
        this.clientService.getClients().subscribe({
            next: data => { this.clients = data; this.cdr.detectChanges(); },
            error: err => console.error('Error loading clients', err)
        });
    }

    loadSale(id: string) {
        this.loading = true;
        this.saleService.getSale(id).subscribe({
            next: (sale) => {
                this.saleForm.patchValue({
                    branch_id: sale.branch_id,
                    client_id: sale.client_id || null,
                    status: sale.status,
                    valid_until: sale.valid_until ? sale.valid_until.split('T')[0] : null,
                    payment_method: sale.payment_method || 'CASH',
                    notes: sale.notes || '',
                    shipping_address: sale.shipping_address || ''
                });

                if (sale.items) {
                    sale.items.forEach(item => {
                        this.items.push(this.fb.group({
                            product_id: [item.product_id, Validators.required],
                            quantity: [item.quantity, [Validators.required, Validators.min(0.01)]],
                            price: [item.price, [Validators.required, Validators.min(0)]],
                            discount: [item.discount || 0, [Validators.min(0)]]
                        }));
                    });
                }

                this.loading = false;
                if (sale.status === 'QUOTE') this.isQuote = true;
                this.cdr.detectChanges();
            },
            error: (err) => {
                this.loading = false;
                this.error = 'Error al cargar la venta';
                console.error(err);
                this.cdr.detectChanges();
            }
        });
    }

    addItem() {
        const item = this.fb.group({
            product_id: ['', Validators.required],
            quantity: [1, [Validators.required, Validators.min(0.01)]],
            price: [0, [Validators.required, Validators.min(0)]],
            discount: [0, [Validators.min(0)]]
        });

        // Auto-fill price when product selected
        item.get('product_id')?.valueChanges.subscribe(prodId => {
            const product = this.products.find(p => p.id === prodId);
            if (product) {
                item.patchValue({ price: product.price }, { emitEvent: false });
                this.cdr.detectChanges();
            }
        });

        this.items.push(item);
    }

    removeItem(index: number) {
        this.items.removeAt(index);
    }

    getItemSubtotal(index: number): number {
        const item = this.items.at(index);
        const qty = item.get('quantity')?.value || 0;
        const price = item.get('price')?.value || 0;
        const discount = item.get('discount')?.value || 0;
        return (qty * price) - discount;
    }

    get subtotal(): number {
        let total = 0;
        for (let i = 0; i < this.items.length; i++) {
            total += this.getItemSubtotal(i);
        }
        return total;
    }

    get totalAmount(): number {
        return this.subtotal; // In future: + tax + shipping - discounts
    }

    onSubmit() {
        if (this.saleForm.invalid) {
            // Mark all fields as touched to show validation errors
            this.saleForm.markAllAsTouched();
            Swal.fire('Campos Incompletos', 'Por favor complete los campos requeridos.', 'warning');
            return;
        }

        if (this.items.length === 0) {
            Swal.fire('Sin Productos', 'Debe agregar al menos un producto.', 'warning');
            return;
        }

        this.loading = true;
        const formValue = this.saleForm.value;

        // Build clean payload - sanitize empty strings to null
        const payload: any = {
            branch_id: formValue.branch_id,
            status: formValue.status || 'DRAFT',
            payment_method: formValue.payment_method || null,
            notes: formValue.notes || null,
            shipping_address: formValue.shipping_address || null,
            valid_until: formValue.valid_until || null,
            client_id: formValue.client_id || null,
            items: formValue.items.map((item: any) => ({
                product_id: item.product_id,
                quantity: Number(item.quantity),
                price: Number(item.price),
                discount: Number(item.discount) || 0
            })),
            payments: []
        };

        if (this.isEditMode && this.saleId) {
            this.saleService.updateSale(this.saleId, payload).subscribe({
                next: () => {
                    this.loading = false;
                    Swal.fire('Actualizado', 'Venta actualizada con éxito.', 'success').then(() => {
                        this.router.navigate(['/sales']);
                    });
                },
                error: (err) => {
                    this.loading = false;
                    const detail = err?.error?.detail || 'Error al actualizar la venta.';
                    Swal.fire('Error', detail, 'error');
                    this.cdr.detectChanges();
                }
            });
        } else {
            this.saleService.createSale(payload).subscribe({
                next: () => {
                    this.loading = false;
                    Swal.fire(
                        'Creado',
                        this.isQuote ? 'Cotización creada con éxito.' : 'Orden de venta creada con éxito.',
                        'success'
                    ).then(() => {
                        this.router.navigate(['/sales']);
                    });
                },
                error: (err) => {
                    this.loading = false;
                    const detail = err?.error?.detail || 'Error al crear la venta.';
                    Swal.fire('Error', detail, 'error');
                    this.cdr.detectChanges();
                }
            });
        }
    }
}
