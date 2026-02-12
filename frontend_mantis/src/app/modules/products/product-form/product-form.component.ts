import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { SharedModule } from '../../../theme/shared/shared.module';
import { CategoryService, Category } from '../../categories/category.service';
import Swal from 'sweetalert2';

interface Brand { id: string; name: string; }
interface UnitOfMeasure { id: string; name: string; abbreviation?: string; }

@Component({
    selector: 'app-product-form',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, RouterModule, SharedModule],
    templateUrl: './product-form.component.html',
    styleUrls: ['./product-form.component.scss']
})
export class ProductFormComponent implements OnInit {
    form: FormGroup;
    isEditMode = false;
    productId: string | null = null;
    isLoading = false;
    activeTab = 'general';

    categories: Category[] = [];
    brands: Brand[] = [];
    units: UnitOfMeasure[] = [];

    productTypes = [
        { value: 'STORABLE', label: 'Almacenable' },
        { value: 'CONSUMABLE', label: 'Consumible' },
        { value: 'SERVICE', label: 'Servicio' }
    ];

    private fb = inject(FormBuilder);
    private api = inject(ApiService);
    private categoryService = inject(CategoryService);
    private router = inject(Router);
    private route = inject(ActivatedRoute);
    private cdr = inject(ChangeDetectorRef);

    constructor() {
        this.form = this.fb.group({
            // General
            name: ['', Validators.required],
            internal_reference: [''],
            sku: [''],
            barcode: [''],
            description: [''],
            image_url: [''],
            product_type: ['STORABLE'],

            // Classification
            category_id: [null],
            brand_id: [null],

            // Pricing
            price: [0, [Validators.required, Validators.min(0)]],
            cost: [0, [Validators.min(0)]],
            tax_rate: [0, [Validators.min(0), Validators.max(100)]],

            // Physical
            weight: [null],
            volume: [null],
            unit_of_measure_id: [null],
            purchase_uom_id: [null],

            // Inventory
            track_inventory: [true],
            min_stock: [0],
            sale_ok: [true],
            purchase_ok: [true],

            // Variants
            variants: this.fb.array([])
        });
    }

    get variants(): FormArray {
        return this.form.get('variants') as FormArray;
    }

    ngOnInit(): void {
        this.loadCategories();
        this.loadBrands();
        this.loadUnits();

        this.productId = this.route.snapshot.paramMap.get('id');
        if (this.productId) {
            this.isEditMode = true;
            this.loadProduct(this.productId);
        }
    }

    loadCategories() {
        this.categoryService.getCategories().subscribe({
            next: (data) => { this.categories = data; this.cdr.detectChanges(); },
            error: (err) => console.error('Error loading categories', err)
        });
    }

    loadBrands() {
        this.api.get<Brand[]>('/brands').subscribe({
            next: (data) => { this.brands = data; this.cdr.detectChanges(); },
            error: (err) => console.error('Error loading brands', err)
        });
    }

    loadUnits() {
        this.api.get<UnitOfMeasure[]>('/units-of-measure').subscribe({
            next: (data) => { this.units = data; this.cdr.detectChanges(); },
            error: (err) => console.error('Error loading units', err)
        });
    }

    loadProduct(id: string) {
        this.isLoading = true;
        this.api.get<any>(`/products/${id}`).subscribe({
            next: (data) => {
                // Patch main form (exclude variants)
                const { variants, ...productData } = data;
                this.form.patchValue(productData);

                // Load existing variants
                if (variants && variants.length > 0) {
                    variants.forEach((v: any) => {
                        this.variants.push(this.fb.group({
                            id: [v.id],
                            name: [v.name, Validators.required],
                            sku: [v.sku || ''],
                            barcode: [v.barcode || ''],
                            price_extra: [v.price_extra || 0],
                            cost_extra: [v.cost_extra || 0],
                            weight: [v.weight]
                        }));
                    });
                }

                this.isLoading = false;
                this.cdr.detectChanges();
            },
            error: (err) => {
                console.error(err);
                this.isLoading = false;
                Swal.fire('Error', 'No se pudo cargar el producto', 'error');
                this.router.navigate(['/products']);
            }
        });
    }

    addVariant() {
        this.variants.push(this.fb.group({
            id: [null],
            name: ['', Validators.required],
            sku: [''],
            barcode: [''],
            price_extra: [0],
            cost_extra: [0],
            weight: [null]
        }));
    }

    removeVariant(index: number) {
        const variant = this.variants.at(index).value;
        if (variant.id && this.productId) {
            // Delete from server
            this.api.delete(`/products/${this.productId}/variants/${variant.id}`).subscribe({
                next: () => {
                    this.variants.removeAt(index);
                    this.cdr.detectChanges();
                },
                error: (err: any) => Swal.fire('Error', 'No se pudo eliminar la variante', 'error')
            });
        } else {
            this.variants.removeAt(index);
        }
    }

    setTab(tab: string) {
        this.activeTab = tab;
    }

    onSubmit() {
        if (this.form.invalid) {
            this.form.markAllAsTouched();
            return;
        }

        this.isLoading = true;
        const formData = { ...this.form.getRawValue() };

        // Sanitize empty strings to null for UUID fields
        ['category_id', 'brand_id', 'unit_of_measure_id', 'purchase_uom_id'].forEach(f => {
            if (formData[f] === '' || formData[f] === undefined) formData[f] = null;
        });

        // Handle variants separately
        const variantsToSave = formData.variants || [];
        delete formData.variants;

        const request = this.isEditMode
            ? this.api.put(`/products/${this.productId}`, formData)
            : this.api.post('/products', formData);

        request.subscribe({
            next: (product: any) => {
                const productId = product.id || this.productId;

                // Save new variants (only for edit mode or after create)
                if (this.isEditMode && variantsToSave.length > 0) {
                    this.saveVariants(productId, variantsToSave);
                } else {
                    this.isLoading = false;

                    if (!this.isEditMode && variantsToSave.length > 0) {
                        // After create, save variants
                        this.saveVariantsAfterCreate(productId, variantsToSave);
                    } else {
                        Swal.fire('Éxito', this.isEditMode ? 'Producto actualizado' : 'Producto creado', 'success');
                        this.router.navigate(['/products']);
                    }
                }
            },
            error: (err) => {
                console.error(err);
                this.isLoading = false;
                Swal.fire('Error', err.error?.detail || 'No se pudo guardar el producto', 'error');
            }
        });
    }

    private saveVariantsAfterCreate(productId: string, variants: any[]) {
        const newVariants = variants.filter((v: any) => !v.id);
        if (newVariants.length === 0) {
            Swal.fire('Éxito', 'Producto creado', 'success');
            this.router.navigate(['/products']);
            return;
        }

        let completed = 0;
        newVariants.forEach((v: any) => {
            const { id, ...variantData } = v;
            this.api.post(`/products/${productId}/variants`, variantData).subscribe({
                next: () => {
                    completed++;
                    if (completed === newVariants.length) {
                        this.isLoading = false;
                        Swal.fire('Éxito', 'Producto creado con variantes', 'success');
                        this.router.navigate(['/products']);
                    }
                },
                error: () => { completed++; }
            });
        });
    }

    private saveVariants(productId: string, variants: any[]) {
        const newVariants = variants.filter((v: any) => !v.id);
        const existingVariants = variants.filter((v: any) => v.id);

        let total = newVariants.length + existingVariants.length;
        let completed = 0;

        if (total === 0) {
            this.isLoading = false;
            Swal.fire('Éxito', 'Producto actualizado', 'success');
            this.router.navigate(['/products']);
            return;
        }

        const checkDone = () => {
            completed++;
            if (completed === total) {
                this.isLoading = false;
                Swal.fire('Éxito', 'Producto actualizado', 'success');
                this.router.navigate(['/products']);
            }
        };

        // Create new
        newVariants.forEach((v: any) => {
            const { id, ...variantData } = v;
            this.api.post(`/products/${productId}/variants`, variantData).subscribe({
                next: checkDone,
                error: checkDone
            });
        });

        // Update existing
        existingVariants.forEach((v: any) => {
            const { id, ...variantData } = v;
            this.api.put(`/products/${productId}/variants/${id}`, variantData).subscribe({
                next: checkDone,
                error: checkDone
            });
        });
    }

    getMargin(): number {
        const price = this.form.get('price')?.value || 0;
        const cost = this.form.get('cost')?.value || 0;
        if (price === 0) return 0;
        return ((price - cost) / price) * 100;
    }
}
