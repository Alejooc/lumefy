import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { SharedModule } from '../../../theme/shared/shared.module';
import { CategoryService, Category } from '../../categories/category.service';

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
    categories: Category[] = [];

    constructor(
        private fb: FormBuilder,
        private apiService: ApiService,
        private categoryService: CategoryService,
        private router: Router,
        private route: ActivatedRoute
    ) {
        this.form = this.fb.group({
            name: ['', Validators.required],
            sku: [''],
            barcode: [''],
            category_id: [null],
            price: [0, [Validators.required, Validators.min(0)]],
            cost: [0, [Validators.min(0)]],
            check_inventory: [true],
            min_stock: [0]
        });
    }

    ngOnInit(): void {
        this.loadCategories();
        this.productId = this.route.snapshot.paramMap.get('id');
        if (this.productId) {
            this.isEditMode = true;
            this.loadProduct(this.productId);
        }
    }

    loadCategories() {
        this.categoryService.getCategories().subscribe({
            next: (data) => this.categories = data,
            error: (err) => console.error('Error loading categories', err)
        });
    }

    loadProduct(id: string) {
        this.isLoading = true;
        this.apiService.get<any>(`/products/${id}`).subscribe({
            next: (data) => {
                this.form.patchValue(data);
                this.isLoading = false;
            },
            error: (err) => {
                console.error(err);
                this.isLoading = false;
            }
        });
    }

    onSubmit() {
        if (this.form.invalid) return;

        this.isLoading = true;
        const data = this.form.value;

        const request = this.isEditMode
            ? this.apiService.put(`/products/${this.productId}`, data)
            : this.apiService.post('/products', data);

        request.subscribe({
            next: () => {
                this.router.navigate(['/products']);
            },
            error: (err) => {
                console.error(err);
                this.isLoading = false;
                // Handle error (show toast?)
            }
        });
    }
}
