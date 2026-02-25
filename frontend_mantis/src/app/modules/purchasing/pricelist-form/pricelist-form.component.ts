import { Component, OnInit, inject } from '@angular/core';

import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { PriceListItem, PriceListService } from '../../../core/services/pricelist.service';
import { ProductService, Product } from '../../../core/services/product.service';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-pricelist-form',
    standalone: true,
    imports: [ReactiveFormsModule, RouterModule],
    templateUrl: './pricelist-form.component.html',
    styleUrls: ['./pricelist-form.component.scss']
})
export class PriceListFormComponent implements OnInit {
    priceListForm: FormGroup;
    products: Product[] = [];
    isEditMode = false;
    priceListId: string | null = null;
    loading = false;
    error = '';

    private fb = inject(FormBuilder);
    private router = inject(Router);
    private route = inject(ActivatedRoute);
    private priceListService = inject(PriceListService);
    private productService = inject(ProductService);

    constructor() {
        this.priceListForm = this.fb.group({
            name: ['', Validators.required],
            type: ['SALE', Validators.required],
            currency: ['USD', Validators.required],
            active: [true],
            items: this.fb.array([])
        });
    }

    get items() {
        return this.priceListForm.get('items') as FormArray;
    }

    ngOnInit() {
        this.loadProducts();
        this.route.paramMap.subscribe(params => {
            this.priceListId = params.get('id');
            if (this.priceListId) {
                this.isEditMode = true;
                this.loadPriceList(this.priceListId);
            }
        });
    }

    loadProducts() {
        this.productService.getProducts().subscribe(data => this.products = data);
    }

    loadPriceList(id: string) {
        this.priceListService.getPriceList(id).subscribe(pl => {
            this.priceListForm.patchValue({
                name: pl.name,
                type: pl.type,
                currency: pl.currency,
                active: pl.active
            });

            // Load items
            pl.items?.forEach(item => {
                this.items.push(this.createItemGroup(item));
            });
        });
    }

    createItemGroup(item?: PriceListItem): FormGroup {
        return this.fb.group({
            product_id: [item?.product_id || '', Validators.required],
            min_quantity: [item?.min_quantity || 0, [Validators.required, Validators.min(0)]],
            price: [item?.price || 0, [Validators.required, Validators.min(0)]]
        });
    }

    addItem() {
        this.items.push(this.createItemGroup());
    }

    removeItem(index: number) {
        this.items.removeAt(index);
    }

    onSubmit() {
        if (this.priceListForm.invalid) return;

        this.loading = true;
        const formVal = this.priceListForm.value;

        if (this.isEditMode && this.priceListId) {
            this.priceListService.updatePriceList(this.priceListId, {
                name: formVal.name,
                type: formVal.type,
                currency: formVal.currency,
                active: formVal.active
            }).subscribe({
                next: () => {
                    this.loading = false;
                    Swal.fire('Guardado', 'Lista de precios actualizada correctamente.', 'success').then(() => {
                        this.router.navigate(['/purchasing/pricelists']);
                    });
                },
                error: (err) => {
                    this.loading = false;
                    Swal.fire('Error', 'No se pudo actualizar: ' + (err.error?.detail || err.message), 'error');
                }
            });
        } else {
            this.priceListService.createPriceList(formVal).subscribe({
                next: () => {
                    this.loading = false;
                    Swal.fire('Creado', 'Lista de precios creada correctamente.', 'success').then(() => {
                        this.router.navigate(['/purchasing/pricelists']);
                    });
                },
                error: (err) => {
                    this.loading = false;
                    Swal.fire('Error', 'No se pudo crear: ' + (err.error?.detail || err.message), 'error');
                }
            });
        }
    }
}
